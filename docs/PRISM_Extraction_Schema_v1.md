# PRISM Extraction Schema v1 — Collection-to-Storage Contract

**Purpose:** This document defines the exact JSON schema that the extraction LLM outputs per page. It is the contract between the collection layer and the normalized database. Every field maps to a column or JSONB field in the `content_items` and `signals` tables. The coding agent should use this document as the authoritative spec for building both the extraction prompt and the Pydantic models.

**Design principle:** One HTTP fetch → two parallel preprocessing paths (content cleaning + technical artifact parsing) → one LLM call → one JSON output → database writes to `content_items` and `signals`.

---

## Pipeline Per Page

```
HTTP Response (headers + full HTML)
        │
        ├──→ [Path A] trafilatura / readability
        │         → cleaned article text
        │         → extracted metadata (title, author, date if available)
        │
        ├──→ [Path B] lightweight HTML parser
        │         → <head> section (meta tags, script srcs, link rels)
        │         → HTTP response headers (Server, X-Powered-By, Set-Cookie)
        │         → script tag sources and inline script signatures
        │         → class name patterns (wp-, __next, __nuxt, etc.)
        │         → structured data (JSON-LD, microdata)
        │
        ├──→ [Path C] pattern library (pre-LLM, zero cost)
        │         → known tech fingerprints matched against Path B output
        │         → outputs preliminary tech detections with evidence strings
        │
        └──→ [STORE] raw_responses table
                  → full HTTP response preserved as-is

        All three paths feed into ONE LLM call:

        ┌─────────────────────────────────────────────────┐
        │  EXTRACTION LLM (Haiku-tier)                    │
        │                                                 │
        │  Input:                                         │
        │    - cleaned_text (from Path A)                 │
        │    - extracted_metadata (from Path A)           │
        │    - technical_artifacts (from Path B)          │
        │    - pattern_matches (from Path C)              │
        │    - page_url                                   │
        │    - account context (company name, domain)     │
        │                                                 │
        │  Output:                                        │
        │    - ExtractionResult JSON (defined below)      │
        └───────────────────┬─────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
        content_items table      signals table
        (one row per page)    (0-N rows per page)
```

---

## Pre-LLM Input Assembly

The LLM receives a structured input package, NOT raw HTML. This keeps token count to ~2,000-4,000 per page instead of 20,000-60,000.

### Input Schema (what gets sent TO the LLM)

```json
{
  "page_url": "https://rillet.com/blog/series-b",
  "account": {
    "company_name": "Rillet",
    "domain": "rillet.com"
  },
  "cleaned_text": "Rillet Raises $70M Series B to Replace...[trafilatura output]",
  "extracted_metadata": {
    "title": "Rillet Raises $70M Series B",
    "author": "Nicolas Kopp",
    "date_candidates": ["2025-08-15", "August 2025"],
    "canonical_url": "https://rillet.com/blog/series-b",
    "language": "en",
    "word_count": 847
  },
  "technical_artifacts": {
    "http_headers": {
      "server": "nginx",
      "x-powered-by": null,
      "set_cookie_prefixes": ["_ga", "__stripe"],
      "cdn_headers": ["cf-ray"]
    },
    "head_meta_tags": [
      {"name": "generator", "content": "Next.js"},
      {"property": "og:type", "content": "article"}
    ],
    "script_sources": [
      "/_next/static/chunks/main.js",
      "https://js.stripe.com/v3/",
      "https://www.googletagmanager.com/gtag/js"
    ],
    "structured_data": [
      {"type": "Organization", "fields": ["name", "url", "logo"]},
      {"type": "BlogPosting", "fields": ["headline", "datePublished", "author"]}
    ],
    "class_signatures": ["__next", "chakra-ui"],
    "link_rels": [
      {"rel": "stylesheet", "href": "...chakra..."}
    ]
  },
  "pattern_matches": [
    {"technology": "Next.js", "evidence": "/_next/static/ in script src", "confidence": "high"},
    {"technology": "Cloudflare", "evidence": "cf-ray header present", "confidence": "high"},
    {"technology": "Google Analytics", "evidence": "gtag.js script loaded", "confidence": "high"},
    {"technology": "Stripe", "evidence": "js.stripe.com script + __stripe cookie", "confidence": "high"},
    {"technology": "Chakra UI", "evidence": "chakra-ui class prefix", "confidence": "medium"}
  ]
}
```

