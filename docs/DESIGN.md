# System Design Document
## UnlockEgypt Site Researcher

**Version:** 3.4
**Last Updated:** 2026-02-01

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Entry Point                           │
│                   (unlockegypt.cli / cli.py)                     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Site Researcher                              │
│                  (Orchestrator / Facade)                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Research Pipeline                      │    │
│  │  Step 1 → Step 2 → Step 3 → Step 4 → Step 5 → Synthesize │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Researchers  │   │    Models     │   │    Utils      │
│  (5 modules)  │   │  (dataclass)  │   │   (config)    │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 1.2 Design Patterns Used

| Pattern | Implementation | Purpose |
|---------|---------------|---------|
| **Facade** | `SiteResearcher` | Simplifies complex multi-source research |
| **Singleton** | `Config` class | Single source of configuration |
| **Strategy** | Individual researchers | Swappable research components |
| **Factory** | `PageType` | Creates appropriate URL paths |
| **Context Manager** | `SiteResearcher` | Resource cleanup (WebDriver) |

---

## 2. Component Design

### 2.1 Research Pipeline

```
For each site:
┌──────────────────────────────────────────────────────────────┐
│ Step 1: Primary Source (egymonuments.gov.eg)                 │
│ - Navigate to site page                                       │
│ - Extract: name, description, images, Arabic name            │
│ - Determine: era, tourism type, place type                   │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 2: Wikipedia Research (EN + AR)                         │
│ - Fuzzy search for matching article                          │
│ - Extract: unique facts, key figures, architectural features │
│ - Get Arabic Wikipedia via langlinks                         │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 3: Governorate Detection                                │
│ - Check known places cache                                   │
│ - Geocode via Nominatim if needed                           │
│ - Map to official 27 governorate names                      │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 4: Arabic Term Extraction                               │
│ - Identify unique terms (pharaohs, deities, architecture)   │
│ - Translate via Google Translate (free)                     │
│ - Generate pronunciation guides                              │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 5: Tips Research                                        │
│ - Generate site-type-specific tips                          │
│ - Search for official ticket information                    │
│ - Estimate visit duration                                    │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ Synthesis: Combine all data into Site object                 │
│ - Merge data from all sources                               │
│ - Create sub-locations, tips, Arabic phrases                │
│ - Add to sites collection                                    │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 Module Responsibilities

```
src/unlockegypt/
├── cli.py                   # CLI entry point, argument parsing
├── site_researcher.py       # Main orchestrator
│   ├── get_site_links()     # Scrape listing pages
│   ├── research_site()      # 5-step pipeline per site
│   ├── export_to_json()     # Output generation
│   └── close()              # Resource cleanup
│
├── researchers/
│   ├── wikipedia.py         # Wikipedia API + fuzzy search
│   │   ├── research()       # Main entry point
│   │   ├── _search_wikipedia()  # Fuzzy matching
│   │   └── _extract_*()     # Data extraction methods
│   │
│   ├── governorate.py       # Governorate detection
│   │   ├── get_governorate()    # Main entry point
│   │   ├── _geocode_to_governorate()
│   │   └── GOVERNORATES     # All 27 official names
│   │
│   ├── arabic_terms.py      # Arabic vocabulary
│   │   ├── extract_terms()  # Pattern matching + translation
│   │   └── TERM_PATTERNS    # Pharaohs, deities, architecture
│   │
│   ├── tips.py              # Visitor tips
│   │   ├── research()       # Main entry point
│   │   └── _generate_contextual_tips()
│   │
│   └── google_maps.py       # Practical info (future)
│
├── models/
│   └── __init__.py          # Site, SubLocation, Tip, ArabicPhrase
│
└── utils/
    └── config.py            # Singleton configuration loader
```

---

## 3. Data Models

### 3.1 Core Models

```python
@dataclass
class Site:
    # Identity
    id: str                    # "site_001"
    name: str                  # "Karnak Temple"
    arabicName: str            # "معبد الكرنك"

    # Classification
    era: str                   # "New Kingdom"
    tourismType: str           # "Pharaonic"
    placeType: str             # "Temple"
    governorate: str           # "Luxor"

    # Location
    latitude: float | None
    longitude: float | None

    # Content
    shortDescription: str
    fullDescription: str
    imageNames: list[str]

    # Practical Info
    estimatedDuration: str     # "2-3 hours"
    bestTimeToVisit: str       # "Early morning"
    openingHours: str
    officialWebsite: str

    # Rich Data
    subLocations: list[SubLocation]
    tips: list[Tip]
    arabicPhrases: list[ArabicPhrase]
    uniqueFacts: list[str]
    keyFigures: list[str]
    architecturalFeatures: list[str]
    wikipediaUrl: str
