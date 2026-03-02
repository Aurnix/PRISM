# PRISM v1 Build Plan — Complete Architecture Specification

**Purpose:** This document is a complete build spec for upgrading PRISM from Phase 0 (portfolio demo with fixture data) to v1 (operational tool with live data, persistence, API, and scheduling). Hand this to an engineer or an AI coding agent and they can build it.

**Current state:** CLI-only, fixture-driven, 10 demo companies, all analysis in-memory, no persistence. Core intelligence chain, scoring engine, signal decay, and dossier renderer are production-quality.

**v1 target:** Take a company domain → auto-enrich → scrape content → run Content Intelligence chain → persist results → serve dossiers via API → re-analyze on schedule.

**Long-term infrastructure note:** Production deployment will run inference on a Mac Studio cluster with an open-source SOTA model (e.g., GLM-5, Qwen, Llama). The architecture must support swappable LLM backends — Claude API for development/testing, local inference for production. All interfaces below are designed with this in mind.

---

## Table of Contents

1. [Interface 1: LLM Backend](#1-interface-1-llm-backend)
2. [Interface 2: Database Schema](#2-interface-2-database-schema)
3. [Interface 3: Data Access Layer (DAL)](#3-interface-3-data-access-layer-dal)
4. [Interface 4: Enrichment Services](#4-interface-4-enrichment-services)
5. [API Layer Spec](#5-api-layer-spec)
6. [Task Queue & Scheduling](#6-task-queue--scheduling)
7. [Migration Path from Phase 0](#7-migration-path-from-phase-0)
8. [File Structure (v1)](#8-file-structure-v1)
9. [Dependencies](#9-dependencies)
10. [Configuration](#10-configuration)

---

## 1. Interface 1: LLM Backend

### Problem

Phase 0 hardcodes the Anthropic SDK in `services/llm.py`. v1 needs to support:
- Claude API (development, fallback)
- Local inference via OpenAI-compatible API (vLLM, SGLang, llama.cpp server)
- Model routing (cheap model for Stage 1 extraction, stronger model for Stages 2-4)

### Interface Definition

```python
# prism/services/llm_backend.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMResponse:
    """Standardized response from any LLM backend."""
    content: str                      # Raw text response
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    latency_ms: int = 0
    cached: bool = False              # True if served from cache


@dataclass
class TokenBudget:
    """Spend tracking and enforcement."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_calls: int = 0
    max_spend_usd: float = 100.0      # Configurable cap
    cost_per_1k_input: float = 0.003
    cost_per_1k_output: float = 0.015

    @property
    def estimated_cost(self) -> float:
        return (
            (self.total_input_tokens / 1000) * self.cost_per_1k_input
            + (self.total_output_tokens / 1000) * self.cost_per_1k_output
        )

    @property
    def budget_remaining(self) -> float:
        return self.max_spend_usd - self.estimated_cost

    def check_budget(self) -> bool:
        """Returns False if budget exhausted."""
        return self.estimated_cost < self.max_spend_usd

    def record(self, response: LLMResponse) -> None:
        self.total_input_tokens += response.input_tokens
        self.total_output_tokens += response.output_tokens
        self.total_calls += 1


class LLMBackend(ABC):
    """Abstract interface for LLM inference backends.

    Implementations: AnthropicBackend, LocalInferenceBackend.
    The Content Intelligence chain calls this interface — it never
    knows or cares which backend is answering.
    """

    @abstractmethod
    async def query(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        response_format: str = "json",   # "json" | "text"
    ) -> Optional[LLMResponse]:
        """Send a prompt and get a response.

        Args:
            system_prompt: System-level instructions.
            user_prompt: The actual query content.
            max_tokens: Max output tokens.
            temperature: Sampling temperature (0.0 = deterministic).
            response_format: Expected format — "json" triggers
                structured output / JSON mode if the backend supports it.

        Returns:
            LLMResponse on success, None on failure after retries.
        """
        ...

    @abstractmethod
    def get_budget(self) -> TokenBudget:
        """Return current token usage and budget status."""
        ...
```

### Anthropic Backend (wraps current `services/llm.py`)

```python
# prism/services/backends/anthropic_backend.py

class AnthropicBackend(LLMBackend):
    """Claude API backend via Anthropic SDK.

    This is a refactor of the existing services/llm.py into the
    LLMBackend interface. Core logic (retry, code fence stripping,
    JSON parsing) stays the same.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_retries: int = 3,
        max_spend_usd: float = 100.0,
    ):
        # Use anthropic.AsyncAnthropic (true async, not asyncio.to_thread)
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_retries = max_retries
        self._budget = TokenBudget(max_spend_usd=max_spend_usd)

    async def query(self, system_prompt, user_prompt, **kwargs) -> Optional[LLMResponse]:
        # 1. Check budget
        # 2. Call self._client.messages.create(...)
        # 3. Strip code fences if response_format == "json"
        # 4. Record tokens in budget
        # 5. Return LLMResponse
        # Retry logic: exponential backoff on RateLimitError/APIError
        ...

    def get_budget(self) -> TokenBudget:
        return self._budget
```

### Local Inference Backend

```python
# prism/services/backends/local_backend.py

class LocalInferenceBackend(LLMBackend):
    """Local inference via OpenAI-compatible API endpoint.

    Works with vLLM, SGLang, llama.cpp server, or any server
    that exposes POST /v1/chat/completions.

    For Mac Studio cluster deployment with GLM-5 or similar.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        model: str = "local-model",
        max_retries: int = 3,
        max_spend_usd: float = float("inf"),  # No cost for local
    ):
        self._base_url = base_url
        self._model = model
        self._max_retries = max_retries
        self._budget = TokenBudget(
            max_spend_usd=max_spend_usd,
            cost_per_1k_input=0.0,   # Free — running locally
            cost_per_1k_output=0.0,
        )

    async def query(self, system_prompt, user_prompt, **kwargs) -> Optional[LLMResponse]:
        # 1. POST to {base_url}/v1/chat/completions
        #    with model, messages, max_tokens, temperature
        # 2. If response_format == "json", request JSON mode
        #    (depends on server — vLLM supports guided decoding,
        #     SGLang supports constrained output)
        # 3. Parse response, extract content + token counts
        # 4. Stricter JSON validation than Anthropic backend
        #    (open models are flakier at structured output)
        # 5. Return LLMResponse
        ...

    def get_budget(self) -> TokenBudget:
        return self._budget
```

### Model Router (optional, for mixed-model strategies)

```python
# prism/services/backends/router.py

class ModelRouter(LLMBackend):
    """Routes requests to different backends based on task type.

    Example: Haiku/small model for Stage 1 extraction (cheap, high volume),
    Sonnet/large model for Stage 2-4 synthesis (needs reasoning quality).
    """

    def __init__(
        self,
        default_backend: LLMBackend,
        routes: dict[str, LLMBackend] | None = None,
    ):
        self._default = default_backend
        self._routes = routes or {}
        # Example routes:
        # {
        #     "extraction": haiku_backend,      # Stage 1
        #     "synthesis": sonnet_backend,       # Stages 2-4
        #     "activation": sonnet_backend,      # Angle generation
        # }

    async def query(self, system_prompt, user_prompt, **kwargs) -> Optional[LLMResponse]:
        # Caller can pass task_type in kwargs to route
        task_type = kwargs.pop("task_type", None)
        backend = self._routes.get(task_type, self._default)
        return await backend.query(system_prompt, user_prompt, **kwargs)
```

### LLM Response Cache

```python
# prism/services/llm_cache.py

class LLMCache:
    """Cache LLM responses to avoid redundant API calls.

    Keyed by hash(system_prompt + user_prompt + model).
    For local inference this is less important (free), but still
    useful for avoiding redundant computation.
    """

    def __init__(self, backend: LLMBackend, cache_store: "CacheStore"):
        self._backend = backend
        self._cache = cache_store

    async def query(self, system_prompt, user_prompt, **kwargs) -> Optional[LLMResponse]:
        cache_key = self._hash(system_prompt, user_prompt, kwargs)

        cached = await self._cache.get(cache_key)
        if cached:
            return LLMResponse(content=cached, cached=True)

        response = await self._backend.query(system_prompt, user_prompt, **kwargs)
        if response:
            await self._cache.set(cache_key, response.content, ttl_hours=168)  # 1 week
        return response
```

### Integration with Content Intelligence Chain

The only change to `analysis/content_intel.py`:

```python
# BEFORE (Phase 0):
class ContentIntelligenceChain:
    def __init__(self, llm: Optional[LLMService] = None):
        self.llm = llm or LLMService()

# AFTER (v1):
class ContentIntelligenceChain:
    def __init__(self, llm: LLMBackend):
        self.llm = llm
    # All self.llm.query_json() calls become self.llm.query(..., response_format="json")
    # JSON parsing moves to a shared utility function
```

### Key Design Decisions

1. **`response_format="json"` is a hint, not a guarantee.** The backend should attempt JSON mode / constrained decoding, but the caller must still validate and handle parse failures.
2. **Budget enforcement is per-backend.** Local inference backends set cost to $0 but still track token counts for analysis.
3. **Cache is a wrapper, not built into backends.** This keeps backends simple and testable.
4. **`asyncio.to_thread` goes away.** The Anthropic backend uses `AsyncAnthropic` natively. The local backend uses `httpx.AsyncClient`. No more sync-to-async bridging.

---

## 2. Interface 2: Database Schema

### Design Principles

- **9 tables total** — raw_responses, accounts, contacts, linkedin_posts, content_items, signals, analyses, dossiers, enrichment_log.
- **Two storage layers** — Raw (audit trail, enables reprocessing) + Normalized (analysis input).
- **JSONB for semi-structured data.** Firmographics, tech_stack, stage results, scores, and signal typed_data are stored as JSONB columns. This avoids schema explosions and lets the Pydantic models evolve without migrations.
- **Append-only where it matters.** content_items, signals, and analyses are append-only. Old signals are never deleted — decay handles relevance naturally. Old content gets status changes (active → gone/changed), not deletion.
- **One row per analysis run.** Full history preserved. Every dossier links to the analysis that produced it.
- **UUIDs for primary keys.** No auto-increment integers leaking into URLs.

### Tables

```sql
-- ─── raw_responses ────────────────────────────────────────────
-- Audit trail. Append-only. Enables reprocessing when extraction prompts improve.
CREATE TABLE raw_responses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id          UUID REFERENCES accounts(id) ON DELETE SET NULL,
    source_type         TEXT NOT NULL,       -- 'blog', 'job_board', 'press', 'api_response'
    url                 TEXT,
    fetched_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    http_status         INTEGER,
    raw_headers         JSONB,
    raw_body            TEXT,                -- Full HTML or JSON response
    response_size_bytes INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_raw_responses_account ON raw_responses(account_id);
CREATE INDEX idx_raw_responses_url ON raw_responses(url);

-- ─── accounts ──────────────────────────────────────────────────
CREATE TABLE accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            TEXT UNIQUE NOT NULL,
    company_name    TEXT NOT NULL,
    domain          TEXT NOT NULL,
    blog_url        TEXT,
    blog_rss        TEXT,
    firmographics   JSONB NOT NULL DEFAULT '{}',
    tech_stack      JSONB NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'active',  -- active | paused | archived
    last_enriched   TIMESTAMPTZ,
    last_analyzed   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_accounts_slug ON accounts(slug);
CREATE INDEX idx_accounts_status ON accounts(status);
CREATE INDEX idx_accounts_domain ON accounts(domain);

-- ─── contacts ──────────────────────────────────────────────────
CREATE TABLE contacts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id              UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    name                    TEXT NOT NULL,
    title                   TEXT NOT NULL,
    email                   TEXT,
    linkedin_url            TEXT,
    start_date_current_role DATE,
    previous_company        TEXT,
    previous_title          TEXT,
    buying_role             TEXT NOT NULL DEFAULT 'unknown',
    buying_role_confidence  FLOAT NOT NULL DEFAULT 0.5,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(account_id, name, title)
);

CREATE INDEX idx_contacts_account ON contacts(account_id);

-- ─── linkedin_posts ────────────────────────────────────────────
CREATE TABLE linkedin_posts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id  UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    post_date   DATE NOT NULL,
    text        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(contact_id, post_date, md5(text))
);

CREATE INDEX idx_linkedin_posts_contact ON linkedin_posts(contact_id);

-- ─── signals ───────────────────────────────────────────────────
CREATE TABLE signals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id          UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    signal_type         TEXT NOT NULL,
    signal_category     TEXT,                -- 'financial', 'hiring', 'technology', 'organizational', 'competitive', 'absence'
    summary             TEXT NOT NULL,
    evidence            TEXT,                -- Supporting text/quotes
    typed_data          JSONB,               -- Schema varies by signal_type (discriminated unions)
    source              TEXT NOT NULL DEFAULT 'manual',
    detected_date       DATE NOT NULL,
    event_date          DATE,                -- When the event actually happened (may differ from detection)
    confidence          TEXT NOT NULL DEFAULT 'extracted',  -- 'extracted' | 'interpolated' | 'inferred'
    source_content_ids  UUID[],              -- Which content_items this signal was derived from
    decay_profile       TEXT,                -- References SIGNAL_DECAY_CONFIG key
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    status              TEXT NOT NULL DEFAULT 'active',  -- 'active' | 'resolved' | 'superseded' | 'expired'
    superseded_by       UUID REFERENCES signals(id),
    raw_response_id     UUID REFERENCES raw_responses(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(account_id, signal_type, detected_date, md5(summary))
);

CREATE INDEX idx_signals_account ON signals(account_id);
CREATE INDEX idx_signals_type ON signals(signal_type);
CREATE INDEX idx_signals_date ON signals(detected_date);
CREATE INDEX idx_signals_active ON signals(account_id, is_active) WHERE is_active = TRUE;

-- ─── content_items ─────────────────────────────────────────────
CREATE TABLE content_items (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id              UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    source_type             TEXT NOT NULL,       -- 'blog_post', 'press_release', 'job_listing', 'news_article'
    content_category        TEXT,                -- 'technical', 'hiring', 'financial', 'thought_leadership', 'product', 'company_news'
    relevance               TEXT DEFAULT 'medium', -- 'high', 'medium', 'low'
    url                     TEXT,
    title                   TEXT,
    author                  TEXT,
    author_role             TEXT,
    publish_date            DATE NOT NULL,
    body_text               TEXT NOT NULL,
    word_count              INT,
    is_authored             BOOLEAN NOT NULL DEFAULT FALSE,
    extracted_data          JSONB,               -- Full ExtractionResult from extraction pipeline
    extraction_model        TEXT,                -- Which LLM model extracted this
    extraction_confidence   FLOAT,               -- 0.0-1.0 extraction quality
    first_seen              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status                  TEXT NOT NULL DEFAULT 'active',  -- 'active', 'gone', 'redirected', 'changed'
    raw_response_id         UUID REFERENCES raw_responses(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(account_id, source_type, publish_date, md5(body_text))
);

CREATE INDEX idx_content_account ON content_items(account_id);
CREATE INDEX idx_content_type ON content_items(source_type);
CREATE INDEX idx_content_date ON content_items(publish_date);
CREATE INDEX idx_content_status ON content_items(account_id, status) WHERE status = 'active';

-- ─── analyses ──────────────────────────────────────────────────
CREATE TABLE analyses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id          UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    status              TEXT NOT NULL DEFAULT 'pending',  -- pending | running | complete | failed
    prompt_version      TEXT NOT NULL DEFAULT 'v1',
    llm_backend         TEXT,          -- 'anthropic' | 'local' | model name
    stage1_results      JSONB,
    stage2_result       JSONB,
    stage3_results      JSONB,         -- Array of PersonAnalysis
    stage4_result       JSONB,
    scores              JSONB,         -- ScoreBreakdown
    why_now             JSONB,
    confidence          JSONB,
    journey_position    FLOAT,
    journey_label       TEXT,
    journey_velocity    TEXT,
    total_input_tokens  INT NOT NULL DEFAULT 0,
    total_output_tokens INT NOT NULL DEFAULT 0,
    total_api_calls     INT NOT NULL DEFAULT 0,
    estimated_cost_usd  FLOAT NOT NULL DEFAULT 0.0,
    limited_analysis    BOOLEAN NOT NULL DEFAULT FALSE,
    limited_reason      TEXT,
    error_message       TEXT,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_analyses_account ON analyses(account_id);
CREATE INDEX idx_analyses_status ON analyses(status);
CREATE INDEX idx_analyses_created ON analyses(created_at DESC);

-- ─── dossiers ──────────────────────────────────────────────────
CREATE TABLE dossiers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dossier_id          TEXT UNIQUE NOT NULL,  -- PRISM-YYYY-NNNN format
    account_id          UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    analysis_id         UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    markdown_content    TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dossiers_account ON dossiers(account_id);
CREATE INDEX idx_dossiers_analysis ON dossiers(analysis_id);

-- ─── enrichment_log ────────────────────────────────────────────
-- Tracks every enrichment attempt for debugging and audit
CREATE TABLE enrichment_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id  UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    source      TEXT NOT NULL,  -- 'apollo' | 'crunchbase' | 'builtwith' | 'scraper'
    status      TEXT NOT NULL,  -- 'success' | 'failed' | 'partial'
    items_added INT NOT NULL DEFAULT 0,
    error       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_enrichment_account ON enrichment_log(account_id);
```

### Pydantic ↔ SQLAlchemy Mapping Strategy

Don't use SQLModel (adds complexity). Keep Pydantic models for API/validation and separate SQLAlchemy models for persistence. Map between them in the DAL.

```python
# Pydantic model (existing — unchanged)
class Account(BaseModel):
    slug: str
    company_name: str
    domain: str
    firmographics: Firmographics
    tech_stack: TechStack

# SQLAlchemy model (new)
class AccountRow(Base):
    __tablename__ = "accounts"
    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    slug = Column(Text, unique=True, nullable=False)
    company_name = Column(Text, nullable=False)
    domain = Column(Text, nullable=False)
    firmographics = Column(JSONB, nullable=False, server_default="{}")
    tech_stack = Column(JSONB, nullable=False, server_default="{}")
    ...

# Conversion in DAL
def row_to_account(row: AccountRow) -> Account:
    return Account(
        slug=row.slug,
        company_name=row.company_name,
        domain=row.domain,
        firmographics=Firmographics(**row.firmographics),
        tech_stack=TechStack(**row.tech_stack),
        blog_url=row.blog_url,
        blog_rss=row.blog_rss,
    )
```

---

## 3. Interface 3: Data Access Layer (DAL)

### Problem

Phase 0's `data/loader.py` reads directly from fixture JSON files. v1 needs to read/write from a database, with fixtures as a seed mechanism for dev/demo.

### Interface Definition

```python
# prism/data/dal.py

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional
from uuid import UUID


class DataAccessLayer(ABC):
    """Abstract data access interface.

    Implementations:
    - DatabaseDAL: reads/writes PostgreSQL (production)
    - FixtureDAL: reads fixture JSON files (dev/testing, read-only)
    """

    # ─── Accounts ───────────────────────────────────────────────

    @abstractmethod
    async def get_account(self, slug: str) -> Optional[Account]:
        """Load account by slug. Returns None if not found."""
        ...

    @abstractmethod
    async def get_account_by_id(self, account_id: UUID) -> Optional[Account]:
        ...

    @abstractmethod
    async def list_accounts(
        self,
        status: str = "active",
        limit: int = 100,
        offset: int = 0,
    ) -> list[Account]:
        """List accounts, filtered by status, paginated."""
        ...

    @abstractmethod
    async def upsert_account(self, account: Account) -> UUID:
        """Create or update account. Returns account ID.
        Upsert on slug — if slug exists, update; otherwise create.
        """
        ...

    @abstractmethod
    async def update_account_status(self, slug: str, status: str) -> None:
        ...

    # ─── Contacts ───────────────────────────────────────────────

    @abstractmethod
    async def get_contacts(self, account_id: UUID) -> list[ContactRecord]:
        """All contacts for an account, with LinkedIn posts loaded."""
        ...

    @abstractmethod
    async def upsert_contact(self, account_id: UUID, contact: ContactRecord) -> UUID:
        """Create or update contact. Upsert on (account_id, name, title)."""
        ...

    @abstractmethod
    async def add_linkedin_posts(
        self, contact_id: UUID, posts: list[LinkedInPost]
    ) -> int:
        """Add LinkedIn posts for a contact. Returns count of new posts added.
        Skips duplicates (same date + text hash).
        """
        ...

    # ─── Signals ────────────────────────────────────────────────

    @abstractmethod
    async def get_signals(self, account_id: UUID) -> list[Signal]:
        """All signals for an account, ordered by detected_date DESC."""
        ...

    @abstractmethod
    async def add_signals(self, account_id: UUID, signals: list[Signal]) -> int:
        """Add signals. Returns count of new signals added.
        Skips duplicates (same type + date + description hash).
        """
        ...

    # ─── Content ────────────────────────────────────────────────

    @abstractmethod
    async def get_content(
        self,
        account_id: UUID,
        source_type: Optional[str] = None,
        limit: int = 30,
    ) -> list[ContentItem]:
        """Content items for an account, ordered by publish_date DESC.
        Optionally filter by source_type.
        """
        ...

    @abstractmethod
    async def add_content(
        self, account_id: UUID, items: list[ContentItem]
    ) -> int:
        """Add content items. Returns count of new items added.
        Skips duplicates (same source_type + date + text hash).
        """
        ...

    # ─── Analyses ───────────────────────────────────────────────

    @abstractmethod
    async def create_analysis(self, account_id: UUID, prompt_version: str) -> UUID:
        """Create a new analysis record in 'pending' status. Returns analysis ID."""
        ...

    @abstractmethod
    async def update_analysis(
        self,
        analysis_id: UUID,
        *,
        status: Optional[str] = None,
        stage1_results: Optional[list[dict]] = None,
        stage2_result: Optional[dict] = None,
        stage3_results: Optional[list[dict]] = None,
        stage4_result: Optional[dict] = None,
        scores: Optional[dict] = None,
        why_now: Optional[dict] = None,
        confidence: Optional[dict] = None,
        journey_position: Optional[float] = None,
        journey_label: Optional[str] = None,
        total_input_tokens: Optional[int] = None,
        total_output_tokens: Optional[int] = None,
        estimated_cost_usd: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update analysis fields. Only non-None fields are updated.
        This enables checkpoint saving after each stage.
        """
        ...

    @abstractmethod
    async def get_latest_analysis(self, account_id: UUID) -> Optional[AnalyzedAccount]:
        """Get most recent completed analysis for an account."""
        ...

    @abstractmethod
    async def get_analysis_history(
        self, account_id: UUID, limit: int = 10
    ) -> list[AnalyzedAccount]:
        """Get analysis history for an account, most recent first."""
        ...

    # ─── Dossiers ───────────────────────────────────────────────

    @abstractmethod
    async def save_dossier(
        self,
        dossier_id: str,
        account_id: UUID,
        analysis_id: UUID,
        markdown_content: str,
    ) -> UUID:
        ...

    @abstractmethod
    async def get_dossier(self, dossier_id: str) -> Optional[str]:
        """Get dossier markdown content by PRISM-YYYY-NNNN ID."""
        ...

    @abstractmethod
    async def get_latest_dossier(self, account_id: UUID) -> Optional[str]:
        """Get most recent dossier for an account."""
        ...

    # ─── Raw Responses ───────────────────────────────────────────

    @abstractmethod
    async def write_raw_response(
        self,
        account_id: Optional[UUID],
        source_type: str,
        url: Optional[str],
        http_status: Optional[int],
        raw_headers: Optional[dict],
        raw_body: Optional[str],
        response_size_bytes: Optional[int] = None,
    ) -> UUID:
        """Store raw HTTP response for audit/reprocessing. Returns response ID."""
        ...

    @abstractmethod
    async def get_raw_response(self, response_id: UUID) -> Optional[dict]:
        """Retrieve raw response by ID for reprocessing."""
        ...

    # ─── Enrichment Log ─────────────────────────────────────────

    @abstractmethod
    async def log_enrichment(
        self,
        account_id: UUID,
        source: str,
        status: str,
        items_added: int = 0,
        error: Optional[str] = None,
    ) -> None:
        ...

    # ─── Scheduler Queries ───────────────────────────────────────

    @abstractmethod
    async def get_accounts_for_reanalysis(
        self, max_signal_age_days: int = 7
    ) -> list[Account]:
        """Get active accounts with signals newer than max_signal_age_days."""
        ...

    @abstractmethod
    async def get_stale_accounts(
        self, stale_after_days: int = 30
    ) -> list[Account]:
        """Get active accounts not analyzed in stale_after_days."""
        ...

    @abstractmethod
    async def get_account_by_domain(self, domain: str) -> Optional[Account]:
        """Look up account by domain (needed for enrichment)."""
        ...

    # ─── Content Queries ─────────────────────────────────────────

    @abstractmethod
    async def get_content_by_url(self, url: str) -> Optional[ContentItem]:
        """Check if content already exists by URL (deduplication)."""
        ...

    @abstractmethod
    async def update_content_status(
        self, content_id: UUID, status: str
    ) -> None:
        """Update content item status (active → gone/redirected/changed)."""
        ...
```

### FixtureDAL (wraps existing loader.py — read-only)

```python
# prism/data/fixture_dal.py

class FixtureDAL(DataAccessLayer):
    """Read-only DAL that loads from fixture JSON files.

    Used for testing and development. Write methods raise NotImplementedError.
    This is a thin wrapper around the existing data/loader.py functions.
    """

    async def get_account(self, slug: str) -> Optional[Account]:
        return load_account(slug)  # Existing function

    async def list_accounts(self, **kwargs) -> list[Account]:
        slugs = list_companies()   # Existing function
        return [load_account(s) for s in slugs if load_account(s)]

    async def upsert_account(self, account: Account) -> UUID:
        raise NotImplementedError("FixtureDAL is read-only")

    # ... etc — read methods delegate to loader.py,
    #           write methods raise NotImplementedError
```

### DatabaseDAL

```python
# prism/data/database_dal.py

class DatabaseDAL(DataAccessLayer):
    """Production DAL backed by PostgreSQL via async SQLAlchemy.

    All methods use the injected async session.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_account(self, slug: str) -> Optional[Account]:
        result = await self._session.execute(
            select(AccountRow).where(AccountRow.slug == slug)
        )
        row = result.scalar_one_or_none()
        return row_to_account(row) if row else None

    async def upsert_account(self, account: Account) -> UUID:
        # Use INSERT ... ON CONFLICT (slug) DO UPDATE
        ...

    # ... full implementation of all abstract methods
```

### DAL Factory

```python
# prism/data/__init__.py

async def get_dal() -> DataAccessLayer:
    """Factory that returns the appropriate DAL based on config.

    Uses DATABASE_URL if configured, otherwise falls back to FixtureDAL.
    """
    if config.DATABASE_URL:
        session = await get_async_session()
        return DatabaseDAL(session)
    return FixtureDAL()
```

---

## 4. Interface 4: Enrichment Services

### Problem

Phase 0 uses hand-entered fixture data. v1 needs pluggable enrichment sources that can be added/removed without touching the analysis pipeline.

### Interface Definition

```python
# prism/services/enrichment/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EnrichmentResult:
    """Standardized result from any enrichment source."""
    source: str                              # 'apollo', 'crunchbase', 'scraper', etc.
    account_updates: Optional[dict] = None   # Firmographics/tech stack updates
    contacts: list[ContactRecord] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    content_items: list[ContentItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class EnrichmentSource(ABC):
    """Abstract interface for data enrichment sources.

    Each source is optional. If the API key is not configured,
    is_available() returns False and the orchestrator skips it.
    """

    @abstractmethod
    def source_name(self) -> str:
        """Human-readable source name for logging."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """True if this source is configured and ready (API key present, etc.)."""
        ...

    @abstractmethod
    async def enrich(self, domain: str, existing_account: Optional[Account] = None) -> EnrichmentResult:
        """Enrich a company by domain.

        Args:
            domain: Company domain (e.g., 'velocitypay.com').
            existing_account: If we already have data, pass it so the source
                can avoid redundant lookups and merge intelligently.

        Returns:
            EnrichmentResult with whatever data this source can provide.
        """
        ...
```

### Concrete Implementations

```python
# prism/services/enrichment/apollo.py

class ApolloEnrichment(EnrichmentSource):
    """Contact and firmographic enrichment via Apollo API.

    Provides: contacts (name, title, email, LinkedIn), company firmographics
    (headcount, funding, industry), and some signals (funding rounds, hires).
    """

    def source_name(self) -> str:
        return "apollo"

    def is_available(self) -> bool:
        return bool(config.APOLLO_API_KEY)

    async def enrich(self, domain: str, existing_account=None) -> EnrichmentResult:
        # 1. POST /v1/mixed_people/search with domain filter
        # 2. For each person: normalize into ContactRecord
        # 3. GET /v1/organizations/enrich?domain=...
        # 4. Map firmographics into account_updates dict
        # 5. Detect signals (new funding, new hires) from Apollo data
        ...
```

```python
# prism/services/enrichment/blog_scraper.py

class BlogScraperEnrichment(EnrichmentSource):
    """Blog content enrichment via RSS/HTML scraping.

    Wraps the existing services/scraper.py BlogScraper.
    """

    def source_name(self) -> str:
        return "blog_scraper"

    def is_available(self) -> bool:
        return True  # Always available — no API key needed

    async def enrich(self, domain: str, existing_account=None) -> EnrichmentResult:
        # 1. Use existing BlogScraper to scrape
        # 2. Wrap results in EnrichmentResult
        ...
```

```python
# prism/services/enrichment/job_boards.py

class JobBoardEnrichment(EnrichmentSource):
    """Job posting enrichment from Greenhouse/Lever APIs.

    Detects finance/accounting hiring signals. These APIs are
    public (no auth required for published job boards).
    """

    def source_name(self) -> str:
        return "job_boards"

    def is_available(self) -> bool:
        return True  # Public APIs, always available

    async def enrich(self, domain: str, existing_account=None) -> EnrichmentResult:
        # 1. Try https://boards-api.greenhouse.io/v1/boards/{company}/jobs
        # 2. Try https://api.lever.co/v0/postings/{company}
        # 3. Filter for finance/accounting keywords in title/description
        # 4. Create signals: job_posting_finance, job_posting_technical
        # 5. Create content_items with full job posting text
        ...
```

```python
# prism/services/enrichment/crunchbase.py
# prism/services/enrichment/builtwith.py
# prism/services/enrichment/proxycurl.py
# ... additional sources follow the same pattern
```

### Enrichment Orchestrator

```python
# prism/services/enrichment/orchestrator.py

class EnrichmentOrchestrator:
    """Runs all available enrichment sources for a company.

    Merges results, deduplicates, and persists to the DAL.
    """

    def __init__(self, dal: DataAccessLayer, sources: list[EnrichmentSource] = None):
        self._dal = dal
        self._sources = sources or self._discover_sources()

    def _discover_sources(self) -> list[EnrichmentSource]:
        """Auto-discover available sources based on configuration."""
        all_sources = [
            ApolloEnrichment(),
            BlogScraperEnrichment(),
            JobBoardEnrichment(),
            CrunchbaseEnrichment(),
            BuiltWithEnrichment(),
            ProxycurlEnrichment(),
        ]
        return [s for s in all_sources if s.is_available()]

    async def enrich_company(self, domain: str, slug: Optional[str] = None) -> dict:
        """Run all available enrichment sources for a company.

        Args:
            domain: Company domain.
            slug: Optional slug (if account already exists).

        Returns:
            Summary dict with counts of items added per source.
        """
        existing = await self._dal.get_account(slug) if slug else None
        summary = {}

        for source in self._sources:
            try:
                result = await source.enrich(domain, existing_account=existing)
                added = await self._persist_result(result, slug or domain)
                summary[source.source_name()] = added

                await self._dal.log_enrichment(
                    account_id=...,
                    source=source.source_name(),
                    status="success",
                    items_added=sum(added.values()),
                )
            except Exception as e:
                logger.warning("Enrichment source %s failed: %s", source.source_name(), e)
                summary[source.source_name()] = {"error": str(e)}
                await self._dal.log_enrichment(
                    account_id=...,
                    source=source.source_name(),
                    status="failed",
                    error=str(e),
                )

        return summary

    async def _persist_result(self, result: EnrichmentResult, slug: str) -> dict:
        """Persist enrichment results to DAL. Returns counts."""
        counts = {}

        if result.account_updates:
            # Merge firmographics/tech_stack updates
            ...

        if result.contacts:
            for contact in result.contacts:
                await self._dal.upsert_contact(account_id, contact)
            counts["contacts"] = len(result.contacts)

        if result.signals:
            counts["signals"] = await self._dal.add_signals(account_id, result.signals)

        if result.content_items:
            counts["content"] = await self._dal.add_content(account_id, result.content_items)

        return counts
```

---

## 5. API Layer Spec

### Endpoints

```
GET    /health                              # Liveness + DB check

GET    /accounts                            # List tracked companies (paginated)
POST   /accounts                            # Add company by domain
GET    /accounts/{slug}                     # Account detail + latest scores
PATCH  /accounts/{slug}                     # Update account data
DELETE /accounts/{slug}                     # Archive (soft delete)

POST   /accounts/{slug}/enrich              # Trigger enrichment from all sources
POST   /accounts/{slug}/analyze             # Trigger full analysis pipeline
GET    /accounts/{slug}/analyses            # Analysis history
GET    /accounts/{slug}/analyses/latest     # Most recent analysis

POST   /accounts/{slug}/content             # Upload content manually
GET    /accounts/{slug}/content             # List content items

GET    /accounts/{slug}/signals             # List signals with decay weights
POST   /accounts/{slug}/signals             # Add signals manually

GET    /accounts/{slug}/contacts            # List contacts
POST   /accounts/{slug}/contacts            # Add/update contacts

GET    /dossiers/{dossier_id}               # Retrieve dossier by PRISM-YYYY-NNNN
GET    /accounts/{slug}/dossier             # Latest dossier for account
```

### Request/Response Schemas

```python
# POST /accounts
class CreateAccountRequest(BaseModel):
    domain: str                          # Required
    company_name: Optional[str] = None   # Auto-discovered if not provided
    slug: Optional[str] = None           # Auto-generated from domain if not provided
    auto_enrich: bool = True             # Trigger enrichment immediately
    auto_analyze: bool = False           # Trigger analysis after enrichment

class CreateAccountResponse(BaseModel):
    slug: str
    account_id: UUID
    status: str
    enrichment_job_id: Optional[UUID] = None

# POST /accounts/{slug}/analyze
class AnalyzeResponse(BaseModel):
    analysis_id: UUID
    status: str  # "pending" — poll for completion

# GET /accounts/{slug}
class AccountDetailResponse(BaseModel):
    slug: str
    company_name: str
    domain: str
    firmographics: dict
    tech_stack: dict
    latest_scores: Optional[ScoreBreakdown] = None
    latest_tier: Optional[str] = None
    last_analyzed: Optional[datetime] = None
    signal_count: int
    content_count: int
    contact_count: int
```

### Auth

Simple API key auth for v1:

```python
# prism/api/deps.py

API_KEYS = config.API_KEYS  # List of valid keys from env

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

---

## 6. Task Queue & Scheduling

### Task Definitions (using arq)

```python
# prism/tasks.py

async def enrich_company_task(ctx, slug: str) -> dict:
    """Background: run all enrichment sources for a company."""
    dal = await get_dal()
    orchestrator = EnrichmentOrchestrator(dal)
    return await orchestrator.enrich_company(domain, slug=slug)

async def analyze_company_task(ctx, slug: str) -> UUID:
    """Background: run full Content Intelligence pipeline."""
    dal = await get_dal()
    llm = get_llm_backend()  # From config — Anthropic or Local
    # ... same logic as cli.py _analyze_company, but persists to DB
    return analysis_id

async def full_pipeline_task(ctx, slug: str) -> dict:
    """Background: enrich → scrape → analyze → render dossier."""
    await enrich_company_task(ctx, slug)
    analysis_id = await analyze_company_task(ctx, slug)
    # Render and persist dossier
    return {"analysis_id": analysis_id, "status": "complete"}
```

### Scheduled Jobs

```python
# Scheduled via arq cron or APScheduler

# Daily: re-analyze active accounts with recent signals
async def daily_reanalyze():
    dal = await get_dal()
    accounts = await dal.list_accounts(status="active")
    for account in accounts:
        signals = await dal.get_signals(account.id)
        has_recent = any(
            (date.today() - s.detected_date).days < 7 for s in signals
        )
        if has_recent:
            await enqueue("analyze_company_task", account.slug)

# Weekly: re-scrape blogs
async def weekly_scrape():
    dal = await get_dal()
    accounts = await dal.list_accounts(status="active")
    for account in accounts:
        if account.blog_url or account.blog_rss:
            await enqueue("enrich_company_task", account.slug)

# Monthly: full re-enrichment
async def monthly_enrich():
    dal = await get_dal()
    accounts = await dal.list_accounts(status="active")
    for account in accounts:
        await enqueue("full_pipeline_task", account.slug)
```

---

## 7. Migration Path from Phase 0

### What stays unchanged

| Component | File | Changes |
|-----------|------|---------|
| Pydantic models | `models/*.py` | None — become API schemas as-is |
| Scoring engine | `analysis/scoring.py` | None |
| Signal decay | `analysis/signal_decay.py` | None |
| Dossier renderer | `output/dossier.py` | Add optional HTML output |
| Prompt templates | `prompts/v1/*.txt` | None |
| Config weights | `config.py` (weights section) | None |
| Product definition | `data/product.py` | None |

### What gets refactored

| Component | Current | v1 |
|-----------|---------|-----|
| `services/llm.py` | Anthropic-only, sync-wrapped | Refactor into `LLMBackend` interface + `AnthropicBackend` |
| `data/loader.py` | Fixture-only reads | Wrap in `FixtureDAL`, add `DatabaseDAL` |
| `cli.py` | Monolithic orchestrator | Extract pipeline logic into shared `pipeline.py`, CLI and API both call it |
| `analysis/content_intel.py` | Takes `LLMService` | Takes `LLMBackend` interface instead |
| `config.py` | Env vars only | Add DB, API, enrichment config sections |

### What's new

| Component | Purpose |
|-----------|---------|
| `prism/db/` | SQLAlchemy models, Alembic migrations, session management |
| `prism/data/dal.py` | Data Access Layer interface |
| `prism/data/database_dal.py` | PostgreSQL DAL implementation |
| `prism/data/fixture_dal.py` | Fixture DAL (wraps existing loader.py) |
| `prism/services/llm_backend.py` | LLM backend interface |
| `prism/services/backends/` | Anthropic, Local, Router implementations |
| `prism/services/enrichment/` | Enrichment source interface + implementations |
| `prism/api/` | FastAPI app, routes, schemas, auth |
| `prism/tasks.py` | Background task definitions |
| `prism/pipeline.py` | Shared pipeline logic (used by CLI and API) |

---

## 8. File Structure (v1)

```
prism/
├── CLAUDE.md
├── pyproject.toml
├── alembic.ini
├── alembic/
│   └── versions/
│
├── prism/
│   ├── __init__.py
│   ├── cli.py                          # Stays — dev/power user tool
│   ├── config.py                       # Extended with DB, API, enrichment config
│   ├── pipeline.py                     # NEW — shared pipeline logic
│   │
│   ├── models/                         # UNCHANGED
│   │   ├── account.py
│   │   ├── contact.py
│   │   ├── content.py
│   │   ├── signal.py
│   │   ├── analysis.py
│   │   └── activation.py
│   │
│   ├── db/                             # NEW — persistence
│   │   ├── __init__.py
│   │   ├── models.py                   # SQLAlchemy table definitions
│   │   ├── session.py                  # Async session factory
│   │   └── migrations/                 # Alembic
│   │
│   ├── data/                           # REFACTORED
│   │   ├── __init__.py                 # DAL factory (get_dal())
│   │   ├── dal.py                      # Abstract DAL interface
│   │   ├── database_dal.py             # PostgreSQL implementation
│   │   ├── fixture_dal.py              # Fixture loader (wraps existing)
│   │   ├── loader.py                   # KEPT — used by FixtureDAL
│   │   └── product.py                  # UNCHANGED
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_backend.py              # NEW — abstract LLM interface
│   │   ├── llm_cache.py                # NEW — response caching
│   │   ├── llm.py                      # KEPT — legacy, used by FixtureDAL path
│   │   ├── scraper.py                  # UNCHANGED
│   │   ├── backends/                   # NEW
│   │   │   ├── __init__.py
│   │   │   ├── anthropic_backend.py
│   │   │   ├── local_backend.py
│   │   │   └── router.py
│   │   └── enrichment/                 # NEW
│   │       ├── __init__.py
│   │       ├── base.py                 # EnrichmentSource interface
│   │       ├── orchestrator.py
│   │       ├── apollo.py
│   │       ├── blog_scraper.py         # Wraps existing scraper.py
│   │       ├── job_boards.py
│   │       ├── crunchbase.py
│   │       ├── builtwith.py
│   │       └── proxycurl.py
│   │
│   ├── analysis/                       # MINIMAL CHANGES
│   │   ├── content_intel.py            # LLMService → LLMBackend
│   │   ├── scoring.py                  # UNCHANGED
│   │   └── signal_decay.py             # UNCHANGED
│   │
│   ├── api/                            # NEW
│   │   ├── __init__.py                 # FastAPI app
│   │   ├── deps.py                     # Auth, DB session injection
│   │   ├── schemas.py                  # Request/response models
│   │   └── routes/
│   │       ├── health.py
│   │       ├── accounts.py
│   │       ├── content.py
│   │       ├── analyses.py
│   │       └── dossiers.py
│   │
│   ├── tasks.py                        # NEW — background job definitions
│   │
│   ├── prompts/v1/                     # UNCHANGED
│   │   ├── stage1_extraction.txt
│   │   ├── stage2_synthesis.txt
│   │   ├── stage3_person.txt
│   │   ├── stage4_scoring.txt
│   │   └── activation_angle.txt
│   │
│   └── output/
│       └── dossier.py                  # UNCHANGED
│
├── fixtures/                           # KEPT — seed data
├── output/dossiers/                    # KEPT — file backup
├── tests/
│   ├── test_scoring.py                 # UNCHANGED
│   ├── test_signal_decay.py            # UNCHANGED
│   ├── test_dossier.py                 # UNCHANGED
│   ├── test_content_intel.py           # UNCHANGED
│   ├── test_dal.py                     # NEW
│   ├── test_api.py                     # NEW
│   ├── test_enrichment.py              # NEW
│   └── test_pipeline.py               # NEW — E2E
└── docs/
    ├── V1_BUILD_PLAN.md                # This file
    └── ...
```

---

## 9. Dependencies

### Phase 0 (current)
```
pydantic>=2.0,<3.0
httpx>=0.25.0
beautifulsoup4>=4.12.0
anthropic>=0.39.0
click>=8.1.0
rich>=13.0.0
python-dotenv>=1.0.0
lxml>=4.9.0
```

### v1 additions
```
# Database
sqlalchemy[asyncio]>=2.0
asyncpg>=0.29.0
alembic>=1.13.0

# API
fastapi>=0.110
uvicorn[standard]>=0.27.0
pydantic-settings>=2.0

# Task queue (pick one)
arq>=0.26                    # Lightweight — recommended for v1
# OR celery>=5.3 + redis>=5.0  # Heavier — if you outgrow arq

# Scraper upgrade
trafilatura>=1.8.0           # Better article text extraction
playwright>=1.40.0           # JS-rendered blog fallback

# Testing
pytest-postgresql>=5.0       # DB integration tests
```

### Optional enrichment dependencies (install only if using)
```
# No additional deps — all enrichment uses httpx (already installed)
```

---

## 10. Configuration

### New environment variables for v1

```bash
# ─── Database ───────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/prism

# ─── API ────────────────────────────────────────────────────────
API_HOST=0.0.0.0
API_PORT=8000
API_KEYS=key1,key2,key3          # Comma-separated valid API keys
CORS_ORIGINS=http://localhost:3000

# ─── LLM Backend ───────────────────────────────────────────────
LLM_BACKEND=anthropic             # 'anthropic' | 'local' | 'router'
LLM_LOCAL_URL=http://localhost:8080  # For local inference
LLM_LOCAL_MODEL=glm-5               # Model name for local server
LLM_MAX_SPEND_USD=100.0             # Budget cap (Anthropic only)

# ─── Enrichment API Keys ───────────────────────────────────────
APOLLO_API_KEY=                   # Optional — skip Apollo if empty
CRUNCHBASE_API_KEY=               # Optional
BUILTWITH_API_KEY=                # Optional
PROXYCURL_API_KEY=                # Optional

# ─── Existing (unchanged) ──────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...
PRISM_MODEL=claude-sonnet-4-20250514
PRISM_PROMPT_VERSION=v1
PRISM_MAX_CORPUS_ITEMS=30
PRISM_MAX_PERSON_POSTS=20
PRISM_LOG_LEVEL=INFO
```

### Config loading (extend existing `config.py`)

```python
# New section in config.py

# ─── Database ───────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "")

# ─── API ────────────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_KEYS = [k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()]
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

# ─── LLM Backend ───────────────────────────────────────────────
LLM_BACKEND = os.getenv("LLM_BACKEND", "anthropic")
LLM_LOCAL_URL = os.getenv("LLM_LOCAL_URL", "http://localhost:8080")
LLM_LOCAL_MODEL = os.getenv("LLM_LOCAL_MODEL", "local-model")
LLM_MAX_SPEND_USD = float(os.getenv("LLM_MAX_SPEND_USD", "100.0"))

# ─── Enrichment ─────────────────────────────────────────────────
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
CRUNCHBASE_API_KEY = os.getenv("CRUNCHBASE_API_KEY", "")
BUILTWITH_API_KEY = os.getenv("BUILTWITH_API_KEY", "")
PROXYCURL_API_KEY = os.getenv("PROXYCURL_API_KEY", "")
```
