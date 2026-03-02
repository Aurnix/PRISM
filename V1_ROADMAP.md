# PRISM v1 Roadmap — From Portfolio Demo to Operational Tool

**Current state:** v1 Phases 1-7 complete. 213 tests passing. Phases 8-9 pending.
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

## Phase 1: Foundation — COMPLETE

**Goal:** Prepare the codebase for v1 by building the swappable LLM interface, migrating to true async, and setting up dev infrastructure.

### Tasks

- [x] **LLMBackend ABC** — `prism/services/llm_backend.py` with `LLMBackend` abstract class, `LLMResponse` dataclass, `TokenBudget` tracker
- [x] **AnthropicBackend** — `prism/services/backends/anthropic_backend.py` using `anthropic.AsyncAnthropic` (true async)
- [x] **LocalInferenceBackend** — `prism/services/backends/local_backend.py` using `httpx.AsyncClient` against OpenAI-compatible API
- [x] **ModelRouter** — `prism/services/backends/router.py` for mixed-model strategies
- [x] **Rewire content_intel.py** — Accepts `LLMBackend` instead of `LLMService`
- [x] **Shared pipeline** — Extracted orchestration from `cli.py` into `prism/pipeline.py`
- [ ] **docker-compose.dev.yml** — PostgreSQL + Redis for local development
- [x] **Unit tests** — 33 tests for LLMBackend interface, mock backends, budget enforcement

### Design decisions

- Keep `services/llm.py` as legacy for backward compatibility during migration. Remove once all callers use LLMBackend.
- Click CLI stays synchronous (calls `asyncio.run()`). Service/analysis layers are fully async.
- `response_format="json"` is a hint, not a guarantee. Callers must still validate and handle parse failures.
- Budget enforcement is per-backend. Local inference backends set cost to $0 but track token counts.

---

## Phase 2: Persistence Layer — COMPLETE

**Goal:** Persistent storage for all data. Everything else depends on this.

### Tasks

- [x] Add dependencies: `sqlalchemy[asyncio]>=2.0`, `alembic`, `asyncpg`
- [x] **SQLAlchemy models** — `prism/db/models.py` with ORM models for all 9 tables using `Mapped[]` annotations
- [x] **Async session factory** — `prism/db/session.py` with `create_async_engine`, `async_sessionmaker`
- [ ] **Alembic setup** — `alembic init`, first migration creating all 9 tables (using `init-db` for now)
- [x] **DAL interface** — `prism/data/dal.py` with full abstract interface:

  **Account operations:** `get_account(slug)`, `get_account_by_id(id)`, `get_account_by_domain(domain)`, `list_accounts(status, limit, offset)`, `upsert_account()`, `update_account_status()`

  **Contact operations:** `get_contacts(account_id)`, `upsert_contact()`, `add_linkedin_posts()`

  **Signal operations:** `get_signals(account_id, signal_types?)`, `add_signals()`, `get_signals_by_type()`

  **Content operations:** `get_content(account_id, source_type?, limit)`, `add_content()`, `get_content_by_url()`, `update_content_status()`

  **Analysis operations:** `create_analysis()`, `update_analysis()` (checkpoint saving), `get_latest_analysis()`, `get_analysis_history()`

  **Dossier operations:** `save_dossier()`, `get_dossier()`, `get_latest_dossier()`

  **Raw response operations:** `write_raw_response()`, `get_raw_response()`

  **Enrichment log:** `log_enrichment()`

  **Scheduler queries:** `get_accounts_for_reanalysis()`, `get_stale_accounts()`

- [x] **DatabaseDAL** — `prism/data/database_dal.py` implementing all operations with PostgreSQL via async SQLAlchemy
- [x] **FixtureDAL** — `prism/data/fixture_dal.py` wrapping existing `data/loader.py` (read-only, write methods raise `NotImplementedError`)
- [x] **DAL factory** — `get_dal()` in `prism/data/__init__.py` returns DatabaseDAL or FixtureDAL based on `DATABASE_URL` config
- [x] **Pydantic ↔ SQLAlchemy mapping** — Bidirectional conversion functions in `prism/db/converters.py`
- [x] **`prism seed` CLI command** — Loads all fixture JSON into PostgreSQL via DAL
- [x] **Shared pipeline** — Extracted from `cli.py` into `prism/pipeline.py` (done in Phase 1)
- [x] **Unit tests** — DB model, converter, DAL tests (FixtureDAL + interface contract)

### Design decisions

- Database-first: all writes go through the DAL. Fixtures are seed data only.
- Don't use SQLModel (rough edges with async). Separate Pydantic and SQLAlchemy models.
- All conversion functions live in `prism/db/converters.py` — not scattered across models.

---

## Phase 3: API Layer — COMPLETE

**Goal:** REST API replaces CLI as primary interface.

### Tasks

- [x] Add dependencies: `fastapi>=0.110`, `uvicorn[standard]`
- [x] **FastAPI app** — `prism/api/__init__.py` with app factory, middleware, CORS
- [x] **Dependency injection** — `prism/api/deps.py` with DB session, auth, LLM backend injection
- [x] **Routes:**

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

- [x] **X-API-Key auth** — Header-based auth via `verify_api_key` dependency
- [x] **Budget enforcement** — `LLM_MAX_SPEND_USD` config in TokenBudget
- [ ] **Checkpoint saving** — Analysis pipeline persists after each stage (architecture ready, needs DB integration)
- [x] **Request/response schemas** — `prism/api/schemas.py` with Pydantic models for all endpoints
- [x] **Error handling** — Structured error responses, soft failover
- [x] **Unit tests** — 9 route tests with TestClient

