# UnlockEgypt Site Researcher

A comprehensive research tool that gathers rich, multi-source information about Egyptian archaeological sites. Unlike simple web scrapers, it treats each site as a research subject, synthesizing data from multiple authoritative sources.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Version 3.3

**Research-Oriented Multi-Source Architecture**

| Feature | Description |
|---------|-------------|
| **Multi-Source Research** | Aggregates data from 4+ authoritative sources per site |
| **Wikipedia Integration** | EN + AR Wikipedia with fuzzy search for name variations |
| **27 Governorates** | Accurate mapping to all Egyptian governorates via Nominatim |
| **Dynamic Arabic Content** | Site-specific vocabulary with translations & pronunciations |
| **No API Keys Required** | All free, publicly accessible data sources |

## Site Coverage

| Page Type | Sites |
|-----------|-------|
| Archaeological Sites | 34 |
| Monuments | 123 |
| Museums | 24 |
| Sunken Monuments | 8 |
| **Total** | **189** |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Site Researcher (Orchestrator)              │
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────┬───────────┼───────────┬─────────┐
        ▼         ▼           ▼           ▼         ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │Primary  │ │Wikipedia│ │Governorate│ │Arabic  │ │ Tips   │
   │Source   │ │Research │ │Service  │ │Extractor│ │Research│
   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
        │           │           │           │           │
        ▼           ▼           ▼           ▼           ▼
   egymonuments  Wikipedia   Nominatim   Google     Official
   .gov.eg       EN + AR     Geocoding   Translate  Sources
```

## Installation

### Using uv (Recommended)

```bash
# Clone repository
git clone https://github.com/Naareman/UnlockEgyptParser.git
cd UnlockEgyptParser

# Install with uv
uv sync

# Run
uv run python research.py
```

### Using pip

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run
python research.py
```

## Usage

```bash
# Research all sites (189 total)
python research.py

# Research specific page type
python research.py -t monuments
python research.py -t museums

# Limit sites per type (for testing)
python research.py -t monuments -m 5

# Custom output path
python research.py -o my_research.json

# Verbose logging
python research.py -v

# Show browser window (non-headless)
python research.py --no-headless
```

## CLI Options

| Option | Description |
|--------|-------------|
| `-t, --type` | Page type(s) to research (repeatable) |
| `-o, --output` | Output JSON file path |
| `-m, --max-sites` | Maximum sites per page type |
| `-v, --verbose` | Enable debug logging |
| `--no-headless` | Show browser window |

## Output Format

```json
{
  "sites": [{
    "id": "site_001",
    "name": "Karnak Temple",
    "arabicName": "معبد الكرنك",
    "governorate": "Luxor",
    "era": "New Kingdom",
    "uniqueFacts": ["Largest ancient religious site..."],
    "keyFigures": ["Ramesses II", "Amenhotep III"],
    "wikipediaUrl": "https://en.wikipedia.org/wiki/Karnak"
  }],
  "subLocations": [...],
  "cards": [...],
  "tips": [...],
  "arabicPhrases": [...]
}
```

## Data Sources

| Source | Data Retrieved |
|--------|---------------|
| egymonuments.gov.eg | Primary info, images, Arabic names |
| Wikipedia (EN/AR) | Historical facts, key figures, features |
| Nominatim/OSM | Coordinates, governorate mapping |
| Google Translate | Arabic vocabulary translations |

## Project Structure

```
UnlockEgyptParser/
├── pyproject.toml          # Project config & dependencies
├── config.yaml             # Runtime configuration
├── research.py             # CLI entry point
├── site_researcher.py      # Main orchestrator
│
├── docs/                   # Documentation
│   ├── PRD.md             # Product requirements
│   ├── DESIGN.md          # System design
│   └── TECH_STACK.md      # Technology stack
│
├── models/                 # Data models
│   └── __init__.py        # Site, SubLocation, Tip, ArabicPhrase
│
├── researchers/            # Research components
│   ├── wikipedia.py       # Wikipedia API + fuzzy search
│   ├── governorate.py     # 27 governorate mapping
│   ├── arabic_terms.py    # Vocabulary extraction
│   ├── tips.py            # Visitor tips
│   └── google_maps.py     # Practical info
│
├── utils/                  # Utilities
│   └── config.py          # Configuration loader
│
└── tests/                  # Test suite
    ├── conftest.py
    └── test_models.py
```

## Development

### Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Code Quality

```bash
# Run linter
ruff check .

# Run formatter
ruff format .

# Run type checker
mypy .

# Run tests
pytest

# Run tests with coverage
pytest --cov=. --cov-report=html
```

### Pre-commit Hooks

The project uses pre-commit hooks for:
- Trailing whitespace removal
- YAML/JSON validation
- Ruff linting and formatting
- MyPy type checking
- Security checks (bandit)

## Configuration

All settings are in `config.yaml`:

```yaml
website:
  base_url: "https://egymonuments.gov.eg"

timing:
  page_load_wait: 5
  scroll_wait: 2
  geocoding_rate_limit: 1

browser:
  headless: true
  window_size: [1920, 1080]
```

## Documentation

- [Product Requirements (PRD)](docs/PRD.md)
- [System Design](docs/DESIGN.md)
- [Tech Stack](docs/TECH_STACK.md)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related

- [UnlockEgypt iOS App](https://github.com/Naareman/UnlockEgypt) - The mobile app that uses this data
