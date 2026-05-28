"""
Facility Serializers.
"""
from rest_framework import serializers
from apps.facilities.models import Facility


class FacilitySerializer(serializers.ModelSerializer):
    """Serializer for Facility CRUD."""
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    egrid_subregion_effective = serializers.CharField(source="get_egrid_subregion", read_only=True)

    class Meta:
        model = Facility
        fields = [
            "id", "organization", "organization_name", "name", "sap_plant_code",
            "sap_cost_center", "address_line_1", "address_line_2", "city",
            "state_province", "postal_code", "country", "latitude", "longitude",
            "utility_account_numbers", "utility_provider_name", "egrid_subregion",
            "egrid_subregion_effective", "facility_type", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
