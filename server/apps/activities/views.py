"""
Activity Record API Views.

Endpoints:
  GET    /api/v1/activities/                        List with filtering
  GET    /api/v1/activities/{id}/                   Detail with full audit trail
  POST   /api/v1/activities/{id}/approve/           Approve record
  POST   /api/v1/activities/{id}/reject/            Reject record
  POST   /api/v1/activities/{id}/flag/              Flag record
  PATCH  /api/v1/activities/{id}/edit_record/       Edit with audit trail
  POST   /api/v1/activities/bulk_review/            Bulk approve/reject/flag
  GET    /api/v1/activities/{id}/audit_trail/       Full audit history
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.activities.models import ActivityRecord
from apps.activities.services.review_service import ReviewService
from apps.activities.services.calculator import EmissionCalculator
from apps.audit.models import AuditLog
from .serializers import (
    ActivityRecordListSerializer,
    ActivityRecordDetailSerializer,
    ActivityRecordEditSerializer,
    BulkReviewSerializer,
)


class ActivityRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ActivityRecord management and the analyst review workflow.

    Filtering:
      ?scope=1|2|3
      ?review_status=pending|flagged|approved|rejected
      ?source_system=sap|utility|travel
      ?activity_type=stationary_fuel|purchased_electricity|business_travel_flight|...
      ?is_estimated=true|false
      ?period_start=YYYY-MM-DD
      ?period_end=YYYY-MM-DD
    """

    queryset = ActivityRecord.objects.filter(is_deleted=False)
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "organization", "facility", "source_system", "scope",
        "activity_type", "review_status", "period_start", "period_end",
        "is_estimated", "fuel_type",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return ActivityRecordListSerializer
        if self.action == "edit_record":
            return ActivityRecordEditSerializer
        if self.action == "bulk_review":
            return BulkReviewSerializer
        return ActivityRecordDetailSerializer

    def get_queryset(self):
        """Scope queryset to the current user's organisations only."""
        user_orgs = self.request.user.organization_memberships.values_list(
            "organization_id", flat=True
        )
        return ActivityRecord.objects.filter(
            organization_id__in=user_orgs, is_deleted=False
        )

    # ── Review actions ────────────────────────────────────────────────────────

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a single ActivityRecord for GHG reporting."""
        activity = self.get_object()
        notes = request.data.get("notes", "")
        ReviewService().approve(activity, request.user, notes)
        return Response({
            "status": "approved",
            "id": str(activity.id),
            "reviewed_at": activity.reviewed_at.isoformat() if activity.reviewed_at else None,
        })

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject an ActivityRecord (excluded from all reporting)."""
        activity = self.get_object()
        notes = request.data.get("notes", "")
        ReviewService().reject(activity, request.user, notes)
        return Response({
            "status": "rejected",
            "id": str(activity.id),
            "reviewed_at": activity.reviewed_at.isoformat() if activity.reviewed_at else None,
        })

    @action(detail=True, methods=["post"])
    def flag(self, request, pk=None):
        """Flag an ActivityRecord for analyst attention."""
        activity = self.get_object()
        notes = request.data.get("notes", "")
        ReviewService().flag(activity, request.user, notes)
        return Response({
            "status": "flagged",
            "id": str(activity.id),
            "reviewed_at": activity.reviewed_at.isoformat() if activity.reviewed_at else None,
        })

    @action(detail=True, methods=["patch"])
    def edit_record(self, request, pk=None):
        """
        Edit an ActivityRecord with a mandatory audit trail.

        Request body example:
            {
                "fuel_type": "diesel",
                "reason": "Corrected fuel type per verified invoice #INV-2024-003."
            }

        If calculation inputs change (activity_amount, fuel_type, etc.) the record
        is automatically reset to 'pending' so the analyst re-reviews the new CO2e.
        """
        activity = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Collect only the explicitly provided editable fields
        EDITABLE_FIELDS = {
            "activity_amount", "activity_unit", "fuel_type", "scope",
            "scope_3_category", "region", "period_start", "period_end",
            "distance_band", "travel_class",
        }
        changes = {
            f: serializer.validated_data[f]
            for f in EDITABLE_FIELDS
            if f in serializer.validated_data
        }
        reason = serializer.validated_data["reason"]

        if not changes:
            return Response(
                {"error": "No editable fields provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ReviewService().edit(activity, request.user, changes, reason)

        # Recalculate CO2e if any calculation inputs changed
        CALC_INPUTS = {
            "activity_amount", "activity_unit", "fuel_type",
            "distance_band", "travel_class", "region",
            "period_start", "period_end",
        }
        if any(f in changes for f in CALC_INPUTS):
            try:
                EmissionCalculator().recalculate(activity)
            except Exception as e:
                return Response({
                    "status": "edited_recalculation_failed",
                    "id": str(activity.id),
                    "error": str(e),
                    "message": (
                        "Record edited successfully but CO2e recalculation failed. "
                        "Check emission factor configuration."
                    ),
                }, status=status.HTTP_200_OK)

        return Response({
            "status": "edited",
            "id": str(activity.id),
            "changes_applied": list(changes.keys()),
            "reason": reason,
            "new_co2e_kg": float(activity.co2e_kg) if activity.co2e_kg else None,
            "review_status": activity.review_status,
        })

    @action(detail=False, methods=["post"])
    def bulk_review(self, request):
        """
        Bulk approve / reject / flag multiple ActivityRecords.

        Request body:
            {
                "ids": ["uuid1", "uuid2", ...],
                "action": "approve",
                "notes": "Verified during Q1 2024 quarterly review."
            }

        Limited to 100 records per call to prevent timeout issues.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ids = serializer.validated_data["ids"]
        bulk_action = serializer.validated_data["action"]
        notes = serializer.validated_data.get("notes", "")

        user_orgs = list(
            request.user.organization_memberships.values_list("organization_id", flat=True)
        )

        queryset = ActivityRecord.objects.filter(
            id__in=ids,
            organization_id__in=user_orgs,
            is_deleted=False,
        )

        service = ReviewService()
        processed = 0
        failed = []

        for activity in queryset:
            try:
                if bulk_action == "approve":
                    service.approve(activity, request.user, notes)
                elif bulk_action == "reject":
                    service.reject(activity, request.user, notes)
                elif bulk_action == "flag":
                    service.flag(activity, request.user, notes)
                processed += 1
            except Exception as e:
                failed.append({"id": str(activity.id), "error": str(e)})

        # Log the bulk action. record_id is NULL for bulk operations (nullable field).
        org_id = user_orgs[0] if user_orgs else None
        AuditLog.objects.create(
            table_name="activities_activityrecord",
            record_id=None,          # nullable — bulk op affects many records
            action=f"bulk_{bulk_action}",
            changed_fields={
                "record_ids": [str(i) for i in ids],
                "processed_count": processed,
                "failed_count": len(failed),
                "notes": notes,
            },
            performed_by=request.user,
            organization_id=org_id,
        )

        return Response({
            "action": bulk_action,
            "requested": len(ids),
            "processed": processed,
            "failed": failed,
        })

    @action(detail=True, methods=["get"])
    def audit_trail(self, request, pk=None):
        """
        Return the complete audit history for a single ActivityRecord.

        Includes state transitions, edits, and any recalculations.
        """
        activity = self.get_object()
        logs = AuditLog.objects.filter(
            table_name="activities_activityrecord",
            record_id=activity.id,
        ).order_by("created_at")

        return Response({
            "activity_id": str(activity.id),
            "raw_data_row_id": (
                str(activity.raw_data_row.id) if activity.raw_data_row else None
            ),
            "audit_entries": [
                {
                    "action": log.action,
                    "changed_fields": log.changed_fields,
                    "performed_by": (
                        log.performed_by.email if log.performed_by else "system"
                    ),
                    "ip_address": log.ip_address,
                    "timestamp": log.created_at.isoformat(),
                }
                for log in logs
            ],
        })