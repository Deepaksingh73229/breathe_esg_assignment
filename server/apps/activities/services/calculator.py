"""
Emission Calculation Engine.

This is the carbon accounting brain. Every CO2e number produced here must be
fully defensible to an external auditor — that is the primary design constraint.

Calculation Philosophy
----------------------
1. Look up the CORRECT emission factor (right activity type, right region, right date)
2. Apply the factor with complete transparency (show the exact arithmetic)
3. Record EVERYTHING in co2e_calculation_audit JSONB so no auditor can say
   "we don't know how you got this number"

Supported Calculations
----------------------
  Scope 1  Stationary Fuel:   kg_fuel   × IPCC/EPA factor (kg CO2e / kg fuel)
  Scope 2  Electricity:       kWh       × eGRID subregion factor (kg CO2e / kWh)
  Scope 3  Flights:           km        × DEFRA distance-band+class factor (kg CO2e / km, RFI incl.)
  Scope 3  Ground transport:  km        × DEFRA mode factor (kg CO2e / km)
  Scope 3  Hotels:            nights    × DEFRA factor (kg CO2e / night)

T&D Loss Note
-------------
eGRID factors are busbar-side (generation only).
T&D losses (~5 %) are Scope 3 Category 3, NOT Scope 2.
Including them in Scope 2 inflates that scope and breaks inter-company comparability.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Any, Dict, Tuple

from django.db.models import Q

from apps.factors.models import EmissionFactor
from apps.activities.models import ActivityRecord


class FactorLookupError(Exception):
    """
    Raised when no suitable emission factor can be found.

    The pipeline catches this, marks the ActivityRecord 'flagged', and writes
    the error into the review notes so an analyst can resolve it.
    """


class EmissionCalculator:
    """
    Calculates CO2e for ActivityRecords using versioned emission factors.

    Usage:
        co2e, audit = EmissionCalculator().calculate(activity)
    """

    def calculate(self, activity: ActivityRecord) -> Tuple[Decimal, Dict[str, Any]]:
        """
        Calculate CO2e and return (co2e_kg, audit_dict).

        Raises FactorLookupError if no valid factor is found.
        The caller is responsible for storing the results on the ActivityRecord.
        """
        factor = self._lookup_factor(activity)

        amount = activity.activity_amount
        factor_value = factor.co2e_kg_per_unit
        co2e = (amount * factor_value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

        audit: Dict[str, Any] = {
            "factor_applied": {
                "factor_id": str(factor.id),
                "factor_name": factor.name,
                "source": factor.get_source_display(),
                "source_version": factor.source_version,
                "region": factor.region,
                "co2e_kg_per_unit": str(factor_value),
                "unit": factor.get_unit_display(),
                "effective_from": factor.effective_from.isoformat(),
                "effective_to": (
                    factor.effective_to.isoformat() if factor.effective_to else None
                ),
            },
            "calculation_math": (
                f"{amount} {activity.activity_unit} "
                f"× {factor_value} kg CO2e/{factor.unit} "
                f"= {co2e} kg CO2e"
            ),
            "activity_details": {
                "activity_type": activity.get_activity_type_display(),
                "amount": str(amount),
                "unit": activity.activity_unit,
                "period": f"{activity.period_start} to {activity.period_end}",
                "facility": activity.facility.name if activity.facility else "Unassigned",
            },
            "scope_rationale": self._get_scope_rationale(activity),
            "calculation_timestamp": date.today().isoformat(),
            "calculator_version": "1.0",
        }

        # Fuel-specific provenance
        if activity.fuel_type:
            audit["fuel_details"] = {
                "fuel_type": activity.fuel_type,
                "original_amount": (
                    str(activity.original_amount) if activity.original_amount else None
                ),
                "original_unit": activity.original_unit,
                "conversion_note": activity.conversion_note,
            }

        # Travel-specific provenance
        TRAVEL_TYPES = {
            "business_travel_flight", "business_travel_rail",
            "business_travel_car", "business_travel_taxi",
        }
        if activity.activity_type in TRAVEL_TYPES:
            audit["travel_details"] = {
                "distance_band": activity.distance_band,
                "travel_class": activity.travel_class,
                "origin": activity.origin_location,
                "destination": activity.destination_location,
            }
            if activity.activity_type == "business_travel_flight":
                audit["travel_details"]["methodology_note"] = (
                    "Distance = Haversine great-circle × 1.08 indirect-routing uplift. "
                    "Emission factor includes Radiative Forcing Index (RFI ≈ 1.9) "
                    "per DEFRA 2025 guidance."
                )

        if factor.metadata:
            audit["factor_metadata"] = factor.metadata

        return co2e, audit

    def _lookup_factor(self, activity: ActivityRecord) -> EmissionFactor:
        """
        Find the best-matching active emission factor for this activity.

        Lookup priority:
          1. activity_type — always required
          2. region        — exact match first, then country, then 'global'
          3. fuel_type     — required for Scope 1; empty for electricity/travel
          4. distance_band — required for flights
          5. travel_class  — required for flights
          6. effective date — factor must be in effect on activity.period_start

        Raises FactorLookupError with a descriptive message if nothing matches.
        """
        qs = EmissionFactor.objects.filter(
            activity_type=activity.activity_type,
            is_active=True,
        )

        # ── Region resolution ─────────────────────────────────────────────────
        region = (
            activity.region
            or (activity.organization.egrid_subregion if activity.organization else "")
            or activity.country
            or ""
        )

        if activity.activity_type == "purchased_electricity":
            # Electricity: eGRID subregion is required — no global fallback exists
            if not region:
                raise FactorLookupError(
                    f"Activity {activity.id} has no region and the organisation has no "
                    "default eGRID subregion. Set Organization.egrid_subregion to proceed."
                )
            qs = qs.filter(region=region)
        else:
            # All other types: try exact region, then country, then 'global'
            region_qs = qs.filter(region=region)
            if not region_qs.exists():
                country = activity.country or (
                    activity.organization.country if activity.organization else ""
                )
                region_qs = qs.filter(Q(region=country) | Q(region="global"))
            qs = region_qs

        # ── Fuel type ─────────────────────────────────────────────────────────
        if activity.fuel_type and activity.fuel_type != "unknown":
            qs = qs.filter(fuel_type=activity.fuel_type)

        # ── Distance band and travel class ────────────────────────────────────
        if activity.distance_band:
            qs = qs.filter(distance_band=activity.distance_band)
        if activity.travel_class:
            qs = qs.filter(travel_class=activity.travel_class)

        # ── Effective date ────────────────────────────────────────────────────
        # Factor must be in effect on the activity's period_start date.
        ref = activity.period_start
        qs = qs.filter(effective_from__lte=ref).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=ref)
        )

        # Most recently effective factor wins when multiple vintages match
        qs = qs.order_by("-effective_from")
        factor = qs.first()

        if not factor:
            fuel_info = (
                f", fuel_type='{activity.fuel_type}'" if activity.fuel_type else ""
            )
            band_info = (
                f", distance_band='{activity.distance_band}'" if activity.distance_band else ""
            )
            class_info = (
                f", travel_class='{activity.travel_class}'" if activity.travel_class else ""
            )
            raise FactorLookupError(
                f"No active emission factor found for "
                f"activity_type='{activity.activity_type}'"
                f", region='{region}'"
                f"{fuel_info}{band_info}{class_info}"
                f", effective on {ref}. "
                "Run 'python manage.py seed_factors' or add a custom factor via Admin."
            )

        return factor

    def recalculate(self, activity: ActivityRecord) -> None:
        """
        Recalculate CO2e for an existing ActivityRecord.

        Called after:
        - An analyst edits a calculation input (fuel_type, amount, region, etc.)
        - Emission factors are updated to a new vintage

        Updates co2e_kg and co2e_calculation_audit in-place.
        """
        co2e, audit = self.calculate(activity)
        activity.co2e_kg = co2e
        activity.co2e_calculation_audit = audit
        activity.save(update_fields=["co2e_kg", "co2e_calculation_audit", "updated_at"])

    @staticmethod
    def _get_scope_rationale(activity: ActivityRecord) -> str:
        """Return the GHG Protocol rationale for this activity's scope classification."""
        rationales = {
            "stationary_fuel": (
                "Stationary combustion in owned/controlled equipment is Scope 1 (Direct Emissions) "
                "per GHG Protocol Corporate Standard §4."
            ),
            "mobile_fuel": (
                "Mobile combustion in owned/controlled vehicles is Scope 1. "
                "Leased or employee-owned vehicles would be Scope 3."
            ),
            "purchased_electricity": (
                "Purchased electricity is Scope 2 (Indirect Emissions). "
                "Location-based method: eGRID subregion factor applied. "
                "T&D losses (~5 %) excluded — they are Scope 3 Category 3 "
                "per GHG Protocol Scope 2 Guidance."
            ),
            "business_travel_flight": (
                "Business travel by air is Scope 3 Category 6. "
                "Distance-based method with DEFRA factors including Radiative Forcing Index (RFI). "
                "RFI multiplier accounts for contrail and NOx warming effects at altitude."
            ),
            "business_travel_rail": (
                "Business travel by rail is Scope 3 Category 6 (purchased transport service)."
            ),
            "business_travel_car": (
                "Business travel by rental/hired car is Scope 3 Category 6. "
                "If company-owned, this would be Scope 1."
            ),
            "business_travel_taxi": (
                "Taxi/ride-share for business travel is Scope 3 Category 6."
            ),
            "business_travel_hotel": (
                "Hotel accommodation for business travel is Scope 3 Category 6 (optional reporting). "
                "Global average DEFRA factor applied per DEFRA 2025 guidance."
            ),
        }
        return rationales.get(
            activity.activity_type,
            "Scope classification per GHG Protocol Corporate Standard.",
        )