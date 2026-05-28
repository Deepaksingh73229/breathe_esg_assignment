"""
Ingestion Pipeline Orchestrator.

This module is the conductor that coordinates the entire data flow:
  1. Receive uploaded file
  2. Validate file structure
  3. Parse into RawDataRows (immutable source of truth)
  4. Normalise into ActivityRecords (reviewable golden records)
  5. Calculate CO2e using EmissionCalculator
  6. Update IngestionRun statistics

Transaction Strategy
--------------------
We use a two-level transaction approach:

  Outer transaction  → wraps the IngestionRun status update only.
  Per-row savepoint  → each row is wrapped in a database savepoint.
                       If a single row's DB operations fail, only THAT
                       row's savepoint is rolled back; the rest survive.

This means: 1 000 valid rows + 1 corrupted row = 999 ActivityRecords created,
1 raw row marked invalid. Without this, the whole batch would roll back.

Error Handling
--------------
  File-level errors (malformed CSV)  → IngestionRun.status = "failed"
  Row-level hard errors              → RawDataRow.parsed_status = "invalid"
  Row-level warnings                 → RawDataRow.parsed_status = "suspicious",
                                       ActivityRecord still created
"""
from datetime import date
from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

from apps.ingestion.models import IngestionRun, RawDataRow
from apps.ingestion.parsers.base import BaseParser
from apps.ingestion.parsers.sap_parser import SAPParser
from apps.ingestion.parsers.utility_parser import UtilityParser
from apps.ingestion.parsers.travel_parser import TravelParser
from apps.activities.models import ActivityRecord
from apps.activities.services.calculator import EmissionCalculator, FactorLookupError
from apps.facilities.models import Facility


# Maps source_type string → parser class
PARSER_REGISTRY: Dict[str, type] = {
    "sap": SAPParser,
    "utility": UtilityParser,
    "travel": TravelParser,
}


