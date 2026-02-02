"""Tests for site researcher module."""

from unittest.mock import MagicMock, patch

import pytest

from unlockegypt.models import ArabicPhrase, Site, SubLocation, Tip
from unlockegypt.site_researcher import PageType, SiteResearcher


class TestSiteResearcherHelpers:
    """Tests for SiteResearcher helper methods."""

    def test_determine_era_old_kingdom(self) -> None:
        """Test era determination for Old Kingdom."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_era("built during the old kingdom period")
        assert result == "Old Kingdom"

    def test_determine_era_middle_kingdom(self) -> None:
        """Test era determination for Middle Kingdom."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_era("dates to the middle kingdom")
        assert result == "Middle Kingdom"

    def test_determine_era_new_kingdom(self) -> None:
        """Test era determination for New Kingdom."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_era("constructed in the new kingdom")
        assert result == "New Kingdom"

    def test_determine_era_18th_dynasty(self) -> None:
        """Test era determination for 18th dynasty."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_era("built during the 18th dynasty")
        assert result == "New Kingdom"

    def test_determine_era_ptolemaic(self) -> None:
        """Test era determination for Ptolemaic."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_era("ptolemaic temple dedicated to")
        assert result == "Ptolemaic"

    def test_determine_era_roman(self) -> None:
        """Test era determination for Roman."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_era("roman period construction")
        assert result == "Roman"

    def test_determine_era_islamic(self) -> None:
        """Test era determination for Islamic."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_era("mamluk architecture")
        assert result == "Islamic"

    def test_determine_era_coptic(self) -> None:
        """Test era determination for Coptic (returns Roman)."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_era("coptic church built")
        assert result == "Roman"

    def test_determine_era_unknown(self) -> None:
        """Test era determination for unknown."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_era("no era keywords here")
        assert result == ""

    def test_determine_tourism_type_pharaonic_era(self) -> None:
        """Test tourism type for pharaonic era."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_tourism_type("Old Kingdom", "", "Pyramid")
        assert result == "Pharaonic"

    def test_determine_tourism_type_greco_roman(self) -> None:
        """Test tourism type for Greco-Roman."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_tourism_type("Roman", "", "Temple")
        assert result == "Greco-Roman"

    def test_determine_tourism_type_islamic(self) -> None:
        """Test tourism type for Islamic."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_tourism_type("Islamic", "", "Mosque")
        assert result == "Islamic"

    def test_determine_tourism_type_from_keywords(self) -> None:
        """Test tourism type from keywords."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_tourism_type("", "coptic church", "Church")
        assert result == "Coptic"

    def test_determine_place_type_pyramid(self) -> None:
        """Test place type for pyramid."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_place_type("Great Pyramid", "")
        assert result == "Pyramid"

    def test_determine_place_type_temple(self) -> None:
        """Test place type for temple."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_place_type("Karnak Temple", "")
        assert result == "Temple"

    def test_determine_place_type_tomb(self) -> None:
        """Test place type for tomb."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_place_type("Tomb of Ramesses", "")
        assert result == "Tomb"

    def test_determine_place_type_museum(self) -> None:
        """Test place type for museum."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_place_type("Egyptian Museum", "")
        assert result == "Museum"

    def test_determine_place_type_mosque(self) -> None:
        """Test place type for mosque."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_place_type("Al-Azhar Mosque", "")
        assert result == "Mosque"

    def test_determine_place_type_church(self) -> None:
        """Test place type for church."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_place_type("", "ancient monastery")
        assert result == "Church"

    def test_determine_place_type_fortress(self) -> None:
        """Test place type for fortress."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_place_type("Qaitbay Citadel", "")
        assert result == "Fortress"

    def test_determine_place_type_monument(self) -> None:
        """Test place type for monument."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_place_type("Roman Amphitheatre", "")
        assert result == "Monument"

    def test_determine_place_type_default(self) -> None:
        """Test place type default is Ruins."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_place_type("Unknown Site", "")
        assert result == "Ruins"

    def test_extract_sub_locations_temple(self) -> None:
        """Test sub-location extraction for temples."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        description = "The Temple of Amun is famous. The Temple of Khonsu is nearby."
        result = researcher._extract_sub_locations("site_001", "Karnak", description)
        assert len(result) > 0
        # Should find at least one Temple of X
        names = [sub.name for sub in result]
        assert any("Temple" in name for name in names)

    def test_extract_sub_locations_tomb(self) -> None:
        """Test sub-location extraction for tombs."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        description = "Contains the Tomb of Ramesses II and Tomb of Seti I."
        result = researcher._extract_sub_locations("site_001", "Valley of Kings", description)
        assert len(result) > 0
        names = [sub.name for sub in result]
        assert any("Tomb" in name for name in names)

    def test_extract_sub_locations_hypostyle(self) -> None:
        """Test sub-location extraction for Hypostyle Hall."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        description = "The famous Hypostyle Hall contains 134 columns."
        result = researcher._extract_sub_locations("site_001", "Karnak", description)
        names = [sub.name for sub in result]
        assert "Hypostyle Hall" in names

    def test_extract_sub_locations_empty(self) -> None:
        """Test sub-location extraction with no matches creates default."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        description = "No specific features mentioned here."
        result = researcher._extract_sub_locations("site_001", "Test Site", description)
        assert len(result) == 1
        assert result[0].name == "Test Site"

    def test_extract_sub_locations_max_five(self) -> None:
        """Test sub-location extraction is limited to 5."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        description = """
        Temple of Amun. Temple of Khonsu. Temple of Mut.
        Temple of Ptah. Temple of Ra. Temple of Horus.
        Temple of Isis. Temple of Osiris.
        """
        result = researcher._extract_sub_locations("site_001", "Complex", description)
        assert len(result) <= 5


class TestSiteResearcherInit:
    """Tests for SiteResearcher initialization."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        researcher = SiteResearcher()
        assert researcher.driver is None
        assert researcher.sites == []
        assert researcher.site_counter == 0

    def test_init_headless_true(self) -> None:
        """Test initialization with headless=True."""
        researcher = SiteResearcher(headless=True)
        assert researcher.headless is True

    def test_init_headless_false(self) -> None:
        """Test initialization with headless=False."""
        researcher = SiteResearcher(headless=False)
        assert researcher.headless is False

    def test_driver_property_raises_without_init(self) -> None:
        """Test that _driver property raises when not initialized."""
        researcher = SiteResearcher()
        with pytest.raises(RuntimeError, match="WebDriver not initialized"):
            _ = researcher._driver

    def test_close_without_driver(self) -> None:
        """Test close when driver is None."""
        researcher = SiteResearcher()
        researcher.close()  # Should not raise


