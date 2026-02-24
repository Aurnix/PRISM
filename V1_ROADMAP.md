# PRISM v1 Roadmap — From Portfolio Demo to Operational Tool

**Current state:** Phase 0. CLI-only, fixture-driven, 10 demo companies, all analysis in-memory.
**v1 goal:** A system that takes a company domain, automatically gathers data, runs the Content Intelligence chain, persists everything, and serves dossiers through an API — with scheduled re-analysis as new signals appear.

**What survives unchanged into v1:** scoring engine, signal decay, content intelligence chain, dossier renderer, prompt templates, all Pydantic models (become API schemas).

**What gets replaced:** `data/loader.py` (fixture-only → DB+fixtures), `cli.py` (stays as dev tool, API becomes primary interface).

---

## Phase 1: Persistence Layer (Week 1–2)

The foundation. Everything else depends on storing and querying data.

### Tasks

- [ ] Add dependencies: `sqlalchemy[asyncio]>=2.0`, `alembic`, `asyncpg` (Postgres driver)
- [ ] Design database schema — 6 core tables:

| Table | Key Columns | Notes |
|-------|------------|-------|
| `accounts` | id, slug (unique), company_name, domain, firmographics (JSONB), tech_stack (JSONB) | Mirror of current Account model |
| `contacts` | id, account_id (FK), name, title, linkedin_url, buying_role, start_date_current_role | One row per person |
| `signals` | id, account_id (FK), signal_type, description, source, detected_date, confidence | Append-only — new signals added, old ones decay naturally |
| `content_items` | id, account_id (FK), source_type, url, title, author, publish_date, raw_text, word_count | Blog posts, LinkedIn posts, job postings, press |
| `analyses` | id, account_id (FK), status, prompt_version, stage1–4 results (JSONB), scores (JSONB), why_now, confidence, token usage, cost, started_at, completed_at | One row per analysis run — full history |
| `dossiers` | id, dossier_id (PRISM-YYYY-NNNN), account_id (FK), analysis_id (FK), markdown_content | Rendered output, linked to the analysis that produced it |

- [ ] Implement SQLAlchemy async models in `prism/db/models.py`
- [ ] Set up Alembic for migrations (`alembic init`, first migration)
- [ ] Create `prism/db/dal.py` (Data Access Layer) with async CRUD operations:
  - `get_account(slug)`, `upsert_account()`, `list_accounts()`
  - `get_contacts(account_id)`, `upsert_contact()`
  - `add_signal()`, `get_signals(account_id)`
  - `add_content_item()`, `get_content(account_id)`
  - `create_analysis()`, `update_analysis()`, `get_latest_analysis(account_id)`
  - `save_dossier()`, `get_dossier(dossier_id)`
- [ ] Add `DATABASE_URL` to config.py (default: `postgresql+asyncpg://localhost/prism`)
- [ ] Add `prism seed` CLI command — loads all fixture JSON into the database (replaces direct fixture reading for production use)
- [ ] Write DAL tests with in-memory SQLite (pytest fixtures for DB session)

### Design decision: Database-first
All writes go to the database. Fixtures remain as seed data only. CLI and API both read/write through the DAL. No sync conflicts.

---

## Phase 2: API Layer (Week 3–4)

Replace CLI as primary interface. The CLI stays as a power-user/dev tool.

### Tasks

- [ ] Add dependencies: `fastapi>=0.110`, `uvicorn[standard]`, `pydantic-settings`
- [ ] Create `prism/api/` package:

```
prism/api/
├── __init__.py          # FastAPI app factory
├── deps.py              # Dependency injection (DB session, auth)
├── schemas.py           # Request/response Pydantic models
├── routes/
│   ├── health.py        # GET /health
│   ├── accounts.py      # CRUD + analyze trigger
│   ├── content.py       # Manual content upload
│   └── dossiers.py      # Dossier retrieval
```

