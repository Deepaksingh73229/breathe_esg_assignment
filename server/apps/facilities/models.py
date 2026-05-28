"""
Facility models.

Facilities are the physical anchor for all emissions data.
Every ActivityRecord links to a Facility (or null for travel without a fixed facility).

Key mappings:
- SAP plant code -> Facility (for fuel/procurement data normalization)
- Utility account number -> Facility (for electricity data routing)
- Zip code / lat-lng -> eGRID subregion (for Scope 2 factor selection)
"""
from django.db import models
from django.contrib.postgres.fields import ArrayField
from apps.core.models import TenantModel


class Facility(TenantModel):
    """
    A physical location belonging to an Organization.

    Examples: Manufacturing plant, corporate office, warehouse, data center.

    SAP Integration:
    - sap_plant_code: The Werk (plant) code from SAP. Often meaningless without
      this lookup table (e.g., "DE01" could be Dusseldorf or Dresden).
    - sap_cost_center: Optional cost center for finer-grained attribution.

    Utility Integration:
    - utility_account_numbers: Array of account numbers with the electric utility.
      A single facility may have multiple meters (main building + parking garage).

    Geolocation:
    - latitude/longitude: Used for precise eGRID subregion lookup.
    - zip_code: Fallback for eGRID lookup when lat/lng unavailable.
    - egrid_subregion_override: If the facility is in a different subregion than
      the organization's default (e.g., headquarters in NYC but plant in Texas).
    """
    name = models.CharField(
        max_length=255,
        help_text="Human-readable facility name, e.g., 'Houston Manufacturing Plant'"
    )

    # SAP mapping fields
    sap_plant_code = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text="SAP Werk (plant) code. Used to map SAP export rows to facilities."
    )
    sap_cost_center = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optional SAP cost center for granular attribution."
    )

    # Address fields (structured for geocoding and eGRID lookup)
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        help_text="Postal/ZIP code. Primary key for eGRID subregion lookup in the US."
    )
    country = models.CharField(
        max_length=2,
        default="US",
        help_text="ISO-3166 country code."
    )

    # Geolocation (optional but preferred for accuracy)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="WGS84 latitude. Used for precise eGRID subregion determination."
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="WGS84 longitude."
    )

    # Utility account tracking
    utility_account_numbers = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        help_text="Electric utility account numbers associated with this facility."
    )
    utility_provider_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name of electric utility (e.g., 'Pacific Gas & Electric')."
    )

    # Emission factor override
    egrid_subregion = models.CharField(
        max_length=10,
        blank=True,
        db_index=True,
        help_text="EPA eGRID subregion override. If blank, uses Organization default."
    )

    # Metadata
    facility_type = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ("manufacturing", "Manufacturing"),
            ("office", "Office"),
            ("warehouse", "Warehouse"),
            ("data_center", "Data Center"),
            ("retail", "Retail"),
            ("other", "Other"),
        ],
        help_text="Type of facility. Affects analyst expectations (e.g., data centers use lots of electricity)."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive facilities are excluded from new ingestion but preserved historically."
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Facility"
        verbose_name_plural = "Facilities"
        # Critical index: when ingesting SAP data, we look up by org + plant code
        indexes = [
            models.Index(fields=["organization", "sap_plant_code"]),
            models.Index(fields=["organization", "postal_code"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

    def get_egrid_subregion(self):
        """Returns the effective eGRID subregion for this facility."""
        return self.egrid_subregion or self.organization.egrid_subregion
