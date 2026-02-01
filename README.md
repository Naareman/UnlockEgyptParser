# UnlockEgypt Parser

A production-quality Python parser that scrapes site information from [egymonuments.gov.eg](https://egymonuments.gov.eg) for the UnlockEgypt iOS app.

## Version 3.2

**New in this version:**
- **External Configuration**: All settings moved to `config.yaml` - no more hardcoded values
- **Improved Pagination**: Proper handling of infinite scroll + "Show More" button pattern
- **Full Site Coverage**: Now loads all sites from each page type (189 total across all categories)

### Site Counts by Category
| Page Type | Sites |
|-----------|-------|
| Archaeological Sites | 34 |
| Monuments | 123 |
| Museums | 24 |
| Sunken Monuments | 8 |
| **Total** | **189** |

## Architecture

```
ConfigLoader              - Loads external YAML configuration
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

## Configuration

All settings are stored in `config.yaml`. Key sections:

```yaml
# Timing settings
timing:
  implicit_wait_timeout: 10
  page_load_wait: 5
  scroll_wait: 2

# Content extraction
content:
  min_paragraph_length: 40
  max_sub_locations: 5

# City name mappings
city_mapping:
  alexandria: "Alexandria"
  cairo: "Cairo"
  # ... add custom mappings

# Arabic phrases by place type
arabic_phrases:
  Temple:
    - english: "Temple"
      arabic: "معبد"
      pronunciation: "Ma'bad"
```

**To customize behavior**, edit `config.yaml` instead of modifying source code.

## Requirements

```
selenium>=4.0.0
requests>=2.25.0
PyYAML>=6.0
```

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Parse all page types (default) - 189 sites
python parser.py

# Parse specific page type
python parser.py -t monuments
python parser.py -t museums
python parser.py -t archaeological-sites
python parser.py -t sunken-monuments

# Parse multiple page types
python parser.py -t monuments -t museums

# Parse first N sites per page type
python parser.py -t monuments -m 3

# Custom output path
python parser.py -o custom_output.json

# Verbose logging (debug mode)
python parser.py -v

# Combine options
python parser.py -t monuments -t museums -m 5 -v -o test.json
```

## CLI Options

| Option | Description |
|--------|-------------|
| `-t, --type` | Page type(s) to parse (can be specified multiple times) |
| `-o, --output` | Output JSON file path (default: parsed_sites.json) |
| `-m, --max-sites` | Maximum number of sites per page type (default: all) |
| `-v, --verbose` | Enable verbose (debug) logging |
| `--no-headless` | Show browser window |
| `--strict` | Enable strict validation |

## Page Types

| Type | Description | Sites |
|------|-------------|-------|
| `archaeological-sites` | Ancient archaeological sites | 34 |
| `monuments` | Historical monuments (temples, etc.) | 123 |
| `museums` | Museums across Egypt | 24 |
| `sunken-monuments` | Underwater archaeological sites | 8 |

## Output Format

The parser generates a JSON file with:
- **sites** - Main site data
- **subLocations** - Sub-locations for each site
- **cards** - Card placeholders with full descriptions
- **tips** - Practical tips for visitors
- **arabicPhrases** - Site-specific Arabic vocabulary

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

- **External Configuration**: All settings in `config.yaml`
- **SOLID Principles**: Single responsibility, dependency injection
- **PEP 8**: Python style guide compliance
- **Type Safety**: Full type annotations
- **Error Handling**: Specific exceptions, no bare except clauses
- **Security**: URL validation, content sanitization
- **Testability**: Dependency injection for mocking
- **Documentation**: Comprehensive docstrings

## Project Structure

```
UnlockEgyptParser/
├── parser.py           # Main parser code
├── config.yaml         # External configuration
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── parsed_sites.json  # Output (generated)
└── venv/              # Virtual environment
```

## Related

- [UnlockEgypt](https://github.com/Naareman/UnlockEgypt) - The iOS app that uses this data