```

### 3.2 Output JSON Structure

```json
{
  "sites": [...],
  "subLocations": [...],
  "cards": [...],
  "tips": [...],
  "arabicPhrases": [...]
}
```

---

## 4. Configuration Architecture

### 4.1 Configuration Hierarchy

```
config.yaml (external)
    │
    ▼
utils/config.py (loader)
    │
    ▼
config singleton (runtime)
    │
    ├── site_researcher.py
    ├── researchers/governorate.py
    ├── researchers/wikipedia.py
    ├── researchers/tips.py
    └── researchers/google_maps.py
```

### 4.2 Configurable Values

| Category | Values |
|----------|--------|
| **Website** | base_url, page_types |
| **Browser** | headless, window_size, user_agent |
| **Timing** | implicit_wait, page_load_wait, scroll_wait, rate_limits |
| **Content** | min_paragraph_length, max_sub_locations |
| **Geography** | egypt_lat/lon bounds for validation |

---

## 5. Caching Strategy

### 5.1 Cache Locations

| Component | Cache Type | Purpose |
|-----------|-----------|---------|
| `GovernorateService` | Class-level dict | Avoid repeated geocoding |
| `ArabicTermExtractor` | Instance dict | Avoid repeated translations |
| `TipsResearcher` | Session object | HTTP connection reuse |

### 5.2 Cache Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│ SiteResearcher.__enter__()                                  │
│   └── Initialize researchers with empty caches             │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ research_all()                                               │
│   └── Caches grow as sites are processed                    │
│       └── Cache hits reduce API calls                       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ SiteResearcher.__exit__() → close()                         │
│   ├── governorate_service.clear_cache()                     │
│   ├── arabic_extractor.clear_cache()                        │
│   └── Free memory for garbage collection                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Error Handling Strategy

### 6.1 Error Hierarchy

```
Site Research Errors
├── Network Errors
│   ├── Connection timeout → Retry with backoff
│   └── HTTP errors → Log and continue
├── Parsing Errors
│   ├── Element not found → Use default/empty
│   └── Invalid data → Log warning, skip field
└── External Service Errors
    ├── Wikipedia not found → Fuzzy search fallback
    ├── Geocoding failed → Use location hint
    └── Translation failed → Return empty
```

### 6.2 Error Recovery

| Error Type | Recovery Strategy |
|------------|------------------|
| Site page load failure | Skip site, log error |
| Wikipedia article not found | Try fuzzy search, then skip |
| Geocoding failure | Use location hint from page |
| Translation failure | Skip term, continue |
| Stale element | Re-find element, retry once |

---

## 7. Scalability Considerations

### 7.1 Current Limitations

| Aspect | Limit | Reason |
|--------|-------|--------|
| Concurrent requests | 1 | Rate limiting compliance |
| Sites per run | ~189 | Website catalog size |
| Memory | ~500MB | WebDriver + caches |

### 7.2 Future Scaling Options

- **Parallel processing**: Multiple WebDriver instances per page type
- **Distributed caching**: Redis for shared geocoding cache
- **Incremental updates**: Track last-modified dates
- **API mode**: Flask/FastAPI endpoint for on-demand research

---

## 8. Security Considerations

| Risk | Mitigation |
|------|------------|
| Credential exposure | No API keys used (free services only) |
| Rate limit violations | Configurable delays, user-agent identification |
| Data integrity | Validation of coordinates, governorate names |
| Memory exhaustion | Cache clearing, slots for dataclasses |

---

## 9. Testing Strategy

### 9.1 Test Pyramid

```
         ┌─────────────────┐
         │   E2E Tests     │  ← Full pipeline with real sources
         │   (few, slow)   │
         └────────┬────────┘
                  │
         ┌────────┴────────┐
         │ Integration     │  ← Researcher + mocked HTTP
         │ Tests (some)    │
         └────────┬────────┘
                  │
         ┌────────┴────────┐
         │   Unit Tests    │  ← Pure functions, data models
         │  (many, fast)   │
         └─────────────────┘
```

### 9.2 Test Coverage Targets

| Component | Target | Focus |
|-----------|--------|-------|
| Models | 100% | Validation, serialization |
| Config | 100% | Loading, defaults |
| Researchers | 80% | Extraction logic |
| Orchestrator | 70% | Pipeline flow |