class TestSiteResearcherSynthesize:
    """Tests for _synthesize_site method."""

    def test_synthesize_site_basic(self) -> None:
        """Test basic site synthesis."""
        researcher = SiteResearcher.__new__(SiteResearcher)

        primary_data = {
            "name": "Test Temple",
            "arabic_name": "معبد اختبار",
            "era": "New Kingdom",
            "tourism_type": "Pharaonic",
            "place_type": "Temple",
            "latitude": 25.5,
            "longitude": 32.5,
            "full_description": "A test temple description",
            "images": ["img1.jpg", "img2.jpg"],
        }

        wiki_data = MagicMock()
        wiki_data.historical_period = "New Kingdom"
        wiki_data.unique_facts = ["Oldest temple"]
        wiki_data.key_figures = ["Ramesses II"]
        wiki_data.architectural_features = ["Hypostyle Hall"]
        wiki_data.url = "https://en.wikipedia.org/wiki/Test"

        tips_data = MagicMock()
        tips_data.tips = ["Bring water", "Wear hat"]
        tips_data.estimated_duration = "2 hours"
        tips_data.best_time_to_visit = "Early morning"
        tips_data.opening_hours = "9 AM - 5 PM"
        tips_data.official_website = "https://example.com"

        arabic_terms = []

        site_info = {"description": "Short description"}

        site = researcher._synthesize_site(
            site_id="site_001",
            name="Test Temple",
            primary_data=primary_data,
            wiki_data=wiki_data,
            governorate="Luxor",
            arabic_terms=arabic_terms,
            tips_data=tips_data,
            site_info=site_info,
        )

        assert site.id == "site_001"
        assert site.name == "Test Temple"
        assert site.governorate == "Luxor"
        assert site.era == "New Kingdom"
        assert len(site.tips) == 2
        assert len(site.uniqueFacts) == 1

    def test_synthesize_site_no_wiki(self) -> None:
        """Test site synthesis without Wikipedia data."""
        researcher = SiteResearcher.__new__(SiteResearcher)

        primary_data = {
            "name": "Test Site",
            "arabic_name": "",
            "era": "Roman",
            "tourism_type": "Greco-Roman",
            "place_type": "Ruins",
            "latitude": None,
            "longitude": None,
            "full_description": "Test description",
            "images": [],
        }

        site = researcher._synthesize_site(
            site_id="site_002",
            name="Test Site",
            primary_data=primary_data,
            wiki_data=None,
            governorate="Alexandria",
            arabic_terms=[],
            tips_data=None,
            site_info={"description": ""},
        )

        assert site.id == "site_002"
        assert site.era == "Roman"
        assert site.uniqueFacts == []
        assert site.wikipediaUrl == ""


