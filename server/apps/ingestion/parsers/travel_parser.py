"""
Corporate Travel Data Parser (Concur / Navan JSON format).

Real-World Context
------------------
Platforms like Concur and Navan expose travel data via REST API with segment types:
  AIRFR  → Air flight
  HOTEL  → Hotel stay
  CARRT  → Car rental
  TAXIF  → Taxi / ride-share
  RAILF  → Rail / train

In practice, most enterprises can NOT grant live API access to their Concur tenant
(it requires an SAP partnership agreement and IT provisioning).  Instead, they
export a JSON or CSV dump from the portal.  We simulate Concur v4 JSON shape.

Key Complexities
----------------
1. Distances are often absent for flights — only origin/destination IATA codes given.
2. Emission factors vary by distance band (short/medium/long-haul) AND cabin class.
3. Radiative Forcing Index (RFI ≈ 1.9) must be applied to flights (per DEFRA guidance).
   RFI accounts for non-CO2 warming effects (contrails, NOx, etc.) at altitude.
4. Ground transport may have start/end addresses but not a distance.
5. Hotel stays need a nights count; check-in/check-out dates are used as fallback.

Distance Calculation
--------------------
We use the Haversine great-circle formula + an 8 % indirect-routing uplift factor.
This is explicitly sanctioned by DEFRA 2025 and the GHG Protocol Travel Guide.
Fuel-based calculation (more accurate) requires per-flight fuel data from the airline,
which Concur never exposes.

DEFRA Distance Bands (2025)
---------------------------
  Short-haul  : ≤ 500 km (any international / domestic short flight)
  Medium-haul : 500 – 3 700 km
  Long-haul   : > 3 700 km
"""
import json
import math
from decimal import Decimal
from typing import Generator, Dict, List, Optional

from dateutil import parser as date_parser

from .base import BaseParser, ParseResult


# ── Airport coordinates (lat, lon) ────────────────────────────────────────────
# Production system would use a full IATA airport DB.  This prototype covers the
# most common business-travel airports.  Extending is trivial (add IATA: (lat, lon)).
AIRPORT_COORDS: Dict[str, tuple] = {
    "LHR": (51.4700, -0.4543),   "LGW": (51.1537, -0.1821),
    "JFK": (40.6413, -73.7781),  "EWR": (40.6895, -74.1745),
    "LAX": (33.9416, -118.4085), "SFO": (37.6213, -122.3790),
    "CDG": (49.0097,   2.5479),  "ORY": (48.7233,   2.3794),
    "FRA": (50.0379,   8.5622),  "MUC": (48.3538,  11.7861),
    "DXB": (25.2532,  55.3657),  "AUH": (24.4330,  54.6511),
    "SIN": ( 1.3644, 103.9915),  "HKG": (22.3080, 113.9185),
    "SYD": (-33.9399, 151.1753), "MEL": (-37.6690, 144.8410),
    "NRT": (35.7647,  140.3864), "HND": (35.5494, 139.7798),
    "ORD": (41.9742,  -87.9073), "DFW": (32.8998,  -97.0403),
    "ATL": (33.6407,  -84.4277), "MIA": (25.7959,  -80.2870),
    "AMS": (52.3105,   4.7683),  "BRU": (50.9010,   4.4844),
    "MAD": (40.4983,  -3.5676),  "BCN": (41.2974,   2.0833),
    "FCO": (41.8004,  12.2502),  "MXP": (45.6306,   8.7231),
    "ZRH": (47.4647,   8.5492),  "GVA": (46.2381,   6.1089),
    "YYZ": (43.6777,  -79.6248), "YVR": (49.1967, -123.1815),
    "GRU": (-23.4356, -46.4731), "BOG": ( 4.7016,  -74.1469),
    "BOM": (19.0896,  72.8656),  "DEL": (28.5562,  77.1000),
    "PEK": (40.0799, 116.6031),  "PVG": (31.1443, 121.8083),
    "ICN": (37.4602, 126.4407),  "BKK": (13.6811, 100.7475),
    "CPT": (-33.9715,  18.6021), "JNB": (-26.1367,  28.2416),
    "DUS": (51.2895,   6.7668),  "HAM": (53.6304,   9.9882),
    "VIE": (48.1103,  16.5697),  "WAW": (52.1657,  20.9671),
    "IST": (40.9762,  28.8146),  "DOH": (25.2609,  51.6138),
}


