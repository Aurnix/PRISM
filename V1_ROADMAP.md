# PRISM v1 Roadmap — From Portfolio Demo to Operational Tool

**Current state:** Phase 0. CLI-only, fixture-driven, 10 demo companies, all analysis in-memory.
**v1 goal:** A system that takes a company domain, automatically gathers data, runs the Content Intelligence chain, persists everything, and serves dossiers through an API — with scheduled re-analysis as new signals appear.

**Shipping model:** Iterative. Each phase ships independently and provides value. Don't batch — deploy each phase as it's done.

**What survives unchanged into v1:** scoring engine, signal decay, content intelligence chain, dossier renderer, prompt templates, all Pydantic models (become API schemas).

**What gets refactored:** `services/llm.py` (→ LLMBackend ABC), `data/loader.py` (→ FixtureDAL), `cli.py` (stays as dev tool, API becomes primary), `analysis/content_intel.py` (LLMService → LLMBackend dependency).

**Data strategy:** Collection-first. Own the data pipeline (blog scraping, job board scraping, press scraping) before depending on third-party enrichment APIs (Apollo, Crunchbase). PRISM's value is Content Intelligence, not enrichment data.

---

## Authoritative Database Schema — 9 Tables

This is the single source of truth. See `docs/V1_BUILD_PLAN.md` for full SQL definitions.

```
RAW LAYER:
  raw_responses         — HTTP response audit trail, append-only (enables reprocessing)

NORMALIZED LAYER:
  accounts              — One row per company
  contacts              — One row per person (FK → accounts)
  linkedin_posts        — One row per post (FK → contacts)
  content_items         — Blog posts, job postings, press releases (FK → accounts)
  signals               — Append-only observations with typed_data JSONB (FK → accounts)

ANALYSIS LAYER:
  analyses              — One row per analysis run, full stage results as JSONB
  dossiers              — Rendered markdown output (FK → analyses)

AUDIT:
  enrichment_log        — Tracks every enrichment attempt per source
```

### Key schema design decisions

- **`raw_responses` exists** for reprocessing. When extraction prompts improve, re-run against stored raw HTML without re-fetching.
- **`linkedin_posts` is a separate table** (not in `content_items`) because the Content Intelligence chain Stage 3 requires per-person content linked to contacts. A separate table preserves the `contact_id` FK.
- **`signals` has `typed_data` JSONB** with schema varying by signal type (discriminated unions in Pydantic). See `docs/PRISM_Extraction_Schema_v1.md` for per-type schemas.
- **`enrichment_log` exists** for debugging and audit. Every enrichment attempt (success or failure) is logged.
- All tables use UUID primary keys. No auto-increment integers in URLs.
- `content_items` and `signals` are append-only. Decay handles relevance naturally.

### Signal type taxonomy

Phase 0 signal types (`new_executive_finance`, `job_posting_finance`, etc.) coexist with extraction pipeline types (`key_hire`, `job_posting`, `tech_detected`, etc.) in a unified enum. A mapping layer converts extraction types to scoring types. The scoring engine ignores types it doesn't use. `SIGNAL_DECAY_CONFIG` in `config.py` is extended for new types.

---

## Phase 1: Foundation

**Goal:** Prepare the codebase for v1 by building the swappable LLM interface, migrating to true async, and setting up dev infrastructure.

### Tasks

- [ ] **LLMBackend ABC** — Create `prism/services/llm_backend.py` with `LLMBackend` abstract class (`query_json`, `query_text`, `get_budget`), `LLMResponse` dataclass, `TokenBudget` tracker
- [ ] **AnthropicBackend** — Implement `prism/services/backends/anthropic_backend.py` using `anthropic.AsyncAnthropic` (true async, not `asyncio.to_thread`)
- [ ] **LocalInferenceBackend** — Implement `prism/services/backends/local_backend.py` using `httpx.AsyncClient` against OpenAI-compatible API endpoint
- [ ] **ModelRouter** — Optional `prism/services/backends/router.py` for mixed-model strategies (Haiku for extraction, Sonnet for CI chain)
- [ ] **Rewire content_intel.py** — Change `ContentIntelligenceChain.__init__` to accept `LLMBackend` instead of `LLMService`. Update all stage functions.
- [ ] **docker-compose.dev.yml** — PostgreSQL + Redis for local development
- [ ] **Test infrastructure** — `pytest-postgresql` or `testcontainers-python` for DB tests. No SQLite — it can't handle UUID/JSONB/ENUM/arrays.
- [ ] **Unit tests** — LLMBackend interface tests with mock backends, budget enforcement tests, retry logic tests

