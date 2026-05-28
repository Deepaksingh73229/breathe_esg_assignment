"""
ActivityRecord models.

This is the centerpiece of the Breathe ESG data model.
An ActivityRecord is a single, auditable, reviewable emission calculation.

It bridges three worlds:
1. RAW DATA (RawDataRow) - what the client gave us
2. ACTIVITY (activity_amount + activity_unit) - normalized, understandable
3. EMISSIONS (co2e_kg + co2e_calculation_audit) - defensible carbon math

Review Workflow:
- pending: Freshly ingested, awaiting analyst review
- flagged: Analyst marked for attention (e.g., "verify this plant code")
- approved: Analyst signed off, locked for reporting
- rejected: Data is wrong or duplicate, excluded from reporting

Edit Policy:
- Analysts CAN edit ActivityRecords (e.g., correct a misclassified fuel type)
- BUT every edit creates an audit trail with original_values snapshot
- RawDataRow is NEVER edited - it remains as evidence
"""
from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models import TenantModel

User = get_user_model()


class ActivityRecord(TenantModel):
    """
    A single normalized and calculated emission activity.

    This is the record that analysts review and auditors verify.
    Every field is designed to answer an auditor's question without ambiguity.
    """

    # === SOURCE LINEAGE (Critical for Audit) ===
    # These fields answer: "Where did this number come from?"

    ingestion_run = models.ForeignKey(
        "ingestion.IngestionRun",
        on_delete=models.PROTECT,  # PROTECT prevents deletion of ingestion run if records exist
        related_name="activity_records",
        help_text="The parent ingestion batch. PROTECT preserves audit trail even if run is deleted."
    )

    raw_data_row = models.OneToOneField(
        "ingestion.RawDataRow",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="derived_activity_record",
        help_text="The exact raw source row. One-to-one because each raw row produces one activity record."
    )

    source_system = models.CharField(
        max_length=20,
        choices=[
            ("sap", "SAP"),
            ("utility", "Utility Portal"),
            ("travel", "Concur/Navan"),
            ("manual", "Manual Entry"),
        ],
        db_index=True,
        help_text="Which external system produced the original data."
    )

    source_identifier = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Unique ID from source system. E.g., SAP Belegnummer, Concur expense ID, utility account+bill date."
    )

    # === FACILITY ATTRIBUTION ===
    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_records",
        help_text="Physical facility where the activity occurred. NULL for travel without fixed facility."
    )

    # === GHG PROTOCOL CLASSIFICATION ===
    # This classification determines which emission factor to use and how to report

    SCOPE_CHOICES = [
        ("1", "Scope 1 - Direct Emissions"),
        ("2", "Scope 2 - Indirect Electricity"),
        ("3", "Scope 3 - Value Chain"),
    ]
    scope = models.CharField(
        max_length=2,
        choices=SCOPE_CHOICES,
        db_index=True,
        help_text="GHG Protocol scope. Determines reporting bucket and audit requirements."
    )

    SCOPE_3_CATEGORY_CHOICES = [
        ("", "Not Applicable"),
        ("3.1", "3.1 - Purchased Goods & Services"),
        ("3.2", "3.2 - Capital Goods"),
        ("3.3", "3.3 - Fuel & Energy Related (Not in Scope 1/2)"),
        ("3.4", "3.4 - Upstream Transport"),
        ("3.5", "3.5 - Waste"),
        ("3.6", "3.6 - Business Travel"),
        ("3.7", "3.7 - Employee Commuting"),
        ("3.8", "3.8 - Upstream Leased Assets"),
    ]
    scope_3_category = models.CharField(
        max_length=10,
        choices=SCOPE_3_CATEGORY_CHOICES,
        blank=True,
        default="",
        db_index=True,
        help_text="Specific Scope 3 category. Empty for Scope 1 and 2."
    )

    ACTIVITY_TYPE_CHOICES = [
        ("stationary_fuel", "Stationary Fuel Combustion"),      # Scope 1
        ("mobile_fuel", "Mobile Fuel Combustion"),              # Scope 1
        ("purchased_electricity", "Purchased Electricity"),      # Scope 2
        ("purchased_heat_steam", "Purchased Heat/Steam"),        # Scope 2
        ("business_travel_flight", "Business Travel - Flight"),  # Scope 3.6
        ("business_travel_rail", "Business Travel - Rail"),      # Scope 3.6
        ("business_travel_car", "Business Travel - Car/Rental"), # Scope 3.6
        ("business_travel_taxi", "Business Travel - Taxi/Ride"), # Scope 3.6
        ("business_travel_hotel", "Business Travel - Hotel"),    # Scope 3.6
    ]
    activity_type = models.CharField(
        max_length=30,
        choices=ACTIVITY_TYPE_CHOICES,
        db_index=True,
        help_text="Type of activity. Determines which emission factor to apply."
    )

    # === NORMALIZED ACTIVITY DATA ===
    # All amounts stored in base units (kg, kWh, km, nights)
    # The ingestion parser handles unit conversion from source-specific units

    activity_amount = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        help_text="Normalized activity quantity in base units. E.g., kg of fuel, kWh of electricity, km of flight."
    )

    ACTIVITY_UNIT_CHOICES = [
        ("kwh", "kWh"),
        ("kg", "Kilogram (kg)"),
        ("km", "Kilometer (km)"),
        ("night", "Hotel night"),
    ]
    activity_unit = models.CharField(
        max_length=10,
        choices=ACTIVITY_UNIT_CHOICES,
        help_text="Base unit of the activity amount."
    )

    # === TEMPORAL DATA ===
    # Billing periods often DON'T align with calendar months.
    # We store the exact period to support accurate reporting.

    period_start = models.DateField(
        db_index=True,
        help_text="Start of the activity period (inclusive). E.g., utility bill start date."
    )
    period_end = models.DateField(
        db_index=True,
        help_text="End of the activity period (inclusive). E.g., utility bill end date."
    )

    # === GEOGRAPHIC DATA (for factor selection) ===
    country = models.CharField(
        max_length=2,
        default="US",
        help_text="ISO-3166 country code where activity occurred. Determines which factor set applies."
    )
    region = models.CharField(
        max_length=20,
        blank=True,
        help_text="Sub-national region for precise factor selection. E.g., eGRID subregion 'RFCW', or state 'TX'."
    )

    # === FUEL-SPECIFIC DATA (Scope 1) ===
    fuel_type = models.CharField(
        max_length=20,
        blank=True,
        help_text="Standardized fuel type. E.g., 'diesel', 'natural_gas'. Used with IPCC/EPA factors."
    )

    # Original unit before conversion (for audit transparency)
    original_amount = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Quantity as originally reported (before unit conversion). E.g., 500 liters."
    )
    original_unit = models.CharField(
        max_length=20,
        blank=True,
        help_text="Original unit from source. E.g., 'liter', 'gal', 'm³'."
    )
    conversion_note = models.TextField(
        blank=True,
        help_text="Human-readable explanation of unit conversion. E.g., '500 L × 0.845 kg/L = 422.5 kg'"
    )

    # === TRAVEL-SPECIFIC DATA (Scope 3) ===
    distance_band = models.CharField(
        max_length=20,
        blank=True,
        help_text="For flights: 'short', 'medium', 'long' per DEFRA classification."
    )
    travel_class = models.CharField(
        max_length=20,
        blank=True,
        help_text="For flights: 'economy', 'business', 'first'."
    )
    origin_location = models.CharField(
        max_length=100,
        blank=True,
        help_text="For travel: origin airport code, station name, or city."
    )
    destination_location = models.CharField(
        max_length=100,
        blank=True,
        help_text="For travel: destination airport code, station name, or city."
    )

    # === EMISSION CALCULATION RESULTS ===
    co2e_kg = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Total CO2 equivalent in kilograms. The number that goes to auditors."
    )

    # Full calculation audit trail (JSONB)
    # This is the DEFENSE against auditor challenge.
    # Example structure:
    # {
    #   "factor_applied": {"id": "uuid", "name": "eGRID2022 RFCW", "value": 0.80205},
    #   "calculation_math": "12450 kWh × 0.80205 kg/kWh = 9985.52 kg",
    #   "scope_rationale": "Purchased electricity = Scope 2 per GHG Protocol",
    #   "date_applied": "2024-03-15",
    #   "version": "1.0"
    # }
    co2e_calculation_audit = models.JSONField(
        default=dict,
        blank=True,
        help_text="Complete provenance of the CO2e calculation. Factor ID, math, rationale, timestamp."
    )

    # === ANALYST REVIEW WORKFLOW ===
    REVIEW_STATUS_CHOICES = [
        ("pending", "Pending Review"),    # Freshly ingested, needs analyst eyes
        ("flagged", "Flagged"),             # Analyst marked for attention
        ("approved", "Approved"),           # Signed off, ready for reporting
        ("rejected", "Rejected"),           # Excluded from reporting
    ]
    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default="pending",
        db_index=True,
        help_text="Current state in the analyst review workflow."
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_activities",
        help_text="Analyst who approved/rejected/flagged this record."
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of review action."
    )
    review_notes = models.TextField(
        blank=True,
        help_text="Analyst's free-text notes. E.g., 'Verified with facilities team - actual read, not estimated.'"
    )

    # === EDIT TRACKING (Immutable History) ===
    # ActivityRecords CAN be edited (unlike RawDataRows), but every edit is audited.

    is_edited = models.BooleanField(
        default=False,
        help_text="True if this record has been modified after initial creation."
    )
    edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edited_activities",
        help_text="User who made the last edit."
    )
    edited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last edit."
    )

    # Snapshot of original values before edit
    # Example: {"activity_amount": "500.000000", "fuel_type": "diesel", "scope": "1"}
    original_values = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON snapshot of fields before they were edited. Enables before/after comparison."
    )

    edit_reason = models.TextField(
        blank=True,
        help_text="Mandatory reason for edit. E.g., 'Corrected fuel type from gasoline to diesel per invoice.'"
    )

    # === UTILITY-SPECIFIC FLAGS ===
    is_estimated = models.BooleanField(
        default=False,
        help_text="For utility data: True if this bill was based on an estimated meter read."
    )

    # === METADATA BUCKET ===
    # Flexible storage for source-specific data that doesn't fit standard fields
    # E.g., utility demand_kw, travel great_circle_km, SAP cost_center
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Source-specific additional data. E.g., {'demand_kw': 450, 'utility_account': '12345'}."
    )

    class Meta:
        ordering = ["-period_start", "-created_at"]
        verbose_name = "Activity Record"
        verbose_name_plural = "Activity Records"
        indexes = [
            # Primary analyst query: "Show me pending Scope 1 records for my org"
            models.Index(fields=["organization", "scope", "review_status"]),
            # Period-based reporting queries
            models.Index(fields=["organization", "period_start", "period_end"]),
            # Source traceability
            models.Index(fields=["organization", "source_system", "source_identifier"]),
            # Facility attribution
            models.Index(fields=["facility", "review_status"]),
        ]
        constraints = [
            # Ensure period_end is not before period_start
            models.CheckConstraint(
                check=models.Q(period_end__gte=models.F("period_start")),
                name="period_end_after_start",
                violation_error_message="Activity period end must be on or after period start."
            ),
        ]

    def __str__(self):
        return f"{self.get_activity_type_display()} | {self.activity_amount} {self.activity_unit} | {self.co2e_kg or '---'} kg CO2e"

    @property
    def period_days(self):
        """Calculate duration of activity period in days."""
        if self.period_start and self.period_end:
            return (self.period_end - self.period_start).days + 1
        return None

    @property
    def is_approved(self):
        """Convenience property for template and API checks."""
        return self.review_status == "approved"
