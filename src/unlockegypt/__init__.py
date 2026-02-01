"""
UnlockEgypt Site Researcher.

A comprehensive research tool that gathers rich, multi-source information
about Egyptian archaeological sites.
"""

__version__ = "3.4.0"
__author__ = "UnlockEgypt Team"

from unlockegypt.models import ArabicPhrase, Site, SubLocation, Tip
from unlockegypt.site_researcher import PageType, SiteResearcher

__all__ = [
    "SiteResearcher",
    "PageType",
    "Site",
    "SubLocation",
    "Tip",
    "ArabicPhrase",
    "__version__",
]
