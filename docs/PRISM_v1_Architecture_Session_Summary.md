# PRISM v1 Architecture Planning Session — Summary for Claude Code
**Session Date:** 2026-03-01
**Participants:** Joseph Sherman + Claude Opus 4.6
**Purpose:** Data architecture, extraction pipeline design, and v1 roadmap refinement
**Context:** This document summarizes decisions and insights from a multi-hour architecture session. An existing v1 roadmap exists (V1_ROADMAP.md). This document should be integrated with that roadmap, updating or overriding where conflicts exist.

---

## 1. CORE THESIS: DATA INDEPENDENCE

The central strategic decision from this session: **PRISM should own its data collection and signals layer rather than depending on third-party enrichment providers as primary sources.**

### Reasoning:
- Apollo, ZoomInfo, Clearbit, etc. are aggregation businesses that scrape public sources, normalize, and resell. The underlying data is largely public.
- Third-party firmographic data (headcount, funding stage, tech stack) are **proxy signals** for organizational state. They correlate with buying readiness but don't measure it.
- PRISM's Content Intelligence chain **directly measures** what firmographic data only approximates — pain coherence, organizational stress, buying journey position, messaging resonance.
- Layering Apollo data underneath Content Intelligence mostly provides confirmation, not independent signal. The firmographic data tells you what the content analysis already knows.
- Dependency on third-party data models, field definitions, refresh cadence, and pricing creates fragility.

### Practical decision:
- Apollo is fine as **one input among many** — it backfills firmographic data efficiently via simple API call. Keep it in the roadmap.
- But it should not be the primary or sole enrichment source. PRISM's own scrapers provide independent signal.
- The architecture must treat every data source as pluggable and optional. If Apollo's API changes or pricing spikes, PRISM continues functioning.

---

## 2. WHAT SIGNALS ARE ACTUALLY INDEPENDENT

Not all data sources add independent analytical dimensions. This matters for prioritizing what to build.

### Truly independent signal types (don't correlate with content analysis):
- **Hiring patterns** — Resource allocation decisions revealed through job postings. Behavioral data, not linguistic. Scrapeable from Greenhouse, Lever (public APIs), Indeed, etc.
- **Technology changes** — Infrastructure decisions that create downstream pain and buying windows. BuiltWith diffs or direct fingerprinting from site scraping.
- **Funding events with timing** — Not "Series B = has money" but the temporal signal. Post-funding companies enter a specific operational mode with a 90-180 day buying window. Press release scraping catches most events.

### Key insight:
These are **event-driven signals with temporal characteristics**, not static firmographic profiles. They fit PRISM's signal decay architecture naturally. A static Apollo record of "180 employees, Series B, SaaS" doesn't decay. A funding announcement from 45 days ago does.

---

## 3. VALIDATION: THE RILLET DOSSIER

Joseph demonstrated PRISM's "Personal Intelligence Variant" — a full interview prep dossier generated for Rillet, Inc. using Claude's deep research mode + PRISM's analytical framework.

### What it proved:
- The analysis framework produces genuinely actionable intelligence (buying committee mapping, counter-signals, organizational assessment, discovery questions).
- The output quality is high enough to justify building production infrastructure around it.
- All source data (30+ URLs) came from public web sources — no Apollo, no ZoomInfo. Firmographic data fell out of collection naturally.
- The 4-stage Content Intelligence chain, scoring system, and dossier format all work.

### What it revealed about the v1 gap:
- The deep research approach doesn't scale. Can't programmatically trigger it, can't schedule it, can't run against a list, can't feed output into the scoring engine.
- Deep research is a black box — no control over query decomposition strategy, source prioritization, or collection logic.
- The research agent approach works as R&D tool for validating which signal types matter. It's not the product.
- **The gap is owning the collection logic so it's deterministic and repeatable.** For every target company, the same source types get checked in the same order with the same query patterns.

---