- [ ] Implement endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness + DB connection check |
| `GET` | `/accounts` | List tracked companies with latest scores/tiers |
| `POST` | `/accounts` | Add a company (domain + optional firmographics) |
| `GET` | `/accounts/{slug}` | Full account detail with latest analysis |
| `POST` | `/accounts/{slug}/analyze` | Trigger analysis (returns job ID) |
| `GET` | `/accounts/{slug}/analyses` | Analysis history |
| `POST` | `/accounts/{slug}/content` | Upload LinkedIn posts, job postings, press manually |
| `GET` | `/dossiers/{dossier_id}` | Retrieve rendered dossier |

- [ ] API key auth middleware (simple `X-API-Key` header for v1 — no JWT complexity yet)
- [ ] Add `LLM_MAX_SPEND_USD` config + enforcement in LLMService (fail gracefully if approaching limit)
- [ ] Wire analysis pipeline to persist results to DB after each stage (checkpoint saving — if Stage 4 fails after 30 min, Stage 1–3 results are already saved)
- [ ] Write route tests with `httpx.AsyncClient` + test DB

---

## Phase 3: Live Data Ingestion (Week 5–6)

Replace hand-entered fixtures with real data sources.

### Tier 1 — Do first (highest value)

- [ ] **Apollo API integration** (`prism/services/apollo.py`)
  - Contact discovery: name, title, LinkedIn URL, email
  - Company firmographics: headcount, funding, industry
  - Pricing: free tier = 50 credits/mo, paid starts $49/mo
  - Normalize responses into existing Pydantic models
- [ ] **Blog scraper hardening** (upgrade existing `scraper.py`)
  - Add Playwright fallback for JS-rendered blogs (many modern blogs are SPAs)
  - Add proxy rotation support (configurable, off by default)
  - Replace raw BeautifulSoup content extraction with `trafilatura` (much better at isolating article text)
  - Add cache TTL — re-scrape if cache older than 7 days
- [ ] **Job board scrapers** (`prism/services/job_boards.py`)
  - Greenhouse API (public, no auth needed)
  - Lever API (public, no auth needed)
  - Detect finance/accounting hires → auto-create `job_posting_finance` signals

### Tier 2 — After Tier 1 is stable

- [ ] **Crunchbase API** — Firmographics, funding rounds, acquisitions ($499/mo or cheaper alternatives via RapidAPI)
- [ ] **BuiltWith / Wappalyzer** — Automated tech stack detection
- [ ] **LinkedIn content** — Proxycurl API ($0.01/profile, gets recent posts) or manual upload via API endpoint

### Tier 3 — Nice-to-have

- [ ] Google News API / NewsAPI — Press releases, funding announcements
- [ ] G2/TrustRadius — Review site activity signals
- [ ] Glassdoor — Employee sentiment trends

### Enrichment orchestrator

- [ ] Create `prism/services/enrichment.py` — calls all available sources for a given domain, normalizes into models, persists to DB
- [ ] Idempotent: re-enriching updates existing records rather than creating duplicates
- [ ] Each source is optional — if API key not configured, skip gracefully

---

## Phase 4: Task Queue & Scheduling (Week 7)

You can't run 200 companies through the LLM chain synchronously.

### Tasks

- [ ] Add dependencies: `arq` (lightweight async task queue, simpler than Celery for early v1) + `redis`
- [ ] Define task functions:
  - `enrich_company(slug)` — Run all enrichment sources
  - `scrape_blog(slug)` — Re-scrape blog content
  - `run_analysis(slug)` — Full Content Intelligence chain + scoring
  - `generate_dossier(slug)` — Render and persist dossier
  - `full_pipeline(slug)` — Enrich → scrape → analyze → dossier (the common case)
- [ ] Background job status tracking — `analyses.status` field: pending → running → complete | failed
- [ ] Scheduled jobs (arq cron or APScheduler):
  - **Daily:** Re-analyze all accounts where newest signal is < 7 days old (active accounts)
  - **Weekly:** Re-scrape blog content for all tracked accounts
  - **Monthly:** Re-enrich firmographics for all accounts (catch funding rounds, headcount changes)
