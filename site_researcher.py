"""
Site Researcher - Main orchestrator for multi-source research.

This module coordinates research from multiple sources for each site:
- egymonuments.gov.eg (primary source)
- Wikipedia (EN + AR)
- Google Maps (practical info)
- Official sources (tickets, hours)

The goal is to create comprehensive, well-researched data for each site,
treating this as a research exercise rather than simple web scraping.
"""

import json
import logging
import re
import time
from dataclasses import asdict
from typing import Optional
from urllib.parse import quote as url_quote

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)

from models import Site, SubLocation, Tip, ArabicPhrase
from researchers.arabic_terms import ArabicTermExtractor
from researchers.google_maps import GoogleMapsResearcher
from researchers.governorate import GovernorateService
from researchers.tips import TipsResearcher
from researchers.wikipedia import WikipediaResearcher
from utils import config

logger = logging.getLogger('UnlockEgyptParser')


class PageType:
    """Supported page types from egymonuments.gov.eg."""
    ARCHAEOLOGICAL_SITES = "archaeological-sites"
    MONUMENTS = "monuments"
    MUSEUMS = "museums"
    SUNKEN_MONUMENTS = "sunken-monuments"

    ALL_TYPES = [ARCHAEOLOGICAL_SITES, MONUMENTS, MUSEUMS, SUNKEN_MONUMENTS]

    @classmethod
    def get_display_name(cls, page_type: str) -> str:
        """Get human-readable name for a page type."""
        names = {
            cls.ARCHAEOLOGICAL_SITES: "Archaeological Sites",
            cls.MONUMENTS: "Monuments",
            cls.MUSEUMS: "Museums",
            cls.SUNKEN_MONUMENTS: "Sunken Monuments",
        }
        return names.get(page_type, page_type.replace("-", " ").title())