## 4. ROADMAP REORDERING — PHASE 3 (DATA INGESTION)

The existing V1_ROADMAP.md puts Apollo API integration as Tier 1 priority in Phase 3. Based on this session's analysis, the priority order should shift:

### Recommended Tier 1 (build first):
1. **Job board scrapers** — Greenhouse and Lever have public APIs, no auth needed. Highest-value independent signal type. Hiring patterns were the backbone of the Rillet dossier's GTM maturity assessment.
2. **Blog scraper hardening** — Already partially built. Upgrade to trafilatura + Playwright for JS-rendered blogs. Primary Content Intelligence input source.
3. **Press/funding event scrapers** — GlobeNewswire, PR Newswire, company blogs. Catches 90% of funding events without Crunchbase's $499/month.
4. **Tech stack detection** — BuiltWith/Wappalyzer API or own fingerprinting (see Section 6). Genuine independent signal.
5. **Apollo API** — Simple integration, backfills firmographics and provides verified email addresses. Good as one source among many.

### Recommended Tier 2:
- LinkedIn content (Proxycurl or manual upload)
- G2/review site scraping
- Google News for press coverage

### Recommended Tier 3:
- Crunchbase (only if own funding scrapers prove insufficient)

### Key cost change:
Removing Apollo and Crunchbase from Tier 1 drops monthly cost from $200-850 to ~$65-160 (Claude API + infrastructure only).

---

## 5. SCHEDULING STRATEGY

### Near-term (v1 launch):
- **Scheduled cadence** — Weekly full pipeline run for all tracked companies. At 10-50 companies, the cost is trivial ($7-15/week in API calls). Simple to implement, simple to debug.

### Future optimization (when cost matters):
- **Change-detection-driven re-analysis** — Collect on schedule, but only trigger the Content Intelligence chain when the collection layer detects material change (new blog post, new job posting, funding event, content disappeared). Cuts API costs 60-70% at scale because most companies don't produce meaningful new signals in any given week.
- This requires a **diff engine** between collection and analysis layers. Not needed for v1 launch but the architecture should not preclude it.

---

## 6. DATA ARCHITECTURE — PIPELINE & STORAGE

### Four data shapes, not one flat table:
1. **Static data** (changes slowly) — Company name, domain, industry. One record per company. Update in place.
2. **Accumulating data** (only grows) — Blog posts, job postings, press releases. Append-only. Never update a content record, just add new ones.
3. **Temporal data** (decays) — Signals. Relevance changes over time. Scoring engine computes decay in real time.
4. **Analytical snapshots** — Each analysis run is a point-in-time assessment. Both versions (old and new) must persist for diffing.

### Database: PostgreSQL, 7 tables, one instance

**NOT a data warehouse.** No Snowflake, BigQuery, columnar storage. Even at 1,000 companies with a year of history, total rows are in the hundreds of thousands. Postgres handles this trivially on local hardware or a small VPS.

### Table structure:

```
RAW LAYER (audit trail + reprocessing)
  raw_responses     — Exact HTTP response stored as-is. Append-only.
                      Columns: id, account_slug, source_type, url,
                      fetched_at, http_status, raw_headers (JSONB),
                      raw_body (TEXT/JSONB), response_size_bytes

NORMALIZED LAYER (what analysis chain reads)
  accounts          — One row per company. Updates in place.
                      slug (unique), domain, company_name,
                      firmographics (JSONB), tech_stack (JSONB)

  contacts          — One row per person. account_id FK.
                      name, title, linkedin_url, buying_role

  content_items     — One row per collected page. Append-only
                      (new version of same URL = new row, old row
                      marked status: changed).
                      See Section 8 for full column spec.

  signals           — Derived observations. Append-only.
                      See Section 8 for full column spec and
                      signal type taxonomy.

ANALYSIS LAYER (versioned output)
  analyses          — One row per analysis run. Append-only.
                      account_id FK, corpus_snapshot_ids[],
                      stage 1-4 results (JSONB), scores, cost

  dossiers          — Rendered output. analysis_id FK.
                      dossier_id (PRISM-YYYY-NNNN), markdown_content
```