# ── Segment type mapping ───────────────────────────────────────────────────────
SEGMENT_TYPE_MAP = {
    # Concur canonical codes
    "AIRFR": "business_travel_flight",
    "HOTEL": "business_travel_hotel",
    "CARRT": "business_travel_car",
    "TAXIF": "business_travel_taxi",
    "RAILF": "business_travel_rail",
    # Common aliases
    "AIR": "business_travel_flight", "FLIGHT": "business_travel_flight",
    "CAR": "business_travel_car",    "RENTAL": "business_travel_car",
    "TAXI": "business_travel_taxi",  "UBER": "business_travel_taxi",
    "LYFT": "business_travel_taxi",
    "RAIL": "business_travel_rail",  "TRAIN": "business_travel_rail",
    "BUS": "business_travel_car",
}

# ── Travel class normalisation ────────────────────────────────────────────────
CLASS_MAP = {
    "economy": "economy", "eco": "economy", "y": "economy",
    "coach": "economy",
    "premium economy": "premium_economy", "premium_economy": "premium_economy",
    "premium eco": "premium_economy", "w": "premium_economy",
    "business": "business", "biz": "business", "c": "business", "j": "business",
    "business class": "business",
    "first": "first", "f": "first", "p": "first", "first class": "first",
    "average": "average", "unknown": "average", "": "average",
}

