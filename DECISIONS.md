# DECISIONS — Breathe ESG Carbon Accounting Platform

Every ambiguity we encountered, what we chose, why we chose it, and what
we'd ask the PM if we could.

---

## Source 1 — SAP Fuel & Procurement

### What real-world format did we choose?

**Flat-file CSV upload from SAP's standard ABAP report output.**

We chose this over:
- **OData service (SAP Gateway):** Requires a Gateway landscape, partner agreement,
  and IT provisioning — typically a 3-month procurement process. Unrealistic for
  an onboarding sprint.
- **IDoc (Intermediate Document):** IDoc is SAP-to-SAP messaging. You'd need your
  own SAP system as a receiver. Not viable for a SaaS analytics platform.
- **BAPI/RFC:** Requires an RFC-capable connector (SAP JCo library), VPN into the
  client's network, and a named SAP user. Security teams reject this 80% of the time.

**Realistic pattern:** The client's BASIS team runs a custom ABAP report (or a
standard MM60 / MB51 variant), exports it as CSV, and drops it on SFTP. The
sustainability consultant downloads it and uploads to our platform. This is what
actually happens in practice at every enterprise sustainability consulting firm.

### German vs English headers?

We support both by normalising headers at parse time using a mapping dict
(`HEADER_MAPPING`). We built the mapping from real SAP field names (MEINH =
unit, Menge = quantity, Werk = plant, Buchungskreis = company code).

### Unit handling?

SAP material masters record quantity in whatever unit the materials management
team configured — could be litres, gallons, kg, tonnes, or cubic metres.  There
is no enforcement of a consistent unit across plants.

We normalise everything to **kg** at parse time using IPCC 2006 fuel density tables.
The original quantity + unit + conversion math are preserved in `original_amount`,
`original_unit`, and `conversion_note` for full audit transparency.

**Critical correctness note:** "t" and "tonne" are metric tonnes (1 t = 1 000 kg),
NOT kilograms. A naive mapping of `"t" → "kg"` would understate emissions by 1 000×.
Our parser maps tonnes correctly.

### European number format?

SAP in European deployments uses "." as a thousands separator and "," as the
decimal separator: `1.234,56` means 1234.56.  Our `_parse_european_number()`
function handles all three formats (European, US, and plain).

### What would we ask the PM?

- "Does the client want us to handle mobile fleet fuel (company vehicles) as Scope 1,
  or is that managed through a separate telematics export?"
- "Are there any SAP cost centres we should *exclude* (e.g., canteen, facilities
  services) from the emission calculation?"
- "Is the plant code always populated, or does the BASIS team sometimes leave it
  blank for certain transaction types?"

---

## Source 2 — Utility Electricity

### What real-world format did we choose?

**Portal CSV export (Green Button-inspired schema).**

We chose this over:
- **PDF bill OCR:** OCR accuracy varies from 95–99% on clean laser prints to 60–80%
  on scanned or photographed bills. A single misread digit in kWh creates a material
  misstatement. The GHG Protocol requires accuracy; OCR guessing is incompatible
  with that requirement.
- **Utility API (e.g., UtilityAPI, Arcadia):** These aggregation services require
  the client to grant OAuth access to their utility portal accounts. Many corporate
  facilities teams don't have the authority to do this without IT approval. Good
  long-term solution, not available at onboarding.
- **Green Button XML (ESPI standard):** Green Button is the formal US DOE standard.
  We support its *schema* but accept CSV because the majority of portal exports are
  CSV, not ESPI XML.

**Green Button CSV** is the right choice because:
1. It's the closest to a standard in the industry.
2. Every major US utility (PG&E, ConEd, ComEd, Duke) exports in a CSV format
   compatible with the Green Button column names.
3. CSV is zero-parsing-risk compared to ESPI XML namespaces.

### Why eGRID subregion instead of national average?

The GHG Protocol Scope 2 Guidance (2015) requires "the most precise publicly
available emission factor."  The EPA publishes eGRID subregion factors for 26
US subregions.  Using the national average (~0.386 kg CO₂e/kWh) when a subregion
is determinable is a methodology violation.

The spread across subregions is significant:
- NYUP (upstate New York, hydro+nuclear heavy): 0.123 kg CO₂e/kWh
- RFCW (Ohio/Indiana, coal heavy): 0.568 kg CO₂e/kWh

A company in Ohio that uses national average *understates* its Scope 2 by ~32%.

### Why are T&D losses NOT in Scope 2?

EPA eGRID factors are *busbar-side* — they measure CO₂e at the point of electricity
generation, not at the customer's meter. Transmission and Distribution losses (~5%)
occur downstream of the busbar.

Per GHG Protocol Scope 2 Guidance §4, T&D losses are **Scope 3 Category 3**
(Fuel and Energy Related Activities Not in Scope 1 or 2).  Including them in
Scope 2 inflates that scope and breaks comparability with peer companies.

### Billing period handling?

Utility billing periods rarely align with calendar months (e.g., January 15 –
February 14). We store exact `period_start` and `period_end` dates as DateFields.
We flag billing periods >35 days (possible missed read) and <20 days (unusual
partial period) for analyst attention.

### What would we ask the PM?

- "Do any facilities have solar panels generating export credits? Negative kWh
  in a bill needs a policy decision: do we net off Scope 2, or report separately?"
- "Should we support market-based Scope 2 (using renewable energy certificates)?
  That requires tracking RECs and supplier-specific emission factors — a separate
  data model."
- "Which eGRID subregion should we use as a fallback for facilities with no
  postal code or GPS coordinates?"

---

## Source 3 — Corporate Travel

### What real-world format did we choose?

**JSON upload simulating Concur Expense API v4 export.**