---

## LLM Output Schema — ExtractionResult

This is the **exact** JSON structure the LLM must output. Every field maps to database storage. The extraction prompt must include this schema as the required output format.

```json
{
  "extraction_version": "v1",
  "extraction_confidence": 0.85,

  "page_classification": {
    "page_type": "blog_post",
    "content_category": "financial",
    "relevance": "high",
    "relevance_reasoning": "Series B funding announcement with specific figures, investor names, and growth metrics. High-value signal for financial and organizational assessment."
  },

  "content": {
    "title": "Rillet Raises $70M Series B to Replace Legacy Accounting Software",
    "author": "Nicolas Kopp",
    "publish_date": "2025-08-15",
    "publish_date_confidence": "high",
    "body_text": "[cleaned text passed through — LLM may lightly restructure if trafilatura output had artifacts, but should NOT summarize or truncate]",
    "word_count": 847,
    "language": "en",
    "canonical_url": "https://rillet.com/blog/series-b"
  },

  "tech_signals": [
    {
      "technology": "Next.js",
      "category": "frontend_framework",
      "evidence": "/_next/static/ script paths, __next root div",
      "confidence": "high",
      "version": null,
      "note": null
    },
    {
      "technology": "Cloudflare",
      "category": "cdn_security",
      "evidence": "cf-ray response header",
      "confidence": "high",
      "version": null,
      "note": null
    },
    {
      "technology": "Stripe",
      "category": "payments",
      "evidence": "js.stripe.com/v3 script, __stripe cookie prefix",
      "confidence": "high",
      "version": "v3",
      "note": "Indicates payment processing integration — consistent with accounting/ERP product"
    },
    {
      "technology": "Google Analytics / GTM",
      "category": "analytics",
      "evidence": "googletagmanager.com/gtag/js script",
      "confidence": "high",
      "version": null,
      "note": null
    },
    {
      "technology": "Chakra UI",
      "category": "ui_framework",
      "evidence": "chakra-ui class prefixes in DOM",
      "confidence": "medium",
      "version": null,
      "note": null
    }
  ],

  "signals": [
    {
      "signal_type": "funding_round",
      "signal_category": "financial",
      "summary": "Series B: $70M raised, Andreessen Horowitz and ICONIQ Growth co-lead",
      "evidence": "Directly stated in blog post: 'We're excited to announce our $70M Series B, co-led by Andreessen Horowitz and ICONIQ Growth'",
      "confidence": "extracted",
      "event_date": "2025-08-15",
      "typed_data": {
        "amount": 70000000,
        "currency": "USD",
        "round_type": "series_b",
        "lead_investors": ["Andreessen Horowitz", "ICONIQ Growth"],
        "co_investors": ["Sequoia Capital"],
        "cumulative_raised": 108500000,
        "valuation": null,
        "source_url": "https://rillet.com/blog/series-b"
      }
    },
    {
      "signal_type": "revenue_milestone",
      "signal_category": "growth",
      "summary": "5x YoY revenue growth, ARR doubling every 12 weeks",
      "evidence": "Blog states 'revenue grew more than 5x year-over-year' and 'ARR has been doubling roughly every 12 weeks'",
      "confidence": "extracted",
      "event_date": "2025-08-15",
      "typed_data": {
        "description": "5x YoY revenue growth, ARR doubling every 12 weeks",
        "metric_type": "revenue_growth",
        "metric_value": "5x YoY",
        "source_url": "https://rillet.com/blog/series-b"
      }
    },
    {
      "signal_type": "market_positioning",
      "signal_category": "competitive",
      "summary": "Positioning as replacement for NetSuite, Sage Intacct, and QuickBooks",
      "evidence": "Post frames Rillet as 'the modern alternative to legacy accounting software' and specifically names NetSuite and Sage Intacct as systems their customers migrate from",
      "confidence": "extracted",
      "event_date": "2025-08-15",
      "typed_data": {
        "positioning_description": "AI-native ERP replacing legacy accounting systems for venture-funded companies",
        "named_competitors": ["NetSuite", "Sage Intacct", "QuickBooks"],
        "evidence": "Blog post framing and customer migration narratives",
        "source_url": "https://rillet.com/blog/series-b"
      }
    }
  ],

  "entities_mentioned": [
    {
      "name": "Nicolas Kopp",
      "type": "person",
      "role": "Co-Founder & CEO",
      "context": "Author and primary voice of the announcement"
    },
    {
      "name": "Andreessen Horowitz",
      "type": "organization",
      "role": "investor",
      "context": "Series B co-lead"
    },
    {
      "name": "ICONIQ Growth",
      "type": "organization",
      "role": "investor",
      "context": "Series B co-lead"
    },
    {
      "name": "Sequoia Capital",
      "type": "organization",
      "role": "investor",
      "context": "Existing investor, participated in round"
    }
  ],

  "extraction_notes": "High-confidence extraction. All financial figures directly stated. Valuation not disclosed. Customer count mentioned as '200+' but not extracted as a standalone signal since it appeared in the Series A announcement context — may be stale by publication date."
}
```