class SiteResearcher:
    """
    Main orchestrator for comprehensive site research.

    For each archaeological site, this class:
    1. Collects basic info from egymonuments.gov.eg
    2. Researches on Wikipedia (EN + AR)
    3. Gets practical info from Google Maps
    4. Extracts unique Arabic vocabulary
    5. Gathers tips from official sources
    6. Synthesizes into comprehensive site data
    """

    def __init__(self, headless: bool = None):
        """
        Initialize the site researcher.

        Args:
            headless: Whether to run browser in headless mode (None = use config)
        """
        self.headless = headless if headless is not None else config.headless
        self.base_url = config.base_url
        self.driver: Optional[webdriver.Chrome] = None
        self.sites: list[Site] = []
        self.site_counter = 0

        # Initialize research components
        self.governorate_service = GovernorateService
        self.wikipedia_researcher = WikipediaResearcher()
        self.google_maps_researcher: Optional[GoogleMapsResearcher] = None
        self.arabic_extractor = ArabicTermExtractor()
        self.tips_researcher = TipsResearcher()

    def __enter__(self):
        """Context manager entry."""
        self._init_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()
        return False

    def _init_driver(self):
        """Initialize the WebDriver."""
        if self.driver is None:
            options = Options()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            width, height = config.window_size
            options.add_argument(f"--window-size={width},{height}")
            options.add_argument("--disable-gpu")
            options.add_argument("--lang=en")
            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(config.implicit_wait)

            # Google Maps researcher creates its own driver
            self.google_maps_researcher = GoogleMapsResearcher(driver=None)

    def close(self):
        """Close all resources and clear caches."""
        if self.driver:
            try:
                self.driver.quit()
            except WebDriverException:
                pass
            self.driver = None

        if self.google_maps_researcher:
            self.google_maps_researcher.close()

        # Clear caches to free memory
        self.governorate_service.clear_cache()
        self.arabic_extractor.clear_cache()

    def get_site_links(
        self,
        page_type: str = PageType.ARCHAEOLOGICAL_SITES,
        max_sites: Optional[int] = None
    ) -> list[dict]:
        """
        Get all site links from a listing page.

        Args:
            page_type: Type of page to parse
            max_sites: Maximum number of sites to return

        Returns:
            List of site info dictionaries
        """
        listing_url = f"{self.base_url}/en/{page_type}/"
        logger.info(f"Loading {PageType.get_display_name(page_type)} page: {listing_url}")

        self.driver.get(listing_url)
        time.sleep(config.page_load_wait)

        # Load all sites using scroll + "Show More" button
        max_iterations = 20 if not max_sites else 5
        iteration = 0
        last_count = 0

        while iteration < max_iterations:
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(config.scroll_wait)

            items = self.driver.find_elements(By.CSS_SELECTOR, "a.listItem")
            current_count = len(items)

            if current_count > last_count:
                logger.debug(f"Scrolled: now {current_count} items loaded")

            # Look for "Show More" button
            try:
                show_more_btns = self.driver.find_elements(
                    By.CSS_SELECTOR, '[class*="showMore"], .showMoreBtn'
                )
                clicked = False
                for btn in show_more_btns:
                    try:
                        if btn.is_displayed() and "Show More" in btn.text:
                            self.driver.execute_script(
                                'arguments[0].scrollIntoView({block: "center"});', btn
                            )
                            time.sleep(0.5)
                            btn.click()
                            logger.debug("Clicked 'Show More' button")
                            time.sleep(config.show_more_wait)
                            clicked = True
                            break
                    except (StaleElementReferenceException, NoSuchElementException):
                        continue

                if not clicked and current_count == last_count:
                    logger.debug("No more items to load")
                    break
            except Exception:
                pass

            items = self.driver.find_elements(By.CSS_SELECTOR, "a.listItem")
            last_count = len(items)

            if max_sites and last_count >= max_sites:
                break

            iteration += 1

        # Extract site links
        site_links = []
        items = self.driver.find_elements(By.CSS_SELECTOR, "a.listItem")
        logger.info(f"Found {len(items)} items")

        for item in items:
            try:
                href = item.get_attribute("href")
                if not href or f"/{page_type}/" not in href:
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
                    "name": title,
                    "location": location,
                    "description": desc,
                    "image": img,
                    "page_type": page_type
                })

            except (StaleElementReferenceException, WebDriverException):
                continue

        logger.info(f"Total sites found: {len(site_links)}")
        return site_links[:max_sites] if max_sites else site_links

    def research_site(self, site_info: dict) -> Optional[Site]:
        """
        Conduct comprehensive research on a single site.

        Args:
            site_info: Basic site information from listing page

        Returns:
            Fully researched Site object or None on failure
        """
        url = site_info.get("url", "")
        name = site_info.get("name", "Unknown")

        logger.info(f"\n{'='*60}")
        logger.info(f"Researching: {name}")
        logger.info(f"{'='*60}")

        try:
            # Step 1: Get detailed info from primary source (egymonuments.gov.eg)
            logger.info("Step 1/5: Primary source (egymonuments.gov.eg)")
            primary_data = self._research_primary_source(url, site_info)

            if not primary_data:
                logger.warning(f"Could not get primary source data for {name}")
                return None

            self.site_counter += 1
            site_id = f"site_{self.site_counter:03d}"

            # Step 2: Research on Wikipedia
            logger.info("Step 2/5: Wikipedia research")
            wiki_data = self.wikipedia_researcher.research(name, primary_data.get("location", ""))

            # Step 3: Determine governorate
            logger.info("Step 3/5: Governorate detection")
            governorate = self.governorate_service.get_governorate(
                name,
                site_info.get("location", ""),
                primary_data.get("latitude"),
                primary_data.get("longitude")
            ) or site_info.get("location", "")

            # Step 4: Extract unique Arabic terms
            logger.info("Step 4/5: Arabic term extraction")
            description_for_arabic = primary_data.get("full_description", "")
            if wiki_data:
                description_for_arabic += " " + wiki_data.full_text[:2000]
            arabic_terms = self.arabic_extractor.extract_terms(name, description_for_arabic)

            # Step 5: Gather tips
            logger.info("Step 5/5: Tips research")
            site_data_for_tips = {
                "placeType": primary_data.get("place_type", ""),
                "tourismType": primary_data.get("tourism_type", ""),
                "city": governorate
            }
            tips_data = self.tips_researcher.research(name, site_data_for_tips)

            # Synthesize all research into Site object
            site = self._synthesize_site(
                site_id=site_id,
                name=name,
                primary_data=primary_data,
                wiki_data=wiki_data,
                governorate=governorate,
                arabic_terms=arabic_terms,
                tips_data=tips_data,
                site_info=site_info
            )

            self._log_site_summary(site)
            return site

        except Exception as e:
            logger.error(f"Error researching site {name}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def _research_primary_source(self, url: str, site_info: dict) -> Optional[dict]:
        """
        Get detailed information from the primary source (egymonuments.gov.eg).

        Args:
            url: Site page URL
            site_info: Basic site info

        Returns:
            Dictionary with extracted data
        """
        try:
            self.driver.get(url)
            time.sleep(3)

            data = {}

            # Get page title
            try:
                title_elem = self.driver.find_element(By.CSS_SELECTOR, "h1, .title h1, .pageTitle")
                data["name"] = title_elem.text.strip()
            except NoSuchElementException:
                data["name"] = site_info.get("name", "")

            # Get full description
            paragraphs = []
            try:
                p_elements = self.driver.find_elements(By.TAG_NAME, "p")
                for p in p_elements:
                    text = p.text.strip()
                    if text and len(text) > 40:
                        # Filter out navigation/footer text
                        if not any(x in text.lower() for x in ["copyright", "developed by", "all rights reserved", "read more", "click here"]):
                            paragraphs.append(text)
            except Exception:
                pass
            data["full_description"] = "\n\n".join(paragraphs)

            # Get Arabic name
            arabic_name = ""
            try:
                arabic_url = url.replace("/en/", "/ar/")
                current_url = self.driver.current_url
                self.driver.get(arabic_url)
                time.sleep(2)

                title_elem = self.driver.find_element(By.CSS_SELECTOR, "h1")
                if title_elem and any('\u0600' <= c <= '\u06FF' for c in title_elem.text):
                    arabic_name = title_elem.text.strip()
                    logger.info(f"Arabic name found: {arabic_name}")

                self.driver.get(current_url)
                time.sleep(2)
            except Exception:
                pass
            data["arabic_name"] = arabic_name

            # Determine era, tourism type, place type
            full_text = data["full_description"].lower()
            data["era"] = self._determine_era(full_text)
            data["tourism_type"] = self._determine_tourism_type(data["era"], full_text, data["name"])
            data["place_type"] = self._determine_place_type(data["name"], full_text)

            # Get coordinates via Nominatim
            try:
                query = f"{data['name']}, Egypt"
                nom_url = f"https://nominatim.openstreetmap.org/search?q={url_quote(query)}&format=json&limit=1"
                headers = {"User-Agent": config.nominatim_user_agent}
                response = requests.get(nom_url, headers=headers, timeout=config.http_timeout)
                results = response.json()
                if results:
                    data["latitude"] = float(results[0]["lat"])
                    data["longitude"] = float(results[0]["lon"])
                    logger.info(f"Coordinates found: {data['latitude']}, {data['longitude']}")
            except Exception:
                data["latitude"] = None
                data["longitude"] = None

            # Get images
            images = []
            if site_info.get("image"):
                images.append(site_info["image"])
            try:
                img_elems = self.driver.find_elements(By.CSS_SELECTOR, ".gallery img, .slider img, article img")
                for img in img_elems:
                    src = img.get_attribute("src")
                    if src and src not in images and "logo" not in src.lower():
                        images.append(src)
            except Exception:
                pass
            data["images"] = images[:5]

            data["location"] = site_info.get("location", "")

            return data

        except Exception as e:
            logger.error(f"Error getting primary source data: {e}")
            return None

    def _determine_era(self, description: str) -> str:
        """Determine historical era from description."""
        if "old kingdom" in description:
            return "Old Kingdom"
        if "middle kingdom" in description:
            return "Middle Kingdom"
        if "new kingdom" in description or "18th dynasty" in description or "19th dynasty" in description:
            return "New Kingdom"
        if "ptolemaic" in description:
            return "Ptolemaic"
        if "roman" in description:
            return "Roman"
        if "islamic" in description or "mamluk" in description or "fatimid" in description:
            return "Islamic"
        if "coptic" in description:
            return "Roman"
        return ""

    def _determine_tourism_type(self, era: str, description: str, name: str) -> str:
        """Determine tourism type classification."""
        pharaonic_eras = ["Old Kingdom", "Middle Kingdom", "New Kingdom", "Late Period"]
        if era in pharaonic_eras:
            return "Pharaonic"
        if era in ["Roman", "Ptolemaic"]:
            return "Greco-Roman"
        if era == "Islamic":
            return "Islamic"

        combined = (description + " " + name).lower()
        if any(w in combined for w in ["mosque", "islamic", "madrasa"]):
            return "Islamic"
        if any(w in combined for w in ["coptic", "church", "monastery"]):
            return "Coptic"
        if any(w in combined for w in ["roman", "greek", "ptolem"]):
            return "Greco-Roman"

        return "Pharaonic"

    def _determine_place_type(self, name: str, description: str) -> str:
        """Determine place type classification."""
        combined = (name + " " + description).lower()

        keywords = [
            ("pyramid", "Pyramid"),
            ("temple", "Temple"),
            ("tomb", "Tomb"),
            ("cemetery", "Tomb"),
            ("museum", "Museum"),
            ("mosque", "Mosque"),
            ("church", "Church"),
            ("monastery", "Church"),
            ("fortress", "Fortress"),
            ("citadel", "Fortress"),
            ("theater", "Monument"),
            ("amphitheatre", "Monument"),
        ]

        for keyword, place_type in keywords:
            if keyword in combined:
                return place_type

        return "Ruins"

    def _synthesize_site(
        self,
        site_id: str,
        name: str,
        primary_data: dict,
        wiki_data,
        governorate: str,
        arabic_terms: list,
        tips_data,
        site_info: dict
    ) -> Site:
        """
        Synthesize all research data into a Site object.
        """
        # Create tips
        tips = []
        if tips_data and tips_data.tips:
            for tip_text in tips_data.tips:
                tips.append(Tip(siteId=site_id, tip=tip_text))

        # Create Arabic phrases
        arabic_phrases = []
        for term in arabic_terms:
            arabic_phrases.append(ArabicPhrase(
                siteId=site_id,
                english=term.english,
                arabic=term.arabic,
                pronunciation=term.pronunciation
            ))

        # Create sub-locations (extract from description)
        sub_locations = self._extract_sub_locations(site_id, name, primary_data.get("full_description", ""))

        # Build the site
        site = Site(
            id=site_id,
            name=name,
            arabicName=primary_data.get("arabic_name", ""),
            era=wiki_data.historical_period if wiki_data and wiki_data.historical_period else primary_data.get("era", ""),
            tourismType=primary_data.get("tourism_type", ""),
            placeType=primary_data.get("place_type", ""),
            governorate=governorate,
            latitude=primary_data.get("latitude"),
            longitude=primary_data.get("longitude"),
            shortDescription=site_info.get("description", "")[:200],
            fullDescription=primary_data.get("full_description", ""),
            imageNames=primary_data.get("images", []),
            estimatedDuration=tips_data.estimated_duration if tips_data else "",
            bestTimeToVisit=tips_data.best_time_to_visit if tips_data else "",
            openingHours=tips_data.opening_hours if tips_data else "",
            officialWebsite=tips_data.official_website if tips_data else "",
            subLocations=sub_locations,
            tips=tips,
            arabicPhrases=arabic_phrases,
            uniqueFacts=wiki_data.unique_facts if wiki_data else [],
            keyFigures=wiki_data.key_figures if wiki_data else [],
            architecturalFeatures=wiki_data.architectural_features if wiki_data else [],
            wikipediaUrl=wiki_data.url if wiki_data else "",
            rating=None,
            reviewCount=None
        )

        return site

    def _extract_sub_locations(self, site_id: str, site_name: str, description: str) -> list[SubLocation]:
        """Extract meaningful sub-locations from description."""
        sub_locations = []
        found_names = set()

        # Patterns for sub-locations
        patterns = [
            (r'Temple\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', "Temple of {}"),
            (r'Tomb\s+of\s+([A-Z][a-z]+(?:\s+[IVX]+)?)', "Tomb of {}"),
            (r'(Great\s+(?:Temple|Pyramid|Sphinx))', "{}"),
            (r'(Hypostyle\s+Hall)', "{}"),
            (r'(Sacred\s+Lake)', "{}"),
        ]

        for pattern, template in patterns:
            matches = re.finditer(pattern, description, re.IGNORECASE)
            for match in matches:
                name = template.format(match.group(1).title())
                if name.lower() not in found_names and len(sub_locations) < 5:
                    found_names.add(name.lower())
                    sub_locations.append(SubLocation(
                        id=f"{site_id}_sub_{len(sub_locations)+1:02d}",
                        siteId=site_id,
                        name=name,
                        arabicName="",
                        shortDescription=f"Notable feature of {site_name}",
                        imageName="",
                        fullDescription=""
                    ))

        # If no sub-locations found, use site itself
        if not sub_locations:
            sub_locations.append(SubLocation(
                id=f"{site_id}_sub_01",
                siteId=site_id,
                name=site_name,
                arabicName="",
                shortDescription=description[:200] if description else f"Archaeological site: {site_name}",
                imageName="",
                fullDescription=description
            ))

        return sub_locations

    def _log_site_summary(self, site: Site):
        """Log a summary of the researched site."""
        logger.info(f"Research complete for: {site.name}")
        logger.info(f"  Governorate: {site.governorate}")
        logger.info(f"  Era: {site.era or 'N/A'}")
        logger.info(f"  Type: {site.tourismType} / {site.placeType}")
        logger.info(f"  Arabic phrases: {len(site.arabicPhrases)}")
        logger.info(f"  Tips: {len(site.tips)}")
        logger.info(f"  Unique facts: {len(site.uniqueFacts)}")
        if site.wikipediaUrl:
            logger.info(f"  Wikipedia: {site.wikipediaUrl}")

    def research_all(
        self,
        page_types: Optional[list[str]] = None,
        max_sites: Optional[int] = None
    ) -> list[Site]:
        """
        Research all sites from specified page types.

        Args:
            page_types: List of page types to research
            max_sites: Maximum sites per page type

        Returns:
            List of fully researched Site objects
        """
        if page_types is None:
            page_types = PageType.ALL_TYPES

        for page_type in page_types:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {PageType.get_display_name(page_type)}")
            logger.info(f"{'='*60}")

            site_links = self.get_site_links(page_type=page_type, max_sites=max_sites)

            for site_info in site_links:
                site = self.research_site(site_info)
                if site:
                    self.sites.append(site)

        return self.sites

    def export_to_json(self, output_path: str) -> dict:
        """
        Export researched sites to JSON.

        Args:
            output_path: Path to output file

        Returns:
            Exported data dictionary
        """
        output = {
            "sites": [],
            "subLocations": [],
            "cards": [],
            "tips": [],
            "arabicPhrases": []
        }

        for site in self.sites:
            site_dict = asdict(site)

            # Extract nested data
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
                "governorate": site_dict["governorate"],
                "latitude": site_dict["latitude"],
                "longitude": site_dict["longitude"],
                "shortDescription": site_dict["shortDescription"],
                "imageNames": site_dict["imageNames"],
                "estimatedDuration": site_dict["estimatedDuration"],
                "bestTimeToVisit": site_dict["bestTimeToVisit"],
                "openingHours": site_dict["openingHours"],
                "officialWebsite": site_dict["officialWebsite"],
                "uniqueFacts": site_dict["uniqueFacts"],
                "keyFigures": site_dict["keyFigures"],
                "architecturalFeatures": site_dict["architecturalFeatures"],
                "wikipediaUrl": site_dict["wikipediaUrl"],
            }
            output["sites"].append(site_export)

            # Sub-locations and cards
            for sub_loc in sub_locs:
                output["subLocations"].append({
                    "id": sub_loc["id"],
                    "siteId": sub_loc["siteId"],
                    "name": sub_loc["name"],
                    "arabicName": sub_loc["arabicName"],
                    "shortDescription": sub_loc["shortDescription"],
                    "imageName": sub_loc["imageName"],
                })
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
