#!/usr/bin/env python3
"""
UnlockEgypt Content Parser

A production-quality web scraper that extracts archaeological site information
from egymonuments.gov.eg for the UnlockEgypt iOS app.

Architecture:
    - EgyMonumentsParser: Main orchestrator (facade pattern)
    - WebScraper: Handles Selenium browser operations
    - ContentExtractor: Extracts and sanitizes content from HTML
    - GeocodingService: Handles coordinate lookups with caching
    - ContentGenerator: Generates tips, phrases, descriptions
    - DataExporter: Exports data to various formats

Author: UnlockEgypt Team
Version: 3.0.0
"""

import argparse
import html
import hashlib
import json
import logging
import os
import re
import sys
import time
import traceback
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field
from functools import wraps, lru_cache
from typing import Optional, TypedDict, Callable, Any
from urllib.parse import urlparse, quote as url_quote

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError as RequestsConnectionError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException
)


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return the application logger.

    Args:
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger('UnlockEgyptParser')


logger = setup_logging()


# =============================================================================
# CONSTANTS
# =============================================================================

class Config:
    """Application configuration constants."""

    # URLs
    BASE_URL = "https://egymonuments.gov.eg"
    SITES_URL = f"{BASE_URL}/en/archaeological-sites/"
    ALLOWED_DOMAIN = "egymonuments.gov.eg"

    # Timing (in seconds)
    IMPLICIT_WAIT_TIMEOUT = 10
    PAGE_LOAD_WAIT = 5
    CLICK_WAIT = 2
    ARABIC_PAGE_WAIT = 2
    GEOCODING_RATE_LIMIT = 1
    HTTP_TIMEOUT = 15

    # Content thresholds
    MIN_PARAGRAPH_LENGTH = 40
    MIN_SENTENCE_LENGTH = 30
    MAX_SUB_LOCATIONS = 5
    SUMMARY_CHAR_LIMIT = 200
    MAX_SHOW_MORE_CLICKS = 50
    MAX_SHOW_MORE_CLICKS_LIMITED = 3

    # Geographic bounds for Egypt
    EGYPT_LAT_MIN = 21
    EGYPT_LAT_MAX = 32
    EGYPT_LON_MIN = 24
    EGYPT_LON_MAX = 37

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    RETRY_BACKOFF = 2.0

    # User agent
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    NOMINATIM_USER_AGENT = "UnlockEgyptParser/3.0 (educational project)"


class EraKeywords:
    """Mapping of keywords to standardized era names."""

    VALID_ERAS = [
        "Pre-Dynastic", "Old Kingdom", "Middle Kingdom", "New Kingdom",
        "Late Period", "Ptolemaic", "Roman", "Islamic", "Modern"
    ]

    KEYWORD_MAP = {
        "predynastic": "Pre-Dynastic",
        "pre-dynastic": "Pre-Dynastic",
        "early dynastic": "Old Kingdom",
        "old kingdom": "Old Kingdom",
        "middle kingdom": "Middle Kingdom",
        "new kingdom": "New Kingdom",
        "18th dynasty": "New Kingdom",
        "19th dynasty": "New Kingdom",
        "20th dynasty": "New Kingdom",
        "late period": "Late Period",
        "ptolemaic": "Ptolemaic",
        "ptolemy": "Ptolemaic",
        "greek": "Ptolemaic",
        "hellenistic": "Ptolemaic",
        "roman": "Roman",
        "byzantine": "Roman",
        "coptic": "Roman",
        "islamic": "Islamic",
        "fatimid": "Islamic",
        "mamluk": "Islamic",
        "ayyubid": "Islamic",
        "ottoman": "Islamic",
        "muhammad ali": "Modern",
        "modern": "Modern",
        "19th century": "Modern",
        "20th century": "Modern",
    }


class TourismTypes:
    """Valid tourism type classifications."""
    VALID = ["Pharaonic", "Greco-Roman", "Coptic", "Islamic", "Modern"]


class PlaceTypes:
    """Valid place type classifications."""
    VALID = [
        "Pyramid", "Temple", "Tomb", "Museum", "Mosque",
        "Church", "Fortress", "Market", "Monument", "Ruins"
    ]


class CityNormalization:
    """City name normalization mappings."""

    CITY_MAP = {
        "alexandria": "Alexandria",
        "cairo": "Cairo",
        "giza": "Giza",
        "luxor": "Luxor",
        "aswan": "Aswan",
        "sinai": "Sinai",
        "south sinai": "Sinai",
        "fayoum": "Fayoum",
        "el fayoum": "Fayoum",
        "al-minya": "Cairo",
        "minya": "Cairo",
        "sohag": "Luxor",
        "qena": "Luxor",
        "beni suef": "Cairo",
        "kafr el-sheikh": "Alexandria",
        "red sea": "Hurghada",
        "hurghada": "Hurghada",
        "sharm": "Sharm El Sheikh",
        "dahab": "Dahab",
        "matrouh": "Alexandria",
        "port said": "Cairo",
        "ismailia": "Cairo",
    }


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class Tip:
    """Visitor tip for a site."""
    siteId: str
    tip: str


@dataclass
class ArabicPhrase:
    """Arabic vocabulary phrase for a site."""
    siteId: str
    english: str
    arabic: str
    pronunciation: str


@dataclass
class SubLocation:
    """Sub-location within a site (e.g., specific temple, tomb)."""
    id: str
    siteId: str
    name: str
    arabicName: str
    shortDescription: str
    imageName: str
    fullDescription: str


@dataclass
class Site:
    """Archaeological site data model."""
    id: str
    name: str
    arabicName: str
    era: str
    tourismType: str
    placeType: str
    city: str
    latitude: Optional[float]
    longitude: Optional[float]
    shortDescription: str
    fullDescription: str
    imageNames: list[str] = field(default_factory=list)
    estimatedDuration: str = ""
    bestTimeToVisit: str = ""
    openingHours: str = ""
    subLocations: list[SubLocation] = field(default_factory=list)
    tips: list[Tip] = field(default_factory=list)
    arabicPhrases: list[ArabicPhrase] = field(default_factory=list)


class TicketPrices(TypedDict, total=False):
    """Ticket price information."""
    foreigners_adult: str
    foreigners_student: str
    egyptians_adult: str
    egyptians_student: str


class AdditionalInfo(TypedDict, total=False):
    """Additional site information from web search."""
    duration: str
    best_time: str


# =============================================================================
# DECORATORS
# =============================================================================

def retry_on_failure(
    max_retries: int = Config.MAX_RETRIES,
    delay: float = Config.RETRY_DELAY,
    backoff: float = Config.RETRY_BACKOFF,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator for retrying failed operations with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}")

            raise last_exception
        return wrapper
    return decorator


@contextmanager
def log_timing(operation: str):
    """
    Context manager for logging operation timing.

    Args:
        operation: Name of the operation being timed

    Yields:
        None
    """
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        logger.debug(f"{operation} completed in {elapsed:.2f}s")


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

