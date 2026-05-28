"""
Audit API Views.

Provides read-only access to audit logs for compliance and debugging.
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.audit.models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for audit logs.

    list: Query audit logs with filters
    retrieve: Get a specific audit entry

    Filtering:
    - ?table_name=activities_activityrecord
    - ?action=update
    - ?organization_id=uuid
    - ?performed_by=userid
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["table_name", "action", "organization_id", "performed_by"]

    def get_queryset(self):
        """
        Scope to user's organizations. 
        System superadmins can see ALL logs.
        """
        if self.request.user.is_superuser:
            return AuditLog.objects.all()
            
        user_orgs = self.request.user.organization_memberships.values_list("organization_id", flat=True)
        return AuditLog.objects.filter(organization_id__in=user_orgs)

    @action(detail=False, methods=["get"])
    def by_record(self, request):
        """Get audit history for a specific record."""
        table_name = request.query_params.get("table_name")
        record_id = request.query_params.get("record_id")

        if not table_name or not record_id:
            return Response({"error": "Both table_name and record_id are required"}, status=400)

        logs = AuditLog.objects.filter(table_name=table_name, record_id=record_id).order_by("created_at")
        serializer = self.get_serializer(logs, many=True)
        return Response({
            "count": logs.count(),
            "results": serializer.data,
        })