---

## Phase 4: Extraction Pipeline — COMPLETE

**Goal:** Transform raw HTML into structured signals and content. This is the bridge between data collection and the Content Intelligence chain.

**Reference:** `docs/PRISM_Extraction_Schema_v1.md` is the authoritative spec.

### Tasks

- [x] **ExtractionResult Pydantic model** — `prism/models/extraction.py` with full schema:
  - `page_classification` (page_type, content_category, relevance)
  - `content` (title, author, publish_date, body_text, word_count)
  - `tech_signals` with per-signal typed_data (discriminated unions)
  - `signals` with typed_data varying by signal_type
  - `entities_mentioned`
  - `extraction_notes`
- [x] **Signal typed_data schemas** — 9 Pydantic models: FundingRoundData, RevenueData, JobPostingData, KeyHireData, TechDetectedData, TechMigrationData, LeadershipChangeData, CompetitorMentionData, ContentRemovedData
- [x] **Signal taxonomy mapping** — `map_signal_type()` with `EXTRACTION_TO_SCORING_TYPE` dict
- [x] **Multi-path preprocessing:**
  - Path B: HTML parser with BeautifulSoup (nav/footer/script removal, meta extraction)
  - Path C: Pattern library (~25 tech fingerprints) for zero-cost tech detection
  - Path A (trafilatura): architecture ready, not yet wired
- [ ] **Extraction LLM prompt** — `prism/prompts/v1/extraction.txt` (not yet created)
- [x] **Extraction service** — `prism/services/extraction.py` with preprocessing → LLM extraction → structured output
- [ ] **Deduplication rules** — Per signal type (architecture ready in DAL)
- [ ] **Derived signal generation** — hiring_burst, hiring_freeze, tech_added/removed, topic_shift (deferred)
- [x] **Unit tests** — 27 tests covering extraction models, tech detection, HTML preprocessing, signal mapping

---

## Phase 5: Collection — COMPLETE

**Goal:** Live data flowing into the system. Collection-first — own the data pipeline.

### Tier 1 — Do first (highest value, no API keys needed)

- [ ] **Blog scraper hardening** (upgrade existing `services/scraper.py`)
  - Replace BeautifulSoup content extraction with `trafilatura`
  - Add Playwright fallback for JS-rendered blogs
  - Add cache TTL — re-scrape if cache older than 7 days
  - Wire through extraction pipeline for signal extraction
- [x] **Job board scrapers** (`prism/services/enrichment/job_boards.py`)
  - Greenhouse API: `https://boards-api.greenhouse.io/v1/boards/{company}/jobs`
  - Lever API: `https://api.lever.co/v0/postings/{company}`
  - Finance/accounting hire auto-detection → signals
  - Full job posting text stored as content_items
- [ ] **Press/funding scrapers** — Basic Google News / press release detection

### Enrichment orchestrator

- [x] **Enrichment interface** — `prism/services/enrichment/base.py` with `EnrichmentSource` ABC + `EnrichmentResult`
- [x] **Blog scraper adapter** — `prism/services/enrichment/blog_scraper.py` wrapping existing scraper
- [x] **Job board adapter** — `prism/services/enrichment/job_boards.py` implementing `EnrichmentSource`
- [x] **Orchestrator** — `prism/services/enrichment/orchestrator.py` running all available sources
- [x] Each source is optional — `is_available()` check, skip gracefully
- [x] Failure isolation — individual source failures don't block other sources
- [x] **Unit tests** — 16 tests for enrichment interface, job board processing, orchestrator

---

## Phase 6: Enrichment — PARTIALLY COMPLETE

**Goal:** Third-party data supplements collection. These are optional — system works without them.

### Tasks

- [x] **Apollo API** (`prism/services/enrichment/apollo.py`)
  - Contact discovery: name, title, LinkedIn URL, email
  - Company firmographics: headcount, funding, industry
  - New hire detection from employment history
- [ ] **Tech stack detection** (`prism/services/enrichment/builtwith.py`)
  - BuiltWith API integration (pattern library already in extraction pipeline)
- [ ] **Crunchbase** (optional, $499/mo or RapidAPI alternatives)
- [ ] **Proxycurl** ($0.01/profile for LinkedIn content)
- [x] Wire Apollo into enrichment orchestrator
- [x] **Unit tests** — Apollo availability check, source name verification

---

## Phase 7: Task Queue & Scheduling — COMPLETE

**Goal:** Background processing. Can't run 200 companies synchronously.

### Tasks

- [x] **Task functions** in `prism/tasks.py`:
  - `enrich_company_task(slug)` — Run all enrichment sources
  - `analyze_company_task(slug)` — Full Content Intelligence chain + scoring
  - `generate_dossier_task(slug)` — Render and persist dossier
  - `full_pipeline_task(slug)` — Enrich → analyze → dossier
- [x] **Scheduled jobs:**
  - `daily_reanalyze()` — Re-analyze accounts with signals < 7 days old
  - `weekly_scrape()` — Re-scrape blog content for all tracked accounts
- [x] **arq WorkerSettings** — Ready for `arq prism.tasks.WorkerSettings` deployment
- [x] **In-process fallback** — All tasks callable directly without Redis
- [ ] **Centralized rate limiter** — Generalize per-domain limiter from scraper.py
- [x] **Cost tracking** — TokenBudget enforcement in LLMBackend, `LLM_MAX_SPEND_USD` config
- [x] **Unit tests** — 8 tests for task imports, worker settings, enrich/analyze/dossier execution

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