class Validator:
    """Input validation utilities."""

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate that URL is from the expected domain.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid and from allowed domain
        """
        if not url:
            return False
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme in ('http', 'https') and
                parsed.netloc.endswith(Config.ALLOWED_DOMAIN)
            )
        except Exception:
            return False

    @staticmethod
    def validate_coordinate(value: Any) -> Optional[float]:
        """
        Safely parse and validate a coordinate value.

        Args:
            value: Value to parse as coordinate

        Returns:
            Parsed float or None if invalid
        """
        try:
            coord = float(value)
            return coord if -180 <= coord <= 180 else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def is_valid_egypt_coordinates(lat: float, lon: float) -> bool:
        """
        Check if coordinates fall within Egypt's boundaries.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            True if coordinates are within Egypt
        """
        return (
            Config.EGYPT_LAT_MIN <= lat <= Config.EGYPT_LAT_MAX and
            Config.EGYPT_LON_MIN <= lon <= Config.EGYPT_LON_MAX
        )

    @staticmethod
    def validate_max_sites(value: Optional[int]) -> Optional[int]:
        """
        Validate max_sites parameter.

        Args:
            value: Value to validate

        Returns:
            Validated value or None

        Raises:
            ValueError: If value is negative
        """
        if value is not None and value < 0:
            raise ValueError("max_sites must be non-negative")
        return value


class Sanitizer:
    """Content sanitization utilities."""

    # Pre-compiled regex patterns for efficiency
    _SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE)
    _HTML_TAG_PATTERN = re.compile(r'<[^>]+>')

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """
        Sanitize scraped text to prevent injection attacks.

        Args:
            text: Raw text to sanitize

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Remove script tags
        text = cls._SCRIPT_PATTERN.sub('', text)
        # Remove HTML tags
        text = cls._HTML_TAG_PATTERN.sub('', text)
        # Escape HTML entities
        text = html.escape(text.strip())

        return text

    @staticmethod
    def normalize_arabic_text(text: str) -> str:
        """
        Normalize Arabic text for consistent storage.

        Args:
            text: Arabic text to normalize

        Returns:
            Normalized text
        """
        if not text:
            return ""
        import unicodedata
        # Normalize to NFC form for consistent representation
        text = unicodedata.normalize('NFC', text)
        # Remove invisible formatting characters
        text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')
        return text.strip()


# =============================================================================
# WEB SCRAPER
# =============================================================================

