# Product Requirements Document (PRD)
## UnlockEgypt Site Researcher

**Version:** 3.4
**Last Updated:** 2026-02-01
**Status:** Active Development

---

## 1. Overview

### 1.1 Product Vision
UnlockEgypt Site Researcher is a comprehensive research tool that gathers rich, multi-source information about Egyptian archaeological sites. Unlike simple web scrapers, it treats each site as a research subject, synthesizing data from multiple authoritative sources to create comprehensive site profiles.

### 1.2 Problem Statement
Travelers and researchers seeking information about Egyptian archaeological sites face fragmented data across multiple sources:
- Official government sites (egymonuments.gov.eg) have authoritative but sometimes incomplete data
- Wikipedia provides historical context but may lack practical visitor information
- Google Maps has operational details but lacks historical depth
- No single source provides Arabic translations, pronunciation guides, and cultural context

### 1.3 Solution
A research-oriented tool that:
- Aggregates data from multiple authoritative sources
- Provides comprehensive site profiles with historical and practical information
- Includes Arabic vocabulary with pronunciation guides
- Generates contextual visitor tips based on site characteristics

---

## 2. Target Users

### 2.1 Primary Users
| User Type | Needs | Usage Pattern |
|-----------|-------|---------------|
| **Travel App Developers** | Structured JSON data for mobile apps | One-time data export, periodic updates |
| **Tourism Researchers** | Comprehensive site information | Research and analysis |
| **Educational Platforms** | Historical facts, Arabic terms | Content creation |

### 2.2 User Stories

**As a travel app developer**, I want structured JSON data about Egyptian sites so that I can populate my mobile application with rich content.

**As a researcher**, I want to gather comprehensive information from multiple sources so that I can analyze patterns across sites.

**As a content creator**, I want accurate Arabic translations and pronunciations so that I can create educational materials.

---

## 3. Features & Requirements

### 3.1 Core Features (MVP - Implemented)

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| **Multi-Source Research** | Aggregate data from 4+ sources per site | P0 | Done |
| **Wikipedia Integration** | EN + AR Wikipedia with fuzzy search | P0 | Done |
| **Governorate Detection** | Accurate mapping to 27 Egyptian governorates | P0 | Done |
| **Arabic Vocabulary** | Dynamic extraction with translations | P0 | Done |
| **Contextual Tips** | Site-type-specific visitor recommendations | P0 | Done |
| **JSON Export** | Structured output for app consumption | P0 | Done |

### 3.2 Data Points Collected

For each site, the system collects:

**Basic Information:**
- Name (English + Arabic)
- Governorate location
- GPS coordinates
- Historical era
- Tourism type (Pharaonic, Islamic, Coptic, etc.)
- Place type (Temple, Tomb, Museum, etc.)

**Rich Content:**
- Short and full descriptions
- Unique historical facts (from Wikipedia)
- Key historical figures mentioned
- Architectural features
- Multiple images

**Practical Information:**
- Estimated visit duration
- Best time to visit
- Opening hours (when available)
- Official website links
- Contextual visitor tips

**Cultural Content:**
- Arabic vocabulary terms
- Pronunciation guides
- Site-specific Arabic phrases

### 3.3 Supported Site Categories

| Category | Example Sites | Count |
|----------|---------------|-------|
| Archaeological Sites | Karnak, Abu Simbel | ~34 |
| Monuments | Pyramids, Sphinx | ~123 |
| Museums | Egyptian Museum, GEM | ~24 |
| Sunken Monuments | Alexandria underwater sites | ~8 |
| **Total** | | **~189** |

---

## 4. Non-Functional Requirements

### 4.1 Performance
| Metric | Requirement |
|--------|-------------|
| Sites per hour | 20-30 (with rate limiting) |
| Memory usage | < 500MB during operation |
| Output file size | Scalable JSON |

### 4.2 Reliability
- Graceful handling of missing data
- Retry logic for network failures
- Comprehensive error logging
- Cache management to prevent memory leaks

### 4.3 Maintainability
- Modular researcher components
- Externalized configuration (config.yaml)
- Type hints throughout codebase
- Comprehensive documentation

### 4.4 Constraints
- **No API Keys Required**: All data sources must be freely accessible
- **Rate Limiting**: Respect source website limits (1 req/sec for Nominatim)
- **Ethical Scraping**: Proper user-agent identification

---

## 5. Data Sources

| Source | Data Retrieved | Method |
|--------|---------------|--------|
| egymonuments.gov.eg | Primary site info, images | Selenium |
| Wikipedia (EN) | Historical facts, key figures | Wikipedia API |
| Wikipedia (AR) | Arabic names, descriptions | Wikipedia API |
| Nominatim/OSM | Coordinates, governorate | REST API |
| Google Translate | Arabic translations | deep-translator |

---

## 6. Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Sites with complete data | > 90% | TBD |
| Sites with Arabic content | > 95% | TBD |
| Sites with unique facts | > 80% | TBD |
| Wikipedia match rate | > 70% | TBD |

---

## 7. Future Roadmap

### Phase 2 (Planned)
- [ ] Google Maps integration for opening hours
- [ ] Ticket pricing from official sources
- [ ] Image optimization and CDN upload
- [ ] Incremental update support

### Phase 3 (Consideration)
- [ ] Multi-language support beyond EN/AR
- [ ] Audio pronunciation files
- [ ] Interactive map generation
- [ ] API endpoint for real-time queries

---

## 8. Glossary

| Term | Definition |
|------|------------|
| **Governorate** | Administrative division of Egypt (27 total) |
| **Pharaonic** | Related to ancient Egyptian pharaohs |
| **Fuzzy Search** | Search that finds results despite spelling variations |
| **Rate Limiting** | Restricting request frequency to avoid overloading servers |