---

## Field-by-Field Mapping to Database

### → content_items table

| ExtractionResult Field | Database Column | Notes |
|------------------------|----------------|-------|
| `page_classification.page_type` | `source_type` | Direct enum mapping |
| `page_classification.content_category` | `content_category` | Direct enum mapping |
| `page_classification.relevance` | `relevance` | Direct enum mapping |
| `content.title` | `title` | Nullable |
| `content.author` | `author` | Nullable |
| `content.publish_date` | `publish_date` | Nullable, parsed to timestamp |
| `content.body_text` | `body_text` | Full cleaned text |
| `content.word_count` | `word_count` | Integer |
| `content.canonical_url` | `url` | Falls back to fetched URL |
| Full JSON output | `extracted_data` | JSONB — the entire ExtractionResult stored verbatim |
| Model used | `extraction_model` | Set by calling code, not LLM |
| `extraction_confidence` | `extraction_confidence` | Float 0-1 |
| Set by collector | `first_seen` | Timestamp of first fetch |
| Set by collector | `last_seen` | Updated on each re-fetch |
| Set by collector | `status` | active / gone / redirected / changed |
| Set by collector | `raw_response_id` | FK to raw_responses |
| Set by collector | `account_id` | FK to accounts |

### → signals table (one row per item in signals[])

| ExtractionResult Field | Database Column | Notes |
|------------------------|----------------|-------|
| `signals[].signal_type` | `signal_type` | Enum — must match defined taxonomy |
| `signals[].signal_category` | `signal_category` | Enum |
| `signals[].summary` | `summary` | Human-readable one-liner |
| `signals[].evidence` | `evidence` | What raw data produced this |
| `signals[].confidence` | `confidence` | extracted / interpolated / inferred |
| `signals[].event_date` | `event_date` | When event occurred (nullable) |
| `signals[].typed_data` | `typed_data` | JSONB — schema varies by signal_type |
| Set by collector | `detected_date` | When YOUR system found this |
| Derived from signal_type | `decay_profile` | Config reference |
| Computed | `is_active` | Boolean, updated periodically |
| Set by collector | `source_content_ids` | UUID[] — which content_items produced this |
| Default | `status` | active (set at creation) |
| Default | `superseded_by` | null (set at creation) |

### → contacts table (from entities_mentioned where type = "person")

Entities of type "person" with a role at the target company are candidates for upserting into the contacts table. The extraction LLM surfaces them; a downstream process decides whether to create/update a contact record (since the same person may appear across multiple pages).

### Not stored separately (embedded in extracted_data JSONB)

- `tech_signals[]` — stored inside `extracted_data` on the content_item row AND optionally promoted to `signals` table as `tech_detected` signal type
- `entities_mentioned[]` — stored in `extracted_data`, consumed by downstream contact enrichment
- `extraction_notes` — stored in `extracted_data`, useful for debugging
- `page_classification.relevance_reasoning` — stored in `extracted_data`

---

## Signal Type Taxonomy — typed_data Schemas

Each signal_type has a defined JSON schema for its `typed_data` field. The LLM must conform to these. Pydantic discriminated unions enforce this at the application layer.

### Financial Signals

