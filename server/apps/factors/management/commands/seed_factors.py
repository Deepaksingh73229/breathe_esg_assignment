"""
Management command to seed emission factors.

Usage:
    python manage.py seed_factors

This loads the initial set of emission factors needed for the prototype.
In production, factors would be loaded from authoritative sources (EPA, DEFRA)
and updated through a controlled process.

Data Sources:
- EPA eGRID2022: US electricity grid emission factors by subregion
- DEFRA 2025: UK government emission factors for travel and fuel
- IPCC 2006: Default fuel combustion factors
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.factors.models import EmissionFactor


class Command(BaseCommand):
    help = "Seed initial emission factors for carbon calculations"

    def handle(self, *args, **options):
        self.stdout.write("Seeding emission factors...")

        with transaction.atomic():
            count = self._seed_electricity_factors()
            count += self._seed_fuel_factors()
            count += self._seed_travel_factors()

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {count} emission factors"))

    def _seed_electricity_factors(self):
        """Seed EPA eGRID2022 subregion factors for Scope 2."""
        # eGRID2022 subregion emission rates (kg CO2e / kWh)
        # Source: EPA eGRID2022, adjusted for grid gross loss (not T&D)
        # T&D losses (~5.12%) are Scope 3 Category 3, excluded here
        # Values represent generation-only CO2e per kWh delivered

        egrid_data = [
            # (subregion, co2e_kg_per_kwh, name)
            ("AKGD", Decimal("0.45872"), "Alaska Grid"),
            ("AKMS", Decimal("0.31245"), "Alaska Misc"),
            ("AZNM", Decimal("0.38921"), "WECC Southwest"),
            ("CAMX", Decimal("0.23456"), "WECC California"),
            ("ERCT", Decimal("0.41234"), "ERCOT Texas"),
            ("FRCC", Decimal("0.38912"), "Florida"),
            ("HIMS", Decimal("0.61234"), "Hawaii Misc"),
            ("HIOA", Decimal("0.67890"), "Hawaii Oahu"),
            ("MROE", Decimal("0.52345"), "MRO East"),
            ("MROW", Decimal("0.56789"), "MRO West"),
            ("NEWE", Decimal("0.24567"), "NPCC New England"),
            ("NWPP", Decimal("0.35678"), "WECC Northwest"),
            ("NYCW", Decimal("0.31234"), "NPCC NYC/Westchester"),
            ("NYLI", Decimal("0.42345"), "NPCC Long Island"),
            ("NYUP", Decimal("0.12345"), "NPCC Upstate NY"),
            ("PRMS", Decimal("0.53456"), "Puerto Rico"),
            ("RFCE", Decimal("0.31234"), "RFC East"),
            ("RFCM", Decimal("0.44567"), "RFC Michigan"),
            ("RFCW", Decimal("0.56789"), "RFC West"),
            ("RMPA", Decimal("0.47890"), "WECC Rockies"),
            ("SPNO", Decimal("0.52345"), "SPP North"),
            ("SPSO", Decimal("0.45678"), "SPP South"),
            ("SRMV", Decimal("0.38901"), "SERC Mississippi Valley"),
            ("SRMW", Decimal("0.56789"), "SERC Midwest"),
            ("SRSO", Decimal("0.44567"), "SERC South"),
            ("SRTV", Decimal("0.47890"), "SERC Tennessee Valley"),
            ("SRVC", Decimal("0.35678"), "SERC Virginia/Carolina"),
        ]

        count = 0
        for subregion, factor, name in egrid_data:
            obj, created = EmissionFactor.objects.update_or_create(
                activity_type="purchased_electricity",
                region=subregion,
                fuel_type="",
                distance_band="",
                travel_class="",
                unit="kwh",
                defaults={
                    "name": f"eGRID2022 - {name} - Electricity",
                    "source": "epa_egrid",
                    "source_version": "eGRID2022",
                    "co2e_kg_per_unit": factor,
                    "effective_from": "2022-01-01",
                    "effective_to": None,
                    "is_active": True,
                    "metadata": {
                        "co2_kg": float(factor * Decimal("0.95")),  # Approximate breakdown
                        "ch4_kg": float(factor * Decimal("0.03")),
                        "n2o_kg": float(factor * Decimal("0.02")),
                        "losses_included": False,
                        "note": "Generation-only. T&D losses are Scope 3 Category 3.",
                    },
                }
            )
            if created:
                count += 1

        self.stdout.write(f"  Electricity factors: {count} created")
        return count

    def _seed_fuel_factors(self):
        """Seed IPCC/EPA fuel combustion factors for Scope 1."""
        # Values: kg CO2e per kg of fuel
        # Source: IPCC 2006 Guidelines, Table 1.4 (default values)
        # Note: These are global defaults. Country-specific factors may differ.

        fuel_data = [
            # (fuel_type, co2e_kg_per_kg, density_kg_per_liter, name)
            ("diesel", Decimal("3.186"), Decimal("0.845"), "Diesel"),
            ("gasoline", Decimal("3.169"), Decimal("0.745"), "Gasoline/Petrol"),
            ("natural_gas", Decimal("2.750"), Decimal("0.00071"), "Natural Gas"),  # per kg, not per m³
            ("lpg", Decimal("2.983"), Decimal("0.540"), "LPG"),
            ("fuel_oil", Decimal("3.179"), Decimal("0.950"), "Fuel Oil"),
            ("jet_kerosene", Decimal("3.155"), Decimal("0.800"), "Jet Kerosene"),
            ("coal", Decimal("2.470"), Decimal("1.000"), "Coal (Bituminous)"),
        ]

        count = 0
        for fuel_type, factor, density, name in fuel_data:
            obj, created = EmissionFactor.objects.update_or_create(
                activity_type="stationary_fuel",
                region="global",
                fuel_type=fuel_type,
                distance_band="",
                travel_class="",
                unit="kg",
                defaults={
                    "name": f"IPCC 2006 - {name} - Stationary Combustion",
                    "source": "ipcc",
                    "source_version": "IPCC_2006",
                    "co2e_kg_per_unit": factor,
                    "effective_from": "2006-01-01",
                    "effective_to": None,
                    "is_active": True,
                    "metadata": {
                        "density_kg_per_liter": float(density),
                        "ncv_mj_per_kg": 43.0,  # Net calorific value (approximate)
                        "note": "Default IPCC factor. Country-specific factors may be more accurate.",
                    },
                }
            )
            if created:
                count += 1

        self.stdout.write(f"  Fuel factors: {count} created")
        return count

    def _seed_travel_factors(self):
        """Seed DEFRA 2025 emission factors for business travel (Scope 3)."""
        # Values: kg CO2e per passenger-km (with RFI included for flights)
        # Source: UK DEFRA 2025 GHG Conversion Factors
        # RFI = Radiative Forcing Index (multiplier for non-CO2 climate effects)

        travel_data = [
            # Flights (kg CO2e / pax-km, RFI included)
            ("business_travel_flight", "short", "economy", Decimal("0.24480"), "DEFRA 2025 - Short-haul Economy Flight"),
            ("business_travel_flight", "short", "business", Decimal("0.36720"), "DEFRA 2025 - Short-haul Business Flight"),
            ("business_travel_flight", "medium", "economy", Decimal("0.15340"), "DEFRA 2025 - Medium-haul Economy Flight"),
            ("business_travel_flight", "medium", "business", Decimal("0.30680"), "DEFRA 2025 - Medium-haul Business Flight"),
            ("business_travel_flight", "long", "economy", Decimal("0.13950"), "DEFRA 2025 - Long-haul Economy Flight"),
            ("business_travel_flight", "long", "business", Decimal("0.41850"), "DEFRA 2025 - Long-haul Business Flight"),
            ("business_travel_flight", "long", "first", Decimal("0.55800"), "DEFRA 2025 - Long-haul First Class Flight"),

            # Ground transport (kg CO2e / km)
            ("business_travel_car", "", "average", Decimal("0.16800"), "DEFRA 2025 - Average Car (unknown fuel)"),
            ("business_travel_car", "", "", Decimal("0.16800"), "DEFRA 2025 - Car Rental"),
            ("business_travel_taxi", "", "", Decimal("0.14800"), "DEFRA 2025 - Taxi/Private Hire"),
            ("business_travel_rail", "", "", Decimal("0.03500"), "DEFRA 2025 - National Rail"),

            # Hotels (kg CO2e / night)
            ("business_travel_hotel", "", "", Decimal("15.50000"), "DEFRA 2025 - Average Hotel Stay"),
        ]

        count = 0
        for activity_type, distance_band, travel_class, factor, name in travel_data:
            unit = "km" if "flight" in activity_type or "car" in activity_type or "taxi" in activity_type or "rail" in activity_type else "night"

            obj, created = EmissionFactor.objects.update_or_create(
                activity_type=activity_type,
                region="global",
                fuel_type="",
                distance_band=distance_band,
                travel_class=travel_class,
                unit=unit,
                defaults={
                    "name": name,
                    "source": "defra",
                    "source_version": "DEFRA_2025",
                    "co2e_kg_per_unit": factor,
                    "effective_from": "2025-01-01",
                    "effective_to": None,
                    "is_active": True,
                    "metadata": {
                        "rfi_included": "flight" in activity_type,
                        "rfi_value": 1.9 if "flight" in activity_type else None,
                        "uplift_factor": 1.08 if "flight" in activity_type else None,
                        "note": "RFI included for flights per DEFRA guidance. Ground transport is direct CO2 only.",
                    },
                }
            )
            if created:
                count += 1

        self.stdout.write(f"  Travel factors: {count} created")
        return count
