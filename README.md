# PRISM — Predictive Revenue Intelligence & Signal Mapping

**A GTM signal engine that uses LLM-powered Content Intelligence to assess buying readiness, map buying committees, and generate actionable outreach strategies from public content.**

PRISM takes a target company, ingests their public content (blog posts, LinkedIn activity, job postings, press releases), runs it through a multi-stage LLM analysis chain, and produces a full **intelligence dossier** for a sales rep — complete with composite scoring, a "why now" hypothesis, buying committee mapping with per-person messaging recommendations, and honest confidence assessments.

---

## What Makes PRISM Different

Every GTM enrichment tool pulls from the same data sources (Crunchbase, Apollo, BuiltWith). PRISM's proprietary layer is **Content Intelligence** — a 4-stage LLM analysis pipeline that extracts sub-semantic organizational signals from public language:

- **Organizational state** — Is the company scaling, stressed, or stable?
- **Pain signal coherence** — Are pain signals scattered or crystallizing around a specific problem?
- **Buying journey position** — Where are they on the awareness-to-decision continuum?
- **Messaging resonance vectors** — What language and framing will land with each stakeholder?

These are signals that keyword matching and traditional NLP cannot detect.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         PRISM v1 Pipeline                            │
│                                                                      │
│  DATA LAYER                                                          │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐           │
│  │ Fixture   │  │  Blog    │  │ Job Board│  │  Apollo    │           │
│  │ Data      │  │ Scraper  │  │ Scraper  │  │  API      │            │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘           │
│        └──────────────┴─────────────┴──────────────┘                 │
│                               │                                      │
│              ┌────────────────▼────────────────┐                     │
│              │   Enrichment Orchestrator       │                     │
│              │   (pluggable sources)           │                     │
│              └────────────────┬────────────────┘                     │
│                               │                                      │
│  EXTRACTION LAYER             ▼                                      │
│  ┌──────────────────────────────────────────────┐                    │
│  │  Multi-Path Extraction                       │                    │
│  │  HTML parser + pattern library + LLM         │                    │
│  │  → structured signals with typed_data        │                    │
│  └──────────────────┬───────────────────────────┘                    │
│                     │                                                │
│  ANALYSIS LAYER     ▼                                                │
│  ┌──────────────────────────────────────────────┐                    │
│  │  Content Intelligence Chain (4-stage LLM)    │                    │
│  │  Stage 1: Per-Item Extraction                │                    │
│  │  Stage 2: Cross-Corpus Synthesis             │                    │
│  │  Stage 3: Person-Level Analysis              │                    │
│  │  Stage 4: Synthesis & Composite Scoring      │                    │
│  └──────────────────┬───────────────────────────┘                    │
│                     │                                                │
│  SCORING LAYER      ▼                                                │
│  ┌──────────────────────────────────────────────┐                    │
│  │  ICP Fit + Buying Readiness + Timing         │                    │
│  │  → Composite Score → Tier Assignment         │                    │
│  └──────────────────┬───────────────────────────┘                    │
│                     │                                                │
│  OUTPUT LAYER       ▼                                                │
│  ┌──────────────────────────────────────────────┐                    │
│  │  Dossier Generator  │  REST API  │  CLI     │                    │
│  └──────────────────────────────────────────────┘                    │
│                                                                      │
│  PERSISTENCE: PostgreSQL (9 tables) ← DAL ← SQLAlchemy async        │
│  LLM BACKEND: Claude API │ Local Inference (vLLM/SGLang)             │
│  TASK QUEUE: arq + Redis (optional)                                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Content Intelligence Chain (4-Stage Pipeline)

### Stage 1 — Per-Item Extraction
Runs independently on each content item (blog post, LinkedIn post, job posting). Extracts four layers:
- **Semantic**: stated facts, announcements, metrics, claims
- **Pragmatic**: why saying this now, target audience, reactive vs proactive
- **Tonal**: confidence/stress/urgency markers, certainty level, emotional register
- **Structural**: what gets emphasis, what's minimized, notable absences

### Stage 2 — Cross-Corpus Synthesis
Analyzes patterns **across** all content items over time. This is where the proprietary analysis happens — trajectory changes, absence analysis, pain coherence scoring, organizational stress indicators, and stated-vs-actual priority alignment.

### Stage 3 — Person-Level Analysis
Per buying committee member: individual pain alignment, buying readiness stage, messaging resonance type (Builder / Optimizer / Risk-manager / Visionary / Pragmatist), influence mapping, and approach/avoid recommendations.

