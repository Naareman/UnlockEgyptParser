# Technology Stack Document
## UnlockEgypt Site Researcher

**Version:** 3.4
**Last Updated:** 2026-02-01

---

## 1. Core Technology

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Language** | Python | 3.12+ | Primary development language |
| **Package Manager** | uv | Latest | Fast dependency management |
| **Build System** | setuptools | 68+ | Package building |

---

## 2. Dependencies

### 2.1 Production Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| **selenium** | >=4.0.0 | Browser automation for web scraping | Apache 2.0 |
| **beautifulsoup4** | >=4.12.0 | HTML parsing | MIT |
| **lxml** | >=4.9.0 | Fast XML/HTML parser (BS4 backend) | BSD |
| **requests** | >=2.25.0 | HTTP client for APIs | Apache 2.0 |
| **PyYAML** | >=6.0 | Configuration file parsing | MIT |
| **deep-translator** | >=1.11.0 | Free Google Translate API | MIT |
| **wikipedia-api** | >=0.6.0 | Wikipedia article retrieval | MIT |

### 2.2 Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **pytest** | >=7.0 | Testing framework |
| **pytest-cov** | >=4.0 | Coverage reporting |
| **ruff** | >=0.1.0 | Linting and formatting |
| **mypy** | >=1.0 | Static type checking |
| **pre-commit** | >=3.0 | Git hooks |

---

## 3. External Services

### 3.1 Data Sources

| Service | URL | Authentication | Rate Limit |
|---------|-----|----------------|------------|
| **egymonuments.gov.eg** | https://egymonuments.gov.eg | None | Respectful |
| **Wikipedia API** | https://en.wikipedia.org/w/api.php | None | None |
| **Nominatim (OSM)** | https://nominatim.openstreetmap.org | User-Agent | 1 req/sec |
| **Google Translate** | Via deep-translator | None | Reasonable |

### 3.2 No Paid Services

This project is designed to operate without any paid API keys:
- No Google Cloud APIs
- No AWS services
- No paid translation services
- All data sources are freely accessible

---

## 4. Development Tools

### 4.1 Code Quality

```toml
# Configured in pyproject.toml

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
```

### 4.2 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
```

### 4.3 IDE Support

| IDE | Recommended Extensions |
|-----|----------------------|
| **VS Code** | Python, Pylance, Ruff |
| **PyCharm** | Built-in Python support |
| **Cursor** | Python, Ruff |

---

## 5. Project Structure

```
UnlockEgyptParser/
├── pyproject.toml          # Project metadata & dependencies
├── .pre-commit-config.yaml # Pre-commit hooks
├── .gitignore
├── README.md
│
├── docs/                   # Documentation
│   ├── PRD.md             # Product requirements
│   ├── DESIGN.md          # System design
│   └── TECH_STACK.md      # This file
│
├── src/                    # Source code (src layout)
│   └── unlockegypt/
│       ├── __init__.py
│       ├── py.typed        # PEP 561 marker
│       ├── cli.py          # CLI entry point
│       ├── site_researcher.py
│       ├── models/
│       ├── researchers/
│       └── utils/
│
├── tests/                  # Test suite
│   ├── conftest.py
│   ├── test_models.py
│   └── test_researchers/
│
└── config.yaml             # Runtime configuration
```

---

## 6. Browser Automation

### 6.1 Selenium Configuration

| Setting | Value | Reason |
|---------|-------|--------|
| Browser | Chrome | Most stable, best automation support |
| Mode | Headless | Server/CI compatibility |
| Window Size | 1920x1080 | Consistent element rendering |
| Language | en | Consistent page content |

### 6.2 WebDriver Management

The project uses Chrome WebDriver with automatic management:
- Selenium 4.0+ includes built-in driver management
- Falls back to system-installed chromedriver if needed

---

## 7. Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Selenium   │────▶│  Requests   │────▶│  JSON File  │
│  (scraping) │     │  (APIs)     │     │  (output)   │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                    │
      ▼                   ▼                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ HTML Pages  │     │ JSON APIs   │     │ Structured  │
│ (gov.eg)    │     │ (Wikipedia, │     │ Site Data   │
│             │     │  Nominatim) │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## 8. Configuration Management

### 8.1 Configuration Sources

| Source | Priority | Purpose |
|--------|----------|---------|
| CLI Arguments | 1 (highest) | Runtime overrides |
| config.yaml | 2 | Project settings |
| Code Defaults | 3 (lowest) | Fallback values |

### 8.2 Configuration Categories

```yaml
# config.yaml structure
app:          # Application metadata
website:      # Target website settings
browser:      # Selenium configuration
timing:       # Delays and timeouts
content:      # Extraction thresholds
geography:    # Coordinate bounds
geocoding:    # Nominatim settings
output:       # Export configuration
```

---

## 9. Testing Infrastructure

### 9.1 Test Framework

| Component | Tool | Purpose |
|-----------|------|---------|
| Runner | pytest | Test discovery and execution |
| Coverage | pytest-cov | Code coverage reporting |
| Mocking | unittest.mock | HTTP response mocking |
| Fixtures | conftest.py | Shared test setup |

### 9.2 Test Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run with verbose output
pytest -v --tb=short
```

---

## 10. CI/CD Pipeline

### 10.1 GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --all-extras --dev
      - run: uv run ruff check .
      - run: uv run mypy src
      - run: uv run pytest --cov
```

### 10.2 Quality Gates

| Check | Tool | Threshold |
|-------|------|-----------|
| Linting | Ruff | 0 errors |
| Type Check | mypy | 0 errors |
| Tests | pytest | 100% pass |
| Coverage | pytest-cov | >80% |

---

## 11. Deployment

### 11.1 Installation

```bash
# Clone repository
git clone https://github.com/Naareman/UnlockEgyptParser.git
cd UnlockEgyptParser

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### 11.2 Running

```bash
# Research all sites
uv run python -m unlockegypt.research

# Research specific type with limit
uv run python -m unlockegypt.research -t monuments -m 5

# Verbose output
uv run python -m unlockegypt.research -v
```

---

## 12. Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.3 | 2026-02-01 | Config loader, code cleanup, memory optimization |
| 3.2 | 2026-02-01 | Multi-source research architecture |
| 3.1 | 2026-01-31 | All 4 page types support |
| 3.0 | 2026-01-31 | Production-quality refactor |

---

## 13. License

MIT License - See LICENSE file for details.

---

## 14. References

- [Python Packaging Guide](https://packaging.python.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Selenium Documentation](https://selenium-python.readthedocs.io/)
- [Wikipedia API](https://www.mediawiki.org/wiki/API:Main_page)
- [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/)
