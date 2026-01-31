#!/usr/bin/env python3
"""
UnlockEgypt Content Parser
Scrapes archaeological site information from egymonuments.gov.eg
Enhanced with web search for additional details like opening hours, tips, etc.
"""

import json
import time
import re
import requests
from dataclasses import dataclass, asdict, field
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


@dataclass
class Tip:
    siteId: str
    tip: str


@dataclass
class ArabicPhrase:
    siteId: str
    english: str
    arabic: str
    pronunciation: str


@dataclass
class SubLocation:
    id: str
    siteId: str
    name: str
    arabicName: str
    shortDescription: str
    imageName: str
    fullDescription: str


@dataclass
class Site:
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


class EgyMonumentsParser:
    BASE_URL = "https://egymonuments.gov.eg"
    SITES_URL = f"{BASE_URL}/en/archaeological-sites/"

    # Valid Era values from UnlockEgypt app
    VALID_ERAS = [
        "Pre-Dynastic", "Old Kingdom", "Middle Kingdom", "New Kingdom",
        "Late Period", "Ptolemaic", "Roman", "Islamic", "Modern"
    ]

    # Era keyword mapping
    ERA_KEYWORDS = {
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

    # Valid Tourism Types from UnlockEgypt app
    VALID_TOURISM_TYPES = ["Pharaonic", "Greco-Roman", "Coptic", "Islamic", "Modern"]

    # Valid Place Types from UnlockEgypt app
    VALID_PLACE_TYPES = [
        "Pyramid", "Temple", "Tomb", "Museum", "Mosque",
        "Church", "Fortress", "Market", "Monument", "Ruins"
    ]

    # City normalization
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
        "al-minya": "Cairo",  # Map to nearest major city
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

    # Common Arabic phrases for tourism
    COMMON_PHRASES = [
        ("Hello", "مرحبا", "Marhaba"),
        ("Thank you", "شكرا", "Shukran"),
        ("How much?", "بكام؟", "Bikam?"),
        ("Where is...?", "فين...؟", "Fein...?"),
        ("Beautiful", "جميل", "Gameel"),
        ("Ancient", "قديم", "Adeem"),
        ("Temple", "معبد", "Ma'bad"),
        ("Pyramid", "هرم", "Haram"),
        ("Tomb", "مقبرة", "Maqbara"),
        ("Museum", "متحف", "Mat-haf"),
        ("Ticket", "تذكرة", "Tazkara"),
        ("Water", "مياه", "Mayya"),
        ("Yes", "أيوه", "Aywa"),
        ("No", "لا", "La"),
    ]

    def __init__(self, headless: bool = True):
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--lang=en")
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        self.sites: list[Site] = []
        self.site_counter = 0

    def close(self):
        self.driver.quit()

    def get_all_site_links(self, max_sites: Optional[int] = None) -> list[dict]:
        """Get all site links from the main listing page."""
        print(f"Loading sites listing page: {self.SITES_URL}")
        self.driver.get(self.SITES_URL)

        print("Waiting for page to load...")
        time.sleep(5)

        # Click "Show More" to load more sites
        show_more_clicks = 0
        max_show_more = 50 if not max_sites else 3

        while show_more_clicks < max_show_more:
            try:
                show_more = self.driver.find_element(
                    By.CSS_SELECTOR, ".showMoreBtn, [class*='showMore'], button.showMore"
                )
                if show_more.is_displayed():
                    self.driver.execute_script("arguments[0].click();", show_more)
                    show_more_clicks += 1
                    print(f"Clicked 'Show More' ({show_more_clicks} times)")
                    time.sleep(2)
                else:
                    break
            except NoSuchElementException:
                break
            except Exception:
                break

        # Find all site links
        site_links = []
        try:
            items = self.driver.find_elements(By.CSS_SELECTOR, "a.listItem")
            print(f"Found {len(items)} site items")

            for item in items:
                try:
                    href = item.get_attribute("href")
                    title = item.get_attribute("title") or ""

                    location = ""
                    try:
                        loc_elem = item.find_element(By.CSS_SELECTOR, ".location p")
                        location = loc_elem.text.strip()
                    except:
                        pass

                    desc = ""
                    try:
                        desc_elem = item.find_element(By.CSS_SELECTOR, ".details > p")
                        desc = desc_elem.text.strip()
                    except:
                        pass

                    img = ""
                    try:
                        img_elem = item.find_element(By.TAG_NAME, "img")
                        img = img_elem.get_attribute("src")
                    except:
                        pass

                    if href and "/archaeological-sites/" in href:
                        site_links.append({
                            "url": href,
                            "name": title,
                            "location": location,
                            "description": desc,
                            "image": img
                        })
                        print(f"  Found: {title} ({location})")
                except:
                    continue

        except Exception as e:
            print(f"Error finding site links: {e}")

        print(f"\nTotal sites found: {len(site_links)}")
        return site_links[:max_sites] if max_sites else site_links

    def parse_site_page(self, site_info: dict) -> Optional[Site]:
        """Parse a single site page and extract all information."""
        url = site_info["url"]
        print(f"\n{'='*60}")
        print(f"Parsing: {site_info['name']}")
        print(f"URL: {url}")

        try:
            self.driver.get(url)
            time.sleep(3)

            self.site_counter += 1
            site_id = f"site_{self.site_counter:03d}"

            # Extract site name
            name = site_info["name"]
            try:
                h1 = self.driver.find_element(By.CSS_SELECTOR, "h1, .title h1, .pageTitle")
                name = h1.text.strip() or name
            except:
                pass

            # Extract full description from the detail page
            full_description = self._extract_full_description()

            # Use full description, don't truncate
            short_description = full_description if full_description else site_info.get("description", "")

            # Extract city
            city = self._normalize_city(site_info.get("location", ""))
            if not city:
                city = self._detect_city_from_text(full_description)

            # Extract era
            era = self._determine_era(full_description)

            # Determine tourism type and place type
            tourism_type = self._determine_tourism_type(era, full_description, name)
            place_type = self._determine_place_type(name, full_description)

            # Extract images
            images = self._extract_images(site_info.get("image", ""))

            # Get Arabic name from Arabic version of the page
            arabic_name = self._fetch_arabic_name(url)

            # Get coordinates from Google Maps search
            latitude, longitude = self._search_coordinates(name, city)

            # Extract opening hours from the page
            opening_hours = self._extract_opening_hours()

            # Extract ticket prices
            ticket_prices = self._extract_ticket_prices()

            # Search for additional info (duration, best time, tips)
            additional_info = self._search_additional_info(name, city)

            # Generate tips
            tips = self._generate_tips(site_id, name, city, opening_hours, ticket_prices, additional_info)

            # Generate Arabic phrases relevant to this site (place-specific, not generic)
            arabic_phrases = self._generate_arabic_phrases(site_id, place_type, full_description)

            # Determine sub-locations
            # If no meaningful sub-locations, site itself becomes the sub-location
            sub_locations = self._extract_meaningful_sublocations(site_id, name, full_description)

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

            self._print_site_summary(site)
            return site

        except Exception as e:
            print(f"Error parsing site {url}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_full_description(self) -> str:
        """Extract the full description text from the page."""
        paragraphs = []

        try:
            # Get all paragraphs on the page
            all_p = self.driver.find_elements(By.TAG_NAME, "p")
            for p in all_p:
                text = p.text.strip()
                # Filter: must be substantial content, not navigation/footer
                if (text and
                    len(text) > 40 and
                    not self._is_navigation_text(text) and
                    not self._is_footer_text(text)):
                    paragraphs.append(text)
        except Exception as e:
            print(f"  Error extracting paragraphs: {e}")

        return "\n\n".join(paragraphs)

    def _is_footer_text(self, text: str) -> bool:
        """Check if text is footer/copyright content."""
        footer_indicators = ["copyright", "developed by", "all rights reserved", "ministry of"]
        text_lower = text.lower()
        return any(footer in text_lower for footer in footer_indicators)

    def _is_navigation_text(self, text: str) -> bool:
        """Check if text is likely navigation/UI rather than content."""
        nav_indicators = ["read more", "click here", "show more", "back to", "home >"]
        text_lower = text.lower()
        return any(nav in text_lower for nav in nav_indicators)

    def _normalize_city(self, location_text: str) -> str:
        """Normalize city name to match UnlockEgypt valid values."""
        if not location_text:
            return ""
        location_lower = location_text.lower().strip()
        for city_keyword, normalized in self.CITY_MAP.items():
            if city_keyword in location_lower:
                return normalized
        return ""

    def _detect_city_from_text(self, text: str) -> str:
        """Try to detect city from description text."""
        if not text:
            return ""
        text_lower = text.lower()
        for city_keyword, normalized in self.CITY_MAP.items():
            if city_keyword in text_lower:
                return normalized
        return ""

    def _determine_era(self, description: str) -> str:
        """Determine historical era from description - picks the OLDEST era mentioned."""
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

        # Then check for later eras
        if "ptolemaic" in desc_lower:
            return "Ptolemaic"
        if "roman and byzantine" in desc_lower or ("roman" in desc_lower and "byzantine" in desc_lower):
            return "Roman"
        if "roman period" in desc_lower or "roman era" in desc_lower:
            return "Roman"
        if "islamic" in desc_lower or "fatimid" in desc_lower or "mamluk" in desc_lower or "ayyubid" in desc_lower:
            return "Islamic"

        # Try to extract century/date patterns
        # Look for BC dates first (older)
        bc_match = re.search(r'(\d+)\s*(bc|b\.c\.|bce)', desc_lower)
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

        # Look for AD dates
        ad_match = re.search(r'(\d+)\s*(?:st|nd|rd|th)?\s*(?:century)?\s*(ad|a\.d\.|ce)', desc_lower)
        if ad_match:
            year = int(ad_match.group(1))
            if year < 100:  # It's a century
                year = year * 100
            if year < 395:
                return "Roman"
            elif year < 641:
                return "Roman"  # Byzantine
            else:
                return "Islamic"

        return ""

    def _determine_tourism_type(self, era: str, description: str, name: str) -> str:
        """Determine tourism type based on era and description."""
        combined = (description + " " + name).lower()

        # For Pharaonic eras, always return Pharaonic
        pharaonic_eras = ["Pre-Dynastic", "Old Kingdom", "Middle Kingdom", "New Kingdom", "Late Period"]
        if era in pharaonic_eras:
            return "Pharaonic"

        # For Roman/Ptolemaic eras, return Greco-Roman
        if era in ["Roman", "Ptolemaic"]:
            return "Greco-Roman"

        # For Islamic era, return Islamic
        if era == "Islamic":
            return "Islamic"

        # Check for specific indicators when era is unknown
        if any(word in combined for word in ["mosque", "madrasa", "minaret", "islamic"]):
            return "Islamic"
        if any(word in combined for word in ["coptic", "christian", "church", "monastery", "convent"]):
            return "Coptic"
        if any(word in combined for word in ["roman", "greco", "greek", "ptolem", "hellenistic", "amphitheatre", "byzantine"]):
            return "Greco-Roman"

        # Check for "modern period" or "modern era" (not just "modern" to avoid "modern Alexandria")
        if "modern period" in combined or "modern era" in combined or "19th century" in combined or "20th century" in combined:
            return "Modern"

        return "Pharaonic"  # Default for ancient Egyptian sites

    def _determine_place_type(self, name: str, description: str) -> str:
        """Determine place type based on name and description."""
        combined = (name + " " + description).lower()

        place_keywords = [
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

        for keyword, place_type in place_keywords:
            if keyword in combined:
                return place_type

        return "Ruins"

    def _extract_images(self, listing_image: str) -> list[str]:
        """Extract all images from the page."""
        images = []
        if listing_image:
            images.append(listing_image)

        try:
            # Look for gallery/slider images
            img_elems = self.driver.find_elements(By.CSS_SELECTOR,
                ".gallery img, .slider img, .monumentGallery img, article img, .swiper-slide img")
            for img in img_elems:
                src = img.get_attribute("src")
                if src and src not in images and "logo" not in src.lower() and "icon" not in src.lower():
                    images.append(src)
        except:
            pass

        return images

    def _fetch_arabic_name(self, english_url: str) -> str:
        """Fetch the Arabic name from the Arabic version of the page."""
        try:
            # Convert /en/ to /ar/ in URL
            arabic_url = english_url.replace("/en/", "/ar/")

            # Store current URL
            current_url = self.driver.current_url

            self.driver.get(arabic_url)
            time.sleep(2)

            # Try to find the Arabic title
            try:
                h1 = self.driver.find_element(By.CSS_SELECTOR, "h1, .title h1, .pageTitle")
                arabic_name = h1.text.strip()
                # Verify it contains Arabic characters
                if arabic_name and any('\u0600' <= c <= '\u06FF' for c in arabic_name):
                    print(f"  Arabic name: {arabic_name}")
                    # Go back to English page
                    self.driver.get(current_url)
                    time.sleep(1)
                    return arabic_name
            except:
                pass

            # Go back to English page
            self.driver.get(current_url)
            time.sleep(1)

        except Exception as e:
            print(f"  Could not fetch Arabic name: {e}")

        return ""

    def _search_coordinates(self, site_name: str, city: str) -> tuple[float, float]:
        """Search for site coordinates using OpenStreetMap Nominatim API."""
        try:
            # Use Nominatim (OpenStreetMap) geocoding API
            search_query = f"{site_name}, {city}, Egypt"
            url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(search_query)}&format=json&limit=1"

            headers = {
                "User-Agent": "UnlockEgyptParser/1.0 (educational project)"
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                results = response.json()
                if results:
                    lat = float(results[0]["lat"])
                    lon = float(results[0]["lon"])

                    # Validate Egypt bounds (lat 21-32, lon 24-37)
                    if 21 <= lat <= 32 and 24 <= lon <= 37:
                        print(f"  Coordinates: {lat}, {lon}")
                        return lat, lon

            # Try with just site name and Egypt
            search_query2 = f"{site_name}, Egypt"
            url2 = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(search_query2)}&format=json&limit=1"

            response2 = requests.get(url2, headers=headers, timeout=10)

            if response2.status_code == 200:
                results2 = response2.json()
                if results2:
                    lat = float(results2[0]["lat"])
                    lon = float(results2[0]["lon"])

                    if 21 <= lat <= 32 and 24 <= lon <= 37:
                        print(f"  Coordinates: {lat}, {lon}")
                        return lat, lon

            # Rate limit: wait between requests
            time.sleep(1)

        except Exception as e:
            print(f"  Could not search coordinates: {e}")

        return None, None

    def _extract_opening_hours(self) -> str:
        """Extract opening hours from the page."""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # Look for Opening Hours section and extract times
            if "Opening Hours" in page_text:
                # Pattern: From HH:MM AM/PM To HH:MM AM/PM
                time_pattern = r'From\s*(\d{1,2}:\d{2}\s*(?:AM|PM))\s*To\s*(\d{1,2}:\d{2}\s*(?:AM|PM))'
                match = re.search(time_pattern, page_text, re.IGNORECASE)
                if match:
                    return f"{match.group(1)} - {match.group(2)}"

            # Fallback: look for any time range pattern
            time_range = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM)?)\s*[-–to]+\s*(\d{1,2}:\d{2}\s*(?:AM|PM)?)', page_text, re.IGNORECASE)
            if time_range:
                return f"{time_range.group(1)} - {time_range.group(2)}"

        except Exception as e:
            print(f"  Error extracting opening hours: {e}")

        return ""

    def _extract_ticket_prices(self) -> dict:
        """Extract ticket prices from the page."""
        prices = {}
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # Look for ticket/admission section
            if "Tickets" in page_text or "FOREIGNERS" in page_text:
                # Extract foreigner prices
                foreigner_match = re.search(r'FOREIGNERS?:?\s*Adult:?\s*EGP\s*(\d+)\s*/?\s*Student:?\s*EGP\s*(\d+)', page_text, re.IGNORECASE)
                if foreigner_match:
                    prices["foreigners_adult"] = f"EGP {foreigner_match.group(1)}"
                    prices["foreigners_student"] = f"EGP {foreigner_match.group(2)}"

                # Extract Egyptian prices
                egyptian_match = re.search(r'EGYPTIANS?:?\s*Adult:?\s*EGP\s*(\d+)\s*/?\s*Student:?\s*EGP\s*(\d+)', page_text, re.IGNORECASE)
                if egyptian_match:
                    prices["egyptians_adult"] = f"EGP {egyptian_match.group(1)}"
                    prices["egyptians_student"] = f"EGP {egyptian_match.group(2)}"

        except Exception as e:
            print(f"  Error extracting ticket prices: {e}")

        return prices

    def _search_additional_info(self, site_name: str, city: str) -> dict:
        """Search for additional info like duration, best time to visit."""
        info = {
            "duration": "",
            "best_time": "",
        }

        try:
            # Use a travel site search for better results
            search_queries = [
                f"{site_name} {city} Egypt how long to visit",
                f"{site_name} Egypt visit time needed",
            ]

            for search_query in search_queries:
                if info["duration"] and info["best_time"]:
                    break

                url = f"https://www.google.com/search?q={requests.utils.quote(search_query)}"

                current_url = self.driver.current_url
                self.driver.get(url)
                time.sleep(2)

                page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()

                # Look for duration mentions
                if not info["duration"]:
                    duration_patterns = [
                        r'(\d+\s*-\s*\d+\s*hours?)',
                        r'(\d+\s*to\s*\d+\s*hours?)',
                        r'(about\s*\d+\s*hours?)',
                        r'(around\s*\d+\s*hours?)',
                        r'(at least\s*\d+\s*hours?)',
                        r'(half\s*a?\s*day)',
                        r'(full\s*day)',
                        r'(\d+\s*hours?\s*(?:is|are)\s*(?:enough|sufficient|recommended))',
                        r'(?:spend|need|takes?|requires?)\s*(?:about|around|approximately)?\s*(\d+\s*-?\s*\d*\s*hours?)',
                    ]
                    for pattern in duration_patterns:
                        match = re.search(pattern, page_text)
                        if match:
                            duration = match.group(1).strip()
                            # Clean up and format
                            duration = re.sub(r'\s+', ' ', duration)
                            info["duration"] = duration.title() if 'day' in duration.lower() else duration
                            print(f"  Duration: {info['duration']}")
                            break

                # Look for best time mentions
                if not info["best_time"]:
                    best_time_patterns = [
                        r'best time[^.]*?(?:is|to visit)[^.]*?(early morning|morning|afternoon|evening|winter|summer|spring|autumn|fall|october|november|december|january|february|march|april)',
                        r'(early morning|morning|late afternoon)[^.]*(?:is |are )?(?:best|ideal|recommended)',
                        r'(?:visit|go)[^.]*?(early morning|morning|late afternoon|winter months?|cooler months?)',
                        r'(?:avoid|skip)[^.]*?(midday|noon|summer heat)',
                    ]
                    for pattern in best_time_patterns:
                        match = re.search(pattern, page_text)
                        if match:
                            best_time = match.group(1).strip().title()
                            info["best_time"] = best_time
                            print(f"  Best time: {info['best_time']}")
                            break

                self.driver.get(current_url)
                time.sleep(1)

        except Exception as e:
            print(f"  Note: Could not search for additional info: {e}")

        return info

    def _generate_tips(self, site_id: str, name: str, city: str, opening_hours: str, ticket_prices: dict, additional_info: dict) -> list[Tip]:
        """Generate practical tips for the site."""
        tips = []

        # Add opening hours as a tip if available
        if opening_hours:
            tips.append(Tip(siteId=site_id, tip=f"Opening hours: {opening_hours}"))

        # Add ticket prices as a tip if available
        if ticket_prices:
            if "foreigners_adult" in ticket_prices:
                tips.append(Tip(
                    siteId=site_id,
                    tip=f"Ticket prices (foreigners): Adult {ticket_prices['foreigners_adult']}, Student {ticket_prices.get('foreigners_student', 'N/A')}"
                ))
            if "egyptians_adult" in ticket_prices:
                tips.append(Tip(
                    siteId=site_id,
                    tip=f"Ticket prices (Egyptians): Adult {ticket_prices['egyptians_adult']}, Student {ticket_prices.get('egyptians_student', 'N/A')}"
                ))

        # Add city-specific tips
        city_tips = {
            "Alexandria": "Bring sunscreen and a hat - the Mediterranean sun can be intense.",
            "Cairo": "Start early to avoid crowds and the midday heat.",
            "Giza": "Hire an official guide at the entrance for the best experience.",
            "Luxor": "Consider visiting early morning or late afternoon to avoid peak heat.",
            "Aswan": "Carry plenty of water, especially during summer months.",
        }
        if city in city_tips:
            tips.append(Tip(siteId=site_id, tip=city_tips[city]))

        # General archaeological site tips
        tips.append(Tip(siteId=site_id, tip="Wear comfortable walking shoes suitable for uneven terrain."))
        tips.append(Tip(siteId=site_id, tip="Photography may require an additional permit - check at the entrance."))

        return tips

    def _generate_arabic_phrases(self, site_id: str, place_type: str, description: str = "") -> list[ArabicPhrase]:
        """Generate site-specific Arabic phrases (not generic greetings)."""
        phrases = []

        # Place-type specific vocabulary
        place_phrases = {
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

        if place_type in place_phrases:
            for eng, ar, pron in place_phrases[place_type]:
                phrases.append(ArabicPhrase(siteId=site_id, english=eng, arabic=ar, pronunciation=pron))

        return phrases

    def _extract_meaningful_sublocations(self, site_id: str, site_name: str, description: str) -> list[SubLocation]:
        """
        Extract meaningful sub-locations that warrant their own cards.
        Only includes significant places that deserve separate exploration.
        If no meaningful sub-locations, the site itself becomes the sub-location.
        """
        sub_locations = []

        # Define patterns for significant sub-locations (places worth their own cards)
        # These should be distinct areas a visitor would explore separately
        significant_features = [
            # Theaters and entertainment venues
            (r'Roman\s+Theater\s*\([^)]+\)', "theater"),  # Roman Theater (Odeon)
            (r'Roman\s+Theater(?!\s*\()', "theater"),     # Roman Theater without parentheses
            (r'Amphitheatre', "theater"),
            # Villas and residential
            (r'Villa\s+of\s+the\s+[A-Z][a-z]+', "villa"),  # Villa of the Birds
            # Baths
            (r'Roman\s+Baths?', "baths"),
            (r'Public\s+Baths?', "baths"),
            # Educational
            (r'Lecture\s+Halls?', "educational"),
            (r'Library', "educational"),
            # Temples - use known Egyptian deity names for accurate extraction
            # Common Egyptian deities (case insensitive for matching)
            (r'[Tt]emple\s+of\s+(?:[^,]*?\s+)?([Kk]hnum|[Ss]atet|[Kk]honsu|[Aa]mun|[Rr]a|[Hh]orus|[Ii]sis|[Oo]siris|[Hh]athor|[Tt]hoth|[Pp]tah|[Aa]nubis|[Ss]obek|[Ss]ekhmet|[Bb]astet|[Mm]ut|[Aa]ten|[Mm]in|[Nn]efertum|[Nn]eith|[Mm]ontu|[Ww]epwawet|[Ss]et)\b', "temple"),
            # Also look for deity name after comma (e.g., "temple of the goddess..., Satet")
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

        found_features = []
        found_names_lower = set()  # Track names to avoid duplicates

        for pattern, feature_type in significant_features:
            matches = re.finditer(pattern, description, re.IGNORECASE)
            for match in matches:
                full_match = match.group(0).strip()

                # For temples/tombs, we capture the deity/person name in group 1
                if match.lastindex and match.lastindex >= 1:
                    captured_name = match.group(1).strip()
                    if feature_type == "temple":
                        feature_name = f"Temple of {captured_name.title()}"
                    elif feature_type == "tomb":
                        feature_name = f"Tomb of {captured_name.title()}"
                    elif feature_type == "mosque":
                        feature_name = f"Mosque of {captured_name.title()}"
                    elif feature_type == "church":
                        feature_name = f"Church of {captured_name.title()}"
                    else:
                        feature_name = full_match.title()
                else:
                    feature_name = full_match.title()

                # Avoid duplicates (case-insensitive)
                name_lower = feature_name.lower()
                # Also check if this is a subset of an existing name
                is_duplicate = False
                for existing in found_names_lower:
                    if name_lower in existing or existing in name_lower:
                        is_duplicate = True
                        break

                if not is_duplicate and len(feature_name) > 4:
                    found_features.append((feature_name, feature_type))
                    found_names_lower.add(name_lower)

        # Create sub-locations for significant features only
        sub_counter = 0
        for feature_name, feature_type in found_features:
            if sub_counter >= 5:
                break
            sub_counter += 1
            sub_id = f"{site_id}_sub_{sub_counter:02d}"

            # Generate a proper English description for this feature
            feature_desc = self._generate_feature_description(feature_name, feature_type, description, site_name)

            sub_locations.append(SubLocation(
                id=sub_id,
                siteId=site_id,
                name=feature_name,
                arabicName="",
                shortDescription=feature_desc,
                imageName="",
                fullDescription=feature_desc
            ))

        # If no meaningful sub-locations found, the site itself is the sub-location
        if not sub_locations:
            # Generate a proper description for the site as a whole
            site_desc = self._summarize_site_description(description, site_name)
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

    def _generate_feature_description(self, feature_name: str, feature_type: str, full_description: str, site_name: str) -> str:
        """Generate a proper English sentence description for a feature."""
        # Extract relevant info from the full description
        feature_lower = feature_name.lower()
        sentences = re.split(r'(?<=[.!?])\s+', full_description)

        relevant_info = []
        for sentence in sentences:
            if feature_lower in sentence.lower() or any(word in sentence.lower() for word in feature_lower.split()):
                relevant_info.append(sentence.strip())

        # Build a proper description based on what we found
        if relevant_info:
            # Extract key details
            details = " ".join(relevant_info)

            # Look for specific descriptive elements
            if feature_type == "theater":
                if "only" in details.lower() and "egypt" in details.lower():
                    return f"The {feature_name} is the only Roman theater discovered in Egypt. It features tiered marble seating and served as a venue for musical performances and public gatherings in ancient times."
                elif "marble" in details.lower() or "seats" in details.lower():
                    return f"The {feature_name} is a well-preserved ancient performance venue with tiered marble seating, offering visitors a glimpse into the entertainment culture of Roman Alexandria."
                else:
                    return f"The {feature_name} is a significant archaeological feature that showcases Roman architectural and cultural influence in ancient Egypt."

            elif feature_type == "villa":
                if "mosaic" in details.lower() or "birds" in details.lower():
                    return f"The {feature_name} is renowned for its stunning floor mosaics depicting colorful birds and intricate geometric patterns, representing the luxurious lifestyle of wealthy Roman residents."
                else:
                    return f"The {feature_name} provides insight into the residential life of affluent citizens during the Roman period."

            elif feature_type == "baths":
                if "hypocaust" in details.lower() or "heating" in details.lower():
                    return f"The {feature_name} demonstrate advanced Roman engineering, featuring a sophisticated hypocaust (underfloor heating) system that showcases the technological achievements of the era."
                else:
                    return f"The {feature_name} were an important social gathering place in ancient times, reflecting Roman bathing culture and engineering."

            elif feature_type == "educational":
                if "school" in details.lower() or "university" in details.lower() or "philosoph" in details.lower():
                    return f"The {feature_name} are believed to be part of an ancient philosophical school or university, offering a rare glimpse into academic life in Greco-Roman Alexandria."
                else:
                    return f"The {feature_name} served as an important educational or civic space in ancient times."

            elif feature_type == "temple":
                return f"The {feature_name} is a sacred religious site that served as a center of worship and spiritual practice in ancient Egypt."

            elif feature_type == "tomb":
                return f"The {feature_name} is an important burial site that provides valuable insights into ancient Egyptian funerary practices and beliefs about the afterlife."

        # Default descriptions by type
        default_descriptions = {
            "theater": f"The {feature_name} is an ancient performance venue that reflects the cultural life of the period.",
            "villa": f"The {feature_name} offers insight into the residential architecture and lifestyle of ancient times.",
            "baths": f"The {feature_name} showcase Roman bathing culture and engineering achievements.",
            "educational": f"The {feature_name} represent the intellectual and educational heritage of ancient Alexandria.",
            "temple": f"The {feature_name} is a sacred site dedicated to ancient Egyptian religious practices.",
            "tomb": f"The {feature_name} provides insights into ancient burial customs and beliefs.",
            "mosque": f"The {feature_name} is an important Islamic religious and architectural landmark.",
            "church": f"The {feature_name} represents the rich Coptic Christian heritage of Egypt.",
            "monument": f"The {feature_name} is a significant historical monument worthy of exploration.",
        }

        return default_descriptions.get(feature_type, f"The {feature_name} is a notable feature of {site_name} that merits individual exploration.")

    def _summarize_site_description(self, description: str, site_name: str) -> str:
        """Create a summary description when site itself is the sub-location."""
        # Take the first meaningful sentence or two
        sentences = re.split(r'(?<=[.!?])\s+', description)
        summary_sentences = []

        for sentence in sentences[:3]:
            if len(sentence) > 30:
                summary_sentences.append(sentence.strip())
                if len(" ".join(summary_sentences)) > 200:
                    break

        if summary_sentences:
            return " ".join(summary_sentences)

        return f"{site_name} is an archaeological site of historical and cultural significance."

    def _print_site_summary(self, site: Site):
        """Print a summary of the parsed site."""
        print(f"\n--- Site Summary ---")
        print(f"ID: {site.id}")
        print(f"Name: {site.name}")
        print(f"Arabic Name: {site.arabicName or 'N/A'}")
        print(f"City: {site.city or 'N/A'}")
        print(f"Coordinates: {site.latitude}, {site.longitude}" if site.latitude else "Coordinates: N/A")
        print(f"Era: {site.era or 'N/A'}")
        print(f"Tourism Type: {site.tourismType}")
        print(f"Place Type: {site.placeType}")
        print(f"Opening Hours: {site.openingHours or 'N/A'}")
        print(f"Duration: {site.estimatedDuration or 'N/A'}")
        print(f"Best Time: {site.bestTimeToVisit or 'N/A'}")
        print(f"Images: {len(site.imageNames)}")
        print(f"Tips: {len(site.tips)}")
        print(f"Arabic Phrases: {len(site.arabicPhrases)}")
        print(f"Sub-locations: {len(site.subLocations)}")
        for sub in site.subLocations:
            print(f"  - {sub.name}")

    def parse_sites(self, max_sites: Optional[int] = None) -> list[Site]:
        """Main method to parse all sites."""
        site_links = self.get_all_site_links(max_sites)

        for site_info in site_links:
            site = self.parse_site_page(site_info)
            if site:
                self.sites.append(site)

        return self.sites

    def export_to_json(self, output_path: str):
        """Export parsed sites to JSON in UnlockEgypt format."""
        output = {
            "sites": [],
            "subLocations": [],
            "cards": [],
            "tips": [],
            "arabicPhrases": []
        }

        for site in self.sites:
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

                # Card with full description
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

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print(f"EXPORT COMPLETE")
        print(f"{'='*60}")
        print(f"Output: {output_path}")
        print(f"Sites: {len(output['sites'])}")
        print(f"Sub-locations: {len(output['subLocations'])}")
        print(f"Cards: {len(output['cards'])}")
        print(f"Tips: {len(output['tips'])}")
        print(f"Arabic Phrases: {len(output['arabicPhrases'])}")


def main():
    print("="*60)
    print("UnlockEgypt Content Parser v2")
    print("="*60)
    print()

    parser = EgyMonumentsParser(headless=True)

    try:
        # Parse all sites
        print("Parsing all sites from egymonuments.gov.eg...")
        sites = parser.parse_sites(max_sites=None)

        # Export results
        output_path = "/Users/nareman/documents/projects/UnlockEgyptParser/parsed_sites.json"
        parser.export_to_json(output_path)

        # Print final summary
        print("\n" + "="*60)
        print("PARSING COMPLETE")
        print("="*60)
        for site in sites:
            print(f"\n{site.name}")
            print(f"  City: {site.city}")
            print(f"  Era: {site.era}")
            print(f"  Type: {site.tourismType} / {site.placeType}")
            print(f"  Duration: {site.estimatedDuration or 'N/A'}")
            print(f"  Sub-locations: {len(site.subLocations)}")
            for sub in site.subLocations:
                print(f"    - {sub.name}")

    finally:
        parser.close()


if __name__ == "__main__":
    main()