### Design decisions

- Keep `services/llm.py` as legacy for backward compatibility during migration. Remove once all callers use LLMBackend.
- Click CLI stays synchronous (calls `asyncio.run()`). Service/analysis layers are fully async.
- `response_format="json"` is a hint, not a guarantee. Callers must still validate and handle parse failures.
- Budget enforcement is per-backend. Local inference backends set cost to $0 but track token counts.

---

## Phase 2: Persistence Layer

**Goal:** Persistent storage for all data. Everything else depends on this.

### Tasks

- [ ] Add dependencies: `sqlalchemy[asyncio]>=2.0`, `alembic`, `asyncpg`
- [ ] **SQLAlchemy models** — `prism/db/models.py` with ORM models for all 9 tables. Use `Mapped[]` annotations (SQLAlchemy 2.0 style).
- [ ] **Async session factory** — `prism/db/session.py` with `create_async_engine`, `async_sessionmaker`
- [ ] **Alembic setup** — `alembic init`, first migration creating all 9 tables
- [ ] **DAL interface** — `prism/data/dal.py` with full abstract interface:

  **Account operations:** `get_account(slug)`, `get_account_by_id(id)`, `get_account_by_domain(domain)`, `list_accounts(status, limit, offset)`, `upsert_account()`, `update_account_status()`

  **Contact operations:** `get_contacts(account_id)`, `upsert_contact()`, `add_linkedin_posts()`

  **Signal operations:** `get_signals(account_id, signal_types?)`, `add_signals()`, `get_signals_by_type()`

  **Content operations:** `get_content(account_id, source_type?, limit)`, `add_content()`, `get_content_by_url()`, `update_content_status()`

  **Analysis operations:** `create_analysis()`, `update_analysis()` (checkpoint saving), `get_latest_analysis()`, `get_analysis_history()`

  **Dossier operations:** `save_dossier()`, `get_dossier()`, `get_latest_dossier()`

  **Raw response operations:** `write_raw_response()`, `get_raw_response()`

  **Enrichment log:** `log_enrichment()`

  **Scheduler queries:** `get_accounts_for_reanalysis()`, `get_stale_accounts()`

- [ ] **DatabaseDAL** — `prism/data/database_dal.py` implementing all operations with PostgreSQL via async SQLAlchemy
- [ ] **FixtureDAL** — `prism/data/fixture_dal.py` wrapping existing `data/loader.py` (read-only, write methods raise `NotImplementedError`)
- [ ] **DAL factory** — `get_dal()` in `prism/data/__init__.py` returns DatabaseDAL or FixtureDAL based on `DATABASE_URL` config
- [ ] **Pydantic ↔ SQLAlchemy mapping** — Bidirectional conversion functions in `prism/db/converters.py` for all model types. Handle nested models (e.g., `AnalyzedAccount` → JSONB columns).
- [ ] **`prism seed` CLI command** — Loads all fixture JSON into PostgreSQL via DAL
- [ ] **Shared pipeline** — Extract analysis orchestration from `cli.py` into `prism/pipeline.py`. CLI and API both call it.
- [ ] **Unit tests** — DAL tests with `pytest-postgresql`, covering all CRUD operations, upsert behavior, duplicate handling, and edge cases (missing data, null fields)

### Design decisions

- Database-first: all writes go through the DAL. Fixtures are seed data only.
- Don't use SQLModel (rough edges with async). Separate Pydantic and SQLAlchemy models.
- All conversion functions live in `prism/db/converters.py` — not scattered across models.

---

## Phase 3: API Layer

**Goal:** REST API replaces CLI as primary interface.

### Tasks