### Key architecture constraints:
1. **Two storage layers for collected data** — Raw store keeps exactly what was fetched (audit trail, enables reprocessing). Normalized store is structured for the analysis chain. When normalizers improve, reprocess from raw instead of re-scraping.
2. **Append-only where it matters** — content_items, signals, and analyses never update in place. New data = new rows. Version history for free. Enables diffing between analysis runs.
3. **One interface for all sources** — Every source adapter outputs the same Pydantic models (ContentItem, Contact, Signal, Account). The analysis chain never knows where data came from. New source = one adapter, zero downstream changes.
4. **Corpus snapshot = reproducibility** — Each analysis record stores which content_item IDs and signal IDs it analyzed. Re-running same analysis on same corpus = same result.

---

## 7. EXTRACTION PIPELINE — SINGLE-PASS MODEL

### Architecture: One HTTP fetch → parallel preprocessing → one LLM call → structured JSON → database writes

```
HTTP Response (headers + full HTML)
    │
    ├──→ [Path A] trafilatura / readability
    │         → cleaned article text + metadata (title, author, date)
    │
    ├──→ [Path B] lightweight HTML parser
    │         → <head> section, script tags, meta tags, HTTP headers,
    │           class name patterns, structured data (JSON-LD)
    │
    ├──→ [Path C] pattern library (Python dict in config.py)
    │         → known tech fingerprints matched against Path B output
    │         → preliminary tech detections with evidence strings
    │         → NOT a replacement for LLM — gives the LLM anchor
    │           points for validation and enrichment
    │
    └──→ [STORE] raw_responses table (full response preserved)

    All three paths feed into ONE LLM call:

    Extraction LLM (Haiku-tier) receives:
      - cleaned_text (Path A) — typically ~500 words / ~700 tokens
      - extracted_metadata (Path A)
      - technical_artifacts (Path B)
      - pattern_matches (Path C)
      - page_url + account context

    Outputs: ExtractionResult JSON → writes to content_items + signals
```

### Why LLM for extraction (not just pattern matching):
- Pattern matching gives booleans ("HubSpot detected"). LLM gives context ("HubSpot tracking + Marketo form embed = likely mid-migration").
- LLM does QA as part of extraction — assesses confidence, resolves conflicting dates, flags anomalies.
- Cost is negligible at typical page sizes (~$0.003-0.005 per page at Haiku tier).
- When local inference becomes available, extraction is the first layer that moves to near-zero cost. A 7-9B model handles structured extraction reliably.

### Pre-filter before LLM (trivial, code-based):
- 404/410 responses → don't send to LLM, but DO track for negative signals
- Pages that are entirely JS with no server-rendered content → skip or flag
- Login walls → skip
- Everything else → send through extraction

### Typical token budget per page:
- Most blog posts/pages: ~500 words → ~700 tokens of cleaned text
- Full extraction input (text + artifacts + context): ~1,500-2,500 tokens
- The 6,000+ token pages are outliers. For those: split and extract separately (multiple LLM calls), then merge with dedup. Do NOT truncate — signals may be buried anywhere in long content.

---

## 8. CONTENT_ITEMS AND SIGNALS TABLE DESIGN

### content_items — full column specification:

