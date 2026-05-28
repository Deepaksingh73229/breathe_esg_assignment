"""
Audit Log models.

Implements an append-only audit trail for all significant system actions.

Design Decisions
----------------
1. Separate table (not Django's built-in admin log) — gives us full control
   over the schema and lets us query it programmatically.
2. JSONB changed_fields — flexible across all table schemas.
3. record_id is nullable — allows logging bulk operations that don't map to
   a single record (e.g., "bulk approve 50 records").
4. No foreign keys to business tables — uses UUID strings to prevent
   cascade-deletion of audit entries if the source record is soft-deleted.
5. This table is NEVER soft-deleted — audit entries are forever.

What gets logged:
  - ActivityRecord edits (before/after snapshot + reason)
  - Review state transitions (pending → approved, etc.)
  - IngestionRun status changes
  - Bulk operations
  - User login / logout events (security forensics)
"""
from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import UUIDPrimaryKeyMixin, TimestampedMixin

User = get_user_model()


class AuditLog(UUIDPrimaryKeyMixin, TimestampedMixin, models.Model):
    """
    Immutable audit log entry.

    Records are only ever INSERTed, never UPDATEd or DELETEd.
    """

    ACTION_CHOICES = [
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Soft Delete"),
        ("review_transition", "Review State Transition"),
        ("bulk_approve", "Bulk Approve"),
        ("bulk_reject", "Bulk Reject"),
        ("bulk_flag", "Bulk Flag"),
        ("ingestion", "Data Ingestion"),
        ("recalculation", "Emission Recalculation"),
        ("login", "User Login"),
        ("logout", "User Logout"),
    ]

    table_name = models.CharField(
        max_length=100,
        help_text="Database table that was affected. E.g., 'activities_activityrecord'.",
    )

    # Nullable to support bulk operations that don't map to a single record.
    record_id = models.UUIDField(
        null=True,
        blank=True,
        help_text=(
            "UUID of the affected record. "
            "NULL for bulk operations affecting multiple records."
        ),
    )

    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        db_index=True,
    )

    # JSONB change snapshot.
    # For "update":            {"original_values": {...}, "new_values": {...}, "reason": "..."}
    # For "review_transition": {"transition": "pending → approved", "notes": "..."}
    # For "bulk_approve":      {"record_ids": [...], "count": N, "notes": "..."}
    changed_fields = models.JSONField(default=dict)

    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="User who performed the action. NULL if system-initiated or user was deleted.",
    )

    # Request metadata for security forensics
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Organisation context — allows per-client audit queries
    organization_id = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log Entries"
        indexes = [
            models.Index(fields=["table_name", "record_id"]),
            models.Index(fields=["organization_id", "action"]),
            models.Index(fields=["performed_by", "created_at"]),
        ]

    def __str__(self):
        who = self.performed_by.email if self.performed_by else "system"
        return f"{self.action} on {self.table_name}:{self.record_id} by {who}"


class AuditLogQuery:
    """Helper class providing common audit queries for analysts and auditors."""

    @staticmethod
    def get_record_history(table_name: str, record_id):
        return (
            AuditLog.objects.filter(table_name=table_name, record_id=record_id)
            .order_by("created_at")
        )

    @staticmethod
    def get_user_actions(user_id, start_date=None, end_date=None):
        qs = AuditLog.objects.filter(performed_by_id=user_id)
        if start_date:
            qs = qs.filter(created_at__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__lte=end_date)
        return qs

    @staticmethod
    def get_organization_audit(organization_id, action_type=None):
        qs = AuditLog.objects.filter(organization_id=organization_id)
        if action_type:
            qs = qs.filter(action=action_type)
        return qs