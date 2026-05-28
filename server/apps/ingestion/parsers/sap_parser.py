"""
SAP Fuel & Procurement Data Parser.

Real-World Context
------------------
SAP exports for fuel/procurement are flat-file CSV dumps from SAP ECC / S4HANA.
They are NOT standardised. Every client's BASIS team configures the extract differently.

Common characteristics we handle:
  - German column headers in European deployments (Buchungskreis, Werk, Belegdatum)
  - Mixed units: liters, gallons, kg, m³ depending on plant location + material master
  - Plant codes (Werk) that are opaque without a lookup table (DE01, US-TX-HOU-01)
  - Document numbers (Belegnummer) as the natural source identifier
  - Dates in DD.MM.YYYY or YYYYMMDD format
  - European number formats: thousands separator "." and decimal separator ","
    e.g., "1.234,56" means 1234.56 — NOT 1.234 or 1234

Deliberate Scope Decisions (documented in DECISIONS.md)
---------------------------------------------------------
- Flat-file CSV upload (not OData/BAPI): realistic enterprise pattern; you rarely
  get live API access to a client's SAP.
- Scope 1 stationary combustion only: mobile fleet fuel is a separate source type.
- Tonne → kg conversion: 1 metric tonne = 1 000 kg (critical correctness fix).
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Generator, List

import pandas as pd
from dateutil import parser as date_parser

from apps.facilities.models import Facility
from .base import BaseParser, ParseResult


# ── Header normalisation ──────────────────────────────────────────────────────
# Maps both German SAP field names and common English variants to canonical names.
# Built from real SAP IDoc/flat-file samples and the SAP MM (Materials Management) schema.
HEADER_MAPPING = {
    # German names (common in European SAP deployments)
    "buchungskreis": "company_code",
    "werk": "plant_code",
    "belegnummer": "document_number",
    "belegdatum": "document_date",
    "buchungsdatum": "posting_date",
    "material": "material_code",
    "menge": "quantity",
    "meinh": "unit",
    "menge_meinh": "quantity",
    "wert": "value",
    "währung": "currency",
    "gjahr": "fiscal_year",
    "kostenstelle": "cost_center",
    "lieferant": "vendor",

    # English / abbreviated variants
    "company_code": "company_code",
    "plant": "plant_code",
    "plant_code": "plant_code",
    "document_number": "document_number",
    "document_no": "document_number",
    "doc_no": "document_number",
    "document_date": "document_date",
    "posting_date": "posting_date",
    "date": "document_date",
    "material_code": "material_code",
    "material": "material_code",
    "quantity": "quantity",
    "qty": "quantity",
    "unit": "unit",
    "uom": "unit",
    "unit_of_measure": "unit",
    "value": "value",
    "amount": "value",
    "currency": "currency",
    "fiscal_year": "fiscal_year",
    "cost_center": "cost_center",
    "vendor": "vendor",
    "supplier": "vendor",
}


# ── Fuel classification ────────────────────────────────────────────────────────
# Material descriptions from the SAP material master vary by client.
# We match on keywords (case-insensitive). Order matters: more specific first.
FUEL_KEYWORDS = {
    "jet_kerosene": ["jet fuel", "kerosene", "kerosin", "aviation fuel", "turbine fuel"],
    "diesel":       ["diesel", "gasoil", "gas oil", "derv", "dieseloel", "diesel kraftstoff"],
    "gasoline":     ["gasoline", "petrol", "benzin", "essence", "unleaded"],
    "natural_gas":  ["natural gas", "erdgas", "gas nat", "lng", "cng", "erdgas"],
    "lpg":          ["lpg", "propane", "butane", "flüssiggas", "autogas"],
    "fuel_oil":     ["fuel oil", "heating oil", "brennstoff", "heizöl", "fueloil", "hfo", "mfo"],
    "coal":         ["coal", "anthracite", "bituminous", "kohle", "coke"],
}


# ── Unit normalisation ─────────────────────────────────────────────────────────
# Maps the raw unit string from SAP to the canonical unit we store and pass to
# the emission calculator.
#
# CRITICAL: "t" / "tonne" is NOT "kg". 1 metric tonne = 1 000 kg.
# We store the canonical unit and apply mass conversion in the pipeline so the
# emission calculator always receives kg.
UNIT_MAPPING = {
    # Volume
    "l": "liter", "ltr": "liter", "litre": "liter", "liters": "liter",
    "litres": "liter",
    "gal": "gal", "gallon": "gal", "gallons": "gal", "us gal": "gal",
    "m3": "m3", "m³": "m3", "cbm": "m3", "cubic meter": "m3",
    "cubic metre": "m3",
    # Mass — note tonne → "tonne" (not "kg"); conversion happens below
    "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
    "t": "tonne", "mt": "tonne", "ton": "tonne", "tons": "tonne",
    "tonne": "tonne", "tonnes": "tonne", "metric ton": "tonne",
    # Energy
    "kwh": "kwh", "kw/h": "kwh", "kilowatt hour": "kwh",
    "mwh": "mwh",
    # Distance (rare in SAP but possible for fleet fuel records)
    "km": "km", "kilometer": "km", "kilometres": "km",
    "mi": "mi", "mile": "mi", "miles": "mi",
}


# ── Fuel density (kg / litre at 15 °C) ────────────────────────────────────────
# Source: IPCC 2006 Guidelines, Table 1.2.  Used to convert volume → mass so
# the emission calculator can apply kg CO2e / kg fuel factors.
FUEL_DENSITY_KG_PER_LITRE = {
    "diesel":       Decimal("0.845"),
    "gasoline":     Decimal("0.745"),
    "lpg":          Decimal("0.540"),
    "fuel_oil":     Decimal("0.950"),
    "jet_kerosene": Decimal("0.800"),
}

# Natural gas density at 15 °C, 1 atm — needed when SAP records gas in m³
# Source: GPA Engineering Data Book (2012): 0.717 kg/m³ for pipeline-quality NG
NATURAL_GAS_DENSITY_KG_PER_M3 = Decimal("0.717")


# ── Sanity bounds (raw quantity per transaction line) ─────────────────────────
# If a quantity exceeds these bounds the row is marked "suspicious" so an
# analyst verifies the unit before approving.
SANITY_BOUNDS = {
    "diesel":       (Decimal("0.1"),  Decimal("1_000_000")),   # litres
    "gasoline":     (Decimal("0.1"),  Decimal("1_000_000")),
    "natural_gas":  (Decimal("0.1"),  Decimal("10_000_000")),  # m³
    "lpg":          (Decimal("0.1"),  Decimal("500_000")),
    "fuel_oil":     (Decimal("0.1"),  Decimal("500_000")),
    "jet_kerosene": (Decimal("0.1"),  Decimal("500_000")),
}


def _parse_european_number(s: str) -> Decimal:
    """
    Parse a number that may use European formatting.

    European style: "1.234,56"  → 1234.56
    US/ISO style:   "1,234.56"  → 1234.56
    Simple:         "1234.56"   → 1234.56

    Strategy:
    - If both "." and "," are present, the last one is the decimal separator.
    - If only "," is present, treat it as decimal separator (European style).
    - If only "." is present or neither, treat as standard.
    """
    s = s.strip()
    last_dot = s.rfind(".")
    last_comma = s.rfind(",")

    if last_dot > 0 and last_comma > 0:
        # Both present — whichever appears last is the decimal separator
        if last_comma > last_dot:
            # European: "1.234,56" → remove ".", replace "," with "."
            s = s.replace(".", "").replace(",", ".")
        else:
            # US: "1,234.56" → remove ","
            s = s.replace(",", "")
    elif last_comma > 0 and last_dot < 0:
        # Only comma — European decimal separator: "1234,56"
        s = s.replace(",", ".")
    else:
        # Only dot or neither — standard: "1234.56" or "1234"
        s = s.replace(",", "")

    return Decimal(s)


class SAPParser(BaseParser):
    """
    Parser for SAP fuel and procurement CSV exports.

    Handles:
    - German/English header auto-detection and normalisation
    - Date auto-detection (DD.MM.YYYY, YYYY-MM-DD, YYYYMMDD, MM/DD/YYYY)
    - Unit inference and European number format parsing
    - Plant code validation against Facility lookup table
    - Fuel type classification from material descriptions
    - Tonne → kg conversion (1 t = 1 000 kg)
    - Volume → mass conversion using fuel density tables
    - Quantity sanity checking
    """

    def validate_file(self, file_obj) -> bool:
        """Quick validation: must be parseable CSV with ≥3 columns and ≥1 data row."""
        try:
            file_obj.seek(0)
            encoding = self.detect_encoding(file_obj)
            # Try to detect delimiter
            first_line = file_obj.readline().decode(encoding)
            file_obj.seek(0)
            sep = ","
            if ";" in first_line and first_line.count(";") > first_line.count(","):
                sep = ";"

            df = pd.read_csv(file_obj, nrows=5, sep=sep, encoding=encoding)
            return len(df.columns) >= 3 and len(df) >= 1
        except Exception:
            return False

    def parse_rows(self, file_obj) -> Generator[ParseResult, None, None]:
        """
        Parse the SAP CSV row by row, yielding one ParseResult per data row.

        Skips completely empty rows and summary/total rows (rows whose document_number
        contains keywords like "TOTAL", "SUM", "GESAMT").
        """
        file_obj.seek(0)
        encoding = self.detect_encoding(file_obj)

        try:
            # Try to detect delimiter
            first_line = file_obj.readline().decode(encoding)
            file_obj.seek(0)
            sep = ","
            if ";" in first_line and first_line.count(";") > first_line.count(","):
                sep = ";"
                
            df = pd.read_csv(file_obj, sep=sep, encoding=encoding, dtype=str, keep_default_na=False)
        except Exception as e:
            # Try lenient parsing (handles non-standard delimiters)
            file_obj.seek(0)
            try:
                df = pd.read_csv(
                    file_obj, encoding=encoding, dtype=str,
                    sep=None, engine="python", keep_default_na=False,
                )
            except Exception:
                yield ParseResult("invalid", {}, [f"Failed to parse CSV: {e}"])
                return

        # Normalise headers → canonical names
        renamed = {}
        for col in df.columns:
            clean = col.strip().lower().replace(" ", "_").replace("-", "_")
            renamed[col] = HEADER_MAPPING.get(clean, clean)
        df.rename(columns=renamed, inplace=True)

        # Pre-load facility lookup (plant_code.upper() → Facility) for this org.
        # Do this once outside the row loop — avoids N DB queries for N rows.
        facilities = {
            f.sap_plant_code.upper(): f
            for f in Facility.objects.filter(organization=self.organization, is_active=True)
            if f.sap_plant_code
        }

        for idx, row in df.iterrows():
            row_num = idx + 2   # 1-based, header is row 1
            raw_payload = row.to_dict()

            # ── Skip empty rows ──────────────────────────────────────────────
            if all(str(v).strip() == "" for v in raw_payload.values()):
                yield ParseResult("skipped", raw_payload, ["Empty row"])
                continue

            # ── Skip summary / total rows ─────────────────────────────────────
            doc_num_raw = str(raw_payload.get("document_number", "")).strip().upper()
            if any(kw in doc_num_raw for kw in ("TOTAL", "SUM", "Σ", "GESAMT", "SUBTOTAL")):
                yield ParseResult("skipped", raw_payload, ["Summary/total row — skipped"])
                continue

            errors: List[str] = []
            warnings: List[str] = []
            normalized = {}

            # ── Plant code → Facility resolution ─────────────────────────────
            plant_code = str(raw_payload.get("plant_code", "")).strip().upper()
            if not plant_code:
                errors.append(
                    "Missing plant code (Werk). Cannot attribute emissions to a facility. "
                    "Check SAP export configuration — Werk field should always be populated."
                )
            else:
                facility = facilities.get(plant_code)
                if facility is None:
                    errors.append(
                        f"Plant code '{plant_code}' not found in Facility lookup table. "
                        f"Add this plant via Admin → Facilities before re-ingesting. "
                        f"Known plant codes: {list(facilities.keys()) or 'none configured yet'}."
                    )
                else:
                    normalized["facility_id"] = str(facility.id)
                    normalized["facility_name"] = facility.name

            # ── Date parsing ──────────────────────────────────────────────────
            # Prefer document_date (transaction date); fall back to posting_date.
            date_str = str(raw_payload.get("document_date", "")).strip()
            if not date_str:
                date_str = str(raw_payload.get("posting_date", "")).strip()

            parsed_date = None
            if date_str:
                # Try SAP-specific formats first, then dateutil as catch-all
                for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%Y%m%d", "%m/%d/%Y", "%d/%m/%Y"):
                    try:
                        parsed_date = datetime.strptime(date_str, fmt).date()
                        break
                    except ValueError:
                        continue
                if parsed_date is None:
                    try:
                        parsed_date = date_parser.parse(date_str, dayfirst=True).date()
                    except Exception:
                        errors.append(
                            f"Cannot parse date '{date_str}'. "
                            "Expected formats: DD.MM.YYYY, YYYY-MM-DD, YYYYMMDD."
                        )

            if parsed_date:
                from datetime import date as _date
                years_ago = (_date.today() - parsed_date).days / 365.25
                if years_ago > 10:
                    warnings.append(
                        f"Date {parsed_date} is {years_ago:.1f} years old. "
                        "SAP sometimes exports records with the default date 01.01.1900 — verify."
                    )
                if years_ago < -1:
                    warnings.append(f"Date {parsed_date} is in the future. Verify this is correct.")
                # SAP records are single-day events, so period_start == period_end
                normalized["period_start"] = parsed_date
                normalized["period_end"] = parsed_date
            else:
                errors.append("Missing date — cannot determine emission reporting period.")

            # ── Quantity & unit ───────────────────────────────────────────────
            qty_str = str(raw_payload.get("quantity", "")).strip()
            unit_str = str(raw_payload.get("unit", "")).strip().lower()

            # If unit is missing, try to infer from the material description
            material = str(raw_payload.get("material_code", "")).strip().lower()
            if not unit_str and material:
                for kw, inferred in [("liter", "l"), ("litre", "l"), ("m3", "m3"),
                                     ("m³", "m3"), ("kg", "kg"), ("gallon", "gal")]:
                    if kw in material:
                        unit_str = inferred
                        warnings.append(f"Unit inferred from material description as '{inferred}'.")
                        break

            canonical_unit = UNIT_MAPPING.get(unit_str, unit_str) if unit_str else ""

            quantity = None
            if qty_str:
                try:
                    quantity = _parse_european_number(qty_str)
                    if quantity < 0:
                        errors.append(
                            f"Negative quantity ({quantity}) is not allowed for fuel consumption. "
                            "If this is a reversal/credit memo, it should be excluded or handled separately."
                        )
                        quantity = None
                    elif quantity == 0:
                        warnings.append("Quantity is zero — this row will produce zero CO2e.")
                except (InvalidOperation, ValueError):
                    errors.append(f"Cannot parse quantity '{qty_str}' as a number. "
                                  "Check for European number format (e.g., 1.234,56).")

            # ── Fuel type classification ──────────────────────────────────────
            fuel_type = None
            material_upper = material.upper()
            for ft, keywords in FUEL_KEYWORDS.items():
                if any(kw.upper() in material_upper for kw in keywords):
                    fuel_type = ft
                    break

            if fuel_type:
                normalized["fuel_type"] = fuel_type
            else:
                warnings.append(
                    f"Could not classify material '{material}' as a known fuel type "
                    f"({', '.join(FUEL_KEYWORDS.keys())}). "
                    "Manual fuel type selection will be required before approval."
                )
                normalized["fuel_type"] = "unknown"

            normalized["activity_type"] = "stationary_fuel"
            normalized["scope"] = "1"

            # ── Unit conversion → kg (required by emission calculator) ────────
            #
            # The emission calculator uses kg CO2e / kg fuel (IPCC factors).
            # We must convert the raw quantity to kg here and record the math.
            #
            # Supported paths:
            #   liter  × density (kg/L)  → kg
            #   gal    → liter × density → kg
            #   m3     × density (kg/m³) → kg
            #   tonne  × 1 000           → kg   (1 metric tonne = 1 000 kg exactly)
            #   kg     → no conversion
            if quantity is not None and canonical_unit:
                converted_kg = None
                conv_note = ""

                if canonical_unit == "liter" and fuel_type in FUEL_DENSITY_KG_PER_LITRE:
                    density = FUEL_DENSITY_KG_PER_LITRE[fuel_type]
                    converted_kg = quantity * density
                    conv_note = (
                        f"{quantity} L × {density} kg/L [{fuel_type} density at 15°C] "
                        f"= {converted_kg:.4f} kg"
                    )

                elif canonical_unit == "gal" and fuel_type in FUEL_DENSITY_KG_PER_LITRE:
                    litres = quantity * Decimal("3.785411784")   # US gallon → litre (exact)
                    density = FUEL_DENSITY_KG_PER_LITRE[fuel_type]
                    converted_kg = litres * density
                    conv_note = (
                        f"{quantity} US gal × 3.785411784 L/gal = {litres:.4f} L; "
                        f"{litres:.4f} L × {density} kg/L [{fuel_type}] = {converted_kg:.4f} kg"
                    )

                elif canonical_unit == "m3":
                    if fuel_type == "natural_gas":
                        converted_kg = quantity * NATURAL_GAS_DENSITY_KG_PER_M3
                        conv_note = (
                            f"{quantity} m³ × {NATURAL_GAS_DENSITY_KG_PER_M3} kg/m³ "
                            f"[natural gas at 15°C, 1 atm, GPA 2012] = {converted_kg:.4f} kg"
                        )
                    elif fuel_type in FUEL_DENSITY_KG_PER_LITRE:
                        litres = quantity * Decimal("1000")
                        density = FUEL_DENSITY_KG_PER_LITRE[fuel_type]
                        converted_kg = litres * density
                        conv_note = (
                            f"{quantity} m³ × 1 000 L/m³ = {litres:.2f} L; "
                            f"{litres:.2f} L × {density} kg/L [{fuel_type}] = {converted_kg:.4f} kg"
                        )

                elif canonical_unit == "tonne":
                    # 1 metric tonne = 1 000 kg exactly (by definition of SI)
                    converted_kg = quantity * Decimal("1000")
                    conv_note = f"{quantity} t × 1 000 kg/t = {converted_kg:.2f} kg"

                elif canonical_unit == "kg":
                    converted_kg = quantity
                    conv_note = "Already in kg — no conversion needed."

                if converted_kg is not None:
                    normalized["activity_amount"] = str(converted_kg)
                    normalized["activity_unit"] = "kg"
                    normalized["original_amount"] = str(quantity)
                    normalized["original_unit"] = canonical_unit
                    normalized["conversion_note"] = conv_note
                else:
                    # Store raw quantity with its unit; analyst must resolve
                    normalized["activity_amount"] = str(quantity)
                    normalized["activity_unit"] = canonical_unit
                    if canonical_unit and fuel_type != "unknown":
                        warnings.append(
                            f"No density conversion available for unit '{canonical_unit}' "
                            f"with fuel type '{fuel_type}'. CO2e calculation may be inaccurate."
                        )

            # ── Sanity check ──────────────────────────────────────────────────
            if quantity is not None and fuel_type and fuel_type in SANITY_BOUNDS:
                lo, hi = SANITY_BOUNDS[fuel_type]
                if quantity < lo:
                    warnings.append(
                        f"Quantity {quantity} {canonical_unit} is very small for {fuel_type}. "
                        "Verify the unit is correct."
                    )
                if quantity > hi:
                    warnings.append(
                        f"Quantity {quantity} {canonical_unit} exceeds typical bounds for "
                        f"{fuel_type}. Possible unit error (e.g., reported in m³ but entered as L)?"
                    )

            # ── Source identifier (dedup key) ──────────────────────────────────
            doc_num = str(raw_payload.get("document_number", "")).strip()
            if doc_num:
                normalized["source_identifier"] = doc_num
            else:
                # Fallback: construct from plant + date
                date_part = str(normalized.get("period_start", ""))
                normalized["source_identifier"] = f"{plant_code}_{date_part}_{idx}"

            # ── Determine final row status ─────────────────────────────────────
            if errors:
                yield ParseResult("invalid", raw_payload, errors + warnings, normalized)
            elif warnings:
                yield ParseResult("suspicious", raw_payload, warnings, normalized)
            else:
                yield ParseResult("valid", raw_payload, [], normalized)