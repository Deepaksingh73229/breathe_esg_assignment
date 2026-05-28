"""
Facilities app configuration.

A Facility represents a physical location (plant, office, warehouse) within
an Organization. It holds the mapping between SAP plant codes and real-world
location data needed for emission factor selection.
"""
from django.apps import AppConfig


class FacilitiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.facilities"
    verbose_name = "Facilities"