class TestSiteResearcherLogSummary:
    """Tests for _log_site_summary method."""

    def test_log_site_summary(self) -> None:
        """Test logging site summary."""
        researcher = SiteResearcher.__new__(SiteResearcher)

        site = Site(
            id="site_001",
            name="Test Temple",
            arabicName="معبد",
            era="New Kingdom",
            tourismType="Pharaonic",
            placeType="Temple",
            governorate="Luxor",
            latitude=25.5,
            longitude=32.5,
            shortDescription="Short",
            fullDescription="Full description",
            tips=[Tip(siteId="site_001", tip="Test tip")],
            arabicPhrases=[],
            uniqueFacts=["Fact 1"],
            wikipediaUrl="https://en.wikipedia.org/wiki/Test",
        )

        # Should not raise
        researcher._log_site_summary(site)

    def test_log_site_summary_no_wikipedia(self) -> None:
        """Test logging site summary without Wikipedia URL."""
        researcher = SiteResearcher.__new__(SiteResearcher)

        site = Site(
            id="site_001",
            name="Test Site",
            arabicName="",
            era="",
            tourismType="Pharaonic",
            placeType="Ruins",
            governorate="Cairo",
            latitude=None,
            longitude=None,
            shortDescription="",
            fullDescription="",
        )

        # Should not raise
        researcher._log_site_summary(site)


class TestSiteResearcherExport:
    """Tests for export_to_json method."""

    def test_export_to_json(self, tmp_path) -> None:
        """Test JSON export."""
        researcher = SiteResearcher()

        # Create a site
        site = Site(
            id="site_001",
            name="Test Temple",
            arabicName="معبد اختبار",
            era="New Kingdom",
            tourismType="Pharaonic",
            placeType="Temple",
            governorate="Luxor",
            latitude=25.5,
            longitude=32.5,
            shortDescription="Short description",
            fullDescription="Full description",
            imageNames=["img1.jpg"],
            subLocations=[
                SubLocation(
                    id="site_001_sub_01",
                    siteId="site_001",
                    name="Main Hall",
                    arabicName="",
                    shortDescription="Main hall description",
                    imageName="hall.jpg",
                    fullDescription="Full hall description",
                )
            ],
            tips=[Tip(siteId="site_001", tip="Bring water")],
            arabicPhrases=[
                ArabicPhrase(
                    siteId="site_001",
                    english="Temple",
                    arabic="معبد",
                    pronunciation="Ma'bad",
                )
            ],
            uniqueFacts=["Oldest temple"],
            keyFigures=["Ramesses II"],
            architecturalFeatures=["Hypostyle Hall"],
            wikipediaUrl="https://en.wikipedia.org/wiki/Test",
        )

        researcher.sites = [site]

        output_file = tmp_path / "test_output.json"
        result = researcher.export_to_json(str(output_file))

        assert output_file.exists()
        assert len(result["sites"]) == 1
        assert len(result["subLocations"]) == 1
        assert len(result["tips"]) == 1
        assert len(result["arabicPhrases"]) == 1
        assert len(result["cards"]) == 1

    def test_export_to_json_empty(self, tmp_path) -> None:
        """Test JSON export with no sites."""
        researcher = SiteResearcher()
        researcher.sites = []

        output_file = tmp_path / "empty_output.json"
        result = researcher.export_to_json(str(output_file))

        assert output_file.exists()
        assert len(result["sites"]) == 0


