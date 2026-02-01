"""
Arabic Term Extractor - Extracts unique terms and translates to Arabic.

For each site, identifies unique, interesting terms from the description
and translates them to Arabic with pronunciation guides.
"""

import logging
import re
from dataclasses import dataclass

from deep_translator import GoogleTranslator

logger = logging.getLogger('UnlockEgyptParser')


@dataclass
class ArabicTerm:
    """A term with its Arabic translation and pronunciation."""
    english: str
    arabic: str
    pronunciation: str
    context: str = ""  # How it relates to this specific site


class ArabicTermExtractor:
    """
    Extracts unique terms from site content and translates to Arabic.

    The goal is to provide site-specific vocabulary, not generic phrases.
    Each site should have Arabic terms that are relevant to THAT specific site.
    """

    # Categories of terms to look for
    TERM_PATTERNS = {
        "pharaoh": re.compile(
            r'\b(Ramesses|Ramses|Amenhotep|Thutmose|Tutankhamun|Khufu|Khafre|'
            r'Menkaure|Hatshepsut|Akhenaten|Seti|Sneferu|Djoser|Nefertiti|'
            r'Cleopatra|Ptolemy)\s*(?:I{1,3}|IV|V|VI{1,3}|IX|X|XI{1,3})?\b',
            re.IGNORECASE
        ),
        "deity": re.compile(
            r'\b(Amun|Amun-Ra|Ra|Re|Horus|Isis|Osiris|Hathor|Thoth|Ptah|Anubis|'
            r'Sobek|Sekhmet|Bastet|Mut|Aten|Min|Khnum|Khonsu|Nefertum|Neith|'
            r'Montu|Set|Seth|Nephthys|Maat|Nut|Geb|Shu|Tefnut)\b',
            re.IGNORECASE
        ),
        "architecture": re.compile(
            r'\b(hypostyle hall|pylon|sanctuary|obelisk|colossus|sphinx|'
            r'mastaba|serdab|pyramid|mortuary temple|valley temple|'
            r'causeway|sacred lake|colonnade|peristyle|naos|pronaos|'
            r'sarcophagus|cartouche|hieroglyph|stele|relief|fresco|'
            r'mummy|burial chamber|false door|offering table)\b',
            re.IGNORECASE
        ),
        "title": re.compile(
            r'\b(pharaoh|king|queen|vizier|priest|priestess|scribe|'
            r'high priest|god\'s wife|royal wife|prince|princess)\b',
            re.IGNORECASE
        ),
        "place_feature": re.compile(
            r'\b(temple|tomb|chapel|shrine|necropolis|cemetery|'
            r'fortress|citadel|mosque|minaret|dome|mihrab|'
            r'church|monastery|basilica|catacomb)\b',
            re.IGNORECASE
        ),
    }

    # Pronunciation guide for common terms (pre-defined for accuracy)
    PRONUNCIATION_GUIDE = {
        # Pharaohs
        "ramesses": "Ram-sees",
        "ramses": "Ram-sees",
        "amenhotep": "Ah-men-HO-tep",
        "thutmose": "Thut-MO-seh",
        "tutankhamun": "Too-tan-KAH-moon",
        "khufu": "KOO-foo",
        "khafre": "KAF-ray",
        "menkaure": "Men-KOW-ray",
        "hatshepsut": "Hat-SHEP-soot",
        "akhenaten": "Ak-en-AH-ten",
        "cleopatra": "Klee-oh-PAT-ra",
        "nefertiti": "Nef-er-TEE-tee",

        # Deities
        "amun": "AH-moon",
        "amun-ra": "AH-moon RAH",
        "ra": "RAH",
        "horus": "HOR-us",
        "isis": "EYE-sis",
        "osiris": "Oh-SY-ris",
        "hathor": "HATH-or",
        "anubis": "Ah-NOO-bis",
        "thoth": "THOTH",
        "ptah": "Puh-TAH",

        # Architecture
        "hypostyle hall": "HY-po-style hall",
        "pylon": "PY-lon",
        "obelisk": "OB-eh-lisk",
        "sarcophagus": "Sar-KOF-ah-gus",
        "cartouche": "Kar-TOOSH",
        "hieroglyph": "HY-ro-glif",
        "mastaba": "Mas-TAH-ba",

        # Islamic
        "minaret": "Min-ah-RET",
        "mihrab": "Mih-RAHB",
        "mosque": "MOSK",
    }

    def __init__(self):
        """Initialize the translator."""
        self.translator = GoogleTranslator(source='en', target='ar')
        self._translation_cache: dict[str, str] = {}

    def extract_terms(
        self,
        site_name: str,
        description: str,
        max_terms: int = 8
    ) -> list[ArabicTerm]:
        """
        Extract unique terms from site content and translate to Arabic.

        Args:
            site_name: Name of the site
            description: Full description text
            max_terms: Maximum number of terms to return

        Returns:
            List of ArabicTerm objects with translations
        """
        logger.info(f"Extracting Arabic terms for: {site_name}")

        terms_found: dict[str, str] = {}  # term -> category
        combined_text = f"{site_name} {description}"

        # Extract terms by category
        for category, pattern in self.TERM_PATTERNS.items():
            matches = pattern.findall(combined_text)
            for match in matches:
                term = match.strip()
                if term and term.lower() not in [t.lower() for t in terms_found]:
                    terms_found[term] = category

        # Prioritize: pharaohs/deities first (more unique), then architecture
        priority_order = ["pharaoh", "deity", "architecture", "title", "place_feature"]
        sorted_terms = sorted(
            terms_found.items(),
            key=lambda x: priority_order.index(x[1]) if x[1] in priority_order else 99
        )

        # Create ArabicTerm objects with translations
        arabic_terms = []
        for term, category in sorted_terms[:max_terms]:
            arabic_translation = self._translate(term)
            pronunciation = self._get_pronunciation(term)

            arabic_terms.append(ArabicTerm(
                english=term.title() if len(term) > 3 else term,
                arabic=arabic_translation,
                pronunciation=pronunciation,
                context=category
            ))

        # Always add the site name itself
        if site_name and len(arabic_terms) < max_terms:
            site_arabic = self._translate(site_name)
            if site_arabic and site_arabic not in [t.arabic for t in arabic_terms]:
                arabic_terms.insert(0, ArabicTerm(
                    english=site_name,
                    arabic=site_arabic,
                    pronunciation=self._get_pronunciation(site_name),
                    context="site_name"
                ))

        logger.debug(f"Extracted {len(arabic_terms)} Arabic terms")
        return arabic_terms[:max_terms]

    def _translate(self, text: str) -> str:
        """
        Translate text to Arabic using Google Translate.

        Args:
            text: English text to translate

        Returns:
            Arabic translation
        """
        if not text:
            return ""

        # Check cache
        cache_key = text.lower().strip()
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]

        try:
            translation = self.translator.translate(text)
            self._translation_cache[cache_key] = translation
            return translation
        except Exception as e:
            logger.warning(f"Translation failed for '{text}': {e}")
            return ""

    def _get_pronunciation(self, term: str) -> str:
        """
        Get pronunciation guide for a term.

        Args:
            term: English term

        Returns:
            Pronunciation guide string
        """
        term_lower = term.lower().strip()

        # Check pre-defined pronunciations
        if term_lower in self.PRONUNCIATION_GUIDE:
            return self.PRONUNCIATION_GUIDE[term_lower]

        # For unknown terms, create a simple phonetic guide
        # This is a basic approximation
        return self._generate_pronunciation(term)

    def _generate_pronunciation(self, term: str) -> str:
        """
        Generate a basic pronunciation guide for unknown terms.

        Args:
            term: The term to pronounce

        Returns:
            Basic pronunciation guide
        """
        # Simple phonetic rules for common patterns
        pronunciation = term

        # Common substitutions
        replacements = [
            (r'ph', 'f'),
            (r'kh', 'kh'),
            (r'th', 'th'),
            (r'ou', 'oo'),
            (r'ei', 'ay'),
            (r'ae', 'ee'),
        ]

        for pattern, replacement in replacements:
            pronunciation = re.sub(pattern, replacement, pronunciation, flags=re.IGNORECASE)

        # Add hyphens between syllables (very basic)
        if len(pronunciation) > 6:
            # Split at vowel-consonant boundaries
            pronunciation = re.sub(r'([aeiou])([^aeiou])', r'\1-\2', pronunciation, flags=re.IGNORECASE)

        return pronunciation.title()

    def translate_custom_terms(self, terms: list[str]) -> list[ArabicTerm]:
        """
        Translate a custom list of terms.

        Args:
            terms: List of English terms to translate

        Returns:
            List of ArabicTerm objects
        """
        arabic_terms = []
        for term in terms:
            arabic_translation = self._translate(term)
            pronunciation = self._get_pronunciation(term)

            arabic_terms.append(ArabicTerm(
                english=term,
                arabic=arabic_translation,
                pronunciation=pronunciation
            ))

        return arabic_terms

    def clear_cache(self) -> None:
        """Clear the translation cache to free memory."""
        self._translation_cache.clear()
