"""
Emission Factor Serializers.
"""
from rest_framework import serializers
from apps.factors.models import EmissionFactor


class EmissionFactorSerializer(serializers.ModelSerializer):
    """Serializer for EmissionFactor CRUD."""
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    activity_type_display = serializers.CharField(source="get_activity_type_display", read_only=True)
    unit_display = serializers.CharField(source="get_unit_display", read_only=True)
    fuel_type_display = serializers.CharField(source="get_fuel_type_display", read_only=True)
    distance_band_display = serializers.CharField(source="get_distance_band_display", read_only=True)
    travel_class_display = serializers.CharField(source="get_travel_class_display", read_only=True)

    class Meta:
        model = EmissionFactor
        fields = [
            "id", "name", "source", "source_display", "source_version",
            "activity_type", "activity_type_display", "region", "fuel_type",
            "fuel_type_display", "distance_band", "distance_band_display",
            "travel_class", "travel_class_display", "co2e_kg_per_unit",
            "unit", "unit_display", "effective_from", "effective_to",
            "is_active", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
