"""
Activities app configuration.

The Activities app holds the "Golden Record" — normalized, calculated,
and reviewable emission data. This is what analysts see and what auditors verify.

Every ActivityRecord represents one quantified emission event:
- 500 liters of diesel at Plant DE01 in March 2024 = X kg CO2e Scope 1
- 12,450 kWh electricity at Houston facility Jan 15-Feb 14 = Y kg CO2e Scope 2
- LHR→JFK business class flight = Z kg CO2e Scope 3

The review workflow ensures no data reaches auditors without human sign-off.
"""
from django.apps import AppConfig


class ActivitiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.activities"
    verbose_name = "Activity Records"
