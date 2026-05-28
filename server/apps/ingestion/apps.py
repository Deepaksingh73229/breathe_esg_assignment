"""
Ingestion app configuration.

The ingestion layer is the "airlock" between external data chaos and internal
audit integrity. It handles:
1. File upload and storage (with SHA-256 checksums)
2. Format-specific parsing (SAP CSV, Utility CSV, Travel JSON)
3. Raw data preservation (immutable JSONB rows)
4. Validation and flagging (suspicious data detection)

Design Principle: RAW DATA IS IMMUTABLE.
Once a file is uploaded, its contents are stored exactly as received.
Analysts never edit raw data. They approve or reject the *derived* ActivityRecords.
"""
from django.apps import AppConfig


class IngestionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ingestion"
    verbose_name = "Data Ingestion"