def _coerce_date(value) -> Optional[date]:
    """
    Normalise a date value that may be a datetime.date, datetime.datetime, or ISO string.

    Parsers are inconsistent: SAP parser returns date objects, utility parser
    returns date objects too (after the fix), travel parser may return either.
    This function ensures the ActivityRecord always receives a date object.
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if hasattr(value, "date"):
        # datetime → date
        return value.date()
    # Assume ISO string "YYYY-MM-DD"
    try:
        from datetime import datetime
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


class IngestionPipeline:
    """
    Main orchestrator for the data ingestion pipeline.

    Usage:
        pipeline = IngestionPipeline()
        result = pipeline.process(ingestion_run, file_obj)
    """

    def __init__(self):
        self.calculator = EmissionCalculator()

    def process(self, ingestion_run: IngestionRun, file_obj) -> Dict[str, Any]:
        """
        Process a single ingestion run end-to-end.

        The outer method is NOT @transaction.atomic because we want partial
        successes to persist. Each row uses a savepoint instead.

        Returns a dict with ingestion statistics.
        """
        organization = ingestion_run.organization
        source_type = ingestion_run.source_type

        # Compute and store file SHA-256 checksum (for tamper evidence)
        ingestion_run.compute_checksum()

        # Get parser
        parser_class = PARSER_REGISTRY.get(source_type)
        if not parser_class:
            raise ValueError(
                f"Unknown source_type '{source_type}'. "
                f"Supported: {list(PARSER_REGISTRY.keys())}"
            )

        parser: BaseParser = parser_class(organization, ingestion_run)

        # File-level validation
        file_obj.seek(0)
        if not parser.validate_file(file_obj):
            with transaction.atomic():
                ingestion_run.status = "failed"
                ingestion_run.error_summary = {
                    "file_validation": (
                        f"File structure does not match expected format for source_type '{source_type}'."
                    )
                }
                ingestion_run.save(update_fields=["status", "error_summary"])
            return {
                "status": "failed",
                "reason": "File validation failed",
                "total_rows": 0, "valid_rows": 0,
                "invalid_rows": 0, "suspicious_rows": 0,
            }

        # ── Row-by-row processing ─────────────────────────────────────────────
        stats = {
            "total_rows": 0,
            "valid_rows": 0,
            "invalid_rows": 0,
            "suspicious_rows": 0,
            "errors_by_type": {},
        }
        period_starts = []
        period_ends = []

        file_obj.seek(0)
        for parse_result in parser.parse_rows(file_obj):
            stats["total_rows"] += 1

            # Each row wrapped in a savepoint so a DB error on row N doesn't
            # roll back rows 1..(N-1).
            try:
                with transaction.atomic():
                    # RawDataRow is created for every row — even invalid ones.
                    # This preserves the complete source record for audit.
                    raw_row = RawDataRow.objects.create(
                        organization=organization,
                        ingestion_run=ingestion_run,
                        source_row_number=stats["total_rows"],
                        raw_payload=parse_result.raw_payload,
                        parsed_status=parse_result.status,
                        parse_errors=parse_result.errors,
                        source_identifier=parse_result.normalized_data.get("source_identifier", ""),
                    )

                    # Aggregate error types for the dashboard
                    for msg in parse_result.errors:
                        key = msg.split(".")[0][:60]
                        stats["errors_by_type"][key] = stats["errors_by_type"].get(key, 0) + 1

                    if parse_result.status == "skipped":
                        continue

                    if parse_result.status == "invalid":
                        stats["invalid_rows"] += 1
                        continue

                    # "valid" and "suspicious" → create ActivityRecord
                    activity = self._create_activity_record(
                        ingestion_run, raw_row, parse_result.normalized_data, organization
                    )

                    if activity:
                        # Link back RawDataRow → ActivityRecord
                        raw_row.activity_record = activity
                        raw_row.raw_period_start = activity.period_start
                        raw_row.raw_period_end = activity.period_end
                        raw_row.save(update_fields=[
                            "activity_record", "raw_period_start", "raw_period_end"
                        ])

                        if parse_result.status == "valid":
                            stats["valid_rows"] += 1
                        else:
                            stats["suspicious_rows"] += 1

                        if activity.period_start:
                            period_starts.append(activity.period_start)
                        if activity.period_end:
                            period_ends.append(activity.period_end)

            except Exception as row_exc:
                # The savepoint was rolled back; continue with next row.
                stats["invalid_rows"] += 1
                key = f"unexpected_row_error: {str(row_exc)[:50]}"
                stats["errors_by_type"][key] = stats["errors_by_type"].get(key, 0) + 1

        # ── Update IngestionRun with final statistics ─────────────────────────
        with transaction.atomic():
            total = stats["total_rows"]
            invalid = stats["invalid_rows"]

            if invalid == total and total > 0:
                ingestion_run.status = "failed"
            elif invalid > 0:
                ingestion_run.status = "partial"
            else:
                ingestion_run.status = "parsed"

            ingestion_run.total_rows = total
            ingestion_run.valid_rows = stats["valid_rows"]
            ingestion_run.invalid_rows = invalid
            ingestion_run.suspicious_rows = stats["suspicious_rows"]
            ingestion_run.error_summary = stats["errors_by_type"]

            if period_starts:
                ingestion_run.period_start = min(period_starts)
            if period_ends:
                ingestion_run.period_end = max(period_ends)

            ingestion_run.save()

        return {
            "status": ingestion_run.status,
            "ingestion_run_id": str(ingestion_run.id),
            "total_rows": stats["total_rows"],
            "valid_rows": stats["valid_rows"],
            "invalid_rows": stats["invalid_rows"],
            "suspicious_rows": stats["suspicious_rows"],
            "errors_by_type": stats["errors_by_type"],
        }

    def _create_activity_record(
        self,
        ingestion_run: IngestionRun,
        raw_row: RawDataRow,
        normalized: Dict[str, Any],
        organization,
    ) -> Optional[ActivityRecord]:
        """
        Build and save an ActivityRecord from normalised parser output.

        All dates are coerced to datetime.date objects here to ensure
        consistent types regardless of which parser produced the data.
        """
        try:
            # Resolve Facility
            facility = None
            facility_id = normalized.get("facility_id")
            if facility_id:
                try:
                    facility = Facility.objects.get(id=facility_id, organization=organization)
                except Facility.DoesNotExist:
                    pass

            # Coerce dates (parsers may return date objects or ISO strings)
            period_start = _coerce_date(normalized.get("period_start"))
            period_end = _coerce_date(normalized.get("period_end"))

            if not period_start or not period_end:
                raw_row.parsed_status = "invalid"
                raw_row.parse_errors = list(raw_row.parse_errors) + [
                    "Missing period_start or period_end — ActivityRecord not created."
                ]
                raw_row.save(update_fields=["parsed_status", "parse_errors"])
                return None

            # Fields that must not go into metadata (they have proper model columns)
            STRUCTURED_FIELDS = {
                "facility_id", "facility_name", "source_identifier", "scope",
                "scope_3_category", "activity_type", "activity_amount", "activity_unit",
                "period_start", "period_end", "country", "region", "fuel_type",
                "original_amount", "original_unit", "conversion_note", "distance_band",
                "travel_class", "origin_airport", "destination_airport",
                "origin_station", "destination_station", "is_estimated",
                "account_number",
            }

            activity = ActivityRecord(
                organization=organization,
                ingestion_run=ingestion_run,
                raw_data_row=raw_row,
                source_system=ingestion_run.source_type,
                source_identifier=normalized.get("source_identifier", ""),
                facility=facility,
                scope=normalized.get("scope", ""),
                scope_3_category=normalized.get("scope_3_category", ""),
                activity_type=normalized.get("activity_type", ""),
                activity_amount=normalized.get("activity_amount", 0),
                activity_unit=normalized.get("activity_unit", ""),
                period_start=period_start,
                period_end=period_end,
                country=normalized.get("country", organization.country),
                region=normalized.get("region", ""),
                fuel_type=normalized.get("fuel_type", ""),
                original_amount=normalized.get("original_amount"),
                original_unit=normalized.get("original_unit", ""),
                conversion_note=normalized.get("conversion_note", ""),
                distance_band=normalized.get("distance_band", ""),
                travel_class=normalized.get("travel_class", ""),
                origin_location=normalized.get(
                    "origin_airport", normalized.get("origin_station", "")
                ),
                destination_location=normalized.get(
                    "destination_airport", normalized.get("destination_station", "")
                ),
                is_estimated=normalized.get("is_estimated", False),
                # Overflow any remaining fields into the flexible JSONB metadata bucket
                metadata={k: v for k, v in normalized.items() if k not in STRUCTURED_FIELDS},
                review_status="pending",
            )

            # Inherit eGRID subregion from Facility if not already set by parser
            if facility and not activity.region:
                activity.region = facility.get_egrid_subregion() or ""

            activity.save()

            # Calculate CO2e immediately after save
            try:
                co2e, audit = self.calculator.calculate(activity)
                activity.co2e_kg = co2e
                activity.co2e_calculation_audit = audit
                activity.save(update_fields=["co2e_kg", "co2e_calculation_audit"])
            except FactorLookupError as e:
                # No matching factor → flag for analyst; don't fail the row entirely
                activity.review_status = "flagged"
                activity.review_notes = f"Auto-flagged: factor not found — {e}"
                activity.save(update_fields=["review_status", "review_notes"])

                raw_row.parsed_status = "suspicious"
                raw_row.parse_errors = list(raw_row.parse_errors) + [
                    f"Factor lookup failed: {e}"
                ]
                raw_row.save(update_fields=["parsed_status", "parse_errors"])

            return activity

        except Exception as exc:
            # Unexpected error — mark raw row invalid and propagate nothing
            raw_row.parsed_status = "invalid"
            raw_row.parse_errors = list(raw_row.parse_errors) + [
                f"ActivityRecord creation failed: {exc}"
            ]
            raw_row.save(update_fields=["parsed_status", "parse_errors"])
            return None