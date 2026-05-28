"""
Ingestion API Views.

Provides endpoints for:
- POST /api/v1/ingestion/ - Create a new ingestion run and upload file
- GET /api/v1/ingestion/{id}/ - Retrieve ingestion run with statistics
- GET /api/v1/ingestion/{id}/rows/ - List raw data rows for a run
- GET /api/v1/ingestion/{id}/errors/ - Summary of errors
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from apps.ingestion.models import IngestionRun, RawDataRow
from apps.ingestion.services import IngestionPipeline
from .serializers import IngestionRunSerializer, IngestionRunCreateSerializer, RawDataRowSerializer


class IngestionRunViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing data ingestion runs.

    create: Upload a file and trigger the ingestion pipeline.
    retrieve: Get ingestion statistics and status.
    list: List all ingestion runs for the organization.
    """
    queryset = IngestionRun.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["source_type", "status", "organization"]
    parser_classes = [MultiPartParser, FormParser]  # Required for file uploads

    def get_serializer_class(self):
        if self.action == "create":
            return IngestionRunCreateSerializer
        return IngestionRunSerializer

    def get_queryset(self):
        """Scope to user's organizations."""
        user_orgs = self.request.user.organization_memberships.values_list("organization_id", flat=True)
        return IngestionRun.objects.filter(organization_id__in=user_orgs)

    def perform_create(self, serializer):
        """
        Override create to run the ingestion pipeline after saving the run.
        Infers organization from user membership if not explicitly provided.
        """
        org = serializer.validated_data.get("organization")
        if not org:
            # Pick the first organization the user belongs to
            membership = self.request.user.organization_memberships.first()
            if not membership:
                raise serializers.ValidationError(
                    {"organization": "User does not belong to any organization."}
                )
            org = membership.organization

        # Save the ingestion run with uploaded file
        ingestion_run = serializer.save(created_by=self.request.user, organization=org)

        # Get the uploaded file from request
        file_obj = self.request.FILES.get("raw_file")
        if not file_obj:
            ingestion_run.status = "failed"
            ingestion_run.error_summary = {"file": "No file uploaded"}
            ingestion_run.save()
            return ingestion_run

        # Run the pipeline
        pipeline = IngestionPipeline()
        try:
            result = pipeline.process(ingestion_run, file_obj)
            # Store result in serializer context for response
            serializer.context["pipeline_result"] = result
        except Exception as e:
            ingestion_run.status = "failed"
            ingestion_run.error_summary = {"pipeline": str(e)}
            ingestion_run.save()
            serializer.context["pipeline_result"] = {
                "status": "failed",
                "reason": str(e),
            }

        return ingestion_run

    def create(self, request, *args, **kwargs):
        """Custom create to include pipeline results in response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        response_data = serializer.data
        response_data["pipeline_result"] = serializer.context.get("pipeline_result", {})

        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["get"])
    def rows(self, request, pk=None):
        """Get all raw data rows for this ingestion run."""
        ingestion_run = self.get_object()
        rows = ingestion_run.rows.all()

        # Filter by status if provided
        status_filter = request.query_params.get("status")
        if status_filter:
            rows = rows.filter(parsed_status=status_filter)

        serializer = RawDataRowSerializer(rows, many=True)
        return Response({
            "count": rows.count(),
            "results": serializer.data,
        })

    @action(detail=True, methods=["get"])
    def statistics(self, request, pk=None):
        """Get detailed statistics for an ingestion run."""
        run = self.get_object()
        return Response({
            "id": str(run.id),
            "status": run.status,
            "source_type": run.get_source_type_display(),
            "total_rows": run.total_rows,
            "valid_rows": run.valid_rows,
            "invalid_rows": run.invalid_rows,
            "suspicious_rows": run.suspicious_rows,
            "error_summary": run.error_summary,
            "period_start": run.period_start.isoformat() if run.period_start else None,
            "period_end": run.period_end.isoformat() if run.period_end else None,
            "checksum": run.checksum,
            "created_at": run.created_at.isoformat(),
        })
