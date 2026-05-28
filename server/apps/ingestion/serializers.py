"""
Ingestion Serializers.

Handles serialization/deserialization of IngestionRun and RawDataRow models.
"""
from rest_framework import serializers
from apps.ingestion.models import IngestionRun, RawDataRow
from apps.organizations.models import Organization


class IngestionRunCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new ingestion run with file upload.

    The raw_file field accepts the uploaded CSV/JSON file.
    organization is optional; if omitted, the backend will attempt to 
    infer it from the user's active membership.
    """
    raw_file = serializers.FileField(required=True)
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), 
        required=False,
        allow_null=True
    )

    class Meta:
        model = IngestionRun
        fields = ["id", "organization", "source_type", "ingestion_method", 
                  "raw_file", "facility", "created_at"]
        read_only_fields = ["id", "created_at"]


class IngestionRunSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving ingestion run details.
    Includes computed statistics and source type display.
    """
    source_type_display = serializers.CharField(source="get_source_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    ingestion_method_display = serializers.CharField(source="get_ingestion_method_display", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    facility_name = serializers.CharField(source="facility.name", read_only=True)

    class Meta:
        model = IngestionRun
        fields = [
            "id", "organization", "organization_name", "source_type", "source_type_display",
            "ingestion_method", "ingestion_method_display", "status", "status_display",
            "raw_file", "checksum", "total_rows", "valid_rows", "invalid_rows",
            "suspicious_rows", "error_summary", "facility", "facility_name",
            "period_start", "period_end", "created_at", "updated_at",
        ]


class RawDataRowSerializer(serializers.ModelSerializer):
    """
    Serializer for raw data rows.
    Includes the linked activity record ID if parsing succeeded.
    """
    parsed_status_display = serializers.CharField(source="get_parsed_status_display", read_only=True)
    activity_record_id = serializers.UUIDField(source="activity_record.id", read_only=True)
    ingestion_run_id = serializers.UUIDField(source="ingestion_run.id", read_only=True)

    class Meta:
        model = RawDataRow
        fields = [
            "id", "ingestion_run_id", "source_row_number", "raw_payload",
            "parsed_status", "parsed_status_display", "parse_errors",
            "activity_record_id", "source_identifier", "raw_period_start",
            "raw_period_end", "created_at",
        ]
