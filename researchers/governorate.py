"""
Governorate Service - Accurate Egyptian governorate detection.

Uses Nominatim geocoding with address details to determine the exact
governorate for any location in Egypt.
"""

import logging
import time
from typing import Optional, Tuple
from urllib.parse import quote as url_quote

import requests
from requests.exceptions import RequestException

logger = logging.getLogger('UnlockEgyptParser')


class GovernorateService:
    """
    Service for detecting Egyptian governorates from place names or coordinates.

    Egypt has 27 governorates. This service accurately maps any location
    to its correct governorate using Nominatim geocoding.
    """

    # All 27 Egyptian Governorates (official names)
    GOVERNORATES = {
        "alexandria": "Alexandria",
        "aswan": "Aswan",
        "asyut": "Asyut",
        "beheira": "Beheira",
        "beni suef": "Beni Suef",
        "cairo": "Cairo",
        "dakahlia": "Dakahlia",
        "damietta": "Damietta",
        "faiyum": "Faiyum",
        "fayoum": "Faiyum",  # Alternative spelling
        "gharbia": "Gharbia",
        "giza": "Giza",
        "ismailia": "Ismailia",
        "kafr el sheikh": "Kafr El Sheikh",
        "kafr el-sheikh": "Kafr El Sheikh",
        "luxor": "Luxor",
        "matruh": "Matruh",
        "matrouh": "Matruh",  # Alternative spelling
        "minya": "Minya",
        "al-minya": "Minya",
        "monufia": "Monufia",
        "menoufia": "Monufia",  # Alternative spelling
        "new valley": "New Valley",
        "wadi al-jadid": "New Valley",
        "north sinai": "North Sinai",
        "port said": "Port Said",
        "qalyubia": "Qalyubia",
        "qena": "Qena",
        "red sea": "Red Sea",
        "sharqia": "Sharqia",
        "sharkia": "Sharqia",  # Alternative spelling
        "al-sharkia": "Sharqia",
        "sohag": "Sohag",
        "south sinai": "South Sinai",
        "suez": "Suez",
    }

    # Common place name to governorate mappings (for known sites)
    KNOWN_PLACES = {
        # Giza sites
        "giza plateau": "Giza",
        "pyramids": "Giza",
        "sphinx": "Giza",
        "saqqara": "Giza",
        "dahshur": "Giza",
        "abu rawash": "Giza",

        # Luxor sites
        "karnak": "Luxor",
        "valley of the kings": "Luxor",
        "valley of the queens": "Luxor",
        "deir el-bahari": "Luxor",
        "deir al-bahari": "Luxor",
        "medinet habu": "Luxor",
        "colossi of memnon": "Luxor",
        "luxor temple": "Luxor",

        # Aswan sites
        "abu simbel": "Aswan",
        "philae": "Aswan",
        "elephantine": "Aswan",
        "nubian museum": "Aswan",
        "unfinished obelisk": "Aswan",

        # Alexandria sites
        "bibliotheca alexandrina": "Alexandria",
        "catacombs of kom el shoqafa": "Alexandria",
        "kom el-dikka": "Alexandria",
        "qaitbay citadel": "Alexandria",
        "pompey's pillar": "Alexandria",

        # Cairo sites
        "egyptian museum": "Cairo",
        "cairo citadel": "Cairo",
        "khan el-khalili": "Cairo",
        "al-azhar": "Cairo",
        "coptic cairo": "Cairo",
        "old cairo": "Cairo",
        "heliopolis": "Cairo",

        # South Sinai
        "saint catherine": "South Sinai",
        "mount sinai": "South Sinai",
        "sharm el-sheikh": "South Sinai",
        "dahab": "South Sinai",

        # Red Sea
        "hurghada": "Red Sea",
    }

    # Cache for geocoded results
    _cache: dict = {}

    # Nominatim configuration
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = "UnlockEgyptParser/3.2 (educational research project)"
    RATE_LIMIT = 1.0  # seconds between requests

    @classmethod
    def get_governorate(
        cls,
        place_name: str,
        location_hint: str = "",
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> Optional[str]:
        """
        Determine the governorate for a place in Egypt.

        Args:
            place_name: Name of the place/site
            location_hint: Additional location info (city, region)
            lat: Latitude (if known)
            lon: Longitude (if known)

        Returns:
            Governorate name or None if not found
        """
        # Check cache first
        cache_key = f"{place_name}|{location_hint}|{lat}|{lon}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        result = None

        # Step 1: Check known places
        place_lower = place_name.lower()
        for known, gov in cls.KNOWN_PLACES.items():
            if known in place_lower:
                result = gov
                break

        # Step 2: Check if location_hint is a governorate
        if not result and location_hint:
            hint_lower = location_hint.lower().strip()
            if hint_lower in cls.GOVERNORATES:
                result = cls.GOVERNORATES[hint_lower]

        # Step 3: Use Nominatim to geocode and get governorate
        if not result:
            result = cls._geocode_to_governorate(place_name, location_hint)

        # Step 4: If we have coordinates, reverse geocode
        if not result and lat is not None and lon is not None:
            result = cls._reverse_geocode_to_governorate(lat, lon)

        # Cache the result
        cls._cache[cache_key] = result
        return result

    @classmethod
    def _geocode_to_governorate(cls, place_name: str, location_hint: str = "") -> Optional[str]:
        """
        Use Nominatim to geocode a place and extract its governorate.

        Args:
            place_name: Name of the place
            location_hint: Additional location context

        Returns:
            Governorate name or None
        """
        queries = [
            f"{place_name}, {location_hint}, Egypt" if location_hint else f"{place_name}, Egypt",
            f"{place_name}, Egypt"
        ]

        for query in queries:
            try:
                url = f"{cls.NOMINATIM_URL}?q={url_quote(query)}&format=json&addressdetails=1&limit=1"
                headers = {"User-Agent": cls.USER_AGENT}

                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()

                results = response.json()
                if results and len(results) > 0:
                    address = results[0].get("address", {})

                    # Try different address fields for governorate
                    for field in ["state", "province", "county", "state_district"]:
                        if field in address:
                            state_name = address[field].lower()
                            # Remove common suffixes
                            state_name = state_name.replace(" governorate", "").replace(" محافظة", "").strip()

                            if state_name in cls.GOVERNORATES:
                                logger.debug(f"Found governorate via geocoding: {cls.GOVERNORATES[state_name]}")
                                return cls.GOVERNORATES[state_name]

                # Rate limit compliance
                time.sleep(cls.RATE_LIMIT)

            except RequestException as e:
                logger.warning(f"Geocoding failed for '{query}': {e}")

        return None

    @classmethod
    def _reverse_geocode_to_governorate(cls, lat: float, lon: float) -> Optional[str]:
        """
        Reverse geocode coordinates to find the governorate.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Governorate name or None
        """
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&addressdetails=1"
            headers = {"User-Agent": cls.USER_AGENT}

            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            result = response.json()
            address = result.get("address", {})

            for field in ["state", "province", "county", "state_district"]:
                if field in address:
                    state_name = address[field].lower()
                    state_name = state_name.replace(" governorate", "").replace(" محافظة", "").strip()

                    if state_name in cls.GOVERNORATES:
                        return cls.GOVERNORATES[state_name]

            time.sleep(cls.RATE_LIMIT)

        except RequestException as e:
            logger.warning(f"Reverse geocoding failed: {e}")

        return None

    @classmethod
    def is_valid_governorate(cls, name: str) -> bool:
        """Check if a name is a valid Egyptian governorate."""
        return name in cls.GOVERNORATES.values()

    @classmethod
    def get_all_governorates(cls) -> list[str]:
        """Get list of all 27 Egyptian governorates."""
        return sorted(set(cls.GOVERNORATES.values()))
