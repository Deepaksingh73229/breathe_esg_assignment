# DATA MODEL — Breathe ESG Carbon Accounting Platform

> This document explains **why** the data model is structured the way it is.
> Every design decision was made to answer a specific auditor or analyst question
> without ambiguity.

---

## Core Philosophy

Carbon accounting has one non-negotiable requirement: **every CO₂e number that
reaches an auditor must be fully traceable back to its source**.

An auditor will ask:

1. *"Where did this 1 234 kg CO₂e come from?"*
2. *"Which emission factor version did you use, and why?"*
3. *"Was this record edited after ingestion? If so, what changed and who approved it?"*
4. *"Show me the original file the client gave you."*

The data model is designed to answer all four questions completely.

---

## Entity Overview

```
Organization (tenant root)
  └── Facility (physical location)
        └── ActivityRecord (one emission event)
              ├── RawDataRow (immutable source evidence)
              ├── IngestionRun (batch upload metadata)
              ├── EmissionFactor (versioned conversion rate)
              └── AuditLog (append-only change history)
```

---

## 1. Organisation & Multi-Tenancy

```python
class Organization(BaseModel):
    name              CharField
    slug              SlugField (unique)
    egrid_subregion   CharField   # default eGRID subregion for Scope 2
    country           CharField   # ISO-3166 alpha-2
    is_active         BooleanField
```

**Multi-tenancy strategy:** Single Database, Shared Schema, application-level isolation.

Every business model inherits `TenantModel`, which adds a non-nullable
`organization` FK. Every query is scoped by `organization_id`. A database index
on this column keeps per-tenant queries fast as the shared table grows.

**Why not separate schemas per tenant?** Schema-per-tenant requires schema-switching
middleware and complicates migrations. Application-level isolation is simpler,
auditable, and sufficient for the enterprise-SaaS threat model (authenticated users
with role-based access can't accidentally see another tenant's data).

---

## 2. Facility

```python
class Facility(TenantModel):
    name                     CharField
    sap_plant_code           CharField   # Werk code from SAP
    sap_cost_center          CharField   # optional, for granular attribution
    address_line_1/2, city, state_province, postal_code, country
    latitude, longitude      Decimal     # WGS84 — preferred for eGRID lookup
    utility_account_numbers  ArrayField  # one facility may have multiple meters
    utility_provider_name    CharField
    egrid_subregion          CharField   # overrides org default if set
    facility_type            CharField   # manufacturing | office | warehouse | ...
    is_active                BooleanField
```

**Key design decisions:**

- `sap_plant_code` is the bridge between SAP's opaque Werk code (e.g., "DE01")
  and a real geographic location. Without this mapping, SAP data cannot be
  attributed to a region for emission factor selection.
- `utility_account_numbers` is an ArrayField because a single facility commonly
  has multiple metered connections (main building + annexe + parking garage).
  Storing them in the same row avoids a join on the hot ingestion path.
- `egrid_subregion` can override the organisation default. A company with
  headquarters in NYC (subregion NYCW) and a factory in Texas (subregion ERCT)
  needs different Scope 2 factors for each facility.

---

## 3. Ingestion Pipeline — Immutable Raw Data

The ingestion layer enforces the principle that **source data is immutable**.

```python
class IngestionRun(TenantModel):
    source_type      CharField   # sap | utility | travel
    ingestion_method CharField   # csv_upload | json_upload | api_pull
    raw_file         FileField   # original file as received
    checksum         CharField   # SHA-256 of raw_file (tamper evidence)
    status           CharField   # pending | parsing | parsed | failed | partial
    total_rows       PositiveIntegerField
    valid_rows       PositiveIntegerField
    invalid_rows     PositiveIntegerField
    suspicious_rows  PositiveIntegerField
    error_summary    JSONField   # aggregated errors for the dashboard
    period_start     DateField   # earliest activity date in the batch
    period_end       DateField   # latest activity date in the batch
```

```python
class RawDataRow(TenantModel):
    ingestion_run    FK(IngestionRun)
    source_row_number PositiveIntegerField   # 1-based row number in source file
    raw_payload      JSONField               # EXACT row data, unmodified
    parsed_status    CharField  # pending | valid | invalid | suspicious | skipped
    parse_errors     JSONField  # list of human-readable error/warning strings
    activity_record  OneToOneField(ActivityRecord, null=True)
    source_identifier CharField  # extracted document ID / account+date key
    raw_period_start  DateField
    raw_period_end    DateField
```

**Why store the raw file AND a JSON copy of every row?**

