# TRADEOFFS — Breathe ESG Carbon Accounting Platform

Three things we deliberately did not build, and why.

---

## 1. Market-Based Scope 2 (Renewable Energy Certificates)

**What we didn't build:**
The GHG Protocol Scope 2 Guidance (2015) requires companies to report both
*location-based* AND *market-based* Scope 2 if they participate in renewable energy
markets.  Market-based Scope 2 uses:
- Renewable Energy Certificates (RECs) / Guarantees of Origin (GOs)
- Power Purchase Agreements (PPAs) with specific suppliers
- Supplier-specific emission disclosure rates

We built location-based only (eGRID subregion factors).

**Why we didn't build it:**
Market-based Scope 2 requires a fundamentally different data model:

1. **Contractual instrument tracking:** Every REC/GO has a certificate serial number,
   vintage year, technology type, and geographic origin. These need to be matched
   against consumption periods — a non-trivial temporal joining problem.

2. **Supplier disclosure rates:** The client must obtain a separate emission factor
   from each electricity supplier, which is published annually and varies by supplier.
   This is a different data flow than eGRID (EPA publishes eGRID; the client must
   obtain supplier rates directly).

3. **Residual mix factors:** When RECs are retired, the remaining ("residual") grid
   has a different emission intensity than the gross grid. The Association of Issuing
   Bodies (AIB) and Green-e publish residual mix factors. These require a separate
   ingestion pipeline.

**The risk of building it badly:**
Incorrect market-based Scope 2 is worse than not reporting it. The GHG Protocol
explicitly says that if contractual instruments cannot be properly tracked and
verified, companies should fall back to location-based. Building a half-working
market-based module would give clients false confidence in numbers that may not
meet GHG Protocol criteria.

**What we'd build next:**
A `RECBatch` model linking RECs to `ActivityRecord` rows, with a flag distinguishing
location-based from market-based calculations, and a reconciliation view showing
unmatched REC surplus/deficit per period.

---

## 2. PDF Bill OCR for Utility Data

**What we didn't build:**
Utility bills are commonly distributed as PDF files. Many facilities teams have PDF
bills and no portal CSV access. We could have used AI-powered OCR to extract data
from PDFs.

**Why we didn't build it:**
OCR accuracy on financial documents is typically 95–99% for clean laser-printed bills,
falling to 60–80% for photographed, faxed, or low-resolution scanned bills.

This means: in the best case, 1 in 100 kWh values will be misread.
For a company with 200 facilities and monthly bills, that's 2 misread values per
month — compounding into a material misstatement over a reporting year.

Carbon reporting has **zero tolerance for systematic misstatement.** An auditor who
finds a pattern of OCR errors will question the entire dataset. The risk is asymmetric:
the efficiency gain from OCR is small (analysts spend ~30 seconds uploading a CSV
instead of a PDF), but the downside risk is large (audit qualification, restatement).

**The production solution:**
Commercial utility data aggregators — UtilityAPI, Arcadia, Urjanet — maintain
per-utility parsers that extract structured data from bills. They handle the
parsing complexity (each utility has a different bill format) and provide
structured output that our platform can ingest directly. The cost is ~$0.05–0.10
per bill and the accuracy approaches 100%. This is the right architectural choice
for production.

**What we built instead:**
A CSV parser that handles the Green Button schema and common proprietary formats.
This works for the majority of portal exports today and is 100% accurate on
well-formed CSV.

---

## 3. Real-Time Emission Factor Auto-Updates

**What we didn't build:**
A background job that automatically fetches and activates new emission factors
when EPA releases new eGRID data (~every 2 years) or DEFRA publishes updated
conversion factors (~annually).

**Why we didn't build it:**
Emission factor changes are **accounting policy changes**, not routine data updates.

If factors update silently:
- The same activity in 2023 produces different CO₂e numbers when recalculated today
  → this is a *restatement* without disclosure.
- Historical approved records appear to change → breaks the audit trail.
- If the new factor has a data quality issue, it immediately infects all calculations
  without a review step.

A GHG auditor's first question when they see a year-over-year CO₂e variance is
"what changed?" If factors auto-updated, the answer is "we don't know exactly when"
— which fails the audit.

**What we built instead:**
Explicit factor versioning with `effective_from`/`effective_to` dates. When a new
factor vintage is released:
1. An admin adds it with a new `source_version` and `effective_from` date.
2. The old factor is deactivated (`effective_to` set, `is_active=False`).
3. Historical records retain their original factor (lookup is date-bounded).
4. New and recalculated records use the new factor.
5. The `seed_factors` management command is the controlled activation mechanism.

This means every calculation can be traced to a specific factor vintage, and
any vintage update is an explicit, auditable admin action.