```
funding_round:
  amount:             int (USD, required)
  currency:           str (default "USD")
  round_type:         enum: pre_seed|seed|series_a|series_b|series_c|
                            series_d|series_e|growth|debt|unknown
  lead_investors:     str[] (required, at least one)
  co_investors:       str[] (optional)
  cumulative_raised:  int (optional — total raised to date)
  valuation:          int (optional, nullable — often undisclosed)
  source_url:         str (required)

revenue_milestone:
  description:        str (required — human-readable milestone)
  metric_type:        enum: revenue_growth|arr|customer_count|
                            ndr|gmv|other
  metric_value:       str (required — "5x YoY", "$10M ARR", "200+ customers")
  source_url:         str (required)

pricing_change:
  change_description: str (required)
  direction:          enum: up|down|restructured|removed_public_pricing
  previous_model:     str (optional)
  new_model:          str (optional)
  source_url:         str (required)
```

### Hiring Signals

```
job_posting:
  title:              str (required)
  department:         enum: engineering|product|design|marketing|sales|
                            finance|operations|hr|legal|customer_success|
                            data|security|executive|other
  seniority:          enum: intern|junior|mid|senior|staff|principal|
                            director|vp|c_level
  location:           str (optional)
  remote_ok:          bool (optional)
  first_seen:         date (required — when collector first found it)
  last_seen:          date (required — updated on re-check)
  posting_url:        str (required)
  status:             enum: active|removed|filled
  key_requirements:   str[] (optional — notable skills/tools mentioned)

hiring_burst:
  count:              int (required — number of postings)
  department:         str (required — which department)
  timeframe_days:     int (required — over what period)
  titles:             str[] (required — list of job titles)
  NOTE: This is a DERIVED signal. Not output by extraction LLM.
        Generated by a post-collection analysis job that queries
        the signals table for recent job_posting signals.

hiring_freeze:
  evidence:           str (required)
  departments:        str[] (required)
  postings_removed:   int (optional)
  NOTE: DERIVED signal. Generated when multiple job_posting signals
        transition to status: removed within a short timeframe.

key_hire:
  person_name:        str (required)
  title:              str (required)
  previous_company:   str (optional)
  previous_title:     str (optional)
  start_date:         date (optional)
  source_url:         str (required)
```

### Technology Signals

```
tech_detected:
  technology:         str (required)
  category:           enum: frontend_framework|backend_framework|cms|
                            ecommerce|analytics|marketing_automation|
                            crm|payments|cdn_security|ui_framework|
                            database|cloud_infra|monitoring|
                            communication|other
  version:            str (optional)
  evidence:           str (required)
  page_url:           str (required)

tech_added:
  technology:         str (required)
  category:           str (enum, same as above)
  first_detected:     date (required)
  evidence:           str (required)
  NOTE: DERIVED signal. Generated when tech_detected appears
        for a technology not previously seen for this account.

tech_removed:
  technology:         str (required)
  category:           str (enum)
  last_detected:      date (required)
  evidence:           str (required)
  NOTE: DERIVED signal. Generated when previously-detected
        technology no longer appears across recent scrapes.

tech_migration:
  from_technology:    str (required)
  to_technology:      str (required)
  evidence:           str[] (required)
  confidence:         enum: high|medium|low
  NOTE: DERIVED signal. Generated when tech_removed and
        tech_added occur for related technologies in same period.
```

### Content Pattern Signals

```
publishing_cadence:
  frequency:          str ("weekly", "2-3x/month", "monthly", "sporadic")
  trend:              enum: increasing|stable|declining
  period_analyzed:    str ("last 6 months", "last 90 days")
  post_count:         int (required)
  NOTE: DERIVED signal from content_items publish_date analysis.

content_gap:
  last_publish_date:  date (required)
  days_silent:        int (required)
  previous_cadence:   str (required — what the norm was before silence)
  NOTE: DERIVED signal. Triggered when days since last publish
        exceeds 2x the previous average cadence.

topic_shift:
  previous_topics:    str[] (required)
  new_topics:         str[] (required)
  period:             str (required)
  NOTE: DERIVED signal from Content Intelligence chain, not
        from extraction LLM. Stage 2 cross-corpus synthesis
        detects this.
```

### Organizational Signals