- The raw file (with SHA-256 checksum) proves the file wasn't tampered with after upload.
- The JSONB `raw_payload` in RawDataRow stores the *parsed* row so analysts can see
  exactly what the source contained without re-reading the file.
- If the parser is improved (bug fixed, new column supported), the file can be
  re-ingested from storage without the client re-uploading it.

**Why is RawDataRow OneToOne with ActivityRecord?**

Each source row produces exactly one normalised ActivityRecord.  A one-to-one
constraint enforces this and prevents accidental double-counting.

---

## 4. ActivityRecord — The Golden Record

```python
class ActivityRecord(TenantModel):
    # Source lineage (answers: "where did this number come from?")
    ingestion_run     FK(IngestionRun, on_delete=PROTECT)
    raw_data_row      OneToOneFK(RawDataRow, on_delete=PROTECT)
    source_system     CharField   # sap | utility | travel | manual
    source_identifier CharField   # SAP Belegnummer, Concur expense ID, etc.

    # GHG Protocol classification
    scope             CharField   # 1 | 2 | 3
    scope_3_category  CharField   # 3.6 Business Travel, etc.
    activity_type     CharField   # stationary_fuel | purchased_electricity | ...

    # Normalised activity data (always SI/base units)
    activity_amount   DecimalField(20, 6)
    activity_unit     CharField   # kwh | kg | km | night

    # Temporal (billing periods don't align with calendar months)
    period_start      DateField
    period_end        DateField

    # Geographic (for factor selection)
    country           CharField   # ISO-3166 alpha-2
    region            CharField   # eGRID subregion, state, or country

    # Fuel-specific (Scope 1)
    fuel_type         CharField   # diesel | natural_gas | etc.
    original_amount   DecimalField  # quantity before unit conversion
    original_unit     CharField     # liter | gal | m3 | tonne
    conversion_note   TextField     # human-readable math: "500 L × 0.845 kg/L = 422.5 kg"

    # Travel-specific (Scope 3)
    distance_band     CharField   # short | medium | long
    travel_class      CharField   # economy | business | first
    origin_location   CharField   # airport IATA code or station name
    destination_location CharField

    # Calculation results
    co2e_kg           DecimalField(20, 6)
    co2e_calculation_audit JSONField  # complete provenance: factor ID, math, timestamp

    # Review workflow
    review_status     CharField   # pending | flagged | approved | rejected
    reviewed_by       FK(User, null=True)
    reviewed_at       DateTimeField(null=True)
    review_notes      TextField

    # Edit tracking
    is_edited         BooleanField
    edited_by         FK(User, null=True)
    edited_at         DateTimeField(null=True)
    original_values   JSONField    # snapshot of fields before the edit
    edit_reason       TextField    # mandatory reason (audit compliance)

    # Flags
    is_estimated      BooleanField  # utility: estimated meter read
    metadata          JSONField     # overflow for source-specific extras
```

**Key design decisions:**

- `on_delete=PROTECT` on the `ingestion_run` and `raw_data_row` FKs prevents
  accidental deletion of an ingestion run that has ActivityRecords derived from it.
  If you need to remove data, you must explicitly reject and soft-delete the records first.
- `period_start`/`period_end` as DateFields (not a month bucket). Utility billing
  periods cross month boundaries. We store exact dates and prorate to months only
  at reporting time.
- The `original_amount`/`original_unit`/`conversion_note` trio makes unit
  conversion transparent. An auditor can see: "500 litres of diesel → 422.5 kg
  → 1 345.5 kg CO₂e" without reverse-engineering anything.
- `co2e_calculation_audit` JSONB contains the full provenance: factor ID, factor
  name, factor version, exact arithmetic, and timestamp. This is what you show an
  auditor who challenges a number.

---

## 5. Emission Factors — Versioned and Time-Bounded

```python
class EmissionFactor(BaseModel):
    source          CharField   # epa_egrid | defra | ipcc | epa | custom
    source_version  CharField   # eGRID2022 | DEFRA_2025 | IPCC_2006
    activity_type   CharField
    region          CharField   # eGRID subregion | ISO country | "global"
    fuel_type       CharField   # blank for electricity and travel factors
    distance_band   CharField   # blank | short | medium | long
    travel_class    CharField   # blank | economy | business | first | average
    co2e_kg_per_unit DecimalField(20, 10)  # high precision for audit accuracy
    unit            CharField   # kwh | kg | km | night | ...
    effective_from  DateField
    effective_to    DateField(null=True)   # null = currently active
    is_active       BooleanField
    metadata        JSONField   # gas breakdown (CO2/CH4/N2O), RFI flag, etc.
```

