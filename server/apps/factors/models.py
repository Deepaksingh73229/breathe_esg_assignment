"""
Emission Factor models.

This module contains the authoritative lookup tables for all carbon calculations.
Every kg CO2e produced by the system must trace back to a specific row here.

Factor Categories:
1. PURCHASED ELECTRICITY (Scope 2, location-based)
   Source: EPA eGRID subregion-specific factors
   Unit: kg CO2e / kWh

2. STATIONARY FUEL (Scope 1)
   Source: IPCC / EPA / national inventories
   Unit: kg CO2e / kg fuel (or / liter, converted via density)

3. BUSINESS TRAVEL (Scope 3 Category 6)
   Source: UK DEFRA / GHG Protocol
   Unit: kg CO2e / passenger-km (flights), kg CO2e / km (ground), kg CO2e / night (hotel)
"""
from django.db import models
from apps.core.models import BaseModel


class EmissionFactor(BaseModel):
    """
    A versioned emission factor for converting activity data to CO2e.

    Example row:
        name: "eGRID2022 - RFCW - Electricity"
        source: "epa_egrid"
        source_version: "eGRID2022"
        activity_type: "purchased_electricity"
        region: "RFCW"  # eGRID subregion code
        co2e_kg_per_unit: 0.80205
        unit: "kwh"
        effective_from: 2022-01-01
        effective_to: None  # Still active

    The region field is polymorphic:
    - For electricity: eGRID subregion code (26 US subregions)
    - For travel: ISO country code ("US", "UK", "DE") or "global"
    - For fuel: Can be country-specific or "global" for IPCC defaults
    """

    # Factor provenance (where did this number come from?)
    SOURCE_CHOICES = [
        ("epa_egrid", "EPA eGRID"),           # US electricity grid factors
        ("defra", "UK DEFRA"),                # UK government travel/fuel factors
        ("ipcc", "IPCC"),                     # International Panel on Climate Change defaults
        ("epa", "EPA"),                       # US EPA general emission factors
        ("custom", "Custom"),                 # Client-specific or consultant-derived
    ]

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        help_text="Authority that published this factor. Determines credibility with auditors."
    )
    source_version = models.CharField(
        max_length=50,
        help_text="Specific vintage, e.g., 'eGRID2022', 'DEFRA_2025', 'IPCC_2019'."
    )

    # What activity does this factor apply to?
    ACTIVITY_TYPE_CHOICES = [
        ("purchased_electricity", "Purchased Electricity"),           # Scope 2
        ("purchased_heat_steam", "Purchased Heat/Steam"),             # Scope 2
        ("stationary_fuel", "Stationary Fuel Combustion"),          # Scope 1
        ("mobile_fuel", "Mobile Fuel Combustion"),                  # Scope 1
        ("business_travel_flight", "Business Travel - Flight"),     # Scope 3.6
        ("business_travel_rail", "Business Travel - Rail"),           # Scope 3.6
        ("business_travel_car", "Business Travel - Car/Ground"),    # Scope 3.6
        ("business_travel_taxi", "Business Travel - Taxi/Ride"),    # Scope 3.6
        ("business_travel_hotel", "Business Travel - Hotel"),       # Scope 3.6
    ]
    activity_type = models.CharField(
        max_length=30,
        choices=ACTIVITY_TYPE_CHOICES,
        db_index=True,
        help_text="Category of activity this factor converts."
    )

    # Geographic scope of the factor
    region = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Geographic code. For eGRID: subregion (RFCW). For travel: country (UK) or 'global'."
    )

    # Fuel specificity (only relevant for fuel combustion factors)
    FUEL_TYPE_CHOICES = [
        ("diesel", "Diesel"),
        ("gasoline", "Gasoline/Petrol"),
        ("natural_gas", "Natural Gas"),
        ("lpg", "LPG"),
        ("jet_kerosene", "Jet Kerosene"),
        ("fuel_oil", "Fuel Oil"),
        ("coal", "Coal"),
        ("", "Not Applicable"),
    ]
    fuel_type = models.CharField(
        max_length=20,
        choices=FUEL_TYPE_CHOICES,
        blank=True,
        default="",
        db_index=True,
        help_text="Specific fuel type. Empty for electricity and general travel factors."
    )

    # Distance band for travel factors (DEFRA uses different factors for short/medium/long-haul)
    DISTANCE_BAND_CHOICES = [
        ("", "Not Applicable"),
        ("short", "Short Haul (< 500 km)"),
        ("medium", "Medium Haul (500-3700 km)"),
        ("long", "Long Haul (> 3700 km)"),
        ("domestic", "Domestic"),
        ("international", "International"),
    ]
    distance_band = models.CharField(
        max_length=20,
        choices=DISTANCE_BAND_CHOICES,
        blank=True,
        default="",
        help_text="For flight factors: distance category determines emission intensity."
    )

    # Travel class multiplier (business class uses more space per passenger)
    TRAVEL_CLASS_CHOICES = [
        ("", "Not Applicable"),
        ("economy", "Economy"),
        ("premium_economy", "Premium Economy"),
        ("business", "Business"),
        ("first", "First Class"),
        ("average", "Average/Unknown"),
    ]
    travel_class = models.CharField(
        max_length=20,
        choices=TRAVEL_CLASS_CHOICES,
        blank=True,
        default="",
        help_text="For flights: emission factor varies by cabin class due to space allocation."
    )

    # The actual conversion rate
    co2e_kg_per_unit = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        help_text="Kilograms of CO2 equivalent per unit of activity. High precision for audit accuracy."
    )

    UNIT_CHOICES = [
        ("kwh", "kWh"),
        ("liter", "Liter (L)"),
        ("kg", "Kilogram (kg)"),
        ("km", "Kilometer (km)"),
        ("pax_km", "Passenger-kilometer"),
        ("night", "Hotel night"),
        ("m3", "Cubic meter (m³)"),
        ("gal", "US Gallon"),
    ]
    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        help_text="Unit of the activity amount that this factor applies to."
    )

    # Versioning dates
    effective_from = models.DateField(
        help_text="First date this factor vintage should be used (inclusive)."
    )
    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text="Last date this factor vintage should be used (inclusive). Null means still active."
    )

    # Active flag for quick filtering
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Quick filter. False suppresses the factor from new calculations without deleting history."
    )

    # Detailed metadata (stored as JSONB for flexibility)
    # Examples:
    # - electricity: {"co2_kg": 0.75, "ch4_kg": 0.01, "n2o_kg": 0.02, "losses_included": false}
    # - flights: {"rfi_included": true, "rfi_value": 1.9, "uplift_factor": 1.08}
    # - fuel: {"density_kg_per_liter": 0.85, "ncv_mj_per_kg": 43.0}
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extended provenance data: gas breakdown (CO2/CH4/N2O), RFI flags, density, etc."
    )

    # Human-readable name for admin display
    name = models.CharField(
        max_length=255,
        help_text="Descriptive name, e.g., 'DEFRA 2025 - Short-haul economy flight'"
    )

    class Meta:
        ordering = ["source", "activity_type", "region", "-effective_from"]
        verbose_name = "Emission Factor"
        verbose_name_plural = "Emission Factors"
        indexes = [
            # Critical lookup index: find the right factor for a calculation
            models.Index(fields=["activity_type", "region", "fuel_type", "is_active"]),
            models.Index(fields=["source", "source_version"]),
        ]
        constraints = [
            # Prevent duplicate active factors for the same activity+region+fuel combo
            models.UniqueConstraint(
                fields=["activity_type", "region", "fuel_type", "distance_band", "travel_class", "unit"],
                condition=models.Q(is_active=True),
                name="unique_active_factor_per_combo",
                violation_error_message="An active factor already exists for this activity/region/fuel combination."
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.source_version})"

    def is_effective_for_date(self, date):
        """Check if this factor should be used for a given activity date."""
        if not self.is_active:
            return False
        if date < self.effective_from:
            return False
        if self.effective_to and date > self.effective_to:
            return False
        return True