- [ ] Add dependencies: `fastapi>=0.110`, `uvicorn[standard]`, `pydantic-settings`
- [ ] **FastAPI app** — `prism/api/__init__.py` with app factory, middleware, CORS
- [ ] **Dependency injection** — `prism/api/deps.py` with DB session, auth, LLM backend injection
- [ ] **Routes:**

  | Method | Path | Purpose |
  |--------|------|---------|
  | `GET` | `/health` | Liveness + DB connection check |
  | `GET` | `/accounts` | List tracked companies with latest scores/tiers |
  | `POST` | `/accounts` | Add a company (domain + optional firmographics) |
  | `GET` | `/accounts/{slug}` | Full account detail with latest analysis |
  | `PATCH` | `/accounts/{slug}` | Update account data |
  | `DELETE` | `/accounts/{slug}` | Archive (soft delete) |
  | `POST` | `/accounts/{slug}/analyze` | Trigger analysis (returns job ID) |
  | `GET` | `/accounts/{slug}/analyses` | Analysis history |
  | `POST` | `/accounts/{slug}/content` | Upload content manually |
  | `GET` | `/accounts/{slug}/signals` | List signals with decay weights |
  | `GET` | `/dossiers/{dossier_id}` | Retrieve dossier by PRISM-YYYY-NNNN |
  | `GET` | `/accounts/{slug}/dossier` | Latest dossier for account |

- [ ] **X-API-Key auth** — Simple header-based auth. No JWT complexity in v1.
- [ ] **Budget enforcement** — `LLM_MAX_SPEND_USD` config, checked before each LLM call
- [ ] **Checkpoint saving** — Analysis pipeline persists results after each stage via `update_analysis()`. If Stage 4 fails, Stages 1-3 are saved.
- [ ] **Request/response schemas** — `prism/api/schemas.py` with Pydantic models for all endpoints
- [ ] **Error handling** — Structured error responses, soft failover (never crash, return degraded results)
- [ ] **Unit tests** — Route tests with `httpx.AsyncClient` + test DB

---

## Phase 4: Extraction Pipeline

**Goal:** Transform raw HTML into structured signals and content. This is the bridge between data collection and the Content Intelligence chain.

**Reference:** `docs/PRISM_Extraction_Schema_v1.md` is the authoritative spec.

### Tasks

- [ ] **ExtractionResult Pydantic model** — `prism/models/extraction.py` with full schema:
  - `page_classification` (page_type, content_category, relevance)
  - `content` (title, author, publish_date, body_text, word_count)
  - `tech_signals` with per-signal typed_data (discriminated unions)
  - `signals` with typed_data varying by signal_type
  - `entities_mentioned`
  - `extraction_notes`
- [ ] **Signal typed_data schemas** — Pydantic discriminated unions for each signal type:
  - Financial: `funding_round` (amount, currency, round_type, lead_investors), `revenue_milestone`, `pricing_change`
  - Hiring: `job_posting` (department, seniority, skills), `key_hire` (name, title, previous_company)
  - Technology: `tech_detected` (technology, category, evidence, version), `tech_migration`
  - Organizational: `leadership_change`, `partner_announced`, `acquisition`
  - Competitive: `competitor_mention`, `market_positioning`
  - Absence: `content_removed`, `page_status_change`
- [ ] **Signal taxonomy mapping** — Function to convert extraction signal types to Phase 0 scoring types. Extend `SIGNAL_DECAY_CONFIG` for new types.
- [ ] **Multi-path preprocessing:**
  - Path A: `trafilatura` for cleaned article text + metadata extraction
  - Path B: Lightweight HTML parser for `<head>`, scripts, meta tags, structured data
  - Path C: Pattern library in `config.py` (~50 tech fingerprints) for zero-cost tech detection
- [ ] **Extraction LLM prompt** — `prism/prompts/v1/extraction.txt` with input template and ExtractionResult schema
- [ ] **Extraction service** — `prism/services/extraction.py` that orchestrates: preprocessing → LLM call (Haiku-tier via LLMBackend) → validate ExtractionResult → write to DB
- [ ] **Deduplication rules** — Per signal type (e.g., funding_round dedupes on amount+date, job_posting dedupes on title+department)
- [ ] **Derived signal generation** — Detect composite signals from multiple extractions:
  - `hiring_burst`: 3+ job postings in 30 days
  - `hiring_freeze`: drop in posting frequency
  - `tech_added`/`tech_removed`: diff between scans
  - `topic_shift`: content theme change over time
- [ ] **Unit tests** — Extraction with fixture HTML pages, signal type validation, dedup logic, derived signal generation

---

## Phase 5: Collection

**Goal:** Live data flowing into the system. Collection-first — own the data pipeline.

### Tier 1 — Do first (highest value, no API keys needed)

- [ ] **Blog scraper hardening** (upgrade existing `services/scraper.py`)
  - Replace BeautifulSoup content extraction with `trafilatura`
  - Add Playwright fallback for JS-rendered blogs (many modern blogs are SPAs)
  - Add cache TTL — re-scrape if cache older than 7 days
  - Wire through extraction pipeline (Phase 4) for signal extraction