**Why version emission factors?**

EPA releases new eGRID data every ~2 years. DEFRA updates factors annually.
If factors auto-updated silently, the same activity in 2023 would produce
different CO₂e numbers when recalculated today — an auditor would flag this
as a restatement without explanation.

By recording `effective_from`/`effective_to`, when we calculate an ActivityRecord
dated March 2023 we use the factor that was active in March 2023, even if a
newer factor exists today. Every calculation audit trail records the exact factor
version used.

**UniqueConstraint on active factors:**
A `UniqueConstraint(condition=Q(is_active=True))` prevents two active factors
for the same `activity_type + region + fuel_type + distance_band + travel_class + unit`.
This makes factor lookup deterministic — there is always exactly zero or one active
factor per combination.

---

## 6. Audit Log — Append-Only, Never Deleted

```python
class AuditLog(UUIDPrimaryKeyMixin, TimestampedMixin):
    table_name      CharField
    record_id       UUIDField(null=True)   # null for bulk operations
    action          CharField   # create | update | delete | review_transition | bulk_* | ...
    changed_fields  JSONField   # before/after snapshot + reason
    performed_by    FK(User, null=True)
    ip_address      GenericIPAddressField
    user_agent      TextField
    organization_id UUIDField(null=True)
```

**Why a separate AuditLog table and not Django's admin log?**

Django's `LogEntry` only records admin-site actions, has a string-based content
type system that's awkward to query, and doesn't capture IP address or custom
change details. Our AuditLog is purpose-built for carbon accounting compliance:

- Stores the full `changed_fields` JSONB: `{"original_values": {...}, "new_values": {...}, "reason": "..."}`
- `record_id` is nullable so bulk operations (e.g., "approve 50 records") produce
  a single aggregate log entry rather than 50 identical ones.
- `organization_id` is denormalised (not a FK) so audit logs survive even if
  the organisation is soft-deleted.

---

## Scope 1/2/3 Classification

| `activity_type`           | Scope | Category | Source          |
|---------------------------|-------|----------|-----------------|
| `stationary_fuel`         | 1     | —        | SAP             |
| `purchased_electricity`   | 2     | —        | Utility         |
| `business_travel_flight`  | 3     | 3.6      | Travel platform |
| `business_travel_rail`    | 3     | 3.6      | Travel platform |
| `business_travel_car`     | 3     | 3.6      | Travel platform |
| `business_travel_taxi`    | 3     | 3.6      | Travel platform |
| `business_travel_hotel`   | 3     | 3.6      | Travel platform |

---

## Unit Normalisation

All `activity_amount` values are stored in base SI units:

| Scope | Unit  | Reason |
|-------|-------|--------|
| Scope 1 fuel | `kg`    | IPCC factors are kg CO₂e / kg fuel |
| Scope 2      | `kwh`   | eGRID factors are kg CO₂e / kWh |
| Scope 3 travel (air/ground) | `km` | DEFRA factors are kg CO₂e / passenger-km |
| Scope 3 hotel | `night` | DEFRA factors are kg CO₂e / hotel night |

Volume → mass conversion (litres, gallons, m³ → kg) happens in the SAP parser
using IPCC 2006 fuel density tables.  The original quantity and the conversion
math are preserved in `original_amount`, `original_unit`, and `conversion_note`.

---

## Database Indexes

Critical indexes for query performance:

```sql
-- Analyst primary query: "show me pending Scope 1 records for this org"
INDEX (organization_id, scope, review_status)

-- Period-based reporting
INDEX (organization_id, period_start, period_end)

-- Source traceability / dedup
INDEX (organization_id, source_system, source_identifier)

-- Facility attribution
INDEX (facility_id, review_status)

-- SAP ingestion lookup
INDEX (organization_id, sap_plant_code)

-- Utility account routing
INDEX (organization_id, postal_code)

-- Audit forensics
INDEX (table_name, record_id)
INDEX (organization_id, action)
```

---

## Soft Deletion Policy

No business data is physically deleted.

Rationale: A record may have been included in a submitted GHG report to
regulators, investors, or auditors.  Deleting it would break the chain of
evidence.  Instead, `is_deleted=True` excludes the record from active queries
while preserving it for historical reporting and audit access.

The `BaseManager` automatically filters `is_deleted=False` from all default
queries.  Use `Model.all_objects.filter(...)` to include deleted records
(audit and compliance views only).