# SOURCES — Research Documentation

For each source: what real-world format we researched, what we learned,
what our sample data looks like and why, and what would break in production.

---

## Source 1 — SAP Fuel & Procurement

### Real-World Format Researched

SAP MM (Materials Management) flat-file export via ABAP report MB51 (Material Document List)
or ME2M (Purchase Orders by Material).

**What a real SAP export looks like:**
```
Buchungskreis,Werk,Belegnummer,Belegdatum,Material,Menge,MEINH,Wert,Währung
1000,DE01,9000012345,15.03.2024,DIESEL KRAFTSTOFF,2500,L,3150.00,EUR
1000,US01,9000012346,03/15/2024,GASOLINE UNLEADED,750,GAL,2812.50,USD
```

**What we learned:**
- **Header language varies by deployment.** German SAP installations use German headers
  (Buchungskreis = Company Code, Werk = Plant, Menge = Quantity, MEINH = Unit of Measure).
  US installations may use English. The same client can have both if they operate globally.
- **Date formats are inconsistent even within one file.** German plants use DD.MM.YYYY;
  US plants use MM/DD/YYYY. SAP's internal date format is YYYYMMDD.
- **Units are whatever the material master says.** A client's global procurement team
  may record diesel in litres while their US operations record in gallons. There is
  no enforcement mechanism in standard SAP configuration.
- **European number formatting.** Large quantities use "." as thousands separator and
  "," as decimal: "1.500,75" means 1500.75 litres. The naive `.replace(",", "")` would
  produce 150075 — wrong by 100×.
- **Werk codes are meaningless without a lookup table.** "DE01" might be Düsseldorf
  or Dresden. The lookup table (our Facility model) is client-specific.
- **Summary rows appear in some export variants.** The ABAP report may include subtotal
  rows with "GESAMT" or "TOTAL" in the document number column.

### Sample Data Design

The platform's parsers are tested against data that includes:
- German headers (Buchungskreis, Werk, Belegnummer, Belegdatum, MEINH)
- Mixed date formats (DD.MM.YYYY and MM/DD/YYYY in the same file)
- Mixed units across rows: L, GAL, M3, KG, MT (metric tonnes)
- Multiple fuel types: diesel, natural gas, gasoline, jet fuel, LPG, fuel oil
- European large number: `15.500` (which means 15500 when combined with MT = 15.5 million kg!)
- Edge cases: missing plant code, unrecognised material

### What Would Break in Production

1. **Plant code churn:** Real SAP has thousands of plants. New plants are created
   and old ones are deactivated as the business changes. A static Facility lookup
   table needs an MDM (Master Data Management) sync process, not manual entry.

2. **Cost centre hierarchy:** We store one cost_center per transaction, but SAP's
   actual cost object model supports profit centres, WBS elements, and functional
   areas. A CFO wanting emissions attributed by business unit needs a cost centre
   hierarchy mapping — a significant additional model.

3. **Reversal documents:** SAP uses reversal/cancellation documents (storno) to
   correct mistakes. These appear as negative quantities with a reference to the
   original document number. Our parser currently rejects negative quantities.
   Production would need to match reversals to originals and net them out.

4. **Goods receipts vs invoice receipts:** MB51 captures goods receipts (physical
   fuel delivery). ME2M captures purchase orders (contracted quantity). These can
   differ due to delivery shortfalls, quality rejections, or split deliveries.
   The correct basis for Scope 1 is actual combustion (goods receipt), not
   contracted quantity (PO). The difference matters for accuracy.

---

## Source 2 — Utility Electricity

### Real-World Format Researched

Green Button CSV (ESPI standard) and proprietary utility portal CSV exports from
PG&E, ConEd, ComEd, Duke Energy, and National Grid.

**What a real utility export looks like:**
```
Account Number,Service,Start Date,End Date,Usage,Units,Demand,Cost,Notes
12345-67890,Electric,2024-01-15,2024-02-14,12450,kWh,145.2,1842.30,
12345-67890,Electric,2024-02-15,2024-03-14,13200,kWh,152.8,1953.60,
12345-67890,Electric,2024-03-15,2024-04-14,11800,kWh,138.5,1745.40,* Estimated read
```

**What we learned:**
- **Non-calendar billing periods are universal.** Every utility bill starts on a
  day determined by the meter read schedule, not the calendar. PG&E bills run
  on the 15th–14th. ConEd bills typically run 12th–11th. Our parser stores exact
  dates; we never assume monthly alignment.
- **Estimated reads are flagged in Notes.** When a meter reader can't access a site
  (locked building, dog in yard), the utility estimates consumption based on the
  same period last year. The flag appears as "Estimated," "Est.," "* Estimated read,"
  or in a separate ReadType column depending on the utility.
- **Multiple meters per facility.** A large office building may have a main meter
  plus separate meters for the server room, parking structure, and HVAC plant.
  All share the same service address but have different account numbers.
- **Demand charges (kW) appear alongside consumption charges (kWh).** Demand is
  the peak 15-minute draw in the billing period. It's used for tariff calculation
  but NOT for Scope 2 emissions — only kWh drives CO₂e.
- **Solar net metering produces negative kWh.** Facilities with solar panels can
  export excess generation back to the grid, appearing as a negative row on the bill.
  The GHG Protocol says to report net consumption for Scope 2, but the analyst
  should verify this isn't a billing error.

