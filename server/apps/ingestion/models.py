"""
Ingestion models.

IngestionRun: Represents a single "batch" of data from a source system.
  Think of it like a shipping container: it has a manifest (metadata),
  contents (raw file), and a seal (SHA-256 checksum).

RawDataRow: Every single row/record from the source file, stored as JSONB.
  This is our "source of truth" insurance policy. If an auditor challenges
  a calculated emission, we can show them the EXACT raw data that produced it.
"""
import hashlib
from django.db import models
from apps.core.models import TenantModel


def raw_upload_path(instance, filename):
    """
    Dynamic upload path for raw source files.
    Organized by organization and date for easy debugging.

    Path format: raw_uploads/{org_slug}/{YYYY}/{MM}/{DD}/{filename}
    """
    from datetime import datetime
    org_slug = instance.organization.slug
    now = datetime.now()
    return f"raw_uploads/{org_slug}/{now.year}/{now.month:02d}/{now.day:02d}/{filename}"


class IngestionRun(TenantModel):
    """
    A single upload or API pull event from an external source system.

    This is the parent container for all raw data rows. It tracks:
    - WHO uploaded it (created_by)
    - WHEN it was uploaded (created_at)
    - WHAT source system it came from (source_type)
    - HOW it was delivered (ingestion_method)
    - The EXACT file that was uploaded (raw_file + checksum)
    - Processing status (pending -> parsing -> parsed / failed)

    Why store the raw file?
    1. Audit defense: "Show me the original SAP export" -> we have it
    2. Re-parsing: If we improve our parser, we can re-process historical files
    3. Debugging: When a client says "that number is wrong", we can inspect the source
    """

    SOURCE_TYPE_CHOICES = [
        ("sap", "SAP - Fuel & Procurement"),
        ("utility", "Utility - Electricity"),
        ("travel", "Travel - Concur/Navan"),
    ]

    INGESTION_METHOD_CHOICES = [
        ("csv_upload", "CSV File Upload"),
        ("json_upload", "JSON File Upload"),
        ("manual_entry", "Manual Data Entry"),
        ("api_pull", "API Pull (Simulated)"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),           # File uploaded, not yet parsed
        ("parsing", "Parsing"),           # Parser is actively processing
        ("parsed", "Parsed"),             # All rows processed, some may be invalid
        ("failed", "Failed"),             # Catastrophic failure (malformed file)
        ("partial", "Partial Success"),   # Parsed but with many invalid rows
    ]

    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        db_index=True,
        help_text="Which external system produced this data. Determines which parser to use."
    )
    ingestion_method = models.CharField(
        max_length=20,
        choices=INGESTION_METHOD_CHOICES,
        default="csv_upload",
        help_text="How the data entered our system. CSV upload is the realistic enterprise pattern."
    )

    # Raw file storage
    raw_file = models.FileField(
        upload_to=raw_upload_path,
        help_text="The exact file as received from the client. Never modified after upload."
    )

    # Cryptographic integrity check
    # SHA-256 ensures the file hasn't been tampered with or corrupted in storage
    checksum = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 hash of the uploaded file. Verifies storage integrity."
    )

    # Processing status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
        help_text="Current state of this ingestion batch."
    )

    # Processing metadata
    total_rows = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total rows detected in the source file."
    )
    valid_rows = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Rows that passed validation and created ActivityRecords."
    )
    invalid_rows = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Rows that failed validation (e.g., missing plant code, negative kWh)."
    )
    suspicious_rows = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Rows that parsed but triggered warnings (e.g., estimated utility read)."
    )

    # Error summary for quick dashboard display
    error_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Aggregated error counts by type. Example: {'missing_plant_code': 5, 'negative_kwh': 2}"
    )

    # Optional: link to a specific facility if the upload is facility-scoped
    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ingestion_runs",
        help_text="If the upload is specific to one facility (e.g., utility bill for Plant A)."
    )

    # Period coverage (for analyst context)
    period_start = models.DateField(
        null=True,
        blank=True,
        help_text="Earliest activity period found in this batch."
    )
    period_end = models.DateField(
        null=True,
        blank=True,
        help_text="Latest activity period found in this batch."
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Ingestion Run"
        verbose_name_plural = "Ingestion Runs"
        indexes = [
            models.Index(fields=["organization", "source_type", "status"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_source_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')} ({self.status})"

    def compute_checksum(self):
        """Compute SHA-256 checksum of the uploaded file. Call after save()."""
        if not self.raw_file:
            return
        sha256 = hashlib.sha256()
        self.raw_file.seek(0)
        for chunk in self.raw_file.chunks():
            sha256.update(chunk)
        self.checksum = sha256.hexdigest()
        self.save(update_fields=["checksum"])


class RawDataRow(TenantModel):
    """
    A single row/record from the source file, stored exactly as received.

    This is our "insurance policy" for audit trails. The JSONB raw_payload
    contains the EXACT data from the CSV/JSON source, unmodified.

    Lifecycle:
    1. Created during parsing with parsed_status='pending'
    2. Parser attempts normalization -> creates ActivityRecord
    3. If normalization succeeds: parsed_status='valid', activity_record is set
    4. If normalization fails: parsed_status='invalid', parse_errors populated
    5. If normalization succeeds but data looks odd: parsed_status='suspicious'

    Why separate RawDataRow from ActivityRecord?
    - RawDataRow = "what the client gave us" (immutable)
    - ActivityRecord = "what we understood and calculated" (reviewable, editable)
    - This separation lets analysts correct OUR interpretation without destroying evidence.
    """

    PARSED_STATUS_CHOICES = [
        ("pending", "Pending"),         # Not yet processed by parser
        ("valid", "Valid"),             # Successfully parsed, ActivityRecord created
        ("invalid", "Invalid"),         # Parse errors, no ActivityRecord created
        ("suspicious", "Suspicious"),   # Parsed but flagged for analyst attention
        ("skipped", "Skipped"),         # Intentionally skipped (e.g., header row, summary row)
    ]

    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.CASCADE,
        related_name="rows",
        help_text="The parent ingestion batch this row belongs to."
    )

    # Position in the source file (for error messages and manual debugging)
    source_row_number = models.PositiveIntegerField(
        help_text="1-based row number in the source file. Helps analysts find the exact raw data."
    )

    # The exact source data, preserved as JSONB
    # For CSV: {"Buchungskreis": "1000", "Werk": "DE01", "Menge": "500", ...}
    # For JSON: {"segmentTypeId": "AIRFR", "trip": {...}, ...}
    raw_payload = models.JSONField(
        help_text="Exact row data as received from source. Immutable after creation."
    )

    # Processing status
    parsed_status = models.CharField(
        max_length=20,
        choices=PARSED_STATUS_CHOICES,
        default="pending",
        db_index=True,
        help_text="Result of parsing this row."
    )

    # Detailed error messages for invalid/suspicious rows
    # Example: ["Plant code 'DE99' not found in lookup table", "Quantity exceeds 1,000,000 L"]
    parse_errors = models.JSONField(
        default=list,
        blank=True,
        help_text="List of human-readable error/warning messages from the parser."
    )

    # Link to the derived ActivityRecord (if parsing succeeded)
    activity_record = models.OneToOneField(
        "activities.ActivityRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_raw_data_row",
        help_text="The normalized ActivityRecord derived from this raw row. Null if parsing failed."
    )

    # Quick lookup fields (denormalized from raw_payload for filtering)
    # These are extracted by the parser for dashboard queries without JSONB scanning
    source_identifier = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Extracted document/transaction ID from source. E.g., SAP Belegnummer, Concur expense ID."
    )
    raw_period_start = models.DateField(
        null=True,
        blank=True,
        help_text="Extracted period start date from raw data."
    )
    raw_period_end = models.DateField(
        null=True,
        blank=True,
        help_text="Extracted period end date from raw data."
    )

    class Meta:
        ordering = ["ingestion_run", "source_row_number"]
        verbose_name = "Raw Data Row"
        verbose_name_plural = "Raw Data Rows"
        indexes = [
            models.Index(fields=["ingestion_run", "parsed_status"]),
            models.Index(fields=["organization", "parsed_status"]),
        ]

    def __str__(self):
        return f"Row {self.source_row_number} of {self.ingestion_run}"