class TestSiteResearcherContextManager:
    """Tests for context manager functionality."""

    def test_context_manager_enter_exit(self) -> None:
        """Test context manager entry and exit."""
        with patch('unlockegypt.site_researcher.webdriver.Chrome') as MockChrome:
            mock_driver = MagicMock()
            MockChrome.return_value = mock_driver

            with SiteResearcher() as researcher:
                assert researcher.driver is not None

            # After exit, driver should be quit
            mock_driver.quit.assert_called()

    def test_context_manager_exit_returns_false(self) -> None:
        """Test that __exit__ returns False."""
        researcher = SiteResearcher()
        result = researcher.__exit__(None, None, None)
        assert result is False


class TestSiteResearcherDetermineType:
    """Tests for tourism and place type determination."""

    def test_determine_tourism_type_late_period(self) -> None:
        """Test tourism type for Late Period."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_tourism_type("Late Period", "", "Temple")
        assert result == "Pharaonic"

    def test_determine_tourism_type_from_name(self) -> None:
        """Test tourism type from site name."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_tourism_type("", "", "Al-Azhar Mosque")
        assert result == "Islamic"

    def test_determine_tourism_type_coptic_keyword(self) -> None:
        """Test tourism type with coptic keyword."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_tourism_type("", "coptic church ancient", "Site")
        assert result == "Coptic"

    def test_determine_tourism_type_roman_keyword(self) -> None:
        """Test tourism type with roman keyword."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_tourism_type("", "ancient roman ruins", "Site")
        assert result == "Greco-Roman"

    def test_determine_place_type_cemetery(self) -> None:
        """Test place type for cemetery."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_place_type("Valley Cemetery", "")
        assert result == "Tomb"

    def test_determine_place_type_amphitheatre(self) -> None:
        """Test place type for amphitheatre."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_place_type("", "roman amphitheatre")
        assert result == "Monument"

    def test_determine_era_19th_dynasty(self) -> None:
        """Test era determination for 19th dynasty."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_era("built during the 19th dynasty")
        assert result == "New Kingdom"

    def test_determine_era_fatimid(self) -> None:
        """Test era determination for Fatimid."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        result = researcher._determine_era("fatimid architecture")
        assert result == "Islamic"