### Sample Data Design

The platform's parsers are tested against data that includes:
- Non-calendar billing periods (15th–14th and 12th–11th billing cycles)
- One estimated read row (flagged in Notes)
- Two account numbers linked to two hypothetical facilities
- One account spanning 62 days (suspicious long period — two bills merged)
- An unlinked account number (UNKNOWN-ACCT) that won't resolve to a Facility
- A variety of consumption levels (small office, large office, manufacturing)

### What Would Break in Production

1. **Time-of-use (TOU) rates:** Many commercial tariffs charge different rates for
   peak and off-peak consumption. The utility bill may break kWh into on-peak and
   off-peak buckets. For emissions purposes we sum all kWh; for spend analysis we'd
   need to model the tariff. Our parser sums them.

2. **Interval data (AMI):** Advanced Metering Infrastructure (smart meters) produce
   15-minute or hourly interval data — thousands of rows per meter per month. Our
   parser handles monthly billing CSV. Interval data requires aggregation logic and
   a different schema (one row per 15-minute interval, not one row per billing period).

3. **Multiple meters, one bill:** Some utilities produce a single bill for all meters
   at a campus, with sub-account line items. Our parser assumes one account number
   per row. A multi-account bill would need a pre-processing step.

4. **Non-US electricity:** Outside the US, eGRID doesn't exist. UK uses DEFRA grid
   factors; EU uses EEA national average factors; Australia uses NGER factors.
   International expansion requires a country → factor source mapping.

---

## Source 3 — Corporate Travel (Concur / Navan)

### Real-World Format Researched

SAP Concur Expense API v4 (REST + JSON) and the legacy Expense Web Services v2.
Also reviewed Navan (TripActions) API documentation.

**What a real Concur API response looks like:**
```json
{
  "id": "EXP-2024-001",
  "segmentTypeId": "AIRFR",
  "trip": {
    "airTrip": {
      "from": "LHR",
      "to": "JFK",
      "class": "business"
    }
  },
  "startDate": "2024-03-04",
  "amount": 4250,
  "currency": "GBP"
}
```

**Concur segment type codes (from official Concur documentation):**
- `AIRFR` — Air/flight
- `HOTEL` — Hotel accommodation
- `CARRT` — Car rental
- `TAXIF` — Taxi / private hire
- `RAILF` — Rail (train)
- `BUSF`  — Bus / ground transport

**What we learned:**
- **Distances are almost never in the data.** Concur records origin and destination
  but not the distance or actual fuel consumed. The distance-based calculation method
  (Haversine + uplift) is not a simplification — it's the only option available.
- **Cabin class is inconsistently coded.** Some Concur tenants use IATA codes
  (Y=economy, C=business, F=first), some use English words, some use company-internal
  codes. Our CLASS_MAP handles 15+ variants.
- **Hotel data is incomplete.** The number of nights is sometimes missing; we fall back
  to check-in/check-out dates. Some Concur configurations omit the hotel entirely
  (only the expense claim is recorded, not the booking details).
- **Concur API access requires a partner agreement.** SAP Concur restricts API access
  to apps registered in the Concur App Center. Most enterprise clients cannot grant
  API access without involving their Concur administrator and SAP.
- **The JSON schema varies by Concur version.** v4 (REST) uses camelCase; v2 (SOAP)
  uses different field names. Our parser checks multiple field name variants to be robust.

### Sample Data Design

The platform's parsers are tested against data that includes:
- Long-haul business class flight (LHR→JFK): high CO₂e, triggers policy warning
- Return economy class flight (JFK→LHR): same route, lower factor
- Hotel stays with explicit nights count and with check-in/check-out dates
- Short-haul European flight (FRA→CDG): ~450 km, short-haul factor
- Rail journey (London→Paris Eurostar): ~495 km
- Car rental segment with distance in miles (requires → km conversion)
- First-class long-haul (LHR→DXB): highest emission factor combination
- Invalid segment with unknown airports (XYZ, ABC): should produce an error row

**Why this sample data:**
Each segment exercises a different code path:
- Long-haul → DEFRA long-haul factor
- Short-haul → DEFRA short-haul factor
- Rail → DEFRA rail factor
- Business/first class → higher cabin class multiplier
- Unknown airports → graceful error, row marked invalid
- Miles → km conversion

### What Would Break in Production

1. **Airport database coverage:** A production system would use a full IATA airport database (OpenFlights.org publishes this under CC-BY licence). Any route with an airport not in our base set produces an error row.

2. **Flight routing accuracy:** The Haversine formula calculates great-circle distance. Real flight paths deviate significantly — transatlantic flights route via the North Atlantic Track system, not straight lines. The 8% uplift compensates partially but under-estimates for routes with significant curvature.

3. **Multi-segment itineraries:** A journey LHR→FRA→JFK is two segments. If Concur records it as one booking with two stops, our parser may not split it correctly. The stopovers matter because FRA→JFK is long-haul while LHR→FRA is short-haul.

4. **Currency and exchange rates:** We store cost in the transaction currency. For spend analysis, all costs need to be converted to a base currency using period exchange rates.

5. **Duty travel vs personal travel:** Employees sometimes book personal trips through the corporate travel tool. These should be excluded from Scope 3.