- [ ] **Job board scrapers** (`prism/services/enrichment/job_boards.py`)
  - Greenhouse API (public, no auth): `https://boards-api.greenhouse.io/v1/boards/{company}/jobs`
  - Lever API (public, no auth): `https://api.lever.co/v0/postings/{company}`
  - Auto-detect finance/accounting hires → create signals
  - Store full job posting text as content_items
- [ ] **Press/funding scrapers** — Basic Google News / press release detection

### Enrichment orchestrator skeleton

- [ ] **Enrichment interface** — `prism/services/enrichment/base.py` with `EnrichmentSource` ABC
- [ ] **Blog scraper adapter** — `prism/services/enrichment/blog_scraper.py` wrapping existing scraper
- [ ] **Job board adapter** — `prism/services/enrichment/job_boards.py` implementing `EnrichmentSource`
- [ ] **Orchestrator** — `prism/services/enrichment/orchestrator.py` running all available sources, merging results, persisting via DAL
- [ ] Each source is optional — if API key not configured, skip gracefully
- [ ] Idempotent: re-enriching updates existing records rather than creating duplicates
- [ ] **Unit tests** — Scraper tests with fixture HTML, job board response mocking, orchestrator integration tests

---

## Phase 6: Enrichment

**Goal:** Third-party data supplements collection. These are optional — system works without them.

### Tasks

- [ ] **Apollo API** (`prism/services/enrichment/apollo.py`)
  - Contact discovery: name, title, LinkedIn URL, email
  - Company firmographics: headcount, funding, industry
  - Free tier: 50 credits/mo, paid starts $49/mo
- [ ] **Tech stack detection** (`prism/services/enrichment/builtwith.py`)
  - BuiltWith API or own fingerprinting from pattern library (Phase 4)
  - Detect accounting/ERP tools → create tech_stack_fit signals
- [ ] **Crunchbase** (optional, $499/mo or RapidAPI alternatives)
- [ ] **Proxycurl** ($0.01/profile for LinkedIn content)
- [ ] Wire all sources into enrichment orchestrator
- [ ] **Unit tests** — API client mocking, response normalization, error handling

---

## Phase 7: Task Queue & Scheduling

**Goal:** Background processing. Can't run 200 companies synchronously.

### Tasks

- [ ] Add dependencies: `arq>=0.26`, `redis`
- [ ] **Task functions** in `prism/tasks.py`:
  - `enrich_company(slug)` — Run all enrichment sources
  - `scrape_blog(slug)` — Re-scrape blog content
  - `run_analysis(slug)` — Full Content Intelligence chain + scoring
  - `generate_dossier(slug)` — Render and persist dossier
  - `full_pipeline(slug)` — Enrich → scrape → extract → analyze → dossier
- [ ] **Job status tracking** — `analyses.status`: pending → running → complete | failed
- [ ] **Scheduled jobs:**
  - Daily: re-analyze accounts with signals < 7 days old
  - Weekly: re-scrape blog content for all tracked accounts
  - Monthly: full re-enrichment for all accounts
- [ ] **Centralized rate limiter** — Generalize per-domain limiter from scraper.py
- [ ] **Cost tracking** — Sum `estimated_cost_usd` per day, alert if approaching `LLM_MAX_SPEND_USD`
- [ ] **Unit tests** — Task function tests, scheduling logic, rate limiter

---

## Phase 8: Discovery Pipeline

**Goal:** Auto-find companies to analyze instead of manual entry.

### Tasks

- [ ] **ICP-based discovery** — Query enrichment APIs with ICP filters:
  - Series A–D, 50–500 employees, SaaS/fintech
  - Using QuickBooks/Xero (if detectable)
  - Recently funded (last 6 months)
- [ ] **Signal-triggered promotion** — Monitor broader watchlist for triggers:
  - New VP Finance hire → auto-promote to tracked
  - Funding round closed → auto-promote
  - Finance job posting → auto-promote
- [ ] **Scored watchlist** — Ranked by composite score. New signals push up, decay pulls down.
- [ ] `POST /accounts/discover` endpoint — Takes ICP criteria, returns candidates
- [ ] **Unit tests** — Discovery filter logic, promotion rules, watchlist scoring

---

## Phase 9: Frontend

**Goal:** Sales reps won't use CLI or API directly.

### Streamlit (ship first)

