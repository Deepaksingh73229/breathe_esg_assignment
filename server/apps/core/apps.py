"""
Core app configuration.
This app provides base models, mixins, and utilities used by all other apps.
It has no dependencies on other local apps.
"""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"
