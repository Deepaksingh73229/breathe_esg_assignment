"""
Factors app configuration.

Emission factors are the conversion rates that turn activity data (liters of diesel,
kWh of electricity, km of flight) into CO2 equivalent (kg CO2e).

CRITICAL DESIGN DECISION: Factors are versioned and time-bounded.

Why? Because emission factors change:
- EPA releases new eGRID data every ~2 years (2020, 2022, 2024...)
- DEFRA updates factors annually
- Grid decarbonization means electricity factors decrease over time

An auditor will ask: "Which factor vintage did you use for FY2023?"
We must be able to answer precisely. Therefore, every factor has:
- source_version: e.g., "eGRID2022", "DEFRA_2025"
- effective_from/to: date range when this factor was the "active" one
- is_active: current flag for quick lookup

When we calculate an ActivityRecord from 2024, we use the factor that was
active in 2024, even if a newer factor exists today.
"""
from django.apps import AppConfig


class FactorsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.factors"
    verbose_name = "Emission Factors"