### Stage 4 — Synthesis & Scoring
Combines all prior stages with firmographic/technographic data to produce composite scores, a why-now hypothesis, play recommendations, confidence assessment, and counter-signals.

---

## Scoring System

### Composite Score

The composite score determines account tier priority:

| Weight | Component | Source |
|--------|-----------|--------|
| 25% | **ICP Fit** | Firmographic/technographic data |
| 50% | **Buying Readiness** | Content Intelligence output (dominant weight) |
| 25% | **Timing** | Signal recency + urgency indicators |

### Tier Thresholds

| Tier | Threshold | Action |
|------|-----------|--------|
| **Tier 1** | >= 70% | Immediate action |
| **Tier 2** | >= 45% | Active outreach this week |
| **Tier 3** | >= 25% | Monitor & nurture |
| Below | < 25% | Not qualified |

### ICP Fit Components

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| Funding Stage Fit | 25% | Can they afford it? (Series B = 1.0) |
| Growth Rate | 20% | Urgency from scaling pain |
| Tech Stack Fit | 20% | Mechanism of pain (QuickBooks + >100 employees = 1.0) |
| Headcount Fit | 15% | Complexity threshold (sweet spot: 100-300) |
| Industry Fit | 10% | SaaS = 1.0, Fintech = 0.95, etc. |
| Geo Fit | 10% | US tech hubs = 1.0 |

### Signal Decay

All signals are temporally weighted using a configurable decay function. Each signal type has a peak window, half-life, and maximum relevance period. A funding round peaks at 30 days and decays over 180 days. A LinkedIn pain post peaks at 3 days and decays over 30 days.

---

## Demo Context

PRISM is demonstrated as if built for **Ledgerflow**, a fictional AI-native accounting automation platform targeting Series A-D SaaS companies outgrowing QuickBooks (50-500 employees). The dossiers recommend outreach angles framed around Ledgerflow's capabilities: automated month-end close, ASC 606 revenue recognition, multi-entity consolidation, and AI anomaly detection.

### Demo Companies (10)

The fixture data includes 10 manually-constructed companies spanning the scoring spectrum:

| Company | Industry | Stage | Headcount | Expected Tier |
|---------|----------|-------|-----------|---------------|
| VelocityPay | SaaS (Payments) | Series B | 180 | Tier 1-2 |
| StackSync | SaaS (DevOps) | Series B | 150 | Tier 1-2 |
| BrightHire | SaaS (HR Tech) | Series A | 85 | Tier 2 |
| DataCanvas | SaaS (Analytics) | Series B | 220 | Tier 2 |
| CloudBolt | SaaS (Cloud Mgmt) | Series C | 310 | Tier 2-3 |
| FinPulse | Fintech | Series B | 240 | Tier 1 |
| CodeBridge | SaaS (API) | Series A | 65 | Tier 2 |
| Meridian Health | Healthcare SaaS | Series B | 200 | Tier 2 |
| ShipStream | E-commerce | Series C | 400 | Tier 3 |
| GreenLedger | Climate Tech | Series A | 45 | Tier 3 |

---

## Dossier Output

Each analysis produces a structured intelligence brief in markdown:

1. **Executive Summary** — Composite score tree, tier classification, journey position
2. **Subject Profile** — Firmographics, funding, tech stack with migration signals
3. **Organizational Intelligence Assessment** — Content Intelligence findings: pain coherence, org stress, solution sophistication, trajectory, notable absences
4. **Key Personnel — Buying Committee Map** — Per-person readiness, messaging resonance, approach/avoid, likely objections
5. **Signal Timeline** — Chronological signals with decay-weighted freshness bars
6. **Why Now — Hypothesis** — Narrative explaining why this company should be contacted today, with counter-signals
7. **Recommended Play** — Play name, sequence, timeline, entry point, per-contact angles
8. **Collection Gaps & Discovery Questions** — Unknowns to prioritize in first conversation
9. **Appendix — Raw Signals & Sources** — Full signal detail with confidence tags

---

## Quick Start

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

### Installation

```bash
# Clone the repository
git clone https://github.com/Aurnix/PRISM.git
cd PRISM

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Usage

```bash
# ─── Analysis (Phase 0 + v1) ─────────────────────────
# List available demo companies
python -m prism.cli list

# Analyze a single company (full pipeline with LLM)
python -m prism.cli analyze velocitypay

# Analyze without LLM calls (scoring from fixture data only)
python -m prism.cli analyze velocitypay --no-llm

# Analyze without blog scraping (use cached/fixture content only)
python -m prism.cli analyze velocitypay --no-scrape

