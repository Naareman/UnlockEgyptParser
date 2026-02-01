"""
Tips Researcher - Gathers practical visitor tips from official sources.

Searches for:
- Official ticket prices from government/official sites
- Online booking availability
- Practical visitor tips based on site characteristics
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote as url_quote

import requests
from bs4 import BeautifulSoup

from utils import config

logger = logging.getLogger('UnlockEgyptParser')


@dataclass
class TicketInfo:
    """Ticket pricing information."""
    foreigners_adult: str = ""
    foreigners_student: str = ""
    egyptians_adult: str = ""
    egyptians_student: str = ""
    source_url: str = ""
    online_booking_url: str = ""


@dataclass
class SiteTips:
    """Practical tips for visiting a site."""
    tips: list[str] = field(default_factory=list)
    opening_hours: str = ""
    best_time_to_visit: str = ""
    estimated_duration: str = ""
    ticket_info: Optional[TicketInfo] = None
    official_website: str = ""
    accessibility_info: str = ""


class TipsResearcher:
    """
    Researches practical visitor tips from official sources.

    Prioritizes official government sources (.gov.eg) for accuracy.
    """

    # Official tourism-related domains
    OFFICIAL_DOMAINS = [
        "egymonuments.gov.eg",
        "tourism.gov.eg",
        "antiquities.gov.eg",
        "sca-egypt.org",
        "egypt.travel",
    ]

    def __init__(self):
        """Initialize the tips researcher."""
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent})

    def research(self, site_name: str, site_data: dict = None) -> SiteTips:
        """
        Research practical tips for a site.

        Args:
            site_name: Name of the site
            site_data: Optional existing site data (description, type, etc.)

        Returns:
            SiteTips with researched information
        """
        logger.info(f"Researching tips for: {site_name}")

        tips = SiteTips()
        site_data = site_data or {}

        # Generate tips based on site characteristics
        tips.tips = self._generate_contextual_tips(site_name, site_data)

        # Search for official ticket information
        ticket_info = self._search_ticket_info(site_name)
        if ticket_info:
            tips.ticket_info = ticket_info
            if ticket_info.foreigners_adult:
                tips.tips.append(f"Ticket price (foreigners): {ticket_info.foreigners_adult}")
            if ticket_info.online_booking_url:
                tips.tips.append(f"Online tickets available at: {ticket_info.online_booking_url}")

        # Search for official website
        official_url = self._find_official_website(site_name)
        if official_url:
            tips.official_website = official_url
            tips.tips.append(f"Official website: {official_url}")

        # Estimate duration based on site type
        tips.estimated_duration = self._estimate_duration(site_name, site_data)
        if tips.estimated_duration:
            tips.tips.append(f"Recommended visit duration: {tips.estimated_duration}")

        # Best time to visit
        tips.best_time_to_visit = self._get_best_time(site_data)
        if tips.best_time_to_visit:
            tips.tips.append(f"Best time to visit: {tips.best_time_to_visit}")

        return tips

    def _generate_contextual_tips(self, site_name: str, site_data: dict) -> list[str]:
        """
        Generate tips based on site characteristics.

        Args:
            site_name: Name of the site
            site_data: Site information dictionary

        Returns:
            List of contextual tips
        """
        tips = []
        site_type = site_data.get("placeType", "").lower()
        tourism_type = site_data.get("tourismType", "").lower()
        city = site_data.get("city", "").lower()

        # General tips for all sites
        tips.append("Bring water and wear comfortable walking shoes.")
        tips.append("Photography rules vary - check at the entrance.")

        # Type-specific tips
        if site_type == "pyramid" or "pyramid" in site_name.lower():
            tips.append("Visiting the interior requires a separate ticket and is not recommended for those with claustrophobia.")
            tips.append("Arrive early to avoid crowds and heat.")

        elif site_type == "tomb" or "tomb" in site_name.lower() or "valley" in site_name.lower():
            tips.append("Flash photography is prohibited to protect the ancient paintings.")
            tips.append("Only a limited number of tombs are open at any time - check which ones before visiting.")

        elif site_type == "temple":
            tips.append("Early morning or late afternoon provides the best lighting for photography.")
            tips.append("Consider hiring a licensed guide to understand the hieroglyphics and history.")

        elif site_type == "museum":
            tips.append("Audio guides are often available at the entrance.")
            tips.append("Large bags may need to be checked at the entrance.")

        elif site_type == "mosque":
            tips.append("Dress modestly - shoulders and knees should be covered.")
            tips.append("Remove shoes before entering prayer areas.")
            tips.append("Non-Muslims may have restricted access during prayer times.")

        elif site_type == "church" or site_type == "monastery":
            tips.append("Dress modestly when visiting religious sites.")
            tips.append("Photography may be restricted in certain areas.")

        # Location-specific tips
        if city in ["luxor", "aswan"]:
            tips.append("The sun can be extremely intense - bring sunscreen and a hat.")

        elif city == "alexandria":
            tips.append("The Mediterranean breeze can make it cooler than Cairo - bring a light jacket.")

        elif city in ["cairo", "giza"]:
            tips.append("Be prepared for persistent vendors and unofficial guides - politely decline if not interested.")

        # Tourism type specific
        if tourism_type == "pharaonic":
            tips.append("Download a hieroglyphics guide app to understand the ancient inscriptions.")

        elif tourism_type == "islamic":
            tips.append("Visit outside of Friday prayer times for a calmer experience.")

        return tips[:8]  # Limit to 8 tips

    def _search_ticket_info(self, site_name: str) -> Optional[TicketInfo]:
        """
        Search for official ticket information.

        Args:
            site_name: Name of the site

        Returns:
            TicketInfo if found, None otherwise
        """
        ticket_info = TicketInfo()

        # Try to find ticket info on egymonuments.gov.eg (primary source)
        search_query = f"{site_name} ticket price site:egymonuments.gov.eg"

        try:
            # Use a simple Google search scrape
            search_url = f"https://www.google.com/search?q={url_quote(search_query)}"
            response = self.session.get(search_url, timeout=config.http_timeout)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')

                # Look for price patterns in the search results
                text = soup.get_text()
                price_patterns = [
                    r'EGP\s*(\d+)',
                    r'(\d+)\s*EGP',
                    r'(\d+)\s*Egyptian pounds?',
                ]

                for pattern in price_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        # Found a price, but we don't know if it's adult/student/etc.
                        # For now, just note that pricing info exists
                        ticket_info.source_url = "egymonuments.gov.eg"
                        break

        except Exception as e:
            logger.debug(f"Ticket search failed: {e}")

        return ticket_info if ticket_info.source_url else None

    def _find_official_website(self, site_name: str) -> str:
        """
        Find the official website for a site.

        Args:
            site_name: Name of the site

        Returns:
            Official website URL or empty string
        """
        # Check known official sites
        name_lower = site_name.lower()

        # Egyptian Museum
        if "egyptian museum" in name_lower:
            return "https://egymonuments.gov.eg/en/museums/the-egyptian-museum"

        # Grand Egyptian Museum
        if "grand egyptian museum" in name_lower or "gem" in name_lower:
            return "https://grandegyptianmuseum.org"

        # Bibliotheca Alexandrina
        if "bibliotheca" in name_lower or "library of alexandria" in name_lower:
            return "https://www.bibalex.org"

        # For most sites, egymonuments.gov.eg is the official source
        return ""

    def _estimate_duration(self, site_name: str, site_data: dict) -> str:
        """
        Estimate visit duration based on site characteristics.

        Args:
            site_name: Name of the site
            site_data: Site information

        Returns:
            Estimated duration string
        """
        site_type = site_data.get("placeType", "").lower()
        name_lower = site_name.lower()

        # Large complexes
        if any(x in name_lower for x in ["karnak", "giza plateau", "valley of the kings", "saqqara"]):
            return "3-4 hours"

        # Medium sites
        if site_type == "temple":
            return "1-2 hours"
        elif site_type == "museum":
            return "2-3 hours"
        elif site_type == "pyramid":
            return "1-2 hours"
        elif site_type == "tomb":
            return "30 minutes - 1 hour"
        elif site_type in ["mosque", "church"]:
            return "30 minutes - 1 hour"
        elif site_type == "fortress":
            return "1-2 hours"

        return "1-2 hours"

    def _get_best_time(self, site_data: dict) -> str:
        """
        Determine the best time to visit based on site type and location.

        Args:
            site_data: Site information

        Returns:
            Best time recommendation
        """
        site_type = site_data.get("placeType", "").lower()
        city = site_data.get("city", "").lower()

        # Outdoor sites - avoid midday heat
        if site_type in ["pyramid", "temple", "tomb", "ruins"]:
            return "Early morning (8-10 AM) or late afternoon (3-5 PM) to avoid heat"

        # Museums - anytime
        if site_type == "museum":
            return "Weekday mornings for fewer crowds"

        # Mosques - avoid prayer times
        if site_type == "mosque":
            return "Mid-morning or mid-afternoon, outside prayer times"

        # Hot locations
        if city in ["luxor", "aswan"]:
            return "Early morning or late afternoon; winter months (Oct-Mar) are cooler"

        return "Early morning for fewer crowds"