class WebScraper:
    """
    Handles Selenium browser operations with proper resource management.

    This class encapsulates all browser-related functionality including
    initialization, navigation, element finding, and cleanup.
    """

    def __init__(self, driver: Optional[webdriver.Chrome] = None, headless: bool = True):
        """
        Initialize the web scraper.

        Args:
            driver: Optional pre-configured WebDriver instance (for testing)
            headless: Whether to run browser in headless mode
        """
        if driver is not None:
            self.driver = driver
            self._owns_driver = False
        else:
            self.driver = self._create_driver(headless)
            self._owns_driver = True

        self.driver.implicitly_wait(Config.IMPLICIT_WAIT_TIMEOUT)

    def _create_driver(self, headless: bool) -> webdriver.Chrome:
        """
        Create and configure a Chrome WebDriver instance.

        Args:
            headless: Whether to run in headless mode

        Returns:
            Configured WebDriver instance
        """
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--lang=en")
        options.add_argument(f"--user-agent={Config.USER_AGENT}")

        return webdriver.Chrome(options=options)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()
        return False

    def close(self):
        """Close the browser and release resources."""
        if self._owns_driver and self.driver:
            try:
                self.driver.quit()
            except WebDriverException as e:
                logger.warning(f"Error closing WebDriver: {e}")

    def navigate(self, url: str) -> bool:
        """
        Navigate to a URL with validation.

        Args:
            url: URL to navigate to

        Returns:
            True if navigation successful
        """
        if not Validator.validate_url(url):
            logger.warning(f"Skipping invalid URL: {url}")
            return False

        try:
            self.driver.get(url)
            return True
        except WebDriverException as e:
            logger.error(f"Navigation failed for {url}: {e}")
            return False

    def wait_for_page_load(self, timeout: int = Config.PAGE_LOAD_WAIT):
        """
        Wait for page to be fully loaded.

        Args:
            timeout: Maximum wait time in seconds
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            logger.warning("Page load timeout, proceeding anyway")

    def find_element_safe(
        self,
        by: By,
        selector: str,
        default: Any = None
    ) -> Any:
        """
        Safely find an element without raising exceptions.

        Args:
            by: Selenium By locator type
            selector: CSS selector or other locator
            default: Default value if element not found

        Returns:
            Found element or default value
        """
        try:
            return self.driver.find_element(by, selector)
        except (NoSuchElementException, StaleElementReferenceException):
            return default

    def find_elements_safe(self, by: By, selector: str) -> list:
        """
        Safely find elements without raising exceptions.

        Args:
            by: Selenium By locator type
            selector: CSS selector or other locator

        Returns:
            List of found elements (empty if none found)
        """
        try:
            return self.driver.find_elements(by, selector)
        except (NoSuchElementException, StaleElementReferenceException):
            return []

    def get_element_text(self, by: By, selector: str, default: str = "") -> str:
        """
        Get text content of an element safely.

        Args:
            by: Selenium By locator type
            selector: CSS selector or other locator
            default: Default value if element not found

        Returns:
            Element text or default value
        """
        element = self.find_element_safe(by, selector)
        if element:
            try:
                return Sanitizer.sanitize_text(element.text.strip())
            except StaleElementReferenceException:
                return default
        return default

    def get_element_attribute(
        self,
        by: By,
        selector: str,
        attribute: str,
        default: str = ""
    ) -> str:
        """
        Get attribute value of an element safely.

        Args:
            by: Selenium By locator type
            selector: CSS selector or other locator
            attribute: Attribute name to retrieve
            default: Default value if element not found

        Returns:
            Attribute value or default
        """
        element = self.find_element_safe(by, selector)
        if element:
            try:
                return element.get_attribute(attribute) or default
            except StaleElementReferenceException:
                return default
        return default

    @property
    def current_url(self) -> str:
        """Get current page URL."""
        return self.driver.current_url

    @property
    def page_text(self) -> str:
        """Get full page text content."""
        try:
            body = self.find_element_safe(By.TAG_NAME, "body")
            return body.text if body else ""
        except Exception:
            return ""


# =============================================================================
# GEOCODING SERVICE
# =============================================================================

class GeocodingService:
    """
    Handles coordinate lookups via OpenStreetMap Nominatim API.

    Features:
    - LRU caching to minimize API calls
    - Rate limiting compliance
    - Retry logic for transient failures
    - Validation of Egypt boundaries
    """

    _cache: dict = {}

    @classmethod
    @retry_on_failure(
        max_retries=Config.MAX_RETRIES,
        exceptions=(RequestException, Timeout)
    )
    def _geocode_query(cls, query: str) -> Optional[tuple[float, float]]:
        """
        Execute a single geocoding query.

        Args:
            query: Search query string

        Returns:
            Tuple of (latitude, longitude) or None
        """
        url = f"https://nominatim.openstreetmap.org/search?q={url_quote(query)}&format=json&limit=1"
        headers = {"User-Agent": Config.NOMINATIM_USER_AGENT}

        response = requests.get(url, headers=headers, timeout=Config.HTTP_TIMEOUT)
        response.raise_for_status()

        results = response.json()
        if results and isinstance(results, list) and len(results) > 0:
            result = results[0]
            lat = Validator.validate_coordinate(result.get("lat"))
            lon = Validator.validate_coordinate(result.get("lon"))

            if lat is not None and lon is not None:
                if Validator.is_valid_egypt_coordinates(lat, lon):
                    return lat, lon

        return None

    @classmethod
    def search_coordinates(cls, site_name: str, city: str) -> tuple[Optional[float], Optional[float]]:
        """
        Search for site coordinates with multiple fallback queries.

        Args:
            site_name: Name of the archaeological site
            city: City where site is located

        Returns:
            Tuple of (latitude, longitude) or (None, None)
        """
        # Check cache first
        cache_key = f"{site_name}|{city}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        queries = [
            f"{site_name}, {city}, Egypt",
            f"{site_name}, Egypt"
        ]

        for query in queries:
            try:
                coords = cls._geocode_query(query)
                if coords:
                    cls._cache[cache_key] = coords
                    logger.info(f"Coordinates found: {coords[0]}, {coords[1]}")
                    return coords

                # Rate limit compliance
                time.sleep(Config.GEOCODING_RATE_LIMIT)

            except Exception as e:
                logger.warning(f"Geocoding failed for '{query}': {e}")

        cls._cache[cache_key] = (None, None)
        return None, None


# =============================================================================
# CONTENT EXTRACTOR
# =============================================================================

class ContentExtractor:
    """
    Extracts and processes content from web pages.

    Handles extraction of:
    - Full descriptions
    - Opening hours
    - Ticket prices
    - Images
    - Arabic names
    """

    # Pre-compiled regex patterns
    TIME_RANGE_PATTERN = re.compile(
        r'From\s*(\d{1,2}:\d{2}\s*(?:AM|PM))\s*To\s*(\d{1,2}:\d{2}\s*(?:AM|PM))',
        re.IGNORECASE
    )
    FALLBACK_TIME_PATTERN = re.compile(
        r'(\d{1,2}:\d{2}\s*(?:AM|PM)?)\s*[-–to]+\s*(\d{1,2}:\d{2}\s*(?:AM|PM)?)',
        re.IGNORECASE
    )
    FOREIGNER_PRICE_PATTERN = re.compile(
        r'FOREIGNERS?:?\s*Adult:?\s*EGP\s*(\d+)\s*/?\s*Student:?\s*EGP\s*(\d+)',
        re.IGNORECASE
    )
    EGYPTIAN_PRICE_PATTERN = re.compile(
        r'EGYPTIANS?:?\s*Adult:?\s*EGP\s*(\d+)\s*/?\s*Student:?\s*EGP\s*(\d+)',
        re.IGNORECASE
    )

    FOOTER_INDICATORS = ["copyright", "developed by", "all rights reserved", "ministry of"]
    NAV_INDICATORS = ["read more", "click here", "show more", "back to", "home >"]

    def __init__(self, scraper: WebScraper):
        """
        Initialize the content extractor.

        Args:
            scraper: WebScraper instance for browser operations
        """
        self.scraper = scraper

    def extract_full_description(self) -> str:
        """
        Extract the full description text from the current page.

        Returns:
            Combined paragraph text from the page
        """
        paragraphs = []

        try:
            all_p = self.scraper.find_elements_safe(By.TAG_NAME, "p")
            for p in all_p:
                try:
                    text = p.text.strip()
                    if (text and
                        len(text) > Config.MIN_PARAGRAPH_LENGTH and
                        not self._is_navigation_text(text) and
                        not self._is_footer_text(text)):
                        paragraphs.append(Sanitizer.sanitize_text(text))
                except StaleElementReferenceException:
                    continue
        except Exception as e:
            logger.warning(f"Error extracting paragraphs: {e}")

        return "\n\n".join(paragraphs)

    def _is_footer_text(self, text: str) -> bool:
        """Check if text is footer/copyright content."""
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in self.FOOTER_INDICATORS)

    def _is_navigation_text(self, text: str) -> bool:
        """Check if text is likely navigation/UI rather than content."""
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in self.NAV_INDICATORS)

    def extract_opening_hours(self) -> str:
        """
        Extract opening hours from the current page.

        Returns:
            Formatted opening hours string or empty string
        """
        page_text = self.scraper.page_text

        if "Opening Hours" in page_text:
            match = self.TIME_RANGE_PATTERN.search(page_text)
            if match:
                return f"{match.group(1)} - {match.group(2)}"

        # Fallback pattern
        match = self.FALLBACK_TIME_PATTERN.search(page_text)
        if match:
            return f"{match.group(1)} - {match.group(2)}"

        return ""

    def extract_ticket_prices(self) -> TicketPrices:
        """
        Extract ticket prices from the current page.

        Returns:
            Dictionary with ticket price information
        """
        prices: TicketPrices = {}
        page_text = self.scraper.page_text

        if "Tickets" in page_text or "FOREIGNERS" in page_text:
            foreigner_match = self.FOREIGNER_PRICE_PATTERN.search(page_text)
            if foreigner_match:
                prices["foreigners_adult"] = f"EGP {foreigner_match.group(1)}"
                prices["foreigners_student"] = f"EGP {foreigner_match.group(2)}"

            egyptian_match = self.EGYPTIAN_PRICE_PATTERN.search(page_text)
            if egyptian_match:
                prices["egyptians_adult"] = f"EGP {egyptian_match.group(1)}"
                prices["egyptians_student"] = f"EGP {egyptian_match.group(2)}"

        return prices

    def extract_images(self, listing_image: str) -> list[str]:
        """
        Extract all relevant images from the current page.

        Args:
            listing_image: Image URL from listing page (used as fallback)

        Returns:
            List of image URLs
        """
        images = []
        if listing_image:
            images.append(listing_image)

        selectors = ".gallery img, .slider img, .monumentGallery img, article img, .swiper-slide img"
        img_elems = self.scraper.find_elements_safe(By.CSS_SELECTOR, selectors)

        for img in img_elems:
            try:
                src = img.get_attribute("src")
                if src and src not in images and "logo" not in src.lower() and "icon" not in src.lower():
                    images.append(src)
            except StaleElementReferenceException:
                continue

        return images

    def fetch_arabic_name(self, english_url: str) -> str:
        """
        Fetch the Arabic name from the Arabic version of the page.

        Args:
            english_url: URL of the English page

        Returns:
            Arabic name or empty string
        """
        if not Validator.validate_url(english_url):
            return ""

        try:
            arabic_url = english_url.replace("/en/", "/ar/")
            current_url = self.scraper.current_url

            if not self.scraper.navigate(arabic_url):
                return ""

            time.sleep(Config.ARABIC_PAGE_WAIT)

            # Try multiple selectors for Arabic title
            for selector in ["h1", ".title h1", ".pageTitle"]:
                arabic_name = self.scraper.get_element_text(By.CSS_SELECTOR, selector)
                if arabic_name and any('\u0600' <= c <= '\u06FF' for c in arabic_name):
                    logger.info(f"Arabic name found: {arabic_name}")
                    self.scraper.driver.get(current_url)
                    time.sleep(Config.CLICK_WAIT)
                    return Sanitizer.normalize_arabic_text(arabic_name)

            # Navigate back to English page
            self.scraper.driver.get(current_url)
            time.sleep(Config.CLICK_WAIT)

        except Exception as e:
            logger.warning(f"Could not fetch Arabic name: {e}")

        return ""


# =============================================================================
# CONTENT GENERATOR
# =============================================================================

class ContentGenerator:
    """
    Generates derived content like tips, Arabic phrases, and descriptions.
    """

    # City-specific tips
    CITY_TIPS = {
        "Alexandria": "Bring sunscreen and a hat - the Mediterranean sun can be intense.",
        "Cairo": "Start early to avoid crowds and the midday heat.",
        "Giza": "Hire an official guide at the entrance for the best experience.",
        "Luxor": "Consider visiting early morning or late afternoon to avoid peak heat.",
        "Aswan": "Carry plenty of water, especially during summer months.",
    }

    # Place-type specific Arabic vocabulary
    PLACE_PHRASES = {
        "Temple": [
            ("Temple", "معبد", "Ma'bad"),
            ("Pharaoh", "فرعون", "Fir'awn"),
            ("God/Goddess", "إله/إلهة", "Ilah/Ilaha"),
            ("Columns", "أعمدة", "A'mida"),
            ("Hieroglyphics", "هيروغليفية", "Hieroglyphia"),
        ],
        "Pyramid": [
            ("Pyramid", "هرم", "Haram"),
            ("King", "ملك", "Malik"),
            ("Chamber", "غرفة", "Ghorfa"),
            ("Stone", "حجر", "Hagar"),
        ],
        "Tomb": [
            ("Tomb", "مقبرة", "Maqbara"),
            ("Mummy", "مومياء", "Mumya"),
            ("Coffin", "تابوت", "Taboot"),
            ("Noble", "نبيل", "Nabeel"),
            ("Cemetery", "جبانة", "Gabbana"),
        ],
        "Mosque": [
            ("Mosque", "مسجد", "Masgid"),
            ("Minaret", "مئذنة", "Me'zana"),
            ("Dome", "قبة", "Qobba"),
            ("Prayer", "صلاة", "Salah"),
        ],
        "Museum": [
            ("Museum", "متحف", "Mat-haf"),
            ("Artifact", "أثر", "Athar"),
            ("Statue", "تمثال", "Timthal"),
            ("Collection", "مجموعة", "Magmoo'a"),
            ("Display", "عرض", "Ard"),
        ],
        "Monument": [
            ("Monument", "نصب تذكاري", "Nasb Tizkari"),
            ("Amphitheatre", "مدرج", "Mudarrag"),
            ("Theater", "مسرح", "Masrah"),
            ("Roman", "روماني", "Romani"),
            ("Mosaic", "فسيفساء", "Fusayfisa'"),
        ],
        "Ruins": [
            ("Ruins", "آثار", "Athar"),
            ("Ancient", "قديم", "Adeem"),
            ("Excavation", "حفريات", "Hafriyat"),
            ("Archaeology", "علم الآثار", "Ilm al-Athar"),
        ],
        "Fortress": [
            ("Fortress", "قلعة", "Qal'a"),
            ("Tower", "برج", "Borg"),
            ("Wall", "سور", "Soor"),
            ("Gate", "بوابة", "Bawwaba"),
        ],
        "Church": [
            ("Church", "كنيسة", "Kaneesa"),
            ("Coptic", "قبطي", "Qibti"),
            ("Monastery", "دير", "Deir"),
            ("Icon", "أيقونة", "Ayqoona"),
        ],
    }

    @classmethod
    def generate_tips(
        cls,
        site_id: str,
        name: str,
        city: str,
        opening_hours: str,
        ticket_prices: TicketPrices,
        additional_info: AdditionalInfo
    ) -> list[Tip]:
        """
        Generate practical tips for a site.

        Args:
            site_id: Site identifier
            name: Site name
            city: City name
            opening_hours: Opening hours string
            ticket_prices: Ticket price information
            additional_info: Additional info from web search

        Returns:
            List of Tip objects
        """
        tips = []

        if opening_hours:
            tips.append(Tip(siteId=site_id, tip=f"Opening hours: {opening_hours}"))

        if ticket_prices:
            if "foreigners_adult" in ticket_prices:
                tips.append(Tip(
                    siteId=site_id,
                    tip=f"Ticket prices (foreigners): Adult {ticket_prices['foreigners_adult']}, "
                        f"Student {ticket_prices.get('foreigners_student', 'N/A')}"
                ))
            if "egyptians_adult" in ticket_prices:
                tips.append(Tip(
                    siteId=site_id,
                    tip=f"Ticket prices (Egyptians): Adult {ticket_prices['egyptians_adult']}, "
                        f"Student {ticket_prices.get('egyptians_student', 'N/A')}"
                ))

        if city in cls.CITY_TIPS:
            tips.append(Tip(siteId=site_id, tip=cls.CITY_TIPS[city]))

        # General tips
        tips.append(Tip(siteId=site_id, tip="Wear comfortable walking shoes suitable for uneven terrain."))
        tips.append(Tip(siteId=site_id, tip="Photography may require an additional permit - check at the entrance."))

        return tips

    @classmethod
    def generate_arabic_phrases(cls, site_id: str, place_type: str) -> list[ArabicPhrase]:
        """
        Generate site-specific Arabic vocabulary phrases.

        Args:
            site_id: Site identifier
            place_type: Type of place (Temple, Tomb, etc.)

        Returns:
            List of ArabicPhrase objects
        """
        phrases = []

        if place_type in cls.PLACE_PHRASES:
            for eng, ar, pron in cls.PLACE_PHRASES[place_type]:
                phrases.append(ArabicPhrase(
                    siteId=site_id,
                    english=eng,
                    arabic=ar,
                    pronunciation=pron
                ))

        return phrases


# =============================================================================
# ERA & TYPE CLASSIFIER
# =============================================================================

class Classifier:
    """
    Classifies sites by era, tourism type, and place type.
    """

    # Pre-compiled patterns for era detection
    BC_DATE_PATTERN = re.compile(r'(\d+)\s*(bc|b\.c\.|bce)', re.IGNORECASE)
    AD_DATE_PATTERN = re.compile(r'(\d+)\s*(?:st|nd|rd|th)?\s*(?:century)?\s*(ad|a\.d\.|ce)', re.IGNORECASE)

    # Place type keywords
    PLACE_KEYWORDS = [
        ("pyramid", "Pyramid"),
        ("temple", "Temple"),
        ("tomb", "Tomb"),
        ("cemetery", "Tomb"),
        ("necropolis", "Tomb"),
        ("burial", "Tomb"),
        ("museum", "Museum"),
        ("mosque", "Mosque"),
        ("madrasa", "Mosque"),
        ("church", "Church"),
        ("cathedral", "Church"),
        ("monastery", "Church"),
        ("convent", "Church"),
        ("fortress", "Fortress"),
        ("citadel", "Fortress"),
        ("fort", "Fortress"),
        ("castle", "Fortress"),
        ("market", "Market"),
        ("bazaar", "Market"),
        ("khan", "Market"),
        ("amphitheatre", "Monument"),
        ("theater", "Monument"),
        ("theatre", "Monument"),
        ("obelisk", "Monument"),
        ("statue", "Monument"),
        ("colossus", "Monument"),
    ]

    @classmethod
    def determine_era(cls, description: str) -> str:
        """
        Determine historical era from description.

        Picks the OLDEST era mentioned to prioritize ancient history.

        Args:
            description: Site description text

        Returns:
            Era name or empty string
        """
        if not description:
            return ""

        desc_lower = description.lower()

        # Check for pharaonic eras first (oldest eras take priority)
        if "old kingdom" in desc_lower:
            return "Old Kingdom"
        if "middle kingdom" in desc_lower:
            return "Middle Kingdom"
        if "new kingdom" in desc_lower or "18th dynasty" in desc_lower or "19th dynasty" in desc_lower:
            return "New Kingdom"
        if "late period" in desc_lower:
            return "Late Period"

        # Later eras
        if "ptolemaic" in desc_lower:
            return "Ptolemaic"
        if "roman and byzantine" in desc_lower or ("roman" in desc_lower and "byzantine" in desc_lower):
            return "Roman"
        if "roman period" in desc_lower or "roman era" in desc_lower:
            return "Roman"
        if any(word in desc_lower for word in ["islamic", "fatimid", "mamluk", "ayyubid"]):
            return "Islamic"

        # Try to extract from BC dates
        bc_match = cls.BC_DATE_PATTERN.search(desc_lower)
        if bc_match:
            year = int(bc_match.group(1))
            if year > 3100:
                return "Pre-Dynastic"
            elif year > 2181:
                return "Old Kingdom"
            elif year > 1650:
                return "Middle Kingdom"
            elif year > 1069:
                return "New Kingdom"
            elif year > 332:
                return "Late Period"
            else:
                return "Ptolemaic"

        # Try AD dates
        ad_match = cls.AD_DATE_PATTERN.search(desc_lower)
        if ad_match:
            year = int(ad_match.group(1))
            if year < 100:  # It's a century
                year = year * 100
            if year < 641:
                return "Roman"
            else:
                return "Islamic"

        return ""

    @classmethod
    def determine_tourism_type(cls, era: str, description: str, name: str) -> str:
        """
        Determine tourism type based on era and description.

        Args:
            era: Determined era
            description: Site description
            name: Site name

        Returns:
            Tourism type classification
        """
        combined = (description + " " + name).lower()

        pharaonic_eras = ["Pre-Dynastic", "Old Kingdom", "Middle Kingdom", "New Kingdom", "Late Period"]
        if era in pharaonic_eras:
            return "Pharaonic"

        if era in ["Roman", "Ptolemaic"]:
            return "Greco-Roman"

        if era == "Islamic":
            return "Islamic"

        # Check for specific indicators when era is unknown
        if any(word in combined for word in ["mosque", "madrasa", "minaret", "islamic"]):
            return "Islamic"
        if any(word in combined for word in ["coptic", "christian", "church", "monastery", "convent"]):
            return "Coptic"
        if any(word in combined for word in ["roman", "greco", "greek", "ptolem", "hellenistic", "amphitheatre", "byzantine"]):
            return "Greco-Roman"

        # Check for modern indicators (must be specific phrases, not just "modern")
        if "modern period" in combined or "modern era" in combined or "19th century" in combined or "20th century" in combined:
            return "Modern"

        return "Pharaonic"  # Default for ancient Egyptian sites

    @classmethod
    def determine_place_type(cls, name: str, description: str) -> str:
        """
        Determine place type based on name and description.

        Args:
            name: Site name
            description: Site description

        Returns:
            Place type classification
        """
        combined = (name + " " + description).lower()

        for keyword, place_type in cls.PLACE_KEYWORDS:
            if keyword in combined:
                return place_type

        return "Ruins"

    @classmethod
    def normalize_city(cls, location_text: str) -> str:
        """
        Normalize city name to match UnlockEgypt valid values.

        Args:
            location_text: Raw location text

        Returns:
            Normalized city name or empty string
        """
        if not location_text:
            return ""
        location_lower = location_text.lower().strip()
        for city_keyword, normalized in CityNormalization.CITY_MAP.items():
            if city_keyword in location_lower:
                return normalized
        return ""

    @classmethod
    def detect_city_from_text(cls, text: str) -> str:
        """
        Try to detect city from description text.

        Args:
            text: Description text

        Returns:
            Detected city name or empty string
        """
        if not text:
            return ""
        text_lower = text.lower()
        for city_keyword, normalized in CityNormalization.CITY_MAP.items():
            if city_keyword in text_lower:
                return normalized
        return ""


# =============================================================================
# SUB-LOCATION EXTRACTOR
# =============================================================================

class SubLocationExtractor:
    """
    Extracts meaningful sub-locations from site descriptions.

    Sub-locations are distinct areas within a site that warrant their own
    exploration cards (e.g., specific temples, tombs, monuments).
    """

    # Known Egyptian deity names for accurate temple extraction
    EGYPTIAN_DEITIES = (
        "Khnum|Satet|Khonsu|Amun|Ra|Horus|Isis|Osiris|Hathor|"
        "Thoth|Ptah|Anubis|Sobek|Sekhmet|Bastet|Mut|Aten|Min|"
        "Nefertum|Neith|Montu|Wepwawet|Set"
    )

    # Patterns for significant sub-locations
    FEATURE_PATTERNS = [
        # Theaters and entertainment venues
        (r'Roman\s+Theater\s*\([^)]+\)', "theater"),
        (r'Roman\s+Theater(?!\s*\()', "theater"),
        (r'Amphitheatre', "theater"),
        # Villas and residential
        (r'Villa\s+of\s+the\s+[A-Z][a-z]+', "villa"),
        # Baths
        (r'Roman\s+Baths?', "baths"),
        (r'Public\s+Baths?', "baths"),
        # Educational
        (r'Lecture\s+Halls?', "educational"),
        (r'Library', "educational"),
        # Temples with deity names
        (rf'[Tt]emple\s+of\s+(?:[^,]*?\s+)?({EGYPTIAN_DEITIES})\b', "temple"),
        (r'[Tt]emple\s+of\s+[^,]+,\s*([A-Z][a-z]{3,12})\b', "temple"),
        (r'([A-Z][a-z]+)\'s\s+Temple', "temple"),
        (r'Great\s+Temple', "temple"),
        # Tombs
        (r'Tomb\s+of\s+([A-Z][a-zA-Z\s]{2,20}?)(?:\s*\(|,|\.|$)', "tomb"),
        (r'Royal\s+Tomb', "tomb"),
        (r'Burial\s+Chamber', "tomb"),
        # Mosques/Churches
        (r'Mosque\s+of\s+([A-Z][a-zA-Z\s]+?)(?:\s*\(|,|\.|$)', "mosque"),
        (r'Church\s+of\s+([A-Z][a-zA-Z\s]+?)(?:\s*\(|,|\.|$)', "church"),
        # Other significant structures
        (r'Nilometer', "monument"),
        (r'Colossi', "monument"),
        (r'Obelisk', "monument"),
        (r'Sphinx', "monument"),
        (r'Pylon', "monument"),
    ]

    # Description templates by feature type
    DESCRIPTION_TEMPLATES = {
        "theater": "The {name} is an ancient performance venue that reflects the cultural life of the period.",
        "villa": "The {name} offers insight into the residential architecture and lifestyle of ancient times.",
        "baths": "The {name} showcase Roman bathing culture and engineering achievements.",
        "educational": "The {name} represent the intellectual and educational heritage of ancient Alexandria.",
        "temple": "The {name} is a sacred site dedicated to ancient Egyptian religious practices.",
        "tomb": "The {name} provides insights into ancient burial customs and beliefs.",
        "mosque": "The {name} is an important Islamic religious and architectural landmark.",
        "church": "The {name} represents the rich Coptic Christian heritage of Egypt.",
        "monument": "The {name} is a significant historical monument worthy of exploration.",
    }

    @classmethod
    def extract_sublocations(
        cls,
        site_id: str,
        site_name: str,
        description: str
    ) -> list[SubLocation]:
        """
        Extract meaningful sub-locations from a site description.

        If no meaningful sub-locations are found, the site itself becomes
        the sole sub-location.

        Args:
            site_id: Site identifier
            site_name: Name of the site
            description: Full site description

        Returns:
            List of SubLocation objects
        """
        sub_locations = []
        found_features = []
        found_names_lower: set[str] = set()

        # Extract features using patterns
        for pattern, feature_type in cls.FEATURE_PATTERNS:
            try:
                matches = re.finditer(pattern, description, re.IGNORECASE)
                for match in matches:
                    full_match = match.group(0).strip()

                    # Handle captured groups for named entities
                    if match.lastindex and match.lastindex >= 1:
                        captured_name = match.group(1).strip()
                        feature_name = cls._format_feature_name(feature_type, captured_name)
                    else:
                        feature_name = full_match.title()

                    # Deduplicate (case-insensitive)
                    name_lower = feature_name.lower()
                    if not cls._is_duplicate(name_lower, found_names_lower) and len(feature_name) > 4:
                        found_features.append((feature_name, feature_type))
                        found_names_lower.add(name_lower)
            except re.error as e:
                logger.warning(f"Regex error for pattern: {e}")

        # Create sub-locations for found features (limit to MAX_SUB_LOCATIONS)
        for idx, (feature_name, feature_type) in enumerate(found_features[:Config.MAX_SUB_LOCATIONS]):
            sub_id = f"{site_id}_sub_{idx + 1:02d}"
            feature_desc = cls._generate_description(feature_name, feature_type, description, site_name)

            sub_locations.append(SubLocation(
                id=sub_id,
                siteId=site_id,
                name=feature_name,
                arabicName="",
                shortDescription=feature_desc,
                imageName="",
                fullDescription=feature_desc
            ))

        # If no sub-locations found, site itself becomes the sub-location
        if not sub_locations:
            site_desc = cls._summarize_description(description, site_name)
            sub_locations.append(SubLocation(
                id=f"{site_id}_sub_01",
                siteId=site_id,
                name=site_name,
                arabicName="",
                shortDescription=site_desc,
                imageName="",
                fullDescription=description
            ))

        return sub_locations

    @classmethod
    def _format_feature_name(cls, feature_type: str, captured_name: str) -> str:
        """Format feature name based on type."""
        name_formats = {
            "temple": f"Temple of {captured_name.title()}",
            "tomb": f"Tomb of {captured_name.title()}",
            "mosque": f"Mosque of {captured_name.title()}",
            "church": f"Church of {captured_name.title()}",
        }
        return name_formats.get(feature_type, captured_name.title())

    @classmethod
    def _is_duplicate(cls, name_lower: str, existing: set[str]) -> bool:
        """Check if name is a duplicate (subset matching)."""
        for existing_name in existing:
            if name_lower in existing_name or existing_name in name_lower:
                return True
        return False

    @classmethod
    def _generate_description(
        cls,
        feature_name: str,
        feature_type: str,
        full_description: str,
        site_name: str
    ) -> str:
        """
        Generate a proper English description for a feature.

        Args:
            feature_name: Name of the feature
            feature_type: Type of feature
            full_description: Full site description
            site_name: Name of the site

        Returns:
            Generated description
        """
        feature_lower = feature_name.lower()
        sentences = re.split(r'(?<=[.!?])\s+', full_description)

        # Find relevant sentences
        relevant_info = []
        for sentence in sentences:
            if feature_lower in sentence.lower() or any(word in sentence.lower() for word in feature_lower.split()):
                relevant_info.append(sentence.strip())

        if relevant_info:
            details = " ".join(relevant_info).lower()

            # Generate specific descriptions based on context
            if feature_type == "theater":
                if "only" in details and "egypt" in details:
                    return (f"The {feature_name} is the only Roman theater discovered in Egypt. "
                           "It features tiered marble seating and served as a venue for musical "
                           "performances and public gatherings in ancient times.")
                elif "marble" in details or "seats" in details:
                    return (f"The {feature_name} is a well-preserved ancient performance venue with "
                           "tiered marble seating, offering visitors a glimpse into the entertainment "
                           "culture of Roman Alexandria.")

            elif feature_type == "villa":
                if "mosaic" in details or "birds" in details:
                    return (f"The {feature_name} is renowned for its stunning floor mosaics depicting "
                           "colorful birds and intricate geometric patterns, representing the luxurious "
                           "lifestyle of wealthy Roman residents.")

            elif feature_type == "baths":
                if "hypocaust" in details or "heating" in details:
                    return (f"The {feature_name} demonstrate advanced Roman engineering, featuring a "
                           "sophisticated hypocaust (underfloor heating) system that showcases the "
                           "technological achievements of the era.")

            elif feature_type == "educational":
                if any(word in details for word in ["school", "university", "philosoph"]):
                    return (f"The {feature_name} are believed to be part of an ancient philosophical "
                           "school or university, offering a rare glimpse into academic life in "
                           "Greco-Roman Alexandria.")

        # Return default template
        template = cls.DESCRIPTION_TEMPLATES.get(
            feature_type,
            f"The {{name}} is a notable feature of {site_name} that merits individual exploration."
        )
        return template.format(name=feature_name)

    @classmethod
    def _summarize_description(cls, description: str, site_name: str) -> str:
        """Create a summary when site itself is the sub-location."""
        sentences = re.split(r'(?<=[.!?])\s+', description)
        summary_sentences = []

        for sentence in sentences[:3]:
            if len(sentence) > Config.MIN_SENTENCE_LENGTH:
                summary_sentences.append(sentence.strip())
                if len(" ".join(summary_sentences)) > Config.SUMMARY_CHAR_LIMIT:
                    break

        if summary_sentences:
            return " ".join(summary_sentences)

        return f"{site_name} is an archaeological site of historical and cultural significance."


# =============================================================================
# DATA EXPORTER
# =============================================================================

class DataExporter:
    """
    Exports parsed site data to various formats.

    Includes validation of output data before export.
    """

    @staticmethod
    def validate_site(site: Site) -> list[str]:
        """
        Validate site data and return list of issues.

        Args:
            site: Site object to validate

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        if not site.id:
            issues.append("Missing site ID")
        if not site.name:
            issues.append("Missing site name")
        if site.latitude is not None and not Validator.is_valid_egypt_coordinates(
            site.latitude, site.longitude or 0
        ):
            issues.append(f"Invalid coordinates: {site.latitude}, {site.longitude}")
        if not site.subLocations:
            issues.append("No sub-locations defined")

        return issues

    @classmethod
    def export_to_json(
        cls,
        sites: list[Site],
        output_path: str,
        strict: bool = False
    ) -> dict:
        """
        Export sites to JSON in UnlockEgypt format.

        Args:
            sites: List of Site objects to export
            output_path: Path to output JSON file
            strict: If True, raise on validation errors

        Returns:
            Dictionary of exported data

        Raises:
            ValueError: If strict mode and validation fails
        """
        output = {
            "sites": [],
            "subLocations": [],
            "cards": [],
            "tips": [],
            "arabicPhrases": []
        }

        for site in sites:
            # Validate
            issues = cls.validate_site(site)
            if issues:
                if strict:
                    raise ValueError(f"Invalid site {site.id}: {issues}")
                else:
                    logger.warning(f"Site '{site.name}' has issues: {issues}")

            site_dict = asdict(site)
            sub_locs = site_dict.pop("subLocations")
            tips = site_dict.pop("tips")
            phrases = site_dict.pop("arabicPhrases")

            # Site export
            site_export = {
                "id": site_dict["id"],
                "name": site_dict["name"],
                "arabicName": site_dict["arabicName"],
                "era": site_dict["era"],
                "tourismType": site_dict["tourismType"],
                "placeType": site_dict["placeType"],
                "city": site_dict["city"],
                "latitude": site_dict["latitude"],
                "longitude": site_dict["longitude"],
                "shortDescription": site_dict["shortDescription"],
                "imageNames": site_dict["imageNames"],
                "estimatedDuration": site_dict["estimatedDuration"],
                "bestTimeToVisit": site_dict["bestTimeToVisit"],
            }
            output["sites"].append(site_export)

            # Sub-locations and cards
            for sub_loc in sub_locs:
                sub_export = {
                    "id": sub_loc["id"],
                    "siteId": sub_loc["siteId"],
                    "name": sub_loc["name"],
                    "arabicName": sub_loc["arabicName"],
                    "shortDescription": sub_loc["shortDescription"],
                    "imageName": sub_loc["imageName"],
                }
                output["subLocations"].append(sub_export)

                output["cards"].append({
                    "id": f"{sub_loc['id']}_card_01",
                    "subLocationId": sub_loc["id"],
                    "fullDescription": sub_loc["fullDescription"] or site_dict["fullDescription"]
                })

            # Tips
            for tip in tips:
                output["tips"].append({
                    "siteId": tip["siteId"],
                    "tip": tip["tip"]
                })

            # Arabic phrases
            for phrase in phrases:
                output["arabicPhrases"].append({
                    "siteId": phrase["siteId"],
                    "english": phrase["english"],
                    "arabic": phrase["arabic"],
                    "pronunciation": phrase["pronunciation"]
                })

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"Export complete: {output_path}")
        logger.info(f"  Sites: {len(output['sites'])}")
        logger.info(f"  Sub-locations: {len(output['subLocations'])}")
        logger.info(f"  Cards: {len(output['cards'])}")
        logger.info(f"  Tips: {len(output['tips'])}")
        logger.info(f"  Arabic Phrases: {len(output['arabicPhrases'])}")

        return output


