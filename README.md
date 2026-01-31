# UnlockEgypt Parser

A Python parser that scrapes archaeological site information from [egymonuments.gov.eg](https://egymonuments.gov.eg) for the UnlockEgypt iOS app.

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

## Usage

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install selenium requests

# Run parser
python parser.py
```

By default, parses first 3 sites for testing. Modify `max_sites` parameter in `main()` to parse all sites.

## Related

- [UnlockEgypt](https://github.com/Naareman/UnlockEgypt) - The iOS app that uses this data
