"""
Wikipedia Researcher - Gathers historical context and unique facts from Wikipedia.

Researches each site on both English and Arabic Wikipedia to:
- Get comprehensive historical information
- Find unique facts not available on primary source
- Extract Arabic terminology and descriptions
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

import wikipediaapi

logger = logging.getLogger('UnlockEgyptParser')


@dataclass
class WikipediaData:
    """Data extracted from Wikipedia research."""
    title: str
    summary: str
    full_text: str
    url: str
    unique_facts: list[str]
    arabic_title: str
    arabic_summary: str
    arabic_url: str
    historical_period: str
    key_figures: list[str]  # Pharaohs, rulers, builders mentioned
    architectural_features: list[str]  # Unique features mentioned


class WikipediaResearcher:
    """
    Researches archaeological sites on Wikipedia (EN + AR).

    Extracts historical context, unique facts, and Arabic content
    that may not be available on the primary source.
    """

    def __init__(self):
        """Initialize Wikipedia API clients for English and Arabic."""
        self.wiki_en = wikipediaapi.Wikipedia(
            user_agent='UnlockEgyptParser/3.2 (educational research project)',
            language='en'
        )
        self.wiki_ar = wikipediaapi.Wikipedia(
            user_agent='UnlockEgyptParser/3.2 (educational research project)',
            language='ar'
        )

        # Patterns for extracting information
        self._pharaoh_pattern = re.compile(
            r'\b(Ramesses|Ramses|Amenhotep|Thutmose|Tutankhamun|Khufu|Khafre|'
            r'Menkaure|Hatshepsut|Akhenaten|Seti|Ptolemy|Cleopatra|Nefertiti|'
            r'Sneferu|Djoser|Cheops|Zoser)\s*[IVX]*\b',
            re.IGNORECASE
        )
        self._deity_pattern = re.compile(
            r'\b(Amun|Ra|Horus|Isis|Osiris|Hathor|Thoth|Ptah|Anubis|Sobek|'
            r'Sekhmet|Bastet|Mut|Aten|Min|Khnum|Khonsu|Nefertum|Neith)\b',
            re.IGNORECASE
        )
        self._architectural_pattern = re.compile(
            r'\b(hypostyle hall|pylon|sanctuary|obelisk|colossus|sphinx|'
            r'mastaba|serdab|pyramid|mortuary temple|valley temple|'
            r'causeway|sacred lake|colonnade|peristyle|naos|pronaos)\b',
            re.IGNORECASE
        )
        self._period_pattern = re.compile(
            r'\b(Old Kingdom|Middle Kingdom|New Kingdom|Late Period|'
            r'Ptolemaic|Roman|Byzantine|Coptic|Islamic|Mamluk|Ottoman|'
            r'Pre-Dynastic|Early Dynastic|First Intermediate|'
            r'Second Intermediate|Third Intermediate)\b',
            re.IGNORECASE
        )

    def research(self, site_name: str, location: str = "") -> Optional[WikipediaData]:
        """
        Research a site on Wikipedia.

        Args:
            site_name: Name of the archaeological site
            location: Location hint (city/governorate)

        Returns:
            WikipediaData with research findings or None if not found
        """
        logger.info(f"Researching on Wikipedia: {site_name}")

        # Try different search queries
        search_queries = self._generate_search_queries(site_name, location)

        page_en = None
        for query in search_queries:
            page_en = self.wiki_en.page(query)
            if page_en.exists():
                logger.debug(f"Found Wikipedia article (exact match): {page_en.title}")
                break

        # If exact match not found, use Wikipedia search API for fuzzy matching
        if not page_en or not page_en.exists():
            page_en = self._search_wikipedia(site_name, location)

        if not page_en or not page_en.exists():
            logger.warning(f"No Wikipedia article found for: {site_name}")
            return None

        # Get Arabic version if available
        page_ar = None
        arabic_title = ""
        arabic_summary = ""
        arabic_url = ""

        langlinks = page_en.langlinks
        if 'ar' in langlinks:
            page_ar = self.wiki_ar.page(langlinks['ar'].title)
            if page_ar.exists():
                arabic_title = page_ar.title
                arabic_summary = self._clean_text(page_ar.summary[:500])
                arabic_url = page_ar.fullurl
                logger.debug(f"Found Arabic Wikipedia: {arabic_title}")

        # Extract information from English article
        full_text = page_en.text
        summary = self._clean_text(page_en.summary)

        # Extract unique facts, key figures, and features
        unique_facts = self._extract_unique_facts(full_text, site_name)
        key_figures = self._extract_key_figures(full_text)
        architectural_features = self._extract_architectural_features(full_text)
        historical_period = self._extract_historical_period(full_text)

        return WikipediaData(
            title=page_en.title,
            summary=summary,
            full_text=full_text,
            url=page_en.fullurl,
            unique_facts=unique_facts,
            arabic_title=arabic_title,
            arabic_summary=arabic_summary,
            arabic_url=arabic_url,
            historical_period=historical_period,
            key_figures=key_figures,
            architectural_features=architectural_features
        )

    def _search_wikipedia(self, site_name: str, location: str = "") -> Optional[wikipediaapi.WikipediaPage]:
        """
        Use Wikipedia search API to find articles with fuzzy matching.

        This handles cases where the exact title doesn't match but a search
        would find the article (e.g., "Kom El-dikka" -> "Kom El Deka").

        Args:
            site_name: Name to search for
            location: Location context

        Returns:
            WikipediaPage if found, None otherwise
        """
        import requests

        search_queries = [
            f"{site_name} Egypt",
            site_name,
            f"{site_name} {location}" if location else None,
        ]

        for query in search_queries:
            if not query:
                continue

            try:
                # Use Wikipedia's search API
                search_url = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "srlimit": 5,  # Get top 5 results
                    "srprop": "snippet"
                }
                headers = {"User-Agent": "UnlockEgyptParser/3.2 (educational research project)"}

                response = requests.get(search_url, params=params, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()

                search_results = data.get("query", {}).get("search", [])

                if search_results:
                    # Check each result for relevance
                    for result in search_results:
                        title = result.get("title", "")
                        snippet = result.get("snippet", "").lower()

                        # Check if the result is relevant (contains Egypt-related terms)
                        egypt_keywords = ["egypt", "egyptian", "pharaoh", "ancient", "temple",
                                         "tomb", "pyramid", "alexandria", "cairo", "luxor",
                                         "aswan", "archaeological", "roman", "ptolemaic"]

                        is_relevant = any(kw in snippet for kw in egypt_keywords)

                        # Also check if the title is similar to what we're looking for
                        name_parts = site_name.lower().replace("-", " ").replace("_", " ").split()
                        title_lower = title.lower()
                        title_match = sum(1 for part in name_parts if part in title_lower)

                        if is_relevant or title_match >= len(name_parts) // 2:
                            page = self.wiki_en.page(title)
                            if page.exists():
                                logger.info(f"Found Wikipedia article (fuzzy search): '{title}' for query '{site_name}'")
                                return page

            except Exception as e:
                logger.debug(f"Wikipedia search failed for '{query}': {e}")

        return None

    def _generate_search_queries(self, site_name: str, location: str) -> list[str]:
        """Generate search queries to find the Wikipedia article."""
        queries = [site_name]

        # Add common spelling variations (handle transliteration differences)
        # Replace hyphens with spaces and vice versa
        if "-" in site_name:
            queries.append(site_name.replace("-", " "))
        if " " in site_name:
            queries.append(site_name.replace(" ", "-"))

        # Handle common Arabic transliteration variations
        variations = [
            ("el-", "el "), ("el ", "el-"),
            ("al-", "al "), ("al ", "al-"),
            ("dikka", "deka"), ("deka", "dikka"),
            ("shek", "sheikh"), ("sheikh", "shek"),
        ]
        for old, new in variations:
            if old in site_name.lower():
                queries.append(site_name.lower().replace(old, new).title())

        # Add variations
        if location:
            queries.append(f"{site_name} ({location})")
            queries.append(f"{site_name}, {location}")

        # Add common suffixes for Egyptian sites
        if "temple" not in site_name.lower():
            queries.append(f"{site_name} Temple")
            queries.append(f"Temple of {site_name}")

        if "pyramid" not in site_name.lower() and any(p in site_name.lower() for p in ["giza", "saqqara", "dahshur"]):
            queries.append(f"{site_name} Pyramid")

        # Clean up the name
        clean_name = site_name.replace("The ", "").replace("the ", "")
        if clean_name != site_name:
            queries.append(clean_name)

        return queries

    def _clean_text(self, text: str) -> str:
        """Clean Wikipedia text by removing references and extra whitespace."""
        # Remove reference markers like [1], [2], etc.
        text = re.sub(r'\[\d+\]', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _extract_unique_facts(self, text: str, site_name: str) -> list[str]:
        """
        Extract unique, interesting facts about the site.

        Looks for sentences containing superlatives, numbers, dates,
        and unique characteristics.
        """
        facts = []
        sentences = re.split(r'(?<=[.!?])\s+', text)

        # Patterns for interesting facts
        fact_indicators = [
            r'\b(oldest|largest|first|only|unique|rare|famous|renowned|'
            r'best-preserved|most|earliest|longest|highest|deepest)\b',
            r'\b(UNESCO|World Heritage|discovered in|built in|constructed in|'
            r'dating to|dates back|excavated|uncovered)\b',
            r'\b(\d{3,4}\s*(BC|BCE|AD|CE|B\.C\.|A\.D\.))\b',
            r'\b(meters?|feet|acres?|hectares?|square)\b.*\b\d+\b',
        ]

        for sentence in sentences:
            # Skip very short or very long sentences
            if len(sentence) < 30 or len(sentence) > 300:
                continue

            # Check for fact indicators
            for pattern in fact_indicators:
                if re.search(pattern, sentence, re.IGNORECASE):
                    clean_fact = self._clean_text(sentence)
                    if clean_fact not in facts and len(facts) < 5:
                        facts.append(clean_fact)
                    break

        return facts

    def _extract_key_figures(self, text: str) -> list[str]:
        """Extract pharaohs, rulers, and historical figures mentioned."""
        figures = set()

        # Find pharaohs and rulers
        pharaoh_matches = self._pharaoh_pattern.findall(text)
        figures.update(pharaoh_matches)

        # Find deities (for temples dedicated to them)
        deity_matches = self._deity_pattern.findall(text)
        figures.update(deity_matches)

        return list(figures)[:10]  # Limit to 10

    def _extract_architectural_features(self, text: str) -> list[str]:
        """Extract notable architectural features mentioned."""
        features = set()

        matches = self._architectural_pattern.findall(text)
        for match in matches:
            features.add(match.lower().title())

        return list(features)

    def _extract_historical_period(self, text: str) -> str:
        """Extract the primary historical period of the site."""
        # Look in the first part of the article (usually introduction)
        intro = text[:2000]

        matches = self._period_pattern.findall(intro)
        if matches:
            # Return the first (most prominent) period mentioned
            return matches[0]

        return ""

    def get_arabic_terms_from_article(self, page_title: str) -> dict[str, str]:
        """
        Get Arabic terms from the Arabic version of an article.

        Returns a dictionary mapping English terms to Arabic.
        """
        terms = {}

        page_en = self.wiki_en.page(page_title)
        if not page_en.exists():
            return terms

        langlinks = page_en.langlinks
        if 'ar' not in langlinks:
            return terms

        page_ar = self.wiki_ar.page(langlinks['ar'].title)
        if not page_ar.exists():
            return terms

        # The Arabic title itself is a term
        terms[page_en.title] = page_ar.title

        return terms
