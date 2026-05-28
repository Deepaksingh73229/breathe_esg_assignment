from django.contrib import admin
from .models import EmissionFactor


@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    """
    Admin configuration for Emission Factors.
    Provides a user-friendly interface for non-technical admins to manage factors.
    """
    
    # Fields to display in the list view
    list_display = (
        "name",
        "activity_type",
        "region",
        "source",
        "source_version",
        "co2e_kg_per_unit",
        "unit",
        "is_active",
    )
    
    # Sidebar filters
    list_filter = (
        "is_active",
        "source",
        "activity_type",
        "region",
        "fuel_type",
        "unit",
    )
    
    # Search functionality
    search_fields = (
        "name",
        "source_version",
        "region",
    )
    
    # Organizing fields in the detail/edit view
    fieldsets = (
        ("Basic Information", {
            "fields": ("name", "is_active")
        }),
        ("Classification", {
            "fields": (
                "activity_type",
                "region",
                "fuel_type",
                "distance_band",
                "travel_class",
            )
        }),
        ("Source & Authority", {
            "fields": ("source", "source_version")
        }),
        ("Calculation Data", {
            "fields": ("co2e_kg_per_unit", "unit", "metadata")
        }),
        ("Validity Period", {
            "fields": ("effective_from", "effective_to")
        }),
        ("Audit Info", {
            "classes": ("collapse",),
            "fields": (
                "id",
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
                "is_deleted",
                "deleted_at",
                "deleted_by"
            )
        }),
    )
    
    # Read-only fields for audit integrity
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "deleted_at",
        "deleted_by",
    )

    def save_model(self, request, obj, form, change):
        """Automatically track who is making changes."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