We chose this over:
- **Live Concur API:** Requires an SAP Concur partner agreement. Most Concur tenants
  restrict API access to approved third-party apps. Not available at onboarding.
- **CSV export from Concur:** Concur does export CSV but the schema changes
  frequently and varies by client configuration. JSON is more structured and
  matches the API v4 schema we documented.
- **Navan / TripActions:** Same architecture as Concur but different field names.
  Our `SEGMENT_TYPE_MAP` can be extended to cover Navan with minimal changes.

### Why distance-based method for flights?

The GHG Protocol Business Travel guidance offers two methods:
1. **Fuel-based:** Most accurate. Requires per-flight fuel consumption from the airline.
   Airlines never share this with Concur or the traveller.
2. **Distance-based:** Approved fallback. Requires only origin + destination airports.

We use the distance-based method because fuel data is simply not available in
any corporate travel system we're aware of.

**Distance calculation:**
- Haversine great-circle formula between IATA airport coordinates
- × 1.08 uplift for indirect routing (DEFRA 2025, GHG Protocol guidance)
- DEFRA emission factors include Radiative Forcing Index (RFI ≈ 1.9) to account
  for non-CO₂ warming effects (contrails, NOₓ) at altitude

### DEFRA vs IPCC factors for travel?

DEFRA 2025 is the most up-to-date travel factor dataset with:
- Distance-band breakdown (short/medium/long-haul)
- Cabin class differentiation (business class uses ~3× the factor of economy
  because it occupies more seat-space per passenger)
- RFI already incorporated

IPCC 2006 doesn't have cabin-class breakdown. DEFRA is the correct choice.

### Hotel as optional Scope 3?

Hotel stays are Scope 3 Category 6 (Business Travel) but explicitly marked as
*optional* in the GHG Protocol. We include them because:
1. The data is available (Concur includes hotel bookings).
2. It allows clients to report "full" business travel, not just flights.
3. An analyst can easily reject hotel records if the client opts not to report them.

### What would we ask the PM?

- "Should we calculate emissions for domestic flights differently? Some clients
  prefer to use national averages rather than DEFRA (UK-centric) factors for
  non-UK routes."
- "What do we do with taxi/ride-share segments that have no distance? Should we
  default to the average UK taxi journey (~8 km) or require manual entry?"
- "Does the client want to report employee commuting (Scope 3 Category 7) through
  the same travel platform, or is that a separate survey-based process?"

---

## Technology Decisions

### Why Next.js 15 (App Router)?

Next.js 15 was chosen for the frontend to leverage:
1. **Server Components** — Data-heavy views like the Activity List and Dashboard summary are rendered on the server, reducing the JavaScript payload sent to the analyst's browser and improving initial load performance.
2. **Streaming & Suspense** — Complex dashboard charts can be streamed as they are ready, providing a "skeleton" UI that feels responsive even during heavy data aggregation.
3. **Type-Safe Routing** — App Router's file-based routing combined with TypeScript ensures that navigation between facilities, factors, and audit logs is robust and error-free.

### Why uv for Python Package Management?

We use `uv` instead of standard `pip` or `poetry` because:
1. **Performance** — `uv` is significantly faster at resolving and installing dependencies, which is critical for CI/CD pipelines and developer productivity in a growing codebase.
2. **Unified Tooling** — `uv` handles virtual environments, dependency locking (`uv.lock`), and Python version management (`.python-version`) in a single, high-performance tool.
3. **Deterministic Builds** — The `uv.lock` file ensures that every developer and production environment uses the exact same package versions, eliminating "it works on my machine" issues.

### Why PostgreSQL (not SQLite, MySQL, or MongoDB)?

Four reasons:
1. **JSONB fields** — `RawDataRow.raw_payload` and `co2e_calculation_audit` need
   efficient semi-structured storage with indexing. PostgreSQL JSONB is the
   best-in-class solution.
2. **ArrayField** — `Facility.utility_account_numbers` is a variable-length array.
   PostgreSQL's native `ARRAY` type with index support is the clean solution.
3. **ACID transactions with savepoints** — Our per-row savepoint strategy in the
   ingestion pipeline requires nested transactions. PostgreSQL handles this natively.
4. **CheckConstraint support** — `period_end >= period_start` enforced at the DB level.

### Why flat-file upload instead of API polling?

API polling (cron job hitting SAP / Concur / Utility APIs on a schedule) is the
production architecture. However:
- It requires client credentials, VPN access, and IT approvals.
- The APIs are unstable during onboarding (schema changes, access revocations).
- File upload is the lowest-common-denominator that works on day one of every
  client engagement.

### Why Token authentication instead of JWT?

DRF's built-in `rest_framework.authtoken` tokens are simpler, server-side revocable,
and don't require a refresh-token flow. For a prototype with a single backend
service, token auth is the right choice. JWTs add complexity (key rotation, token
blacklisting) without benefit at this scale.

### Why soft deletion everywhere?

Carbon data may have been included in regulatory filings or investor disclosures.
Physically deleting it would create a gap in the audit trail. Soft deletion
preserves all records while excluding them from active queries.

---

## What We Would Change With More Time

1. **Market-based Scope 2:** Our model supports location-based method only.
   Market-based Scope 2 requires tracking renewable energy certificates (RECs)
   and supplier emission factors — a substantial additional data model.

2. **Automated factor updates:** Currently `seed_factors` is run manually.
   Production should have a controlled process: new factor vintages are staged,
   reviewed, and activated by an admin — never auto-applied silently.

3. **SFTP / email ingestion:** An SFTP dropzone or email-based ingestion would
   eliminate the manual upload step and support automated monthly batch processing.