# ── Uplift factor ────────────────────────────────────────────────────────────
# Real flight paths deviate from great-circle due to airways, weather, holds.
# DEFRA 2025 and GHG Protocol both recommend a multiplier; 8 % is the standard.
ROUTING_UPLIFT = 1.08


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance using the Haversine formula.

    Returns kilometres.  Accuracy: < 0.5 % for distances > 10 km.
    """
    R = 6371.0  # mean Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def classify_distance_band(km: float) -> str:
    """
    Classify a flight into DEFRA 2025 distance bands.

    Short  : km ≤ 500
    Medium : 500 < km ≤ 3 700
    Long   : km > 3 700
    """
    if km <= 500:
        return "short"
    if km <= 3700:
        return "medium"
    return "long"


class TravelParser(BaseParser):
    """
    Parser for corporate travel JSON exports (Concur / Navan shape).

    Handles flight distance calculation, cabin-class lookup, ground transport,
    and hotel stay extraction for Scope 3 Category 6.
    """

    def validate_file(self, file_obj) -> bool:
        """File must be valid JSON with a known top-level array key."""
        try:
            file_obj.seek(0)
            data = json.load(file_obj)
            return isinstance(data, dict) and any(
                k in data for k in ("expenses", "trips", "segments", "travel", "bookings")
            )
        except Exception:
            return False

    def parse_rows(self, file_obj) -> Generator[ParseResult, None, None]:
        file_obj.seek(0)
        try:
            data = json.load(file_obj)
        except json.JSONDecodeError as e:
            yield ParseResult("invalid", {}, [f"Invalid JSON: {e}"])
            return

        # Find the array of segments/expenses
        segments = []
        for key in ("expenses", "trips", "segments", "travel", "bookings"):
            if isinstance(data.get(key), list):
                segments = data[key]
                break

        if not segments:
            yield ParseResult(
                "invalid", data,
                ["No travel segments found. Expected top-level key: "
                 "expenses, trips, segments, travel, or bookings."],
            )
            return

        for idx, segment in enumerate(segments):
            raw_payload = segment
            errors: List[str] = []
            warnings: List[str] = []
            normalized: Dict = {}

            # ── Segment type ───────────────────────────────────────────────────
            seg_type_raw = ""
            for key in ("segmentTypeId", "type", "category", "expenseType", "segment_type"):
                if key in segment:
                    seg_type_raw = str(segment[key]).upper().strip()
                    break

            activity_type = SEGMENT_TYPE_MAP.get(seg_type_raw)
            if not activity_type:
                warnings.append(
                    f"Unknown segment type '{seg_type_raw}'. "
                    "Defaulting to ground transport (business_travel_car). "
                    "Review and correct if this is a flight or hotel."
                )
                activity_type = "business_travel_car"

            normalized["activity_type"] = activity_type
            normalized["scope"] = "3"
            normalized["scope_3_category"] = "3.6"   # Business Travel

            # ── Type-specific processing ───────────────────────────────────────
            if activity_type == "business_travel_flight":
                self._process_flight(segment, normalized, errors, warnings)
            elif activity_type == "business_travel_hotel":
                self._process_hotel(segment, normalized, errors, warnings)
            else:
                self._process_ground(segment, normalized, errors, warnings, activity_type)

            # ── Common: extract date ───────────────────────────────────────────
            for date_key in ("startDate", "date", "departureDate", "checkInDate", "fromDate"):
                if date_key in segment:
                    try:
                        d = date_parser.parse(str(segment[date_key])).date()
                        normalized["period_start"] = d
                        normalized["period_end"] = d
                        break
                    except Exception:
                        pass

            # ── Common: source identifier ─────────────────────────────────────
            for id_key in ("id", "expenseId", "transactionId", "bookingId", "reportId"):
                if id_key in segment:
                    normalized["source_identifier"] = str(segment[id_key])
                    break
            if "source_identifier" not in normalized:
                normalized["source_identifier"] = f"travel_segment_{idx + 1}"

            # ── Determine final status ────────────────────────────────────────
            if errors:
                yield ParseResult("invalid", raw_payload, errors + warnings, normalized)
            elif warnings:
                yield ParseResult("suspicious", raw_payload, warnings, normalized)
            else:
                yield ParseResult("valid", raw_payload, [], normalized)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _process_flight(
        self,
        segment: Dict,
        normalized: Dict,
        errors: List[str],
        warnings: List[str],
    ) -> None:
        """Extract flight data and calculate Haversine distance."""
        # Concur API nests flight details under trip → airTrip.
        # We also check the segment root as a fallback.
        trip = segment.get("trip", {}) or {}
        air_trip = trip.get("airTrip", trip.get("flight", {})) or {}

        origin = self._get_airport(air_trip, segment, ("from", "origin", "departureAirport",
                                                        "originAirport", "departure_airport"))
        destination = self._get_airport(air_trip, segment, ("to", "destination", "arrivalAirport",
                                                             "destinationAirport", "arrival_airport"))

        if not origin or not destination:
            errors.append(
                "Missing origin or destination airport code. "
                "Cannot calculate flight distance without IATA codes."
            )
            return

        if origin == destination:
            errors.append(
                f"Origin and destination are both '{origin}'. "
                "This is not a valid flight segment."
            )
            return

        normalized["origin_airport"] = origin
        normalized["destination_airport"] = destination

        # Look up coordinates
        origin_coords = AIRPORT_COORDS.get(origin)
        dest_coords = AIRPORT_COORDS.get(destination)

        if not origin_coords:
            errors.append(
                f"Airport '{origin}' is not in the coordinate database. "
                "Extend AIRPORT_COORDS in travel_parser.py to cover this airport."
            )
            return
        if not dest_coords:
            errors.append(
                f"Airport '{destination}' is not in the coordinate database. "
                "Extend AIRPORT_COORDS in travel_parser.py to cover this airport."
            )
            return

        # Great-circle distance + 8 % uplift
        gc_km = haversine_km(origin_coords[0], origin_coords[1],
                             dest_coords[0], dest_coords[1])
        uplifted_km = round(gc_km * ROUTING_UPLIFT, 2)

        normalized["great_circle_km"] = round(gc_km, 2)
        normalized["uplifted_km"] = uplifted_km
        normalized["distance_calculation"] = (
            f"Haversine({origin}→{destination}) = {gc_km:.1f} km "
            f"× {ROUTING_UPLIFT} routing uplift = {uplifted_km:.1f} km"
        )

        distance_band = classify_distance_band(uplifted_km)
        normalized["distance_band"] = distance_band

        # Cabin class
        travel_class = "average"
        for key in ("class", "cabinClass", "travelClass", "cabin", "serviceClass"):
            raw_class = (
                str(air_trip.get(key, "")).lower().strip()
                or str(segment.get(key, "")).lower().strip()
            )
            if raw_class:
                travel_class = CLASS_MAP.get(raw_class, "average")
                break

        normalized["travel_class"] = travel_class
        normalized["activity_amount"] = str(uplifted_km)
        normalized["activity_unit"] = "km"

        # Policy flag: business/first long-haul has significant cost + emissions
        if travel_class in ("business", "first") and distance_band == "long":
            warnings.append(
                "Business/First class long-haul flight detected. "
                "This produces 3–4× the CO2e of economy. "
                "Verify against corporate travel policy."
            )

    def _process_hotel(
        self,
        segment: Dict,
        normalized: Dict,
        errors: List[str],
        warnings: List[str],
    ) -> None:
        """Extract hotel stay data — nights is the activity unit."""
        trip = segment.get("trip", {}) or {}
        hotel_trip = trip.get("hotelTrip", trip.get("hotel", {})) or {}

        nights = 0

        # Try explicit nights field first
        for key in ("nights", "numberOfNights", "stayNights", "duration"):
            val = hotel_trip.get(key) or segment.get(key)
            if val is not None:
                try:
                    nights = int(val)
                    break
                except (ValueError, TypeError):
                    pass

        # Fall back to check-in / check-out dates
        if nights <= 0:
            check_in = self._extract_date(hotel_trip, segment,
                                          ("checkInDate", "checkIn", "startDate", "fromDate"))
            check_out = self._extract_date(hotel_trip, segment,
                                           ("checkOutDate", "checkOut", "endDate", "toDate"))
            if check_in and check_out and check_out > check_in:
                nights = (check_out - check_in).days
                normalized["check_in"] = check_in.isoformat()
                normalized["check_out"] = check_out.isoformat()

        if nights <= 0:
            errors.append(
                "Cannot determine hotel nights. "
                "Provide 'nights' or 'checkInDate'/'checkOutDate' fields."
            )
            return

        if nights > 30:
            warnings.append(
                f"Hotel stay is {nights} nights. "
                "This may be extended business travel or temporary relocation. "
                "Confirm this is Category 6 Business Travel and not Category 7 Commuting."
            )

        normalized["activity_amount"] = str(nights)
        normalized["activity_unit"] = "night"

        # Location metadata (for reporting, not factor selection — we use a global hotel factor)
        for key in ("location", "city", "destination", "hotelCity", "country"):
            val = hotel_trip.get(key) or segment.get(key)
            if val:
                normalized["location"] = str(val)
                break

    def _process_ground(
        self,
        segment: Dict,
        normalized: Dict,
        errors: List[str],
        warnings: List[str],
        activity_type: str,
    ) -> None:
        """Extract ground transport (car, taxi, rail) data."""
        trip = segment.get("trip", {}) or {}

        distance_km = 0.0
        for key in ("distance", "distanceKm", "tripDistance", "km"):
            val = trip.get(key) or segment.get(key)
            if val is not None:
                try:
                    distance_km = float(val)
                    break
                except (ValueError, TypeError):
                    pass

        # Miles → km conversion
        for key in ("miles", "distanceMiles"):
            val = trip.get(key) or segment.get(key)
            if val is not None:
                try:
                    distance_km = float(val) * 1.60934
                    break
                except (ValueError, TypeError):
                    pass

        if distance_km > 0:
            normalized["activity_amount"] = str(round(distance_km, 2))
            normalized["activity_unit"] = "km"
        else:
            warnings.append(
                "No distance provided for ground transport segment. "
                "CO2e will be zero until an analyst enters the distance manually."
            )
            normalized["activity_amount"] = "0"
            normalized["activity_unit"] = "km"

        # Rail origin / destination
        if activity_type == "business_travel_rail":
            for key in ("from", "origin", "departureStation", "fromStation"):
                val = trip.get(key) or segment.get(key)
                if val:
                    normalized["origin_station"] = str(val)
                    break
            for key in ("to", "destination", "arrivalStation", "toStation"):
                val = trip.get(key) or segment.get(key)
                if val:
                    normalized["destination_station"] = str(val)
                    break

    # ── Utility methods ───────────────────────────────────────────────────────

    @staticmethod
    def _get_airport(
        air_trip: Dict, segment: Dict, keys: tuple,
    ) -> Optional[str]:
        """Return the first non-empty airport code found in air_trip or segment."""
        for key in keys:
            val = air_trip.get(key) or segment.get(key)
            if val:
                code = str(val).upper().strip()
                # Strip surrounding parentheses e.g. "(LHR)"
                code = code.strip("()")
                if len(code) == 3:
                    return code
        return None

    @staticmethod
    def _extract_date(source1: Dict, source2: Dict, keys: tuple):
        """Try to parse a date from two dicts across multiple key names."""
        for key in keys:
            val = source1.get(key) or source2.get(key)
            if val:
                try:
                    return date_parser.parse(str(val)).date()
                except Exception:
                    pass
        return None