- [ ] Dashboard: company cards sorted by composite score, color-coded by tier
- [ ] Individual dossier view (rendered markdown)
- [ ] Signal timeline visualization
- [ ] Score trend over time (requires analysis history)
- [ ] Trigger analysis from UI

### Next.js (when Streamlit limits hit)

- [ ] Proper React frontend against FastAPI backend
- [ ] Comparison view (two companies side by side)
- [ ] Pipeline/kanban view for sales workflow
- [ ] Notification feed for new high-scoring signals

---

## LLM Service Upgrades (Parallel — Can be done alongside any phase)

- [ ] LLM response caching — keyed by `(slug, stage, input_hash)`, skip API call if cache hit
- [ ] Database logging of all LLM calls (prompt version, tokens, raw response)
- [ ] Model selection strategy — Haiku for extraction (cheaper), Sonnet for CI Stages 2–4 (smarter)

---

## Cost Model (Collection-First)

| Item | Monthly Cost | Notes |
|------|-------------|-------|
| Claude API | $15–60 | ~$0.15–0.30/company, 100–200 companies/month |
| Infrastructure | $50–100 | PostgreSQL + Redis + one VPS |
| **Tier 1 total** | **~$65–160/mo** | Collection-first, no third-party APIs |
| Apollo (Tier 2) | $49–149 | Added when contact discovery needed |
| Proxycurl (Tier 2) | $20–40 | Added when LinkedIn content needed |
| Crunchbase (Tier 3) | $50–499 | Added if own scrapers insufficient |
| **Full stack total** | **~$200–850/mo** | With all enrichment sources active |

---

## Engineering Standards

### Unit testing

- Every module gets comprehensive unit tests
- Use `pytest-postgresql` or `testcontainers-python` for DB tests — no SQLite (can't handle UUID/JSONB/arrays/ENUMs)
- Mock external APIs (Anthropic, Apollo, job boards) in tests
- Test graceful degradation paths (missing data, API failures, malformed responses)
- Target: every public function has tests, every error path is tested

### Error handling & soft failover

- **Never crash.** Every error is caught, logged, and produces degraded output rather than failure.
- External API failures → log warning, skip source, continue with available data
- LLM parse failures → retry once, if still fails mark stage as failed, continue with partial results
- Database write failures → log error, return error response, don't lose upstream computation
- Enrichment source failures → log to `enrichment_log`, skip source, other sources continue
- Rate limit hits → exponential backoff with configurable max retries
- Budget exhaustion → fail gracefully with clear message, preserve work done so far

### Observability

- Structured logging via Python `logging` module
- Token usage tracked per-company, per-stage, cumulative
- Cost tracking with daily summaries and budget alerts
- Enrichment success/failure rates logged to `enrichment_log`

---

## What NOT to Build in v1

Explicitly deferred to v2+:

- CRM export (Salesforce/HubSpot push)
- Feedback loop / recalibration engine
- Re-engagement monitor
- Multi-tenant / team management
- Email/Slack notifications
- Docker Compose for production (dev only)
- Webhook callbacks (polling is fine for v1)

---

## Success Criteria for v1

1. **Add a company by domain** → system auto-enriches and scrapes within 60 seconds
2. **Blog content scraped automatically** for any company with a real blog
3. **Full analysis pipeline** runs end-to-end and persists results to database
4. **API serves dossiers** — a frontend or script can fetch the latest dossier
5. **Scheduled re-analysis** — companies re-scored weekly as signals appear/decay
6. **Cost stays under $500/mo** for 100 companies
7. **Dossier quality** — 7/10 produce genuinely useful, non-obvious insights (same bar as Phase 0, real data)
8. **Comprehensive test coverage** — every module has unit tests, every error path is tested
9. **Zero crashes** — all failures produce degraded output, never unhandled exceptions

---

## Phase Dependencies

```
Phase 1 (Foundation) ──→ Phase 2 (Persistence) ──→ Phase 3 (API)
                                    │                     │
                                    ▼                     ▼
                          Phase 4 (Extraction) ──→ Phase 5 (Collection)
                                                          │
                                                          ▼
                                                  Phase 6 (Enrichment)
                                                          │
                          Phase 3 (API) ──────────→ Phase 7 (Task Queue)
                                                          │
                                                          ▼
                                                  Phase 8 (Discovery)
                                                          │
                          Phase 3 (API) ──────────→ Phase 9 (Frontend)
```

LLM Service Upgrades can be done in parallel with any phase.