class TestSiteResearcherExtractSubLocations:
    """Tests for sub-location extraction edge cases."""

    def test_extract_great_pyramid(self) -> None:
        """Test extraction of Great Pyramid."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        description = "The Great Pyramid of Giza is the oldest."
        result = researcher._extract_sub_locations("site_001", "Giza", description)
        names = [sub.name for sub in result]
        assert any("Great Pyramid" in name for name in names)

    def test_extract_great_sphinx(self) -> None:
        """Test extraction of Great Sphinx."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        description = "The Great Sphinx guards the pyramids."
        result = researcher._extract_sub_locations("site_001", "Giza", description)
        names = [sub.name for sub in result]
        assert any("Great Sphinx" in name for name in names)

    def test_extract_sacred_lake(self) -> None:
        """Test extraction of Sacred Lake."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        description = "The temple includes a Sacred Lake for rituals."
        result = researcher._extract_sub_locations("site_001", "Karnak", description)
        names = [sub.name for sub in result]
        assert "Sacred Lake" in names

    def test_extract_sub_locations_unique_names(self) -> None:
        """Test that duplicate sub-location names are filtered."""
        researcher = SiteResearcher.__new__(SiteResearcher)
        # Use punctuation after names to avoid extra word captures in regex
        description = "Temple of Amun. More text about Temple of Amun! Yet another Temple of Amun."
        result = researcher._extract_sub_locations("site_001", "Karnak", description)
        names = [sub.name for sub in result]
        # Should only have one Temple of Amun (duplicates filtered)
        assert "Temple of Amun" in names
        # Count exact matches
        exact_count = sum(1 for n in names if n == "Temple of Amun")
        assert exact_count == 1


class TestSiteResearcherSynthesizeEdgeCases:
    """Edge case tests for _synthesize_site method."""

    def test_synthesize_with_all_none_wiki(self) -> None:
        """Test synthesis when wiki_data is None."""
        researcher = SiteResearcher.__new__(SiteResearcher)

        primary_data = {
            "name": "Test Site",
            "arabic_name": "",
            "era": "Roman",
            "tourism_type": "Greco-Roman",
            "place_type": "Ruins",
            "latitude": 30.0,
            "longitude": 31.0,
            "full_description": "Test description",
            "images": [],
        }

        site = researcher._synthesize_site(
            site_id="site_001",
            name="Test Site",
            primary_data=primary_data,
            wiki_data=None,
            governorate="Cairo",
            arabic_terms=[],
            tips_data=None,
            site_info={"description": "Short desc"},
        )

        assert site.era == "Roman"
        assert site.uniqueFacts == []
        assert site.keyFigures == []
        assert site.wikipediaUrl == ""

    def test_synthesize_with_empty_tips(self) -> None:
        """Test synthesis with empty tips."""
        researcher = SiteResearcher.__new__(SiteResearcher)

        primary_data = {
            "name": "Test Site",
            "arabic_name": "موقع",
            "era": "New Kingdom",
            "tourism_type": "Pharaonic",
            "place_type": "Temple",
            "latitude": 25.0,
            "longitude": 32.0,
            "full_description": "Temple description",
            "images": ["img.jpg"],
        }

        mock_tips = MagicMock()
        mock_tips.tips = []  # Empty tips
        mock_tips.estimated_duration = ""
        mock_tips.best_time_to_visit = ""
        mock_tips.opening_hours = ""
        mock_tips.official_website = ""

        site = researcher._synthesize_site(
            site_id="site_002",
            name="Test Site",
            primary_data=primary_data,
            wiki_data=None,
            governorate="Luxor",
            arabic_terms=[],
            tips_data=mock_tips,
            site_info={"description": ""},
        )

        assert len(site.tips) == 0

    def test_synthesize_with_arabic_terms(self) -> None:
        """Test synthesis with Arabic terms."""
        from unlockegypt.researchers.arabic_terms import ArabicTerm
        researcher = SiteResearcher.__new__(SiteResearcher)

        primary_data = {
            "name": "Temple",
            "arabic_name": "معبد",
            "era": "New Kingdom",
            "tourism_type": "Pharaonic",
            "place_type": "Temple",
            "latitude": None,
            "longitude": None,
            "full_description": "",
            "images": [],
        }

        arabic_terms = [
            ArabicTerm(english="Temple", arabic="معبد", pronunciation="Ma'bad"),
            ArabicTerm(english="Pharaoh", arabic="فرعون", pronunciation="Fir'awn"),
        ]

        site = researcher._synthesize_site(
            site_id="site_003",
            name="Temple",
            primary_data=primary_data,
            wiki_data=None,
            governorate="Luxor",
            arabic_terms=arabic_terms,
            tips_data=None,
            site_info={"description": ""},
        )

        assert len(site.arabicPhrases) == 2
        assert site.arabicPhrases[0].english == "Temple"
        assert site.arabicPhrases[1].english == "Pharaoh"


class TestPageTypeClass:
    """Tests for PageType class."""

    def test_page_type_constants(self) -> None:
        """Test PageType constants are correct."""
        assert PageType.ARCHAEOLOGICAL_SITES == "archaeological-sites"
        assert PageType.MONUMENTS == "monuments"
        assert PageType.MUSEUMS == "museums"
        assert PageType.SUNKEN_MONUMENTS == "sunken-monuments"

    def test_all_types_length(self) -> None:
        """Test ALL_TYPES contains 4 types."""
        assert len(PageType.ALL_TYPES) == 4

    def test_get_display_name_default(self) -> None:
        """Test get_display_name with unknown type uses title case."""
        result = PageType.get_display_name("some-unknown-type")
        assert result == "Some Unknown Type"


class TestSiteResearcherClose:
    """Tests for close method."""

    def test_close_clears_caches(self) -> None:
        """Test that close clears all caches."""
        researcher = SiteResearcher()

        with (
            patch.object(researcher.governorate_service, 'clear_cache') as mock_gov,
            patch.object(researcher.arabic_extractor, 'clear_cache') as mock_arabic,
        ):
            researcher.close()
            mock_gov.assert_called_once()
            mock_arabic.assert_called_once()

    def test_close_handles_google_maps_researcher(self) -> None:
        """Test that close handles google_maps_researcher."""
        researcher = SiteResearcher()
        mock_gm = MagicMock()
        researcher.google_maps_researcher = mock_gm

        researcher.close()
        mock_gm.close.assert_called_once()
