"""
Data models for UnlockEgypt Parser.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ArabicPhrase:
    """Arabic vocabulary phrase for a site."""
    siteId: str
    english: str
    arabic: str
    pronunciation: str


@dataclass
class Tip:
    """Visitor tip for a site."""
    siteId: str
    tip: str


@dataclass
class SubLocation:
    """Sub-location within a site."""
    id: str
    siteId: str
    name: str
    arabicName: str
    shortDescription: str
    imageName: str
    fullDescription: str


@dataclass
class Site:
    """Complete archaeological site data model."""
    id: str
    name: str
    arabicName: str
    era: str
    tourismType: str
    placeType: str
    governorate: str  # Changed from 'city' to 'governorate'
    latitude: Optional[float]
    longitude: Optional[float]
    shortDescription: str
    fullDescription: str
    imageNames: list[str] = field(default_factory=list)
    estimatedDuration: str = ""
    bestTimeToVisit: str = ""
    openingHours: str = ""
    officialWebsite: str = ""
    subLocations: list[SubLocation] = field(default_factory=list)
    tips: list[Tip] = field(default_factory=list)
    arabicPhrases: list[ArabicPhrase] = field(default_factory=list)
    uniqueFacts: list[str] = field(default_factory=list)
    keyFigures: list[str] = field(default_factory=list)
    architecturalFeatures: list[str] = field(default_factory=list)
    wikipediaUrl: str = ""
    rating: Optional[float] = None
    reviewCount: Optional[int] = None


__all__ = ['Site', 'SubLocation', 'Tip', 'ArabicPhrase']