# =============================================================================
# MAIN PARSER (FACADE)
# =============================================================================

class EgyMonumentsParser:
    """
    Main parser class that orchestrates all components.

    This class implements the Facade pattern, providing a simple interface
    to the complex subsystem of scraping, extraction, classification, and export.

    Usage:
        with EgyMonumentsParser() as parser:
            sites = parser.parse_sites(max_sites=10)
            parser.export_to_json("output.json")
    """

    def __init__(
        self,
        headless: bool = True,
        driver: Optional[webdriver.Chrome] = None
    ):
        """
        Initialize the parser.

        Args:
            headless: Whether to run browser in headless mode
            driver: Optional pre-configured WebDriver (for testing)
        """
        self.scraper = WebScraper(driver=driver, headless=headless)
        self.extractor = ContentExtractor(self.scraper)
        self.sites: list[Site] = []
        self.site_counter = 0

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()
        return False

    def close(self):
        """Close the parser and release resources."""
        self.scraper.close()

    def get_all_site_links(self, max_sites: Optional[int] = None) -> list[dict]:
        """
        Get all site links from the main listing page.

        Args:
            max_sites: Maximum number of sites to return (None for all)

        Returns:
            List of site info dictionaries
        """
        max_sites = Validator.validate_max_sites(max_sites)

        logger.info(f"Loading sites listing page: {Config.SITES_URL}")
        self.scraper.driver.get(Config.SITES_URL)
        self.scraper.wait_for_page_load()

        # Click "Show More" to load more sites
        max_clicks = Config.MAX_SHOW_MORE_CLICKS_LIMITED if max_sites else Config.MAX_SHOW_MORE_CLICKS
        show_more_clicks = 0

        while show_more_clicks < max_clicks:
            try:
                show_more = self.scraper.find_element_safe(
                    By.CSS_SELECTOR,
                    ".showMoreBtn, [class*='showMore'], button.showMore"
                )
                if show_more and show_more.is_displayed():
                    self.scraper.driver.execute_script("arguments[0].click();", show_more)
                    show_more_clicks += 1
                    logger.debug(f"Clicked 'Show More' ({show_more_clicks} times)")
                    time.sleep(Config.CLICK_WAIT)
                else:
                    break
            except (NoSuchElementException, StaleElementReferenceException):
                break

        # Extract site links
        site_links = []
        items = self.scraper.find_elements_safe(By.CSS_SELECTOR, "a.listItem")
        logger.info(f"Found {len(items)} site items")

        for item in items:
            try:
                href = item.get_attribute("href")
                if not href or "/archaeological-sites/" not in href:
                    continue

                title = item.get_attribute("title") or ""

                # Extract location
                location = ""
                try:
                    loc_elem = item.find_element(By.CSS_SELECTOR, ".location p")
                    location = loc_elem.text.strip()
                except (NoSuchElementException, StaleElementReferenceException):
                    pass

                # Extract description
                desc = ""
                try:
                    desc_elem = item.find_element(By.CSS_SELECTOR, ".details > p")
                    desc = desc_elem.text.strip()
                except (NoSuchElementException, StaleElementReferenceException):
                    pass

                # Extract image
                img = ""
                try:
                    img_elem = item.find_element(By.TAG_NAME, "img")
                    img = img_elem.get_attribute("src")
                except (NoSuchElementException, StaleElementReferenceException):
                    pass

                site_links.append({
                    "url": href,
                    "name": Sanitizer.sanitize_text(title),
                    "location": Sanitizer.sanitize_text(location),
                    "description": Sanitizer.sanitize_text(desc),
                    "image": img
                })
                logger.debug(f"  Found: {title} ({location})")

            except (StaleElementReferenceException, WebDriverException) as e:
                logger.warning(f"Error extracting site link: {e}")
                continue

        logger.info(f"Total sites found: {len(site_links)}")
        return site_links[:max_sites] if max_sites else site_links

    def parse_site_page(self, site_info: dict) -> Optional[Site]:
        """
        Parse a single site page and extract all information.

        Args:
            site_info: Dictionary with site URL, name, location, etc.

        Returns:
            Parsed Site object or None on failure
        """
        url = site_info.get("url", "")
        name = site_info.get("name", "Unknown")

        logger.info(f"Parsing: {name}")
        logger.debug(f"URL: {url}")

        if not Validator.validate_url(url):
            logger.warning(f"Skipping invalid URL: {url}")
            return None

        try:
            with log_timing(f"Parse {name}"):
                if not self.scraper.navigate(url):
                    return None

                self.scraper.wait_for_page_load()

                self.site_counter += 1
                site_id = self._generate_site_id(name, url)

                # Extract page title
                page_title = self.scraper.get_element_text(
                    By.CSS_SELECTOR, "h1, .title h1, .pageTitle"
                )
                name = page_title or name

                # Extract content
                full_description = self.extractor.extract_full_description()
                short_description = full_description or site_info.get("description", "")

                # Classify
                city = Classifier.normalize_city(site_info.get("location", ""))
                if not city:
                    city = Classifier.detect_city_from_text(full_description)

                era = Classifier.determine_era(full_description)
                tourism_type = Classifier.determine_tourism_type(era, full_description, name)
                place_type = Classifier.determine_place_type(name, full_description)

                # Extract additional data
                images = self.extractor.extract_images(site_info.get("image", ""))
                arabic_name = self.extractor.fetch_arabic_name(url)
                latitude, longitude = GeocodingService.search_coordinates(name, city)
                opening_hours = self.extractor.extract_opening_hours()
                ticket_prices = self.extractor.extract_ticket_prices()

                # Generate content
                additional_info: AdditionalInfo = {"duration": "", "best_time": ""}
                tips = ContentGenerator.generate_tips(
                    site_id, name, city, opening_hours, ticket_prices, additional_info
                )
                arabic_phrases = ContentGenerator.generate_arabic_phrases(site_id, place_type)
                sub_locations = SubLocationExtractor.extract_sublocations(
                    site_id, name, full_description
                )

                site = Site(
                    id=site_id,
                    name=name,
                    arabicName=arabic_name,
                    era=era,
                    tourismType=tourism_type,
                    placeType=place_type,
                    city=city,
                    latitude=latitude,
                    longitude=longitude,
                    shortDescription=short_description,
                    fullDescription=full_description,
                    imageNames=images,
                    estimatedDuration=additional_info.get("duration", ""),
                    bestTimeToVisit=additional_info.get("best_time", ""),
                    openingHours=opening_hours,
                    subLocations=sub_locations,
                    tips=tips,
                    arabicPhrases=arabic_phrases
                )

                self._log_site_summary(site)
                return site

        except Exception as e:
            logger.error(f"Error parsing site {url}: {e}")
            logger.debug(traceback.format_exc())
            return None

    def _generate_site_id(self, name: str, url: str) -> str:
        """
        Generate a consistent, unique site ID.

        Uses a hash of name and URL for consistency across runs.

        Args:
            name: Site name
            url: Site URL

        Returns:
            Site ID string
        """
        # Use counter for human-readable sequential IDs
        return f"site_{self.site_counter:03d}"

    def _log_site_summary(self, site: Site):
        """Log a summary of the parsed site."""
        logger.info(f"  ID: {site.id}")
        logger.info(f"  Arabic Name: {site.arabicName or 'N/A'}")
        logger.info(f"  City: {site.city or 'N/A'}")
        if site.latitude:
            logger.info(f"  Coordinates: {site.latitude}, {site.longitude}")
        logger.info(f"  Era: {site.era or 'N/A'}")
        logger.info(f"  Type: {site.tourismType} / {site.placeType}")
        logger.info(f"  Sub-locations: {len(site.subLocations)}")
        for sub in site.subLocations:
            logger.info(f"    - {sub.name}")

    def parse_sites(self, max_sites: Optional[int] = None) -> list[Site]:
        """
        Parse all sites from the listing page.

        Args:
            max_sites: Maximum number of sites to parse (None for all)

        Returns:
            List of parsed Site objects
        """
        site_links = self.get_all_site_links(max_sites)

        for site_info in site_links:
            site = self.parse_site_page(site_info)
            if site:
                self.sites.append(site)

        return self.sites

    def export_to_json(self, output_path: str, strict: bool = False) -> dict:
        """
        Export parsed sites to JSON.

        Args:
            output_path: Path to output file
            strict: If True, raise on validation errors

        Returns:
            Dictionary of exported data
        """
        return DataExporter.export_to_json(self.sites, output_path, strict)


