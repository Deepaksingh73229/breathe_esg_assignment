"""
Organizations app configuration.
This is the multi-tenancy root. Every piece of client data belongs to an Organization.
"""
from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.organizations"
    verbose_name = "Organizations"
