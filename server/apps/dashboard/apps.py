"""
Dashboard app configuration.

Provides summary statistics and analytics for the analyst dashboard.
This is a read-only aggregation layer on top of ActivityRecords.

Key Metrics:
- Total CO2e by scope (pending vs approved)
- Review queue counts (how many need analyst attention)
- Ingestion health (success rates by source)
- Period-over-period trends
"""
from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"
    verbose_name = "Dashboard Analytics"
