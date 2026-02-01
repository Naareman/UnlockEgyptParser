"""Tests for data models."""

import pytest
from dataclasses import asdict

from models import Site, SubLocation, Tip, ArabicPhrase


class TestArabicPhrase:
    """Tests for ArabicPhrase model."""

    def test_creation(self) -> None:
        """Test basic ArabicPhrase creation."""
        phrase = ArabicPhrase(
            siteId="site_001",
            english="Temple",
            arabic="معبد",
            pronunciation="Ma'bad",
        )
        assert phrase.siteId == "site_001"
        assert phrase.english == "Temple"
        assert phrase.arabic == "معبد"
        assert phrase.pronunciation == "Ma'bad"

    def test_slots(self) -> None:
        """Test that slots are used for memory efficiency."""
        phrase = ArabicPhrase(
            siteId="site_001",
            english="Temple",
            arabic="معبد",
            pronunciation="Ma'bad",
        )
        # Slots means no __dict__
        assert not hasattr(phrase, "__dict__")


class TestTip:
    """Tests for Tip model."""

    def test_creation(self) -> None:
        """Test basic Tip creation."""
        tip = Tip(
            siteId="site_001",
            tip="Bring water and wear comfortable shoes.",
        )
        assert tip.siteId == "site_001"
        assert "water" in tip.tip


class TestSubLocation:
    """Tests for SubLocation model."""

    def test_creation(self) -> None:
        """Test basic SubLocation creation."""
        sub_loc = SubLocation(
            id="site_001_sub_01",
            siteId="site_001",
            name="Hypostyle Hall",
            arabicName="قاعة الأعمدة",
            shortDescription="The great hall of columns",
            imageName="hall.jpg",
            fullDescription="The Hypostyle Hall contains 134 massive columns...",
        )
        assert sub_loc.id == "site_001_sub_01"
        assert sub_loc.name == "Hypostyle Hall"


class TestSite:
    """Tests for Site model."""

    def test_creation_minimal(self) -> None:
        """Test Site creation with minimal required fields."""
        site = Site(
            id="site_001",
            name="Karnak Temple",
            arabicName="معبد الكرنك",
            era="New Kingdom",
            tourismType="Pharaonic",
            placeType="Temple",
            governorate="Luxor",
            latitude=25.7188,
            longitude=32.6573,
            shortDescription="The largest temple complex in Egypt",
            fullDescription="Karnak is the largest ancient religious site...",
        )
        assert site.id == "site_001"
        assert site.name == "Karnak Temple"
        assert site.governorate == "Luxor"

    def test_creation_full(self) -> None:
        """Test Site creation with all fields."""
        site = Site(
            id="site_001",
            name="Karnak Temple",
            arabicName="معبد الكرنك",
            era="New Kingdom",
            tourismType="Pharaonic",
            placeType="Temple",
            governorate="Luxor",
            latitude=25.7188,
            longitude=32.6573,
            shortDescription="The largest temple complex in Egypt",
            fullDescription="Full description here...",
            imageNames=["image1.jpg", "image2.jpg"],
            estimatedDuration="2-3 hours",
            bestTimeToVisit="Early morning",
            openingHours="6:00 AM - 5:30 PM",
            officialWebsite="https://example.com",
            uniqueFacts=["Built over 2000 years"],
            keyFigures=["Ramesses II", "Amenhotep III"],
            architecturalFeatures=["Hypostyle Hall", "Sacred Lake"],
            wikipediaUrl="https://en.wikipedia.org/wiki/Karnak",
        )
        assert len(site.imageNames) == 2
        assert len(site.uniqueFacts) == 1
        assert len(site.keyFigures) == 2

    def test_serialization(self) -> None:
        """Test Site serialization to dict."""
        site = Site(
            id="site_001",
            name="Test Site",
            arabicName="موقع اختبار",
            era="Modern",
            tourismType="Cultural",
            placeType="Museum",
            governorate="Cairo",
            latitude=30.0,
            longitude=31.0,
            shortDescription="Test",
            fullDescription="Test description",
        )
        data = asdict(site)
        assert data["id"] == "site_001"
        assert data["name"] == "Test Site"
        assert isinstance(data["imageNames"], list)