```
leadership_change:
  person_name:        str (required)
  old_role:           str (optional, nullable)
  new_role:           str (required)
  change_type:        enum: hired|promoted|departed|role_expanded
  source_url:         str (required)

partner_announced:
  partner_name:       str (required)
  partnership_type:   enum: technology|channel|consulting|reseller|
                            integration|strategic|other
  description:        str (optional)
  source_url:         str (required)

acquisition:
  counterparty:       str (required — who was acquired or who acquired)
  direction:          enum: acquired|was_acquired
  deal_value:         int (optional, nullable)
  source_url:         str (required)
```

### Competitive Signals

```
competitor_mention:
  competitor_name:    str (required)
  context:            enum: comparison|migration_from|migration_to|
                            partnership|negative|neutral
  sentiment:          enum: positive|negative|neutral
  quote_or_context:   str (required — brief context of the mention)
  source_url:         str (required)

market_positioning:
  positioning:        str (required — how the company positions itself)
  target_segment:     str (optional — who they say they serve)
  named_competitors:  str[] (optional)
  evidence:           str (required)
  source_url:         str (required)
```

### Absence / Negative Signals

```
content_removed:
  url:                str (required)
  content_type:       str (required — source_type of the removed item)
  was_title:          str (optional — title when it was live)
  first_seen:         date (required)
  last_seen:          date (required — last time it returned 200)
  removal_detected:   date (required — when 404/410 was detected)
  NOTE: DERIVED signal. Generated by state tracking in collection
        layer when content_item status changes to 'gone'.

page_status_change:
  url:                str (required)
  old_status:         int (required — HTTP status code)
  new_status:         int (required — HTTP status code)
  detected_date:      date (required)
  NOTE: DERIVED signal. Generated by collection layer on any
        HTTP status change (200→301, 200→404, etc.)

bulk_removal:
  count:              int (required)
  content_types:      str[] (required)
  timeframe_days:     int (required)
  urls:               str[] (required)
  NOTE: DERIVED signal. Triggered when N+ content_removed signals
        appear within X days. Indicates site migration, rebrand,
        or organizational change.
```

---

## Derived Signals — Generation Rules

Derived signals are NOT output by the extraction LLM. They are generated by post-collection analysis jobs that query the normalized store. These jobs should run after each collection cycle.

| Derived Signal | Trigger Condition | Query Pattern |
|----------------|-------------------|---------------|
| `hiring_burst` | 5+ job_postings in same department within 30 days | GROUP BY department, COUNT within time window |
| `hiring_freeze` | 3+ job_postings transition to removed within 14 days | Status change tracking on job_posting signals |
| `tech_added` | tech_detected signal for technology not in prior scrapes | Compare current tech_detected set vs historical |
| `tech_removed` | previously-detected technology absent from last 2 scrapes | Compare current vs historical, require 2 consecutive absences to avoid false positives |
| `tech_migration` | tech_removed + tech_added in related category within 60 days | Correlation between removal and addition events |
| `publishing_cadence` | Computed from content_items publish_date distribution | Statistical analysis of publish dates |
| `content_gap` | Days since last publish > 2x average cadence | Compare latest publish_date to historical average |
| `content_removed` | content_item status changes from active to gone | State tracking in collection layer |
| `page_status_change` | Any HTTP status code change between collection runs | Compare current vs previous HTTP response |
| `bulk_removal` | 5+ content_removed signals within 7 days | Count content_removed signals in time window |
| `topic_shift` | Detected by Content Intelligence Stage 2 | Cross-corpus synthesis output |

---

## Deduplication Rules

The same signal can be detected from multiple pages (e.g., a funding round mentioned on the company blog AND on TechCrunch). The pipeline must deduplicate.

**Dedup key by signal type:**

| Signal Type | Dedup Key | Rule |
|-------------|-----------|------|
| `funding_round` | (account_id, round_type, amount) | Same round from multiple sources → merge, keep all source_content_ids |
| `revenue_milestone` | (account_id, metric_type, metric_value) | Same metric stated twice → merge |
| `job_posting` | (account_id, posting_url) | Same URL = same posting. If URL differs but title+department match, flag for review |
| `key_hire` | (account_id, person_name, title) | Same person+title → merge |
| `tech_detected` | (account_id, technology) | Same tech on multiple pages → one signal, update evidence |
| `competitor_mention` | NO DEDUP | Each mention is a separate data point, even if same competitor |
| `market_positioning` | (account_id, positioning) | Substantially similar → merge |
| `leadership_change` | (account_id, person_name, new_role) | Same change from multiple sources → merge |
| `partner_announced` | (account_id, partner_name) | Same partnership → merge |

