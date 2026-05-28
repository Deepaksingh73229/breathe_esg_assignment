"""
Facility API Views.
"""
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend

from apps.facilities.models import Facility
from .serializers import FacilitySerializer


class FacilityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing facilities.

    list: List facilities for user's organizations
    retrieve: Get facility details
    create: Add new facility (admin only)
    update: Modify facility details
    """
    queryset = Facility.objects.filter(is_active=True, is_deleted=False)
    serializer_class = FacilitySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["organization", "facility_type", "is_active", "sap_plant_code"]

    def get_queryset(self):
        """Scope to user's organizations."""
        user_orgs = self.request.user.organization_memberships.values_list("organization_id", flat=True)
        return Facility.objects.filter(organization_id__in=user_orgs, is_deleted=False)
