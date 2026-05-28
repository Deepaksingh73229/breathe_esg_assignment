"""
Emission Factor API Views.
"""
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend

from apps.factors.models import EmissionFactor
from .serializers import EmissionFactorSerializer


class EmissionFactorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for emission factors.

    Factors are managed by system administrators, not end users.
    Analysts can browse and view factor details for transparency.

    Filtering:
    - ?activity_type=purchased_electricity
    - ?region=RFCW
    - ?fuel_type=diesel
    - ?is_active=true
    """
    queryset = EmissionFactor.objects.filter(is_active=True)
    serializer_class = EmissionFactorSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activity_type", "region", "fuel_type", "distance_band", 
                        "travel_class", "is_active", "source"]