# Analyze all demo companies
python -m prism.cli analyze-all --no-scrape

# Estimate analysis cost before running
python -m prism.cli estimate velocitypay

# View current scoring weights
python -m prism.cli weights

# ─── Enrichment (v1) ─────────────────────────────────
# Run all enrichment sources for a company
python -m prism.cli enrich velocitypay

# ─── API Server (v1) ─────────────────────────────────
# Start the REST API server
python -m prism.cli serve

# ─── Database (v1, requires PostgreSQL) ──────────────
# Create all database tables
python -m prism.cli init-db

# Load fixture data into PostgreSQL
python -m prism.cli seed
```

Dossiers are saved to `output/dossiers/<slug>_dossier.md`.

### REST API (v1)

When running with `python -m prism.cli serve`, the following endpoints are available:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness check |
| `GET` | `/accounts` | List all tracked companies |
| `POST` | `/accounts` | Add a company |
| `GET` | `/accounts/{slug}` | Full account detail |
| `PATCH` | `/accounts/{slug}` | Update account |
| `DELETE` | `/accounts/{slug}` | Archive (soft delete) |
| `POST` | `/accounts/{slug}/analyze` | Trigger analysis |
| `POST` | `/accounts/{slug}/enrich` | Trigger enrichment |
| `GET` | `/accounts/{slug}/signals` | List signals with decay weights |
| `POST` | `/accounts/{slug}/content` | Upload content |
| `GET` | `/accounts/{slug}/dossier` | Latest dossier |
| `GET` | `/dossiers/{dossier_id}` | Retrieve dossier by ID |

All endpoints require `X-API-Key` header. Configure valid keys via `API_KEYS` env var.

### Running Tests

```bash
pytest tests/
```

---

## Project Structure

```
prism/
├── prism/
│   ├── cli.py                 # Click CLI (analyze, enrich, serve, seed, init-db)
│   ├── config.py              # All weights, thresholds, decay parameters, env config
│   ├── pipeline.py            # [v1] Shared analysis orchestration
│   ├── tasks.py               # [v1] Background tasks + arq worker
│   │
│   ├── models/                # Pydantic v2 data models
│   │   ├── account.py         # Account, firmographics
│   │   ├── contact.py         # Contacts, buying committee
│   │   ├── content.py         # Content items, corpus
│   │   ├── signal.py          # Signals, decay config
│   │   ├── analysis.py        # Analysis results, scores, hypotheses
│   │   ├── activation.py      # Plays, angles, account briefs
│   │   └── extraction.py      # [v1] Signal typed_data schemas
│   │
│   ├── analysis/              # Core analysis engines
│   │   ├── content_intel.py   # 4-stage LLM analysis chain
│   │   ├── scoring.py         # ICP fit, readiness, timing, composite
│   │   └── signal_decay.py    # Temporal decay weighting
│   │
│   ├── services/              # External integrations
│   │   ├── llm_backend.py     # [v1] LLMBackend ABC + budget tracking
│   │   ├── llm.py             # Legacy Claude API wrapper
│   │   ├── scraper.py         # Blog scraper (RSS + HTML fallback)
│   │   ├── extraction.py      # [v1] Multi-path extraction pipeline
│   │   ├── backends/          # [v1] Swappable LLM implementations
│   │   │   ├── anthropic_backend.py
│   │   │   ├── local_backend.py
│   │   │   └── router.py
│   │   └── enrichment/        # [v1] Pluggable data enrichment
│   │       ├── base.py        # EnrichmentSource ABC
│   │       ├── orchestrator.py
│   │       ├── blog_scraper.py
│   │       ├── job_boards.py  # Greenhouse + Lever
│   │       └── apollo.py
│   │
│   ├── api/                   # [v1] FastAPI REST API
│   │   ├── deps.py            # Dependency injection
│   │   ├── schemas.py         # Request/response models
│   │   └── routes.py          # All endpoints
│   │
│   ├── db/                    # [v1] SQLAlchemy persistence
│   │   ├── models.py          # 9 ORM tables
│   │   ├── session.py         # Async engine + sessions
│   │   └── converters.py      # Pydantic <-> SQLAlchemy
│   │
│   ├── data/                  # Data access layer
│   │   ├── dal.py             # [v1] DAL abstract interface
│   │   ├── database_dal.py    # [v1] PostgreSQL implementation
│   │   ├── fixture_dal.py     # [v1] Fixture fallback
│   │   ├── loader.py          # Phase 0 fixture loader
│   │   └── product.py         # Ledgerflow product definition
│   │
│   ├── prompts/v1/            # Versioned prompt templates
│   └── output/
│       └── dossier.py         # Markdown dossier renderer
│
├── fixtures/                  # Demo company data (10 companies)
├── output/dossiers/           # Generated dossier files
├── docs/                      # Architecture & spec documents
└── tests/                     # 213 tests across 12 files
```

---

## Configuration

All scoring weights, thresholds, and parameters are centralized in `prism/config.py`. No weights are hardcoded in analysis functions. This makes it straightforward to tune scoring without touching analysis logic.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required. Your Anthropic API key |
| `PRISM_MODEL` | `claude-sonnet-4-20250514` | Claude model for analysis |
| `PRISM_PROMPT_VERSION` | `v1` | Prompt template version directory |
| `PRISM_MAX_CORPUS_ITEMS` | `30` | Max content items per company |
| `PRISM_MAX_PERSON_POSTS` | `20` | Max LinkedIn posts per person |
| `PRISM_LOG_LEVEL` | `INFO` | Logging level |
| `DATABASE_URL` | — | PostgreSQL connection string (v1) |
| `API_KEYS` | — | Comma-separated valid API keys (v1) |
| `LLM_BACKEND` | `anthropic` | `anthropic`, `local`, or `router` (v1) |
| `LLM_MAX_SPEND_USD` | `100.0` | Daily LLM budget cap (v1) |
| `APOLLO_API_KEY` | — | Optional Apollo enrichment (v1) |
| `REDIS_URL` | — | Optional Redis for task queue (v1) |

---

## Tech Stack

**Core:**
- **Python 3.11+** with type hints throughout
- **Pydantic v2** — all data models with validation
- **Anthropic SDK** — Claude API for Content Intelligence chain
- **httpx** — async HTTP for scraping, API calls, enrichment
- **BeautifulSoup4** — HTML parsing for content extraction
- **Click** + **Rich** — CLI with progress bars and colored output
- **pytest** — 213 tests

**v1 Additions:**
- **SQLAlchemy 2.0** (async) — ORM with 9 PostgreSQL tables
- **asyncpg** — PostgreSQL async driver
- **FastAPI** + **uvicorn** — REST API server
- **arq** + **Redis** — background task queue (optional)

---

## Cost

The full analysis pipeline for 10 companies costs approximately **$5-10** in Claude API usage. Use `python -m prism.cli estimate <slug>` to preview costs before running.

---

## Current Phase & Roadmap

**v1 — Operational Tool** (in progress, Phases 1-7 complete). The system now supports swappable LLM backends, persistent PostgreSQL storage, a full REST API, multi-path extraction, pluggable enrichment sources, and background task processing. 213 tests passing.

### v1 Build Status

| Phase | Name | Status |
|-------|------|--------|
| 1 | Foundation (LLM Backend Abstraction) | **Complete** |
| 2 | Persistence (PostgreSQL + DAL) | **Complete** |
| 3 | API Layer (FastAPI) | **Complete** |
| 4 | Extraction Pipeline | **Complete** |
| 5 | Collection & Enrichment | **Complete** |
| 6 | Third-Party Enrichment (Apollo) | **Complete** |
| 7 | Task Queue & Scheduling | **Complete** |
| 8 | Discovery Pipeline | Planned |
| 9 | Frontend (Streamlit/Next.js) | Planned |

### Key v1 Interfaces

- **`LLMBackend`** — Abstract LLM interface with `AnthropicBackend` (Claude API) and `LocalInferenceBackend` (vLLM/SGLang). `ModelRouter` for mixed-model strategies.
- **`DataAccessLayer`** — Abstract DAL with `DatabaseDAL` (PostgreSQL) and `FixtureDAL` (JSON fixture fallback).
- **`EnrichmentSource`** — Pluggable enrichment with blog scraper, job board (Greenhouse/Lever), and Apollo adapters. `EnrichmentOrchestrator` runs all available sources.
- **REST API** — FastAPI with 12 endpoints for account management, analysis, enrichment, and dossier retrieval.
- **Task Queue** — arq-compatible task functions for background enrichment, analysis, and scheduled re-processing.

**Phase 0 — Portfolio Demo** (complete). The foundation: Content Intelligence pipeline, scoring engine, signal decay, dossier renderer, 10 demo companies with fixture data.

See [`docs/V1_BUILD_PLAN.md`](docs/V1_BUILD_PLAN.md) for full architecture spec and [`V1_ROADMAP.md`](V1_ROADMAP.md) for the phase-by-phase build order.

---

## Author

**Joseph Sherman**

---

## License

This project is proprietary. All rights reserved.