- [ ] Centralized rate limiter across all API calls (generalize the per-domain limiter from scraper.py)
- [ ] Cost tracking: sum `estimated_cost_usd` per day, alert if approaching `LLM_MAX_SPEND_USD`

---

## Phase 5: Discovery Pipeline (Week 8)

Phase 0 requires knowing which companies to analyze. v1 should find them.

- [ ] **ICP-based discovery** — Query Apollo/Crunchbase with ICP filters:
  - Series A–D, 50–500 employees, SaaS/fintech
  - Using QuickBooks/Xero (if detectable via BuiltWith)
  - Recently funded (last 6 months)
- [ ] **Signal-triggered promotion** — Monitor for trigger events across a broader watchlist:
  - New VP Finance hire → auto-promote to tracked
  - Funding round closed → auto-promote
  - Job posting for "Senior Accountant" or "Controller" → auto-promote
- [ ] **Scored watchlist** — Ranked by composite score. New signals push companies up, decay pulls them down. Top N surface for action.
- [ ] `POST /accounts/discover` endpoint — Takes ICP criteria, returns candidate companies with preliminary scores

---

## Phase 6: Frontend (Week 9–10)

Sales reps won't use a CLI.

### Start with Streamlit (fastest path)

- [ ] Dashboard: company cards sorted by composite score, color-coded by tier
- [ ] Individual dossier view (rendered markdown)
- [ ] Signal timeline visualization
- [ ] Score trend over time (requires analysis history)
- [ ] Trigger analysis from UI

### Then Next.js (when Streamlit limits hit)

- [ ] Proper React frontend against the FastAPI backend
- [ ] Comparison view (two companies side by side)
- [ ] Pipeline/kanban view for sales workflow
- [ ] Notification feed for new high-scoring signals

---

## LLM Service Upgrades (Parallel — Anytime)

These improvements to `services/llm.py` can be done alongside any phase:

- [ ] Switch from `asyncio.to_thread(sync_client)` to `anthropic.AsyncAnthropic` (true async)
- [ ] Add LLM response caching — keyed by `(slug, stage, input_hash)`, skip API call if cache hit
- [ ] Add database logging of all LLM calls (prompt version, tokens, raw response) for audit
- [ ] Add model selection strategy — Haiku for Stage 1 extraction (cheaper), Sonnet for Stages 2–4 (smarter)
- [ ] Budget enforcement — check cumulative spend before each call, fail gracefully if at limit

---

## Cost Model

| Item | Monthly Cost | Notes |
|------|-------------|-------|
| Claude API | $15–60 | ~$0.15–0.30/company, 100–200 companies/month |
| Apollo | $49–149 | Contact discovery + firmographics |
| Proxycurl | $20–40 | ~$0.01/profile, ~100–200 profiles/month |
| Crunchbase | $499 | Or cheaper alternatives via RapidAPI ($50–100) |
| Infrastructure | $50–100 | Postgres + Redis + one VPS |
| **Total** | **~$200–850/mo** | Scales with number of tracked companies |

---

## What NOT to Build in v1

These are explicitly deferred to v2+:

- CRM export (Salesforce/HubSpot push)
- Feedback loop / recalibration engine (learning from rep outcomes)
- Re-engagement monitor (tracking when to re-contact churned leads)
- Multi-tenant / team management
- Email/Slack notifications
- Docker Compose (just deploy to a VPS with systemd for v1)
- Webhook callbacks (polling is fine for v1)

---

## Success Criteria for v1

1. **Add a company by domain** → system auto-enriches firmographics + contacts within 60 seconds
2. **Blog content scraped automatically** for any company with a real blog
3. **Full analysis pipeline** runs end-to-end and persists results to database
4. **API serves dossiers** — a frontend or script can fetch the latest dossier for any tracked company
5. **Scheduled re-analysis** — companies are re-scored weekly as new signals appear, old ones decay
6. **Cost stays under $500/mo** for a watchlist of 100 companies
7. **Dossier quality** — 7/10 dossiers produce genuinely useful, non-obvious insights (same bar as Phase 0, but with real data instead of fixtures)
