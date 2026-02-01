"""
Google Maps Researcher - Gathers practical visitor information.

Uses web scraping to get:
- Opening hours
- Visitor ratings and review count
- Exact coordinates
- Popular times
- Contact information
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote as url_quote

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from utils import config

logger = logging.getLogger('UnlockEgyptParser')


@dataclass
class GoogleMapsData:
    """Data extracted from Google Maps research."""
    name: str = ""
    address: str = ""
    opening_hours: dict[str, str] = field(default_factory=dict)
    opening_hours_text: str = ""
    rating: Optional[float] = None
    review_count: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: str = ""
    website: str = ""
    place_type: str = ""
    visitor_tips: list[str] = field(default_factory=list)


class GoogleMapsResearcher:
    """
    Researches sites on Google Maps for practical visitor information.

    Uses Selenium to scrape Google Maps search results and place details.
    """

    GOOGLE_MAPS_URL = "https://www.google.com/maps/search/"

    def __init__(self, driver: Optional[webdriver.Chrome] = None):
        """
        Initialize the Google Maps researcher.

        Args:
            driver: Optional shared WebDriver instance
        """
        self._driver = driver
        self._owns_driver = driver is None

    def _get_driver(self) -> webdriver.Chrome:
        """Get or create a WebDriver instance."""
        if self._driver is None:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            width, height = config.window_size
            options.add_argument(f"--window-size={width},{height}")
            options.add_argument("--lang=en")
            self._driver = webdriver.Chrome(options=options)
        return self._driver

    def close(self):
        """Close the WebDriver if we own it."""
        if self._owns_driver and self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

    def research(self, site_name: str, location: str = "Egypt") -> Optional[GoogleMapsData]:
        """
        Research a site on Google Maps.

        Args:
            site_name: Name of the site to research
            location: Location context (default: Egypt)

        Returns:
            GoogleMapsData with research findings or None if not found
        """
        logger.info(f"Researching on Google Maps: {site_name}")

        search_query = f"{site_name} {location}"
        search_url = f"{self.GOOGLE_MAPS_URL}{url_quote(search_query)}"

        try:
            driver = self._get_driver()
            driver.get(search_url)

            # Wait for results to load
            time.sleep(config.show_more_wait)

            data = GoogleMapsData()
            data.name = site_name

            # Try to extract information from the page
            self._extract_basic_info(driver, data)
            self._extract_opening_hours(driver, data)
            self._extract_coordinates_from_url(driver, data)
            self._extract_reviews_info(driver, data)

            return data

        except Exception as e:
            logger.warning(f"Google Maps research failed for {site_name}: {e}")
            return None

    def _extract_basic_info(self, driver: webdriver.Chrome, data: GoogleMapsData):
        """Extract basic place information."""
        try:
            # Try to find the place name
            name_selectors = [
                "h1.DUwDvf",
                "h1[data-attrid='title']",
                ".qBF1Pd",
            ]
            for selector in name_selectors:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, selector)
                    if elem.text:
                        data.name = elem.text.strip()
                        break
                except NoSuchElementException:
                    continue

            # Try to find address
            address_selectors = [
                "button[data-item-id='address']",
                ".rogA2c",
                "[data-tooltip='Copy address']",
            ]
            for selector in address_selectors:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, selector)
                    if elem.text:
                        data.address = elem.text.strip()
                        break
                except NoSuchElementException:
                    continue

            # Try to find phone
            try:
                phone_elem = driver.find_element(By.CSS_SELECTOR, "button[data-item-id^='phone']")
                if phone_elem.text:
                    data.phone = phone_elem.text.strip()
            except NoSuchElementException:
                pass

            # Try to find website
            try:
                website_elem = driver.find_element(By.CSS_SELECTOR, "a[data-item-id='authority']")
                data.website = website_elem.get_attribute("href") or ""
            except NoSuchElementException:
                pass

        except Exception as e:
            logger.debug(f"Error extracting basic info: {e}")

    def _extract_opening_hours(self, driver: webdriver.Chrome, data: GoogleMapsData):
        """Extract opening hours information."""
        try:
            # Try to find and click on opening hours to expand
            hours_button_selectors = [
                "button[data-item-id='oh']",
                ".OqCZI button",
                "[aria-label*='hours']",
            ]

            for selector in hours_button_selectors:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, selector)
                    elem.click()
                    time.sleep(config.geocoding_rate_limit)  # Short wait for UI
                    break
                except (NoSuchElementException, Exception):
                    continue

            # Try to extract hours text
            hours_selectors = [
                ".t39EBf",
                ".OqCZI",
                "[aria-label*='hours']",
            ]

            for selector in hours_selectors:
                try:
                    elems = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elems:
                        text = elem.text.strip()
                        if text and any(day in text.lower() for day in ['monday', 'tuesday', 'sunday', 'open', 'closed']):
                            data.opening_hours_text = text
                            self._parse_hours_text(text, data)
                            return
                except NoSuchElementException:
                    continue

        except Exception as e:
            logger.debug(f"Error extracting opening hours: {e}")

    def _parse_hours_text(self, text: str, data: GoogleMapsData):
        """Parse opening hours text into structured format."""
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower()
            for day in days:
                if day in line_lower:
                    # Extract time range
                    time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM)?)\s*[-–to]+\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM)?)', line, re.IGNORECASE)
                    if time_match:
                        data.opening_hours[day.title()] = f"{time_match.group(1)} - {time_match.group(2)}"
                    elif 'closed' in line_lower:
                        data.opening_hours[day.title()] = "Closed"
                    break

    def _extract_coordinates_from_url(self, driver: webdriver.Chrome, data: GoogleMapsData):
        """Extract coordinates from the Google Maps URL."""
        try:
            current_url = driver.current_url

            # URL format: .../@lat,lon,zoom...
            coord_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', current_url)
            if coord_match:
                data.latitude = float(coord_match.group(1))
                data.longitude = float(coord_match.group(2))
                logger.debug(f"Extracted coordinates: {data.latitude}, {data.longitude}")

        except Exception as e:
            logger.debug(f"Error extracting coordinates: {e}")

    def _extract_reviews_info(self, driver: webdriver.Chrome, data: GoogleMapsData):
        """Extract rating and review count."""
        try:
            # Try to find rating
            rating_selectors = [
                ".F7nice span[aria-hidden='true']",
                ".ceNzKf",
                "[aria-label*='stars']",
            ]

            for selector in rating_selectors:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, selector)
                    text = elem.text or elem.get_attribute("aria-label") or ""
                    rating_match = re.search(r'(\d+\.?\d*)', text)
                    if rating_match:
                        rating = float(rating_match.group(1))
                        if 0 <= rating <= 5:
                            data.rating = rating
                            break
                except NoSuchElementException:
                    continue

            # Try to find review count
            review_selectors = [
                ".F7nice span:last-child",
                "[aria-label*='review']",
            ]

            for selector in review_selectors:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, selector)
                    text = elem.text or elem.get_attribute("aria-label") or ""
                    count_match = re.search(r'([\d,]+)\s*review', text, re.IGNORECASE)
                    if count_match:
                        data.review_count = int(count_match.group(1).replace(',', ''))
                        break
                except NoSuchElementException:
                    continue

        except Exception as e:
            logger.debug(f"Error extracting reviews info: {e}")

    def get_opening_hours_simple(self, site_name: str, location: str = "Egypt") -> str:
        """
        Get a simple opening hours string for a site.

        Returns a formatted string like "9:00 AM - 5:00 PM" or empty string.
        """
        data = self.research(site_name, location)
        if data and data.opening_hours_text:
            # Try to extract a simple time range
            time_match = re.search(
                r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM)?)\s*[-–to]+\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM)?)',
                data.opening_hours_text,
                re.IGNORECASE
            )
            if time_match:
                return f"{time_match.group(1)} - {time_match.group(2)}"

        return ""
