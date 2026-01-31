# UnlockEgypt Parser

A production-quality Python parser that scrapes archaeological site information from [egymonuments.gov.eg](https://egymonuments.gov.eg) for the UnlockEgypt iOS app.

## Version 3.0

This version includes a complete architectural refactoring with:

- **Modular Architecture**: Separated into focused components (WebScraper, ContentExtractor, GeocodingService, etc.)
- **Proper Logging**: Replaced print statements with Python's logging module
- **Security Features**: URL validation, content sanitization, input validation
- **Retry Logic**: Automatic retries with exponential backoff for network operations
- **Context Manager Support**: Proper resource cleanup with `with` statement
- **CLI Interface**: Command-line arguments for configuration
- **Type Hints**: Full type annotations throughout
- **Comprehensive Docstrings**: All public methods documented

## Architecture

```
EgyMonumentsParser (Facade)
    ├── WebScraper           - Browser operations with Selenium
    ├── ContentExtractor     - HTML content extraction & sanitization
    ├── GeocodingService     - Coordinate lookups via Nominatim API
    ├── ContentGenerator     - Tips, phrases, descriptions
    ├── SubLocationExtractor - Sub-location pattern matching
    ├── Classifier           - Era, tourism type, place type classification
    └── DataExporter         - JSON export with validation
```

## Features

- Scrapes site information including name, Arabic name, coordinates, era, and descriptions
- Extracts meaningful sub-locations (temples, tombs, monuments, etc.)
- Generates proper English descriptions for each sub-location
- Fetches Arabic names from the Arabic version of pages
- Gets GPS coordinates via OpenStreetMap Nominatim API
- Extracts opening hours and ticket prices
- Generates site-specific tips and Arabic vocabulary phrases

## Output Format

The parser generates a JSON file with:
- **sites** - Main site data
- **subLocations** - Sub-locations for each site
- **cards** - Card placeholders with full descriptions
- **tips** - Practical tips for visitors
- **arabicPhrases** - Site-specific Arabic vocabulary

## Requirements

```
selenium
requests
```

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install selenium requests
```

## Usage

```bash
# Parse all sites (default)
python parser.py

# Parse first N sites (for testing)
python parser.py -m 3

# Custom output path
python parser.py -o custom_output.json

# Verbose logging (debug mode)
python parser.py -v

# Show browser window
python parser.py --no-headless

# Strict validation (fail on invalid data)
python parser.py --strict

# Combine options
python parser.py -m 5 -v -o test.json
```

## CLI Options

| Option | Description |
|--------|-------------|
| `-o, --output` | Output JSON file path (default: parsed_sites.json) |
| `-m, --max-sites` | Maximum number of sites to parse (default: all) |
| `-v, --verbose` | Enable verbose (debug) logging |
| `--no-headless` | Show browser window |
| `--strict` | Enable strict validation |

## Programmatic Usage

```python
from parser import EgyMonumentsParser

# Using context manager (recommended)
with EgyMonumentsParser(headless=True) as parser:
    sites = parser.parse_sites(max_sites=10)
    parser.export_to_json("output.json")

# Manual cleanup
parser = EgyMonumentsParser()
try:
    sites = parser.parse_sites()
    parser.export_to_json("output.json")
finally:
    parser.close()
```

## Code Quality

This codebase follows best practices:

- **SOLID Principles**: Single responsibility, dependency injection
- **PEP 8**: Python style guide compliance
- **Type Safety**: Full type annotations
- **Error Handling**: Specific exceptions, no bare except clauses
- **Security**: URL validation, content sanitization
- **Testability**: Dependency injection for mocking
- **Documentation**: Comprehensive docstrings

## Related

- [UnlockEgypt](https://github.com/Naareman/UnlockEgypt) - The iOS app that uses this data
