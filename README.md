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
┌─────────────────────────────────────────────────────────────────┐
│                        PRISM Pipeline                          │
│                                                                 │
│  ┌──────────┐    ┌──────────────────────────────────────────┐  │
│  │ Fixture  │    │     Content Intelligence Chain           │  │
│  │  Data    │───▶│                                          │  │
│  │ (JSON)   │    │  Stage 1: Per-Item Extraction            │  │
│  └──────────┘    │     ▼ (parallelized per content item)    │  │
│                  │  Stage 2: Cross-Corpus Synthesis          │  │
│  ┌──────────┐    │     ▼                                    │  │
│  │  Blog    │───▶│  Stage 3: Person-Level Analysis          │  │
│  │ Scraper  │    │     ▼ (per buying committee member)      │  │
│  └──────────┘    │  Stage 4: Synthesis & Composite Scoring  │  │
│                  └──────────────┬───────────────────────────┘  │
│                                 │                               │
│                  ┌──────────────▼───────────────────────────┐  │
│                  │       Scoring Engine                     │  │
│                  │  ICP Fit + Buying Readiness + Timing     │  │
│                  │  → Composite Score → Tier Assignment     │  │
│                  └──────────────┬───────────────────────────┘  │
│                                 │                               │
│                  ┌──────────────▼───────────────────────────┐  │
│                  │       Dossier Generator                  │  │
│                  │  Markdown intelligence brief             │  │
│                  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
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
```

Dossiers are saved to `output/dossiers/<slug>_dossier.md`.

### Running Tests

```bash
pytest tests/
```

---

## Project Structure

```
prism/
├── prism/
│   ├── cli.py                 # Click CLI entry point
│   ├── config.py              # All weights, thresholds, decay parameters
│   ├── models/                # Pydantic v2 data models
│   │   ├── account.py         # Account, firmographics
│   │   ├── contact.py         # Contacts, buying committee
│   │   ├── content.py         # Content items, corpus
│   │   ├── signal.py          # Signals, decay config
│   │   ├── analysis.py        # Analysis results, scores, hypotheses
│   │   └── activation.py      # Plays, angles, account briefs
│   ├── analysis/              # Core analysis engines
│   │   ├── content_intel.py   # 4-stage LLM analysis chain
│   │   ├── scoring.py         # ICP fit, readiness, timing, composite
│   │   └── signal_decay.py    # Temporal decay weighting
│   ├── services/              # External integrations
│   │   ├── llm.py             # Claude API wrapper (retry, cost tracking)
│   │   └── scraper.py         # Blog scraper (RSS + HTML fallback)
│   ├── prompts/v1/            # Versioned prompt templates
│   ├── output/
│   │   └── dossier.py         # Markdown dossier renderer
│   └── data/
│       ├── loader.py          # Fixture data loader
│       └── product.py         # Ledgerflow product definition
├── fixtures/
│   ├── companies/             # One JSON file per demo company
│   └── scraped_content/       # Cached blog scrapes
├── output/dossiers/           # Generated dossier markdown files
└── tests/                     # pytest test suite
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

---

## Tech Stack

- **Python 3.11+** with type hints throughout
- **Pydantic v2** — all data models with validation
- **Anthropic SDK** — Claude API for Content Intelligence chain
- **httpx** — async HTTP for blog scraping and API calls
- **BeautifulSoup4** — HTML parsing for blog content extraction
- **Click** — CLI framework
- **Rich** — terminal formatting, progress bars, colored output
- **python-dotenv** — environment variable management
- **pytest** — test suite

---

## Cost

The full analysis pipeline for 10 companies costs approximately **$5-10** in Claude API usage. Use `python -m prism.cli estimate <slug>` to preview costs before running.

---

## Current Phase

**Phase 0 — Portfolio Demo.** This is a working demonstration of the Content Intelligence concept. It processes demo companies through the full analysis chain and produces markdown dossiers. There is no database, no frontend, no CRM integration, and no automated company discovery — those are Phase 1+ concerns.

---

## Author

**Joseph Sherman**

---

## License

This project is proprietary. All rights reserved.
