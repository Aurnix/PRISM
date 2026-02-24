# CLAUDE.md — PRISM Build Instructions

## Project Identity

**PRISM** — Predictive Revenue Intelligence & Signal Mapping  
A GTM (Go-To-Market) signal engine that combines standard firmographic/technographic enrichment with a proprietary **Content Intelligence Layer** — an LLM-based analytical engine that extracts sub-semantic organizational signals from public content to assess buying readiness, map buying committee psychology, and generate contextual outreach strategies.

**Author:** Joseph Sherman
**Repo name:** `prism`
**Current phase:** Phase 0 — Portfolio Demo (complete)
**Next phase:** v1 — Operational Tool (spec'd in `docs/V1_BUILD_PLAN.md`)

---

## What PRISM Does (Plain English)

PRISM takes a target company, scrapes their public content (blog, LinkedIn, job postings, press releases), runs that content through a multi-stage LLM analysis chain, and produces an **intelligence dossier** for a sales rep. The dossier includes: composite scoring (ICP fit, buying readiness, timing), a "why now" hypothesis for why this company should be contacted today, a buying committee map with per-person messaging recommendations, recommended outreach plays, and honest confidence assessments with counter-signals.

**The differentiation:** Every GTM tool enriches with the same data (Crunchbase, Apollo, BuiltWith). PRISM's proprietary layer is the Content Intelligence analysis — extracting organizational state, pain signal coherence, buying journey position, and messaging resonance vectors from public language that keyword matching cannot detect.

---

## Phase 0 Scope (COMPLETE)

Phase 0 is a **portfolio demonstration piece**. All components below are implemented and tested (91 tests passing).

### Completed Components

1. **Data models** (Pydantic) for accounts, contacts, content items, signals, analyses
2. **Content scraper** — Blog scraping via BeautifulSoup/httpx (RSS detection + fallback to HTML parsing)
3. **Content Intelligence analysis chain** — The 4-stage LLM prompt pipeline (Stage 1: per-item extraction → Stage 2: cross-corpus synthesis → Stage 3: person-level analysis → Stage 4: synthesis & scoring)
4. **Scoring engine** — ICP fit score, buying readiness score, timing score, composite score with configurable weights
5. **Signal decay engine** — Temporal weighting function for all signal types
6. **Dossier generator** — Renders the full intelligence brief in markdown (see format specification below)
7. **CLI orchestrator** — `python -m prism.cli analyze <company_slug>` runs the full pipeline for one company, `python -m prism.cli analyze-all` runs all companies
8. **Fixture data** — Manual JSON files for 10 demo companies (firmographics, contacts, tech stack, LinkedIn posts)
9. **Rules-based play fallback** — PLAY_MATRIX lookup when LLM doesn't generate a play

---

## v1 Scope (WHAT TO BUILD NEXT)

v1 upgrades PRISM from a CLI demo to an operational tool. Full architecture spec is in `docs/V1_BUILD_PLAN.md`. The roadmap is in `V1_ROADMAP.md`.

### v1 Key Additions

- **PostgreSQL + SQLAlchemy** — Persistent storage for accounts, analyses, dossiers
- **Data Access Layer (DAL)** — Abstract interface with Database and Fixture implementations
- **LLM Backend abstraction** — Swappable between Claude API and local inference (vLLM/SGLang on Mac Studio cluster with open-source models like GLM-5)
- **FastAPI endpoints** — REST API for account management, analysis triggering, dossier retrieval
- **Enrichment services** — Pluggable data sources (Apollo, Crunchbase, job board scrapers, Proxycurl)
- **Task queue** — Background analysis with arq + Redis
- **Scheduled re-analysis** — Daily/weekly re-scoring as signals decay and new ones appear
- **Discovery pipeline** — Auto-find ICP-matching companies from enrichment APIs

### v1 Does NOT Include

- CRM export (Salesforce/HubSpot)
- Feedback loop / recalibration engine
- Re-engagement monitor
- Multi-tenant / team management
- Docker Compose
- Email/Slack notifications

### v1 Architecture Reference

The four load-bearing interfaces are fully specified in `docs/V1_BUILD_PLAN.md`:

1. **`LLMBackend`** — Abstract LLM interface with `AnthropicBackend` and `LocalInferenceBackend` implementations
2. **Database schema** — 7 PostgreSQL tables (accounts, contacts, linkedin_posts, signals, content_items, analyses, dossiers)
3. **`DataAccessLayer`** — Abstract DAL with `DatabaseDAL` and `FixtureDAL` implementations
4. **`EnrichmentSource`** — Pluggable enrichment interface with orchestrator

### Phase 0 Data Strategy

| Data Type | Source | Method |
|-----------|--------|--------|
| Company firmographics | Manual JSON in `fixtures/` | Hand-entered from Crunchbase |
| Blog content | Real company blogs | BeautifulSoup scraping |
| LinkedIn posts | Manual text in `fixtures/` | Copy-pasted (defer API) |
| Job postings | Manual text in `fixtures/` | Copy-pasted from job boards |
| Tech stack | Manual JSON in `fixtures/` | BuiltWith free lookup |
| Contacts | Manual JSON in `fixtures/` | Apollo free tier / LinkedIn |
| News/press | Manual text in `fixtures/` | Google search |
| LLM analysis | Claude API | Real API calls (~$5 total) |

---

## Tech Stack

- **Python 3.11+** with type hints throughout
- **Pydantic v2** for all data models (use `BaseModel`, validate everything)
- **httpx** for async HTTP (blog scraping, Claude API)
- **BeautifulSoup4** for HTML parsing
- **anthropic** Python SDK for Claude API calls
- **Click** for CLI
- **Rich** for CLI output formatting and progress display
- **python-dotenv** for environment variables
- **pytest** for testing

### NOT using (Phase 0)

- FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery, Next.js, Docker

---

## File Structure

```
prism/
├── CLAUDE.md                       # This file
├── pyproject.toml
├── README.md
├── .env.example                    # ANTHROPIC_API_KEY=sk-ant-...
├── .gitignore
│
├── prism/
│   ├── __init__.py
│   ├── cli.py                      # Click CLI entry point
│   ├── config.py                   # Settings, weights, ICP config
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── account.py              # Account, DiscoveredAccount
│   │   ├── contact.py              # ContactRecord, BuyingCommittee
│   │   ├── content.py              # ContentItem, ContentCorpus
│   │   ├── signal.py               # Signal, SignalDecayConfig
│   │   ├── analysis.py             # AnalyzedAccount, WhyNowHypothesis, ConfidenceAssessment
│   │   └── activation.py           # Play, Angle, AccountBrief
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm.py                  # Claude API wrapper (structured output, retry, cost tracking)
│   │   └── scraper.py              # Blog scraper (RSS + HTML fallback)
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── content_intel.py        # THE proprietary layer — 4-stage analysis chain
│   │   ├── scoring.py              # ICP scoring, readiness scoring, composite scoring
│   │   └── signal_decay.py         # Temporal decay weighting
│   │
│   ├── prompts/
│   │   ├── v1/
│   │   │   ├── stage1_extraction.txt
│   │   │   ├── stage2_synthesis.txt
│   │   │   ├── stage3_person.txt
│   │   │   ├── stage4_scoring.txt
│   │   │   └── activation_angle.txt
│   │   └── README.md               # Prompt versioning notes
│   │
│   ├── output/
│   │   ├── __init__.py
│   │   └── dossier.py              # Markdown dossier renderer
│   │
│   └── data/
│       ├── __init__.py
│       ├── loader.py               # Loads fixture data
│       └── product.py              # Fictional product definition (Ledgerflow)
│
├── fixtures/
│   ├── companies/
│   │   ├── _template.json          # Template for adding new companies
│   │   ├── company_a.json          # One file per demo company
│   │   ├── company_b.json
│   │   └── ...
│   └── scraped_content/            # Cached blog scrapes (avoid re-scraping)
│       └── company_a/
│           ├── blog_posts.json
│           └── raw_html/
│
├── output/                         # Generated dossiers land here
│   └── dossiers/
│       ├── company_a_dossier.md
│       └── ...
│
└── tests/
    ├── conftest.py
    ├── test_scoring.py
    ├── test_signal_decay.py
    ├── test_content_intel.py
    └── test_dossier.py
```

---

## Configuration: config.py

All scoring weights, ICP definitions, and signal decay parameters are centralized in `config.py`. These are NOT hardcoded into analysis functions. The scoring engine reads from config so weights can be changed without touching analysis code.

### ICP Fit Weights (v1.0)

```python
ICP_WEIGHTS = {
    "funding_stage_fit": 0.25,   # Gating factor — can they afford it?
    "growth_rate":       0.20,   # Creates the urgency / scaling pain
    "tech_stack_fit":    0.20,   # Mechanism of the pain
    "headcount_fit":     0.15,   # Complexity threshold
    "industry_fit":      0.10,   # Contextual
    "geo_fit":           0.10,   # Contextual
}
```

### Buying Readiness Weights (v1.0)

```python
READINESS_WEIGHTS = {
    "journey_position":          0.20,  # Where on 0.0-1.0 buying continuum
    "pain_coherence":            0.20,  # Focused vs scattered pain
    "new_leader_signal":         0.20,  # New VP Finance = strongest single signal
    "org_stress_indicators":     0.15,  # Is pain escalating?
    "solution_sophistication":   0.15,  # How articulate about their problem
    "active_evaluation_signals": 0.10,  # Direct vendor eval evidence (high false positive)
}
```

### Timing Weights (v1.0)

```python
TIMING_WEIGHTS = {
    "trigger_event_recency": 0.35,  # Most recent trigger freshness
    "signal_freshness_avg":  0.25,  # Mean decay-weighted freshness
    "urgency_indicators":    0.25,  # Language-based urgency from content
    "window_closing_signals": 0.15, # Evidence window about to shut (inverted: 1.0 = open)
}
```

### Composite Weights (v1.0)

```python
COMPOSITE_WEIGHTS = {
    "icp_fit":          0.25,
    "buying_readiness":  0.50,  # Dominant — Content Intelligence earns its keep here
    "timing":           0.25,
}
```

### Tier Thresholds

```python
TIER_THRESHOLDS = {
    "tier_1": 0.70,   # Immediate action
    "tier_2": 0.45,   # Active outreach this week
    "tier_3": 0.25,   # Monitor & nurture
    # Below 0.25: not qualified
}
```

### Signal Decay Configuration

```python
SIGNAL_DECAY_CONFIG = {
    # signal_type: (peak_days, half_life_days, max_relevance_days)
    "funding_round":             (30,  90,  180),
    "new_executive_finance":     (60,  150, 365),
    "new_executive_other":       (45,  90,  180),
    "champion_departed":         (7,   30,  60),
    "job_posting_finance":       (14,  45,  90),
    "job_posting_technical":     (14,  45,  90),
    "job_posting_urgent":        (7,   21,  45),
    "tech_stack_change":         (7,   30,  60),
    "migration_signal":          (14,  45,  90),
    "blog_post_pain":            (7,   30,  90),
    "linkedin_post_pain":        (3,   14,  30),
    "earnings_mention":          (14,  45,  90),
    "press_release_relevant":    (7,   30,  60),
    "pricing_page_visit":        (1,   7,   21),
    "content_engagement":        (3,   14,  30),
    "g2_research_activity":      (7,   21,  45),
    "competitor_evaluation":     (7,   30,  60),
    "competitor_contract_renewal": (30, 60, 120),
    "glassdoor_trend":           (30,  90,  180),
}
```

### Signal Decay Function

```python
def calculate_decay_weight(signal_type: str, signal_date: date, current_date: date) -> float:
    """Returns 0.0-1.0 weight based on signal freshness."""
    peak, half_life, max_days = SIGNAL_DECAY_CONFIG[signal_type]
    age_days = (current_date - signal_date).days

    if age_days > max_days:
        return 0.0
    if age_days < 0:
        return 0.0
    if age_days <= peak:
        return min(1.0, age_days / peak) if peak > 0 else 1.0

    decay_age = age_days - peak
    return max(0.0, 0.5 ** (decay_age / half_life))
```

---

## The Fictional Product: Ledgerflow

PRISM is being demoed as if built for **Ledgerflow**, a fictional AI-native accounting automation platform. Full product definition is in `docs/PRISM_Demo_Product_Ledgerflow.md`. Key details:

- **What it does:** Automated month-end close, ASC 606 revenue recognition, multi-entity consolidation, real-time financial reporting, AI anomaly detection
- **Target:** Series A-D SaaS/tech companies outgrowing QuickBooks (50-500 employees)
- **Competes with:** Rillet, Puzzle, Digits, Numeric (direct); QuickBooks, NetSuite (displacement)
- **Key buyer personas:** VP Finance (champion), CFO/CEO (economic buyer), CTO (technical gatekeeper), Staff Accountant (user)

When generating outreach angles and plays, reference Ledgerflow capabilities and positioning.

---

## Content Intelligence Chain — The Core Engine

### Overview

The Content Intelligence chain is a sequential 4-stage LLM analysis pipeline. Each stage feeds into the next. Prompts are stored in `prism/prompts/v1/` as plain text files with `{variable}` placeholders.

### Stage 1: Per-Item Extraction (parallelizable)

**Input:** Single content item (blog post, LinkedIn post, job posting, etc.)  
**Output:** Structured JSON with semantic, pragmatic, tonal, and structural layers  
**LLM:** Claude Sonnet (cost-efficient, sufficient for extraction)  
**Tokens:** ~3K per item  

Runs independently for each content item. Can be parallelized with asyncio.

**Extraction layers:**
- **Semantic:** Stated facts, announcements, metrics, claims
- **Pragmatic:** Why saying this now, target audience, reactive vs proactive
- **Tonal:** Confidence/stress/urgency markers, certainty level, emotional register
- **Structural:** What gets emphasis, what's minimized, notable absences

### Stage 2: Cross-Corpus Synthesis

**Input:** All Stage 1 outputs (serialized chronologically), max 30 items  
**Output:** Structured JSON with trajectory, absence analysis, pain coherence, org stress, priority alignment, solution sophistication  
**LLM:** Claude Sonnet (large context, synthesis task)  
**Tokens:** ~15K input (Stage 1 outputs) + 4K output  

This is where the proprietary analysis happens. Looks for patterns ACROSS documents over time, not within individual items.

**Analysis dimensions:**
- **Trajectory:** How language/tone/emphasis changed over time
- **Absence analysis:** Expected topics that are missing/avoided
- **Pain signal coherence:** Score 0.0-1.0, scattered vs crystallized pain
- **Organizational stress indicators:** Language compression, urgency escalation
- **Stated vs actual priorities:** Alignment between messaging and energy
- **Solution sophistication:** "this is frustrating" → "we know what fix looks like"

### Stage 3: Person-Level Analysis (per buying committee member)

**Input:** Individual's LinkedIn posts/content + company analysis summary from Stage 2  
**Output:** Per-person buying readiness, messaging resonance vector, influence mapping  
**LLM:** Claude Sonnet  
**Tokens:** ~5K per person  

Runs for each identified contact with available content. Skip contacts with no public content (flag as "person-level analysis unavailable").

**Per-person outputs:**
- Individual pain alignment (ahead/behind/aligned with org)
- Buying readiness stage (unaware → problem-aware → solution-exploring → active evaluation → decision-ready)
- Messaging resonance (Builder / Optimizer / Risk-manager / Visionary / Pragmatist)
- Influence mapping (authority / influence / evaluation / execution signals)
- Recommended approach and avoid topics

### Stage 4: Synthesis & Composite Scoring

**Input:** Stage 2 output + Stage 3 outputs + firmographic/technographic data + signal list  
**Output:** Composite scores, why-now hypothesis, play recommendation, confidence assessment  
**LLM:** Claude Sonnet  
**Tokens:** ~15K input + 3K output  

Produces the final analysis that feeds the dossier generator.

### Token Management Rules

- Max corpus per company: 30 content items (most recent, prioritize authored over corporate)
- Max per person: 20 LinkedIn posts
- If corpus < 5 items OR < 2 months span: auto-downgrade confidence to LOW
- If no blog content at all: skip Stages 1-2, produce brief from firmographic signals only, flag "limited analysis"

### Prompt Versioning

Prompts live in `prism/prompts/v1/` as `.txt` files. Analysis records store the prompt version used. When iterating prompts, create `v2/` directory — never edit v1 in place.

---

## Dossier Output Format

The dossier is the primary deliverable. It's rendered as a markdown file using ASCII box-drawing characters for structure. Eventually this becomes a styled dark-themed UI, but Phase 0 outputs markdown.

### Dossier Sections

The dossier follows an intelligence brief format:

```
═══════════════════════════════════════════════════════════════════
                    P R I S M
        Predictive Revenue Intelligence & Signal Mapping
═══════════════════════════════════════════════════════════════════

ACCOUNT DOSSIER
Classification: TIER [1/2/3] — [IMMEDIATE ACTION / ACTIVE OUTREACH / MONITOR]
Dossier ID: PRISM-[YYYY]-[sequential]
Generated: [ISO timestamp]
Analyst Confidence: [HIGH / MEDIUM / LOW]
Prompt Chain Version: v[N]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 1: EXECUTIVE SUMMARY
─────────────────────────────
[2-3 sentence summary. Composite score breakdown as tree.]

SECTION 2: SUBJECT PROFILE
──────────────────────────
[Company firmographics, funding, technology stack with migration signals]

SECTION 3: ORGANIZATIONAL INTELLIGENCE ASSESSMENT
─────────────────────────────────────────────────
[Content Intelligence output: buying journey position, pain coherence,
 org stress, solution sophistication, stated vs actual priorities,
 notable absences. Each with score and evidence.]

SECTION 4: KEY PERSONNEL — BUYING COMMITTEE MAP
────────────────────────────────────────────────
[Per-person: role, tenure, buying readiness, messaging resonance,
 approach/avoid, likely objection + handle.
 Recommended entry point. Committee dynamics. Gaps.]

SECTION 5: SIGNAL TIMELINE
──────────────────────────
[Chronological, most recent first. Decay weight as bar chart.
 Source and confidence tag per signal.]

SECTION 6: WHY NOW — HYPOTHESIS
───────────────────────────────
[2-3 paragraph narrative. Confidence level.
 Counter-signals listed separately.]

SECTION 7: RECOMMENDED PLAY
────────────────────────────
[Play name, sequence, timeline, entry point, fallback.
 Specific angles per contact.]

SECTION 8: COLLECTION GAPS & DISCOVERY QUESTIONS
─────────────────────────────────────────────────
[Unknowns to prioritize in first conversation.
 Enrichment gaps (missing data sources).]

SECTION 9: APPENDIX — RAW SIGNALS & SOURCES
───────────────────────────────────────────
[Full signal detail, source URLs, extraction confidence tags,
 prompt versions used.]

═══════════════════════════════════════════════════════════════════
END DOSSIER | PRISM-[YYYY]-[N] | Generated by PRISM v0.1
═══════════════════════════════════════════════════════════════════
```

### Dossier Rendering Rules

- Use box-drawing characters: `═ ━ ─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ ▼ ▲ ► ◄ ● ○ ◆ ★ ☐ ☑ ⚠️`
- Signal timeline uses block characters for decay bars: `█ ▓ ▒ ░`
- Scores shown as tree structure with `├──` and `└──`
- Confidence tags: `[EXTRACTED]` = multi-source corroborated, `[INTERPOLATED]` = pattern-consistent single-source, `[GENERATED]` = plausible but unverified
- All contacts in Section 4 get approach/avoid recommendations
- Counter-signals in Section 6 are mandatory — if the system can't find any, note "No significant counter-signals detected" but flag this as unusual
- Section 8 must always have at least 3 discovery questions

---

## Fixture Data Format

Each demo company has a JSON file in `fixtures/companies/`:

```json
{
  "slug": "company_a",
  "company_name": "Example Corp",
  "domain": "example.com",
  "blog_url": "https://example.com/blog",
  "blog_rss": "https://example.com/blog/rss",

  "firmographics": {
    "founded_year": 2020,
    "headcount": 180,
    "headcount_growth_12mo": 0.34,
    "funding_stage": "Series B",
    "total_raised": 42000000,
    "last_round_amount": 28000000,
    "last_round_date": "2025-09-15",
    "last_round_lead": "Sequoia Capital",
    "industry": "SaaS",
    "hq_location": "San Francisco, CA",
    "description": "B2B payments platform for scaling SaaS companies"
  },

  "tech_stack": {
    "erp_accounting": "QuickBooks Online",
    "crm": "HubSpot",
    "payment_processor": "Stripe",
    "cloud_provider": "AWS",
    "primary_languages": ["TypeScript", "Python"],
    "stack_maturity": "early",
    "migration_signals": ["Job posting references NetSuite evaluation"]
  },

  "contacts": [
    {
      "name": "Jane Smith",
      "title": "VP Finance",
      "linkedin_url": "https://linkedin.com/in/janesmith",
      "start_date_current_role": "2025-11-01",
      "previous_company": "Stripe",
      "previous_title": "Senior Controller",
      "buying_role": "champion",
      "linkedin_posts": [
        {
          "date": "2026-02-08",
          "text": "Full text of LinkedIn post about automating finance..."
        }
      ]
    }
  ],

  "signals": [
    {
      "signal_type": "funding_round",
      "description": "$28M Series B closed",
      "source": "Crunchbase",
      "detected_date": "2025-09-15"
    },
    {
      "signal_type": "new_executive_finance",
      "description": "VP Finance hired from Stripe",
      "source": "LinkedIn",
      "detected_date": "2025-11-01"
    }
  ],

  "additional_content": [
    {
      "source_type": "job_posting",
      "title": "Senior Accountant",
      "date": "2026-02-14",
      "text": "Full text of job posting..."
    },
    {
      "source_type": "press",
      "title": "Example Corp Raises $28M Series B",
      "date": "2025-09-16",
      "url": "https://techcrunch.com/...",
      "text": "Full text of press release..."
    }
  ]
}
```

---

## LLM Service (services/llm.py)

### Requirements

- Use **anthropic** Python SDK
- Model: `claude-sonnet-4-20250514` for all stages (cost-efficient for Phase 0)
- All calls return structured JSON — use system prompts that end with `OUTPUT FORMAT: JSON` and specify exact schema
- Implement retry with exponential backoff (3 retries, 1s/2s/4s)
- Track and log token usage per call and cumulative per company
- Strip markdown code fences from responses before JSON parsing
- Handle JSON parse failures gracefully — log the raw response, return None, mark analysis as failed

### Cost Tracking

Log per-company: total input tokens, total output tokens, estimated cost, number of API calls. Print summary after each company analysis.

---

## Blog Scraper (services/scraper.py)

### Requirements

- Try RSS feed first (check `blog_rss` in fixture, or try common paths: `/feed`, `/rss`, `/blog/feed`, `/blog/rss.xml`)
- Fallback to HTML scraping with BeautifulSoup
- Extract: title, author, publish date, full text content (strip HTML tags, nav, footer, sidebar)
- Handle pagination (follow "next page" / "older posts" links, max 5 pages)
- Cache scraped content to `fixtures/scraped_content/<slug>/` so we don't re-scrape
- Respect robots.txt (check before scraping)
- User-Agent: `PRISM/0.1 (research; +https://github.com/Aurnix/prism)`
- Rate limit: 1 request per second per domain
- Timeout: 10 seconds per request
- If scraping fails entirely, log warning and continue with fixture content only

---

## Scoring Engine (analysis/scoring.py)

### ICP Fit Scoring

Each component returns 0.0-1.0 based on scoring logic defined in `PRISM_Scoring_Weights_v1.md`. Key mappings:

**funding_stage_fit:**
- Series B: 1.0 | Series C: 0.95 | Series A (>$5M): 0.70 | Series D: 0.50 | Seed (>$2M): 0.30 | Pre-seed/Bootstrapped: 0.10 | Public: 0.20

**growth_rate:**
- >50% YoY: 1.0 | 30-50%: 0.85 | 15-30%: 0.60 | 5-15%: 0.35 | Flat/declining: 0.10

**tech_stack_fit:**
- QuickBooks/Xero + >100 employees: 1.0 | +50-100: 0.85 | Spreadsheets/manual: 0.90 | Early NetSuite: 0.70 | Established NetSuite: 0.30 | SAP/Oracle: 0.10 | Unknown: 0.50
- Migration signal boost: +0.20 (capped at 1.0)

**headcount_fit:**
- 100-300: 1.0 | 50-100: 0.85 | 300-500: 0.75 | 30-50: 0.40 | 500-1000: 0.35 | <30: 0.10 | >1000: 0.15

**industry_fit:**
- SaaS: 1.0 | Fintech: 0.95 | E-commerce/Marketplace: 0.90 | B2B Services: 0.75 | Healthcare: 0.70 | Other tech: 0.60 | Non-tech: 0.30

**geo_fit:**
- US major tech hubs: 1.0 | US other: 0.90 | Canada: 0.80 | UK/Western Europe: 0.60 | Other English: 0.50 | Non-English: 0.30

### Buying Readiness Scoring

Components `journey_position`, `pain_coherence`, `org_stress_indicators`, `solution_sophistication` are derived from Stage 2 Content Intelligence output. The LLM returns numeric scores (0.0-1.0) as part of its structured JSON output. Pass these through directly.

`new_leader_signal` scoring:
- 30-120 days in role: 1.0 | <30 days: 0.60 | 120-180 days: 0.70 | 180-365 days: 0.35 | No new leader: 0.0

`active_evaluation_signals` — derived from signals list and content analysis. Multiple direct eval signals: 1.0 | Single strong signal: 0.75 | Indirect signals: 0.45 | None detected: 0.0

### Composite Score

```python
composite = (
    icp_fit_score      * COMPOSITE_WEIGHTS["icp_fit"] +
    readiness_score    * COMPOSITE_WEIGHTS["buying_readiness"] +
    timing_score       * COMPOSITE_WEIGHTS["timing"]
)
```

Tier assignment based on TIER_THRESHOLDS.

---

## Graceful Degradation

When data is missing (and it will be):

| Condition | Behavior |
|-----------|----------|
| No blog content found | Skip Stages 1-2, produce brief from firmographic/signal data only. Flag "LIMITED ANALYSIS — no public content corpus" |
| No LinkedIn posts for a contact | Score with role/tenure only. Flag "Person-level analysis unavailable" |
| Corpus < 5 items or < 2 months | Run analysis but auto-set confidence to LOW |
| LLM API failure | Log error, mark stage as failed, produce partial brief with available data |
| Blog scrape fails | Fall back to fixture content only |
| JSON parse failure on LLM response | Log raw response, retry once, if still fails mark stage as failed |

Never crash. Always produce output, even if degraded. The quality of degradation handling is itself a demonstration of engineering maturity.

---

## CLI Interface

```bash
# Analyze a single company
python -m prism.cli analyze company_a

# Analyze all companies in fixtures/
python -m prism.cli analyze-all

# List available companies
python -m prism.cli list

# Show scoring weights
python -m prism.cli weights

# Estimate cost before running
python -m prism.cli estimate company_a
```

Use **Rich** for output formatting:
- Progress bar during analysis
- Colored tier indicators (Tier 1 = red/urgent, Tier 2 = yellow, Tier 3 = blue)
- Token usage summary after each company
- Total cost estimate at end of batch run

---

## Testing Strategy

### What to Test

1. **Signal decay function** — Unit tests with known dates, verify decay curves match expected values
2. **Scoring engine** — Unit tests with fixture accounts, verify score calculations and tier assignments
3. **Dossier renderer** — Verify all sections are present, no empty sections, proper formatting
4. **JSON parsing** — Test handling of malformed LLM responses
5. **Graceful degradation** — Test with intentionally sparse fixture data

### What NOT to Test (Phase 0)

- LLM output quality (evaluated manually by reading dossiers)
- Blog scraper against live websites (too fragile for CI)
- End-to-end pipeline (manual evaluation)

---

## Code Style & Conventions

- Type hints everywhere. Use `Optional[X]` for nullable fields.
- Docstrings on all public functions (Google style)
- f-strings for string formatting
- `pathlib.Path` for file operations, not `os.path`
- Logging via `logging` module, not `print()` (except Rich console output in CLI)
- Constants in SCREAMING_SNAKE_CASE
- Classes in PascalCase
- Functions and variables in snake_case
- All config values in `config.py`, never hardcoded in functions
- Prompts in separate `.txt` files, never inline in Python code

---

## Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...
PRISM_MODEL=claude-sonnet-4-20250514
PRISM_PROMPT_VERSION=v1
PRISM_MAX_CORPUS_ITEMS=30
PRISM_MAX_PERSON_POSTS=20
PRISM_LOG_LEVEL=INFO
```

---

## Build Order (Suggested Sequence)

1. **Project setup** — pyproject.toml, directory structure, .env, .gitignore
2. **Data models** — All Pydantic models in `models/`
3. **Config** — All weights, thresholds, decay config in `config.py`
4. **Signal decay engine** — `analysis/signal_decay.py` + tests
5. **Scoring engine** — `analysis/scoring.py` + tests (can test with fixture data before LLM is integrated)
6. **Fixture loader** — `data/loader.py` to read company JSON files
7. **LLM service** — `services/llm.py` with Claude API wrapper, retry, cost tracking
8. **Prompt files** — Write all prompts in `prompts/v1/`
9. **Content Intelligence chain** — `analysis/content_intel.py` (Stage 1 → 2 → 3 → 4)
10. **Blog scraper** — `services/scraper.py` (can run independently to populate fixture cache)
11. **Dossier renderer** — `output/dossier.py`
12. **CLI** — `cli.py` tying everything together
13. **Integration test** — Run one company end-to-end, verify dossier output
14. **Remaining fixture data** — Fill in remaining demo companies
15. **Run full batch** — Generate all dossiers, manual quality review

---

## Success Criteria

A successful Phase 0 produces dossiers that pass these tests:

1. **Plausibility:** Would a human reading the company's blog reach similar conclusions?
2. **Non-obvious insight:** Does the analysis surface something not immediately apparent?
3. **Actionability:** Could a sales rep actually use the recommended angle in a real call?
4. **Calibration:** Do confidence scores feel right? (High for rich data, low for sparse)
5. **Counter-signals:** Does the system identify legitimate counter-arguments?

Target: 7-8 out of 10 companies produce genuinely useful analysis.

---

## Reference Documents

These files contain additional detail referenced by this CLAUDE.md:

- `docs/PRISM_Build_Plan_v01.md` — Full Phase 0 architecture spec with all Pydantic schemas, prompt templates, cost modeling
- `docs/PRISM_Scoring_Weights_v1.md` — Complete scoring weight documentation with rationale for every weight
- `docs/PRISM_Demo_Product_Ledgerflow.md` — Fictional product definition, ICP, buyer personas, competitive landscape
- `docs/V1_BUILD_PLAN.md` — **v1 architecture specification** with full interface definitions (LLMBackend, Database schema, DAL, Enrichment services, API layer, task queue)
- `V1_ROADMAP.md` — Phase-by-phase build order with timeline estimates

For Phase 0, this CLAUDE.md is the source of truth. For v1 architecture, `docs/V1_BUILD_PLAN.md` is the source of truth.

---

## Important Notes

- **This is a portfolio piece** demonstrating the Content Intelligence layer concept. The dossier quality IS the demo. Every architectural shortcut is acceptable as long as the dossiers look impressive and the analysis is genuinely insightful.
- **The blog scraper is secondary.** If scraping is difficult for a company, just manually paste content into fixture files. The LLM analysis chain is what matters.
- **Cost should stay under $10 total** for analyzing 10 companies. Track token usage carefully.
- **The internal codename is PRISM.** The public-facing name (if this becomes a product) is TBD. Use PRISM everywhere in code and output.
- **Prompt iteration is expected.** The v1 prompts are starting points. After seeing initial output, prompts will be refined. The prompt versioning system exists for this reason. Don't get precious about v1 — get it working, then iterate.
