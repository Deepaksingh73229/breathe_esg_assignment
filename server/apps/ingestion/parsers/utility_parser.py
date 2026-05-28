"""
Utility Electricity Data Parser.

Real-World Context
------------------
Facilities teams typically download CSV exports from utility portals.
The near-universal North American standard is "Green Button" (ESPI), but most
utilities also offer proprietary CSV with common columns:

  Account Number | Service Address | Meter Number
  Billing Period Start / End   (often NOT calendar months!)
  Usage (kWh) | Demand (kW) | Cost
  Rate Schedule | Notes (estimated vs. actual reads)

Key complexities we handle:
  1. Non-calendar billing periods (e.g., Jan 15 – Feb 14)
  2. Estimated reads flagged in Notes column
  3. Multiple meters per facility → same account maps to one Facility
  4. Demand charges (kW peak) — stored in metadata, not used for Scope 2 CO2e
  5. Negative kWh (solar export credit) — treated specially

Emission calculation note:
  - EPA eGRID subregion-specific factors (not national average: using national
    average when a subregion is determinable is a GHG Protocol methodology error)
  - T&D losses (~5 %) are Scope 3 Category 3, NOT Scope 2.  Including them in
    Scope 2 is a common and auditor-detectable error.
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Generator, List

import pandas as pd
from dateutil import parser as date_parser

from apps.facilities.models import Facility
from .base import BaseParser, ParseResult


# ── Header normalisation ──────────────────────────────────────────────────────
UTILITY_HEADER_MAPPING = {
    # Account info
    "account number": "account_number", "account": "account_number",
    "acct": "account_number", "acct no": "account_number",
    "acct_no": "account_number",
    "service": "service_type", "service type": "service_type",
    "type": "service_type",

    # Billing period
    "start date": "period_start", "start": "period_start",
    "from": "period_start", "bill start": "period_start",
    "billing period start": "period_start", "period_start": "period_start",
    "end date": "period_end", "end": "period_end",
    "to": "period_end", "bill end": "period_end",
    "billing period end": "period_end", "period_end": "period_end",

    # Usage
    "usage": "usage_kwh", "kwh": "usage_kwh", "consumption": "usage_kwh",
    "total usage": "usage_kwh", "total kwh": "usage_kwh",
    "energy": "usage_kwh", "usage_kwh": "usage_kwh",

    # Demand
    "demand": "demand_kw", "kw": "demand_kw", "peak demand": "demand_kw",
    "max demand": "demand_kw", "demand_kw": "demand_kw",

    # Cost
    "cost": "total_cost", "amount": "total_cost", "total amount": "total_cost",
    "bill amount": "total_cost", "total cost": "total_cost",

    # Units
    "units": "usage_unit", "unit": "usage_unit", "uom": "usage_unit",

    # Notes / flags
    "notes": "notes", "note": "notes", "description": "notes",
    "remarks": "notes", "read type": "read_type",
    "meter read": "read_type", "reading type": "read_type",
}

# Keywords that indicate an estimated meter read (vs. actual read)
ESTIMATED_KEYWORDS = (
    "estimated", "estimate", "calc", "calculated",
    "avg", "average", "proj", "projected", "est.",
)

# Date formats to try, in preference order
DATE_FORMATS = (
    "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y",
    "%m-%d-%Y", "%d-%m-%Y", "%Y%m%d",
    "%d.%m.%Y",
)


class UtilityParser(BaseParser):
    """
    Parser for utility electricity CSV exports (Green Button and proprietary).

    Maps utility account numbers to Facilities for automatic attribution.
    Produces Scope 2 ActivityRecords for purchased electricity.
    """

    def validate_file(self, file_obj) -> bool:
        """File must have at least one date-like column and one usage/kWh column."""
        try:
            file_obj.seek(0)
            # Try to detect delimiter by reading first line
            first_line = file_obj.readline().decode(self.detect_encoding(file_obj))
            file_obj.seek(0)
            
            sep = ","
            if ";" in first_line and first_line.count(";") > first_line.count(","):
                sep = ";"
                
            df = pd.read_csv(file_obj, nrows=5, sep=sep, encoding=self.detect_encoding(file_obj))
            cols_lower = " ".join(c.lower() for c in df.columns)
            
            # Broaden detection keywords
            has_period = any(kw in cols_lower for kw in ("date", "period", "from", "to", "billing"))
            has_usage = any(kw in cols_lower for kw in ("usage", "kwh", "consumption", "energy", "quantity", "amount"))
            
            return has_period and has_usage
        except Exception:
            return False

    def parse_rows(self, file_obj) -> Generator[ParseResult, None, None]:
        file_obj.seek(0)
        encoding = self.detect_encoding(file_obj)

        try:
            # Detect delimiter again for the full parse
            first_line = file_obj.readline().decode(encoding)
            file_obj.seek(0)
            sep = ","
            if ";" in first_line and first_line.count(";") > first_line.count(","):
                sep = ";"
                
            df = pd.read_csv(file_obj, sep=sep, encoding=encoding, dtype=str, keep_default_na=False)
        except Exception as e:
            yield ParseResult("invalid", {}, [f"Failed to parse utility CSV: {e}"])
            return

        # Normalise headers
        renamed = {}
        for col in df.columns:
            clean = col.strip().lower()
            renamed[col] = UTILITY_HEADER_MAPPING.get(clean, clean)
        df.rename(columns=renamed, inplace=True)

        # Pre-load Facility lookup: account_number → Facility
        # A single facility may have multiple meters (multiple account numbers).
        facilities_by_account: dict = {}
        for facility in Facility.objects.filter(organization=self.organization, is_active=True):
            for acct in facility.utility_account_numbers:
                facilities_by_account[acct.strip()] = facility

        for idx, row in df.iterrows():
            raw_payload = row.to_dict()

            # Skip empty rows
            if all(str(v).strip() == "" for v in raw_payload.values()):
                yield ParseResult("skipped", raw_payload, ["Empty row"])
                continue

            errors: List[str] = []
            warnings: List[str] = []
            normalized = {}

            # ── Account number & facility resolution ──────────────────────────
            account = str(raw_payload.get("account_number", "")).strip()
            if account:
                normalized["account_number"] = account
                facility = facilities_by_account.get(account)
                if facility:
                    normalized["facility_id"] = str(facility.id)
                    normalized["facility_name"] = facility.name
                    # Carry eGRID subregion for the emission calculator
                    egrid = facility.get_egrid_subregion()
                    if egrid:
                        normalized["region"] = egrid
                else:
                    warnings.append(
                        f"Account '{account}' is not linked to any Facility. "
                        "Electricity will be attributed to the organisation level only. "
                        "Update the Facility's utility_account_numbers to enable auto-routing."
                    )
            else:
                warnings.append(
                    "Missing account number. Cannot link to a Facility automatically."
                )

            # ── Billing period parsing ────────────────────────────────────────
            # Billing periods RARELY align with calendar months (e.g., Jan 15 – Feb 14).
            # We store exact dates and prorate to calendar months only at reporting time.
            period_start = self._parse_date(
                str(raw_payload.get("period_start", "")).strip(),
                "period_start", errors,
            )
            period_end = self._parse_date(
                str(raw_payload.get("period_end", "")).strip(),
                "period_end", errors,
            )

            if period_start and period_end:
                if period_end < period_start:
                    errors.append(
                        f"Billing period end ({period_end}) is before start ({period_start})."
                    )
                else:
                    # Return date objects consistently (pipeline converts to isoformat if needed)
                    normalized["period_start"] = period_start
                    normalized["period_end"] = period_end

                    days = (period_end - period_start).days
                    if days > 35:
                        warnings.append(
                            f"Billing period is {days} days (typical is 28–31). "
                            "Possible missed meter read or two bills merged — verify with facilities team."
                        )
                    if days < 20:
                        warnings.append(
                            f"Billing period is only {days} days. "
                            "Verify this is a complete billing period, not a partial bill."
                        )
            else:
                errors.append("Missing billing period dates. Cannot determine reporting period.")

            # ── Usage (kWh) ───────────────────────────────────────────────────
            usage_str = str(raw_payload.get("usage_kwh", "")).strip()
            if not usage_str:
                # Fallback: scan all columns for any kWh-named column
                for key, val in raw_payload.items():
                    if "kwh" in key.lower() or "usage" in key.lower():
                        usage_str = str(val).strip()
                        if usage_str:
                            break

            if usage_str:
                try:
                    clean = usage_str.replace(",", "").replace("$", "").strip()
                    usage = Decimal(clean)

                    if usage < 0:
                        # Negative kWh = solar export credit or meter reversal.
                        # GHG Protocol says report NET consumption for Scope 2.
                        # We store abs() and flag for analyst decision.
                        warnings.append(
                            f"Negative usage ({usage} kWh) — this may be a solar export credit. "
                            "Per GHG Protocol, Scope 2 should report net consumption. "
                            "Verify with facilities team before approving."
                        )
                        usage = abs(usage)

                    normalized["activity_amount"] = str(usage)
                    normalized["activity_unit"] = "kwh"
                    normalized["activity_type"] = "purchased_electricity"
                    normalized["scope"] = "2"

                    # Sanity: 50 GWh per bill is only realistic for the largest data centres
                    if usage > Decimal("50_000_000"):
                        warnings.append(
                            f"Usage {usage} kWh is extremely high. "
                            "Verify unit is kWh (not MWh). "
                            "50 M kWh = 50 GWh, typical only for large industrial sites."
                        )

                    # Daily-average check: >500 MWh/day flags potential meter aggregation
                    if period_start and period_end:
                        days = max((period_end - period_start).days, 1)
                        daily = usage / days
                        if daily > Decimal("500_000"):
                            warnings.append(
                                f"Daily average {daily:,.0f} kWh is very high. "
                                "Verify this meter is not aggregated across multiple facilities."
                            )

                except (InvalidOperation, ValueError):
                    errors.append(
                        f"Cannot parse usage '{usage_str}' as a number. "
                        "Remove any non-numeric characters (currency symbols, spaces)."
                    )
            else:
                errors.append(
                    "Missing electricity usage (kWh). "
                    "Cannot calculate Scope 2 emissions without a consumption value."
                )

            # ── Demand (kW peak) — stored in metadata, not in CO2e calc ───────
            # Peak demand drives capacity charges but not carbon emissions.
            # We store it so analysts can cross-check utility bills.
            demand_str = str(raw_payload.get("demand_kw", "")).strip()
            if demand_str:
                try:
                    normalized["demand_kw"] = str(Decimal(demand_str.replace(",", "")))
                except (InvalidOperation, ValueError):
                    pass  # Non-critical — demand is optional

            # ── Cost — stored for spend analytics ────────────────────────────
            cost_str = str(raw_payload.get("total_cost", "")).strip()
            if cost_str:
                try:
                    normalized["total_cost"] = str(
                        Decimal(cost_str.replace(",", "").replace("$", "").strip())
                    )
                except (InvalidOperation, ValueError):
                    pass  # Non-critical

            # ── Estimated read detection ──────────────────────────────────────
            # Utilities flag estimated reads in Notes or ReadType columns.
            # Estimated reads MUST be reviewed — the actual bill may differ significantly.
            notes_text = str(raw_payload.get("notes", "")).lower()
            read_type_text = str(raw_payload.get("read_type", "")).lower()
            combined = notes_text + " " + read_type_text

            is_estimated = any(kw in combined for kw in ESTIMATED_KEYWORDS)
            normalized["is_estimated"] = is_estimated
            if is_estimated:
                warnings.append(
                    "Estimated meter read (not actual). "
                    "Emissions may need correction when the actual read becomes available. "
                    "Flag for follow-up with the facilities team."
                )

            # ── Source identifier ─────────────────────────────────────────────
            if account and period_start:
                normalized["source_identifier"] = f"{account}_{period_start.isoformat()}"
            elif account:
                normalized["source_identifier"] = account
            else:
                normalized["source_identifier"] = f"row_{idx + 2}"

            # ── Determine final status ────────────────────────────────────────
            if errors:
                yield ParseResult("invalid", raw_payload, errors + warnings, normalized)
            elif warnings:
                yield ParseResult("suspicious", raw_payload, warnings, normalized)
            else:
                yield ParseResult("valid", raw_payload, [], normalized)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _parse_date(date_str: str, field_name: str, errors: List[str]):
        """Try multiple date formats; append to errors if none succeed."""
        if not date_str:
            return None
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        try:
            return date_parser.parse(date_str).date()
        except Exception:
            errors.append(
                f"Cannot parse {field_name} date '{date_str}'. "
                "Expected formats: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY."
            )
            return None