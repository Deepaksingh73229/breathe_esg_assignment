from django.contrib import admin
from .models import Facility


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "facility_type", "country", "is_active")
    list_filter = ("facility_type", "country", "is_active", "organization")
    search_fields = ("name", "organization__name")
