"""
Activity Record Serializers.

Provides serialization for the golden record - ActivityRecord.
Different serializers for list, detail, and edit operations.
"""
from rest_framework import serializers
from apps.activities.models import ActivityRecord


class ActivityRecordListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views (review queue, tables).
    Includes only fields needed for quick scanning.
    """
    activity_type_display = serializers.CharField(source="get_activity_type_display", read_only=True)
    scope_display = serializers.CharField(source="get_scope_display", read_only=True)
    source_system_display = serializers.CharField(source="get_source_system_display", read_only=True)
    review_status_display = serializers.CharField(source="get_review_status_display", read_only=True)
    facility_name = serializers.CharField(source="facility.name", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = ActivityRecord
        fields = [
            "id", "organization", "organization_name", "facility", "facility_name",
            "source_system", "source_system_display", "source_identifier",
            "scope", "scope_display", "activity_type", "activity_type_display",
            "activity_amount", "activity_unit", "co2e_kg",
            "period_start", "period_end", "review_status", "review_status_display",
            "is_estimated", "is_edited", "created_at",
        ]


class ActivityRecordDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for detail views.
    Includes complete audit trail, raw data linkage, and edit history.
    """
    activity_type_display = serializers.CharField(source="get_activity_type_display", read_only=True)
    scope_display = serializers.CharField(source="get_scope_display", read_only=True)
    source_system_display = serializers.CharField(source="get_source_system_display", read_only=True)
    review_status_display = serializers.CharField(source="get_review_status_display", read_only=True)
    facility_name = serializers.CharField(source="facility.name", read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    edited_by_name = serializers.SerializerMethodField()
    raw_data_payload = serializers.JSONField(source="raw_data_row.raw_payload", read_only=True)
    raw_parse_errors = serializers.JSONField(source="raw_data_row.parse_errors", read_only=True)
    ingestion_run_id = serializers.UUIDField(source="ingestion_run.id", read_only=True)

    class Meta:
        model = ActivityRecord
        fields = [
            "id", "organization", "facility", "facility_name", "ingestion_run_id",
            "raw_data_row", "raw_data_payload", "raw_parse_errors",
            "source_system", "source_system_display", "source_identifier",
            "scope", "scope_display", "scope_3_category",
            "activity_type", "activity_type_display",
            "activity_amount", "activity_unit",
            "period_start", "period_end", "period_days",
            "country", "region", "fuel_type",
            "original_amount", "original_unit", "conversion_note",
            "distance_band", "travel_class",
            "origin_location", "destination_location",
            "co2e_kg", "co2e_calculation_audit",
            "review_status", "review_status_display",
            "reviewed_by", "reviewed_by_name", "reviewed_at", "review_notes",
            "is_edited", "edited_by", "edited_by_name", "edited_at",
            "original_values", "edit_reason",
            "is_estimated", "metadata",
            "created_at", "updated_at",
        ]

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return f"{obj.reviewed_by.first_name} {obj.reviewed_by.last_name}".strip() or obj.reviewed_by.email
        return None

    def get_edited_by_name(self, obj):
        if obj.edited_by:
            return f"{obj.edited_by.first_name} {obj.edited_by.last_name}".strip() or obj.edited_by.email
        return None


class ActivityRecordEditSerializer(serializers.Serializer):
    """
    Serializer for editing ActivityRecords.

    Only specific fields can be edited by analysts:
    - activity_amount (if original was wrong)
    - activity_unit (rarely)
    - fuel_type (common correction)
    - scope / scope_3_category (if misclassified)
    - region (if wrong eGRID subregion)
    - period_start / period_end (if dates were parsed wrong)

    The 'reason' field is MANDATORY for audit compliance.
    """
    activity_amount = serializers.DecimalField(max_digits=20, decimal_places=6, required=False)
    activity_unit = serializers.ChoiceField(choices=ActivityRecord.ACTIVITY_UNIT_CHOICES, required=False)
    fuel_type = serializers.CharField(max_length=20, required=False, allow_blank=True)
    scope = serializers.ChoiceField(choices=ActivityRecord.SCOPE_CHOICES, required=False)
    scope_3_category = serializers.ChoiceField(choices=ActivityRecord.SCOPE_3_CATEGORY_CHOICES, required=False, allow_blank=True)
    region = serializers.CharField(max_length=20, required=False, allow_blank=True)
    period_start = serializers.DateField(required=False)
    period_end = serializers.DateField(required=False)
    distance_band = serializers.CharField(max_length=20, required=False, allow_blank=True)
    travel_class = serializers.CharField(max_length=20, required=False, allow_blank=True)
    reason = serializers.CharField(required=True, help_text="Mandatory reason for audit trail.")


class BulkReviewSerializer(serializers.Serializer):
    """Serializer for bulk approve/reject operations."""
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100,
        help_text="List of ActivityRecord IDs to process."
    )
    action = serializers.ChoiceField(
        choices=["approve", "reject", "flag"],
        help_text="Review action to apply to all selected records."
    )
    notes = serializers.CharField(required=False, allow_blank=True, help_text="Optional notes for all records.")