**Merge behavior:** When deduplicating, the surviving signal gets all `source_content_ids` from both records, the highest confidence level, and the earliest `event_date`. The summary and evidence fields come from the highest-confidence source.

---

## Extraction Prompt Template (System Prompt)

The actual prompt sent to the extraction LLM. This goes in `prism/prompts/v1/extraction.py` or similar.

```
You are a structured data extraction system for PRISM, a GTM intelligence
platform. You receive pre-processed web page data and output a single JSON
document conforming to the ExtractionResult schema.

RULES:
1. Output ONLY valid JSON. No markdown, no explanation, no preamble.
2. Every field in the schema must be present. Use null for unknown values.
3. The "signals" array should contain ONLY signals you can directly extract
   from this page's content. Do NOT infer signals that require cross-page
   analysis (those are generated downstream).
4. For tech_signals: validate pattern_matches against the technical_artifacts.
   Confirm, reject, or adjust confidence. Add any technologies the pattern
   matcher missed.
5. For content.body_text: pass through the cleaned_text. Do NOT summarize,
   truncate, or rewrite. You may fix obvious encoding artifacts.
6. For publish_date: choose the most likely date from available candidates.
   Set publish_date_confidence to "low" if ambiguous.
7. For relevance: assess how useful this content is for understanding the
   company's organizational state, buying readiness, pain signals, or
   competitive position. A company blog about their holiday party = "low".
   A funding announcement = "high". A technical blog post about scaling
   challenges = "high".
8. For entities_mentioned: extract people and organizations mentioned in
   the content that are relevant to the company's business context.
   Skip generic mentions (e.g., "Google" in "Google Analytics").
9. extraction_notes should flag anything unusual: conflicting dates,
   ambiguous figures, content that seems AI-generated, stale information
   presented as current, or anything the downstream analysis should know.

SCHEMA:
[Insert full ExtractionResult schema here]

SIGNAL TYPE DEFINITIONS:
[Insert signal_type taxonomy with typed_data schemas here]

INPUT:
{input_json}
```

---

## Implementation Notes for Coding Agent

1. **Pydantic models should use discriminated unions for typed_data.** The signal_type field determines which typed_data schema applies. Use `Literal["funding_round"]` discriminators so Pydantic validates the correct inner schema automatically.

2. **The extraction prompt is versioned.** Store in `prism/prompts/v1/extraction.py`. When the schema changes, create v2. Old analyses reference which prompt version produced them via `analyses.prompt_version`.

3. **Retry on malformed JSON.** If the LLM returns invalid JSON, retry once with a shorter prompt saying "Your previous output was not valid JSON. Output only the JSON object, no other text." If second attempt fails, log the raw response and skip this page.

4. **Token budget awareness.** The input assembly step should estimate token count before sending. If cleaned_text exceeds 6,000 tokens, truncate to first 4,000 + last 1,000 tokens (keeps intro and conclusion). Log when truncation occurs.

5. **Batch signal writes.** A single page extraction may produce 0-10 signals. Write them all in one database transaction with the content_item write. If any write fails, roll back the entire page extraction.

6. **Tech signal promotion is optional.** tech_signals live in extracted_data JSONB by default. Promote to signals table as tech_detected only if tech stack tracking is enabled for the account. This avoids generating dozens of low-value tech signals for every page.

7. **The pattern library is a Python dict, not a database table.** It's configuration, not data. Store in `prism/config.py` alongside scoring weights. Format: `{"_next/static": {"technology": "Next.js", "category": "frontend_framework", "confidence": "high"}}`. Fast lookup, easy to extend, version-controlled.

---

*PRISM Extraction Schema v1 — J. Sherman — February 2026*
*This document is the authoritative spec for collection-to-storage data flow.*
*All Pydantic models, extraction prompts, and database schemas derive from this document.*
