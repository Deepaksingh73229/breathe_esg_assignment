"""
Dashboard API Views.

Aggregation endpoints for the React analyst dashboard.
All endpoints are scoped to the user's organizations.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import datetime, timedelta

from apps.activities.models import ActivityRecord
from apps.ingestion.models import IngestionRun
from apps.facilities.models import Facility


class DashboardViewSet(viewsets.ViewSet):
    """
    Dashboard analytics endpoints.

    No model directly - this is a read-only aggregation viewset.
    """
    permission_classes = [IsAuthenticated]

    def get_user_organizations(self):
        """Helper to get user's organization IDs."""
        return self.request.user.organization_memberships.values_list("organization_id", flat=True)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """
        Main dashboard summary.

        Returns:
        - Total approved CO2e by scope
        - Pending review counts
        - Flagged items count
        - Recent ingestion activity
        """
        org_ids = self.get_user_organizations()

        # CO2e totals by scope (approved only)
        scope_totals = ActivityRecord.objects.filter(
            organization_id__in=org_ids,
            review_status="approved",
            is_deleted=False,
        ).values("scope").annotate(
            total_co2e=Sum("co2e_kg"),
            count=Count("id"),
        ).order_by("scope")

        # Review queue breakdown
        review_queue = ActivityRecord.objects.filter(
            organization_id__in=org_ids,
            is_deleted=False,
        ).values("review_status").annotate(
            count=Count("id"),
            total_co2e=Sum("co2e_kg"),
        ).order_by("review_status")

        # Recent ingestion runs (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_ingestions = IngestionRun.objects.filter(
            organization_id__in=org_ids,
            created_at__gte=thirty_days_ago,
            is_deleted=False,
        ).values("source_type", "status").annotate(
            count=Count("id"),
        ).order_by("source_type")

        # Facility coverage
        facility_count = Facility.objects.filter(
            organization_id__in=org_ids,
            is_active=True,
            is_deleted=False,
        ).count()

        return Response({
            "scope_totals": {
                item["scope"]: {
                    "total_co2e_kg": float(item["total_co2e"] or 0),
                    "record_count": item["count"],
                } for item in scope_totals
            },
            "review_queue": {
                item["review_status"]: {
                    "count": item["count"],
                    "total_co2e_kg": float(item["total_co2e"] or 0),
                } for item in review_queue
            },
            "recent_ingestions": list(recent_ingestions),
            "facility_count": facility_count,
            "organization_count": len(org_ids),
        })

    @action(detail=False, methods=["get"])
    def review_queue(self, request):
        """
        Detailed review queue data.

        Query params:
        - ?scope=1|2|3
        - ?source_type=sap|utility|travel
        - ?status=pending|flagged
        """
        org_ids = self.get_user_organizations()

        queryset = ActivityRecord.objects.filter(
            organization_id__in=org_ids,
            is_deleted=False,
        )

        # Apply filters
        scope = request.query_params.get("scope")
        if scope:
            queryset = queryset.filter(scope=scope)

        source_type = request.query_params.get("source_type")
        if source_type:
            queryset = queryset.filter(source_system=source_type)

        status_filter = request.query_params.get("status", "pending,flagged")
        statuses = status_filter.split(",")
        queryset = queryset.filter(review_status__in=statuses)

        # Annotate with facility name for display
        from django.db.models import OuterRef, Subquery
        facility_names = Facility.objects.filter(id=OuterRef("facility_id")).values("name")[:1]
        queryset = queryset.annotate(facility_name=Subquery(facility_names))

        # Pagination
        page_size = int(request.query_params.get("page_size", 50))
        page = int(request.query_params.get("page", 1))
        start = (page - 1) * page_size
        end = start + page_size

        total = queryset.count()
        records = queryset[start:end]

        data = []
        for r in records:
            data.append({
                "id": str(r.id),
                "activity_type": r.get_activity_type_display(),
                "scope": r.get_scope_display(),
                "source_system": r.get_source_system_display(),
                "activity_amount": float(r.activity_amount),
                "activity_unit": r.activity_unit,
                "co2e_kg": float(r.co2e_kg) if r.co2e_kg else None,
                "period_start": r.period_start.isoformat() if r.period_start else None,
                "period_end": r.period_end.isoformat() if r.period_end else None,
                "facility_name": getattr(r, "facility_name", None) or "Unassigned",
                "review_status": r.review_status,
                "is_estimated": r.is_estimated,
                "is_edited": r.is_edited,
                "created_at": r.created_at.isoformat(),
                "parse_errors": r.raw_data_row.parse_errors if r.raw_data_row else [],
            })

        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": data,
        })

    @action(detail=False, methods=["get"])
    def trends(self, request):
        """
        Monthly CO2e trends by scope.

        Query params:
        - ?months=6 (default 6 months back)
        """
        org_ids = self.get_user_organizations()
        months = int(request.query_params.get("months", 6))

        start_date = timezone.now() - timedelta(days=30 * months)

        trends = ActivityRecord.objects.filter(
            organization_id__in=org_ids,
            review_status="approved",
            is_deleted=False,
            period_start__gte=start_date,
        ).annotate(
            month=TruncMonth("period_start")
        ).values("month", "scope").annotate(
            total_co2e=Sum("co2e_kg"),
            count=Count("id"),
        ).order_by("month", "scope")

        # Reformat for charting
        months_data = {}
        for item in trends:
            month_key = item["month"].strftime("%Y-%m") if item["month"] else "unknown"
            if month_key not in months_data:
                months_data[month_key] = {"month": month_key, "scope_1": 0, "scope_2": 0, "scope_3": 0, "total": 0}

            scope_key = f"scope_{item['scope']}"
            co2e = float(item["total_co2e"] or 0)
            months_data[month_key][scope_key] = co2e
            months_data[month_key]["total"] += co2e

        return Response({
            "months": months,
            "data": list(months_data.values()),
        })

    @action(detail=False, methods=["get"])
    def ingestion_health(self, request):
        """
        Ingestion success rates and recent activity.
        """
        org_ids = self.get_user_organizations()

        # Overall stats
        total_runs = IngestionRun.objects.filter(
            organization_id__in=org_ids,
            is_deleted=False,
        )

        by_source = total_runs.values("source_type").annotate(
            total=Count("id"),
            successful=Count("id", filter=Q(status="parsed")),
            failed=Count("id", filter=Q(status="failed")),
            partial=Count("id", filter=Q(status="partial")),
        )

        # Recent runs (last 10)
        recent = total_runs.order_by("-created_at")[:10]
        recent_data = []
        for run in recent:
            recent_data.append({
                "id": str(run.id),
                "source_type": run.get_source_type_display(),
                "status": run.status,
                "total_rows": run.total_rows,
                "valid_rows": run.valid_rows,
                "invalid_rows": run.invalid_rows,
                "created_at": run.created_at.isoformat(),
            })

        return Response({
            "by_source": list(by_source),
            "recent_runs": recent_data,
        })
