"""
Audit Serializers.
"""
from rest_framework import serializers
from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for audit log entries.
    Includes human-readable action name and performer email.
    """
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    performed_by_email = serializers.EmailField(source="performed_by.email", read_only=True)
    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id", "table_name", "record_id", "action", "action_display",
            "changed_fields", "performed_by", "performed_by_email", "performed_by_name",
            "ip_address", "user_agent", "organization_id", "created_at",
        ]

    def get_performed_by_name(self, obj):
        if obj.performed_by:
            return f"{obj.performed_by.first_name} {obj.performed_by.last_name}".strip() or obj.performed_by.email
        return "System"