# =============================================================================
# CLI INTERFACE
# =============================================================================

def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="UnlockEgypt Content Parser - Scrapes archaeological site information from egymonuments.gov.eg",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python parser.py                          # Parse all sites
  python parser.py -m 3                     # Parse first 3 sites (testing)
  python parser.py -o custom_output.json    # Custom output path
  python parser.py -v                       # Verbose output
  python parser.py --no-headless            # Show browser window
        """
    )

    parser.add_argument(
        "-o", "--output",
        default=os.path.join(os.path.dirname(__file__), "parsed_sites.json"),
        help="Output JSON file path (default: parsed_sites.json)"
    )

    parser.add_argument(
        "-m", "--max-sites",
        type=int,
        default=None,
        help="Maximum number of sites to parse (default: all)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging"
    )

    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window (disable headless mode)"
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation (fail on invalid data)"
    )

    return parser.parse_args()


def main():
    """Main entry point for the parser."""
    args = parse_arguments()

    # Configure logging level
    if args.verbose:
        logging.getLogger('UnlockEgyptParser').setLevel(logging.DEBUG)

    print("=" * 60)
    print("UnlockEgypt Content Parser v3.0")
    print("=" * 60)
    print()

    headless = not args.no_headless

    with EgyMonumentsParser(headless=headless) as parser:
        # Parse sites
        if args.max_sites:
            logger.info(f"Parsing first {args.max_sites} sites...")
        else:
            logger.info("Parsing all sites from egymonuments.gov.eg...")

        sites = parser.parse_sites(max_sites=args.max_sites)

        # Export results
        parser.export_to_json(args.output, strict=args.strict)

        # Print final summary
        print()
        print("=" * 60)
        print("PARSING COMPLETE")
        print("=" * 60)

        for site in sites:
            print(f"\n{site.name}")
            print(f"  City: {site.city or 'N/A'}")
            print(f"  Era: {site.era or 'N/A'}")
            print(f"  Type: {site.tourismType} / {site.placeType}")
            print(f"  Sub-locations: {len(site.subLocations)}")
            for sub in site.subLocations:
                print(f"    - {sub.name}")


if __name__ == "__main__":
    main()
