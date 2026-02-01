"""
Pytest configuration and shared fixtures.
"""

import pytest


@pytest.fixture
def sample_site_data() -> dict:
    """Sample site data for testing."""
    return {
        "url": "https://egymonuments.gov.eg/en/monuments/test-site",
        "name": "Test Temple",
        "location": "Luxor",
        "description": "A test temple from the New Kingdom period.",
        "image": "https://example.com/image.jpg",
        "page_type": "monuments",
    }


@pytest.fixture
def sample_wikipedia_text() -> str:
    """Sample Wikipedia article text for testing extraction."""
    return """
    The Temple of Test was built during the reign of Ramesses II in the New Kingdom.
    It features a magnificent hypostyle hall with 134 columns.
    The temple was dedicated to Amun-Ra, the king of the gods.
    It is one of the largest temples in Egypt, covering over 200 acres.
    UNESCO designated it as a World Heritage Site in 1979.
    """
