"""
Analyst Review Workflow Service.

Implements the four-state review state machine:

  pending → approved  (analyst signs off)
  pending → flagged   (needs more information)
  pending → rejected  (data confirmed bad)
  flagged → approved  (issue resolved)
  flagged → rejected  (confirmed bad)

Every transition is recorded in AuditLog for compliance.
Edits to ActivityRecords require a mandatory reason and create a before/after snapshot.
"""
from typing import Any, Dict

from django.db import transaction
from django.utils import timezone

from apps.activities.models import ActivityRecord
from apps.audit.models import AuditLog


class ReviewService:
    """
    Service for analyst review operations.

    All mutating methods are atomic so partial state changes cannot occur.
    """

    @transaction.atomic
    def approve(self, activity: ActivityRecord, user, notes: str = "") -> ActivityRecord:
        """
        Approve an ActivityRecord for inclusion in GHG reporting.

        Once approved the record is considered "locked" for that reporting period.
        It can still be edited (with a reason), but the edit triggers a re-review.
        """
        old_status = activity.review_status
        now = timezone.now()

        activity.review_status = "approved"
        activity.reviewed_by = user
        activity.reviewed_at = now
        activity.review_notes = notes
        activity.updated_by = user
        activity.save(update_fields=[
            "review_status", "reviewed_by", "reviewed_at",
            "review_notes", "updated_by", "updated_at",
        ])

        self._log_transition(activity, user, "approve", old_status, "approved", notes)
        return activity

    @transaction.atomic
    def reject(self, activity: ActivityRecord, user, notes: str = "") -> ActivityRecord:
        """
        Reject an ActivityRecord.

        Rejected records are excluded from all reporting totals.
        The raw data (RawDataRow) is preserved so the source evidence remains.
        """
        old_status = activity.review_status
        now = timezone.now()

        activity.review_status = "rejected"
        activity.reviewed_by = user
        activity.reviewed_at = now
        activity.review_notes = notes
        activity.updated_by = user
        activity.save(update_fields=[
            "review_status", "reviewed_by", "reviewed_at",
            "review_notes", "updated_by", "updated_at",
        ])

        self._log_transition(activity, user, "reject", old_status, "rejected", notes)
        return activity

    @transaction.atomic
    def flag(self, activity: ActivityRecord, user, notes: str = "") -> ActivityRecord:
        """
        Flag an ActivityRecord for analyst attention.

        Common reasons: "Verify plant code with SAP team", "Confirm this is
        not an estimated utility read", "Check if flight class is correct".
        Flagged records remain in the review queue but are highlighted.
        """
        old_status = activity.review_status
        now = timezone.now()

        activity.review_status = "flagged"
        activity.reviewed_by = user
        activity.reviewed_at = now
        activity.review_notes = notes
        activity.updated_by = user
        activity.save(update_fields=[
            "review_status", "reviewed_by", "reviewed_at",
            "review_notes", "updated_by", "updated_at",
        ])

        self._log_transition(activity, user, "flag", old_status, "flagged", notes)
        return activity

    @transaction.atomic
    def edit(
        self,
        activity: ActivityRecord,
        user,
        changes: Dict[str, Any],
        reason: str,
    ) -> ActivityRecord:
        """
        Edit an ActivityRecord with a full, mandatory audit trail.

        This is the ONLY permitted way to change ActivityRecord data after creation.
        It captures a snapshot of original values before applying the change.

        Args:
            activity:  The ActivityRecord to modify.
            user:      The analyst making the change.
            changes:   Dict of field_name → new_value.
            reason:    Human-readable reason (required for audit compliance).

        Raises:
            ValueError: If reason is empty.
        """
        if not reason or not reason.strip():
            raise ValueError(
                "Edit reason is required for audit compliance. "
                "Example: 'Corrected fuel type from gasoline to diesel per verified invoice.'"
            )

        # Capture originals before mutation
        original_values: Dict[str, Any] = {}
        for field_name in changes:
            val = getattr(activity, field_name)
            # Serialise date/datetime for JSON storage
            if hasattr(val, "isoformat"):
                val = val.isoformat()
            original_values[field_name] = str(val) if val is not None else None

        # Apply changes
        for field_name, new_value in changes.items():
            setattr(activity, field_name, new_value)

        # Mark as edited
        activity.is_edited = True
        activity.edited_by = user
        activity.edited_at = timezone.now()
        activity.original_values = original_values
        activity.edit_reason = reason
        activity.updated_by = user

        # If calculation inputs changed, reset to pending so the analyst must
        # re-review the new CO2e value before it goes to auditors.
        CALC_INPUTS = {
            "activity_amount", "activity_unit", "fuel_type",
            "distance_band", "travel_class", "region",
            "period_start", "period_end",
        }
        if any(f in changes for f in CALC_INPUTS):
            old_status = activity.review_status
            activity.review_status = "pending"
            activity.review_notes = (
                f"Auto-reset to pending after edit to calculation inputs: {reason}"
            )
            self._log_transition(
                activity, user, "auto_reset", old_status, "pending",
                f"Calculation input changed: {reason}",
            )

        activity.save()

        # Append full change record to AuditLog
        AuditLog.objects.create(
            table_name="activities_activityrecord",
            record_id=activity.id,
            action="update",
            changed_fields={
                "original_values": original_values,
                "new_values": {
                    k: str(v) if v is not None else None
                    for k, v in changes.items()
                },
                "reason": reason,
            },
            performed_by=user,
            organization_id=activity.organization_id,
        )

        return activity

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _log_transition(
        activity: ActivityRecord,
        user,
        action: str,
        old_status: str,
        new_status: str,
        notes: str,
    ) -> None:
        """Write a review_transition entry to the AuditLog."""
        AuditLog.objects.create(
            table_name="activities_activityrecord",
            record_id=activity.id,
            action="review_transition",
            changed_fields={
                "transition": f"{old_status} → {new_status}",
                "action": action,
                "notes": notes,
            },
            performed_by=user,
            organization_id=activity.organization_id,
        )