```
IDENTITY
  id                    UUID, primary key
  account_id            FK → accounts

CLASSIFICATION (set by extraction LLM)
  source_type           ENUM: blog_post, job_listing, press_release,
                        linkedin_post, about_page, pricing_page,
                        case_study, podcast_appearance, review,
                        careers_page, other
  content_category      ENUM: technical, hiring, product, culture,
                        thought_leadership, competitive, financial,
                        partnership, other
  relevance             ENUM: high, medium, low

SOURCE TRACKING
  url                   TEXT
  raw_response_id       FK → raw_responses

EXTRACTED CONTENT
  title                 TEXT, nullable
  author                TEXT, nullable
  publish_date          TIMESTAMP, nullable
  body_text             TEXT
  word_count            INTEGER

LLM EXTRACTION METADATA
  extracted_data        JSONB — full ExtractionResult JSON stored verbatim
  extraction_model      TEXT — which model did the extraction
  extraction_confidence FLOAT 0-1

STATE TRACKING (enables negative signals)
  first_seen            TIMESTAMP — when scraper first found this URL
  last_seen             TIMESTAMP — when scraper last confirmed it's live
  status                ENUM: active, gone, redirected, changed

HOUSEKEEPING
  created_at            TIMESTAMP
  updated_at            TIMESTAMP
```

**State tracking behavior:**
- Weekly scraper visits every known URL
- Still returns same content → update last_seen, status stays active
- Returns 404/410 → status = gone, generate content_removed signal
- Returns 301/302 → status = redirected, store redirect target
- Content substantially changed → status = changed on old row, create NEW row with new content (both versions preserved for diffing)

**Important:** A burst of 404s across a company's site = potential site migration or organizational change. Individual 404s are noise. The pattern is the signal. This is detected by derived signal generation (bulk_removal), not by the extraction LLM.

### signals — full column specification:

```
IDENTITY
  id                    UUID, primary key
  account_id            FK → accounts

CLASSIFICATION
  signal_type           ENUM (see taxonomy below)
  signal_category       ENUM: growth, pain, hiring, financial,
                        technology, competitive, organizational,
                        content_pattern, absence

SIGNAL CONTENT
  summary               TEXT — human-readable one-liner
  evidence              TEXT — what raw data produced this
  typed_data            JSONB — structured data, schema varies by signal_type

TEMPORAL
  detected_date         TIMESTAMP — when PRISM detected this signal
  event_date            TIMESTAMP, nullable — when the event actually occurred

QUALITY
  confidence            ENUM: extracted, interpolated, inferred
  source_content_ids    UUID[] — content_item IDs that produced this signal

SCORING SUPPORT
  decay_profile         TEXT — references named config in config.py
  is_active             BOOLEAN — has signal decayed below threshold?

STATE
  status                ENUM: active, resolved, superseded, expired
  superseded_by         FK → signals, nullable
```

### Signal type taxonomy:

**FINANCIAL:** funding_round, revenue_milestone, pricing_change
**HIRING:** job_posting, hiring_burst (DERIVED), hiring_freeze (DERIVED), key_hire
**TECHNOLOGY:** tech_detected, tech_added (DERIVED), tech_removed (DERIVED), tech_migration (DERIVED)
**CONTENT PATTERNS:** publishing_cadence (DERIVED), content_gap (DERIVED), topic_shift (DERIVED — from CI chain)
**ORGANIZATIONAL:** leadership_change, partner_announced, acquisition
**COMPETITIVE:** competitor_mention, market_positioning
**ABSENCE/NEGATIVE:** content_removed (DERIVED), page_status_change (DERIVED), bulk_removal (DERIVED)

Full typed_data schemas for each signal type are defined in PRISM_Extraction_Schema_v1.md (companion document).

### Two categories of signals:
1. **Extracted signals** — Output by the extraction LLM from a single page. funding_round, job_posting, key_hire, tech_detected, competitor_mention, etc.
2. **Derived signals** — Generated by post-collection analysis jobs that query across multiple records. hiring_burst, content_gap, tech_migration, bulk_removal, etc. These are NOT LLM outputs — they're database queries or lightweight pattern detection.

---

## 9. EXTRACTION PROMPT SCHEMA (ExtractionResult)

Full spec is in companion document: **PRISM_Extraction_Schema_v1.md**

Key points:
- One JSON output per page containing: page_classification, content, tech_signals, signals[], entities_mentioned, extraction_notes
- Maps directly to content_items row + 0-N signals rows
- Includes deduplication rules per signal type
- Includes derived signal generation rules (trigger conditions + query patterns)
- Includes the system prompt template for the extraction LLM
- Implementation notes for coding agent (discriminated unions, retry logic, token budgets, batch writes, etc.)

---

## 10. TECHNICAL DECISIONS

### Tech fingerprinting approach:
- Pattern library (Python dict in config.py) runs first — catches obvious technologies at zero cost
- Pattern library output is sent TO the extraction LLM as anchor points
- LLM validates, enriches, adds context, and catches what patterns miss
- Pattern library based on Wappalyzer's open-source fingerprint database (Apache licensed) as starting point
- Start with ~50 patterns for most common technologies, expand over time

### LLM strategy:
- Extraction: Haiku-tier (cheapest model that reliably follows JSON schema)
- Content Intelligence chain (4-stage analysis): Sonnet/Opus (needs deeper reasoning)
- Swappable backend architecture (already in roadmap)
- Local inference (Mac Studio / GLM-5 or similar) as future optimization — extraction layer moves to local first since it needs less reasoning capability
- Architect for current API costs, don't prematurely optimize for local inference

### Infrastructure:
- All local or Docker — no cloud VPS initially
- PostgreSQL handles all storage needs at projected scale
- Future Mac Studio for local inference (post-capex, timeline TBD)

---

## 11. SCALE PROJECTIONS

At 1,000 companies with one year of data:
- accounts: ~1,000 rows
- contacts: ~5,000-10,000 rows
- content_items: ~50,000-200,000 rows
- signals: ~20,000-100,000 rows
- analyses: ~2,000-5,000 rows
- dossiers: ~2,000-5,000 rows
- raw_responses: ~200,000-500,000 rows

PostgreSQL handles all of this without optimization, partitioning, or read replicas. Scaling concerns are years away if ever.

---

## 12. WHAT THE EXISTING V1 ROADMAP SHOULD INTEGRATE

1. **Reorder Phase 3 tiers** per Section 4 above
2. **Add raw_responses table** to Phase 1 database schema (7 tables, not 6)
3. **Add state tracking fields** to content_items (first_seen, last_seen, status)
4. **Add derived signal generation** as a post-collection job in Phase 4
5. **Add change detection layer** as future optimization (not needed for v1 launch, but architecture should not preclude it)
6. **Add extraction pipeline spec** — the two-path preprocessing + single LLM call model (Section 7)
7. **Add signal type taxonomy** with typed_data schemas (Section 8)
8. **Add deduplication rules** per signal type
9. **Replace truncation strategy** for long pages with split-and-extract-separately approach

---

## 13. COMPANION DOCUMENTS

- **PRISM_Extraction_Schema_v1.md** — Full extraction contract with JSON schemas, field-by-field database mapping, signal type taxonomy with typed_data schemas, dedup rules, derived signal generation rules, extraction prompt template, and implementation notes for coding agent.
- **prism-architecture.jsx** — Interactive pipeline block diagram showing all 7 layers from data sources through analysis output.

---

## 14. RECOMMENDED READING

For Joseph's reference (not for Claude Code):
1. **Designing Data-Intensive Applications** — Kleppmann (data pipelines, storage, schema evolution)
2. **A Philosophy of Software Design** — Ousterhout (clean abstractions, module boundaries)
3. **The Pragmatic Programmer** — Hunt & Thomas (software engineering fundamentals)
4. **System Design Interview vols 1&2** — Alex Xu (system architecture walkthroughs)
5. **PostgreSQL official documentation** — Tutorial chapters (relational DB concepts from first principles)

---

*This document is a planning handoff. Claude Code should read this alongside the existing V1_ROADMAP.md and PRISM_Extraction_Schema_v1.md, identify conflicts, and propose an integrated build plan.*
