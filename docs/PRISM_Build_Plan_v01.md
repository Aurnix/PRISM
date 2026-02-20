# GTM Signal Engine — Complete Build Plan
## Codename: PRISM (Predictive Revenue Intelligence & Signal Mapping)

**Author:** Joseph Sherman  
**Version:** 0.1-draft  
**Date:** February 2026  
**Purpose:** Full architecture and build specification for AI-powered GTM signal engine with proprietary content intelligence layer.

---

## System Overview

PRISM is a multi-agent pipeline that discovers, enriches, analyzes, and activates B2B sales targets. It combines standard firmographic/technographic enrichment with a proprietary **Content Intelligence Layer** — an LLM-based analytical engine that extracts sub-semantic organizational signals from public content to assess buying readiness, map decision-maker psychology, and generate contextual outreach strategies.

### What Makes This Different

Every GTM tool has access to the same data sources (Crunchbase, Apollo, BuiltWith, etc.). PRISM's differentiation is the Content Intelligence Layer — it processes the same public content everyone can read (blog posts, LinkedIn, job descriptions, press releases) and extracts signals that keyword matching and topic classification cannot detect:

- **Buying journey position** inferred from narrative trajectory of public communications
- **Organizational stress indicators** from language pattern shifts over time
- **Pain signal coherence** — whether scattered complaints have crystallized into defined problems
- **Solution sophistication** — how articulate the org is about what they need
- **Stated vs. actual priorities** — structural analysis of what gets emphasis vs. what gets buried
- **Absence analysis** — what they conspicuously don't talk about

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                                 │
│           (Task scheduling, pipeline coordination, state mgmt)      │
└────────┬──────────┬──────────┬──────────┬──────────┬───────────────┘
         │          │          │          │          │
         ▼          ▼          ▼          ▼          ▼
┌─────────┐ ┌───────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
│ DISCOVER │ │  ENRICH   │ │ANALYZE │ │ ACTIVATE │ │ FEEDBACK │
│  Agent   │ │  Agents   │ │ Agent  │ │  Agent   │ │   Loop   │
│          │ │           │ │        │ │          │ │          │
│ Find     │ │ Company   │ │Content │ │Play      │ │Outcome   │
│ target   │ │ People    │ │Intel   │ │Selection │ │tracking  │
│ accounts │ │ Content   │ │ICP     │ │Angle gen │ │Score     │
│          │ │ Tech      │ │Scoring │ │CRM fmt   │ │recalib   │
│          │ │ Compete   │ │Decider │ │Routing   │ │Signal    │
│          │ │           │ │mapping │ │          │ │decay     │
└─────────┘ └───────────┘ └────────┘ └──────────┘ └──────────┘
```

---

## Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Backend/API** | Python + FastAPI (async) | Matches existing GeoTrack stack, async critical for parallel API calls |
| **Database** | PostgreSQL + SQLAlchemy 2.0 | Structured data, JSONB for flexible signal storage, proven at scale |
| **Cache/Queue** | Redis | Rate limit management, job queuing, signal freshness TTLs |
| **LLM Processing** | Claude API (primary), OpenAI API (fallback/cross-validation) | Claude for deep analysis, cross-model validation for high-confidence signals |
| **Task Orchestration** | Celery + Redis (or lightweight custom) | Async pipeline stages, retry logic, rate limit backoff |
| **Frontend/Dashboard** | Next.js 14 + TypeScript + Tailwind | Matches GeoTrack stack, React ecosystem |
| **Containerization** | Docker Compose | Local dev + deployment parity |
| **Testing** | pytest + coverage | Consistent with GeoTrack approach |

---

## Phase 1: DISCOVER Agent

### Purpose
Identify target companies that match broad ICP filters before expensive enrichment.

### Data Sources

| Source | What It Provides | Access Method | Cost |
|--------|-----------------|---------------|------|
| **Crunchbase** | Funding, headcount, industry, investors | API (Basic: free tier, Pro: $49/mo) | $ |
| **PitchBook** | Deeper funding data, board, financials | API (enterprise, expensive) | $$$$ |
| **Y Combinator directory** | Batch companies, stage, description | Scrape (public) | Free |
| **LinkedIn Sales Nav** | Company search, headcount, growth | API (restricted) or scrape | $$$ |
| **Job boards** | Hiring signals | Indeed API, scrape career pages | $ |
| **ProductHunt** | New product launches | API | Free |
| **G2/Capterra** | Product reviews, competitor usage | Scrape or API | $$ |

### ICP Filter Schema (Configurable Per Deployment)

```python
class ICPFilter(BaseModel):
    """Defines ideal customer profile for initial discovery filtering."""
    
    # Firmographic
    headcount_min: int = 50
    headcount_max: int = 500
    funding_stages: list[str] = ["Series A", "Series B", "Series C", "Series D"]
    min_funding_raised: int = 5_000_000  # $5M
    industries: list[str] = ["SaaS", "Fintech", "E-commerce", "Marketplace"]
    geo: list[str] = ["US", "CA", "UK"]  # HQ or primary ops
    
    # Exclusions
    exclude_public_companies: bool = True  # Too slow, different buying motion
    exclude_industries: list[str] = ["Government", "Defense"]
    
    # Recency
    last_funding_within_months: int = 18  # Stale funding = likely committed budget
    
    # Signals (any one of these elevates priority)
    boost_signals: list[str] = [
        "hiring_finance_roles",      # Controller, VP Finance, FP&A
        "recent_leadership_change",   # New CFO/VP Finance (< 6 months)
        "tech_stack_migration",       # QuickBooks → NetSuite signals
        "headcount_growth_30pct",     # Scaling pains
    ]
```

### Output Schema

```python
class DiscoveredAccount(BaseModel):
    """Raw account from discovery, pre-enrichment."""
    
    company_name: str
    domain: str
    crunchbase_url: Optional[str]
    linkedin_url: Optional[str]
    
    # Basic firmographics (from discovery source)
    headcount_estimate: Optional[int]
    funding_stage: Optional[str]
    total_raised: Optional[int]
    last_funding_date: Optional[date]
    industry: Optional[str]
    hq_location: Optional[str]
    
    # Discovery metadata
    source: str  # Which discovery channel found this
    discovery_date: date
    icp_filter_version: str  # Track which ICP def was used
    initial_boost_signals: list[str]  # Which boost signals triggered
    
    # Pipeline state
    status: str = "discovered"  # discovered → enriching → analyzed → activated → feedback
```

### What's Missing / Open Questions

- **LinkedIn access**: Official API is locked down. Options: Sales Navigator export, Proxycurl API ($), PhantomBuster, or manual export + CSV ingest. Need to decide.
- **Rate limiting strategy**: Crunchbase free tier = 200 calls/min. Need backoff + caching.
- **Deduplication**: Entity resolution across sources. "Rillet" vs "Rillet, Inc." vs "rillet.com". Need fuzzy matching layer (likely Levenshtein + domain normalization).
- **Volume calibration**: How many accounts per batch? 50? 500? 5000? Affects downstream processing cost.

---

## Phase 2: ENRICH Agents (Parallel Branches)

### Purpose
Build comprehensive dossier on each discovered account. Five parallel enrichment branches, each independently callable and cacheable.

### Branch 2A: Company Enrichment

**Sources:** Crunchbase (detailed), LinkedIn company page, company website/about, Glassdoor

**Output adds to account record:**
```python
class CompanyEnrichment(BaseModel):
    # Detailed firmographics
    founded_year: int
    employee_count: int
    employee_growth_6mo: Optional[float]  # % change
    employee_growth_12mo: Optional[float]
    revenue_estimate: Optional[str]  # Range bucket
    
    # Funding detail
    investors: list[str]
    last_round_amount: Optional[int]
    last_round_date: Optional[date]
    last_round_lead: Optional[str]
    total_funding: int
    
    # Company signals
    description: str
    mission_statement: Optional[str]
    product_categories: list[str]
    
    # Glassdoor signals
    glassdoor_rating: Optional[float]
    glassdoor_trend: Optional[str]  # improving, stable, declining
    ceo_approval: Optional[float]
    # Note: Glassdoor language analysis feeds into Content Intelligence
```

### Branch 2B: Technographic Enrichment

**Sources:** BuiltWith, Wappalyzer, job postings (tech stack mentions), GitHub org

**Output:**
```python
class TechEnrichment(BaseModel):
    # Current stack detection
    crm: Optional[str]  # Salesforce, HubSpot, etc.
    erp_accounting: Optional[str]  # QuickBooks, NetSuite, Sage, etc.
    marketing_automation: Optional[str]
    data_warehouse: Optional[str]
    payment_processor: Optional[str]
    
    # Dev stack (signals engineering culture)
    primary_languages: list[str]
    cloud_provider: Optional[str]
    has_public_api: bool
    github_activity_level: Optional[str]  # active, moderate, minimal, none
    
    # Migration signals (HIGH VALUE)
    stack_changes_detected: list[dict]  # What changed, when, from→to
    job_postings_mentioning_migration: list[str]
    
    # Stack maturity score
    stack_maturity: str  # "early" | "growing" | "mature" | "legacy"
    # early = spreadsheets + QuickBooks (prime target)
    # growing = migrating to real tools (PRIME target)
    # mature = established stack, harder sell
    # legacy = SAP/Oracle, enterprise motion required
```

### Branch 2C: Contact Discovery & People Enrichment

**Sources:** Apollo, LinkedIn (via Proxycurl or similar), company team page, conference speaker lists

**Output:**
```python
class ContactRecord(BaseModel):
    name: str
    title: str
    linkedin_url: Optional[str]
    email: Optional[str]  # Via Apollo or Hunter.io
    
    # Role classification
    buying_role: str  # "champion" | "economic_buyer" | "technical_gatekeeper" | "user" | "unknown"
    buying_role_confidence: float  # 0-1
    
    # Tenure and timing
    start_date_current_role: Optional[date]
    is_new_in_role: bool  # < 6 months = high signal
    previous_company: Optional[str]
    previous_title: Optional[str]
    
    # Engagement signals
    linkedin_post_frequency: Optional[str]  # active, moderate, minimal, none
    recent_topics: list[str]  # What they post about
    conference_appearances: list[str]
    
    # For Content Intelligence processing
    linkedin_posts_corpus: Optional[list[str]]  # Raw text for analysis
    
class BuyingCommittee(BaseModel):
    """Mapped buying committee for the account."""
    
    contacts: list[ContactRecord]
    likely_champion: Optional[str]  # Contact name
    champion_confidence: float
    likely_economic_buyer: Optional[str]
    economic_buyer_confidence: float
    likely_technical_gatekeeper: Optional[str]
    
    # Committee dynamics (inferred)
    champion_ahead_of_org: bool  # Champion's language more urgent than company's
    new_leader_in_seat: bool  # Key buyer < 6 months in role
    committee_alignment: str  # "aligned" | "mixed_signals" | "unknown"
    
    # Missing coverage
    gaps: list[str]  # "No economic buyer identified", etc.
```

### Branch 2D: Content Corpus Assembly

**Sources:** Company blog (RSS/scrape), leadership LinkedIn posts, press releases (news APIs), job descriptions (full text), earnings calls/investor materials, changelog/product updates, support docs/community forums

**This is the critical input for the Content Intelligence Layer.**

```python
class ContentCorpus(BaseModel):
    """Assembled content corpus for a single account."""
    
    account_id: str
    assembly_date: date
    
    items: list[ContentItem]
    
    # Corpus metadata
    total_items: int
    date_range: tuple[date, date]  # Oldest to newest
    source_distribution: dict[str, int]  # {"blog": 12, "linkedin": 8, ...}
    
    # Signal density assessment (pre-analysis)
    estimated_density: str  # "high" | "medium" | "low"
    # high = founder-written, candid, technical
    # medium = mix of genuine and corporate
    # low = generic marketing fluff, agency-produced
    
    # Minimum viable corpus check
    meets_minimum: bool  # Enough content for reliable extraction?
    # Minimum: 10+ items across 3+ months from 2+ source types

class ContentItem(BaseModel):
    source_type: str  # "blog" | "linkedin" | "press" | "job_posting" | "earnings" | "changelog"
    url: str
    title: Optional[str]
    author: Optional[str]  # Critical: author-specific content is higher signal
    publish_date: date
    raw_text: str
    word_count: int
    
    # Content metadata
    is_authored: bool  # Named human author vs. "Company Blog"
    author_role: Optional[str]  # If authored, what's their title?
    signal_density_estimate: str  # Pre-processing estimate
```

**Content Scraping Implementation Notes:**

| Source | Method | Challenges |
|--------|--------|------------|
| Company blog | RSS feed → full page scrape via BeautifulSoup/Playwright | JS-rendered blogs need headless browser |
| LinkedIn posts | Proxycurl API or PhantomBuster | Rate limits, cost per profile, TOS gray area |
| Press releases | NewsAPI, Google News API, company newsroom scrape | Noise filtering (relevant vs. irrelevant mentions) |
| Job descriptions | Indeed API, LinkedIn Jobs, careers page scrape | Postings expire, need archival strategy |
| Earnings calls | SEC EDGAR (public cos), Seeking Alpha transcripts | Only available for public companies |
| Changelog | Scrape /changelog or /releases pages | Inconsistent formatting |
| Glassdoor reviews | Scrape (TOS issues) or Glassdoor API (limited) | Anonymized, noisy, but high signal-density |

### Branch 2E: Competitive Intelligence

**Sources:** G2 reviews, BuiltWith (competitor product detection), job postings mentioning competitor tools, company blog (competitor mentions), third-party intent data (if available)

**Output:**
```python
class CompetitiveIntel(BaseModel):
    # Detected competitor usage
    known_competitors_in_stack: list[str]  # Products detected via BuiltWith/job posts
    competitor_mentions_in_content: list[dict]  # {"competitor": "X", "context": "...", "sentiment": "..."}
    
    # Competitor evaluation signals
    actively_evaluating: bool  # Intent signals for competitor category
    evaluating_confidence: float
    evaluation_signals: list[str]  # What triggered this assessment
    
    # Competitive context
    current_solution: Optional[str]  # What they use now for the problem you solve
    current_solution_satisfaction: Optional[str]  # "satisfied" | "mixed" | "dissatisfied" | "unknown"
    contract_renewal_estimate: Optional[str]  # If detectable
    
    # Play implications
    competitive_context: str  # "greenfield" | "competitive_displacement" | "expansion" | "unknown"
    # greenfield = no current solution, using spreadsheets/manual
    # competitive_displacement = using a competitor
    # expansion = using a partial solution, need more
```

### Entity Resolution Layer

Runs AFTER all enrichment branches complete. Deduplicates and reconciles conflicts.

```python
class EntityResolver:
    """
    Reconciles data conflicts across enrichment sources.
    
    Examples:
    - Crunchbase says 200 employees, LinkedIn says 250 → Use LinkedIn (more current)
    - Apollo says CFO is John Smith, LinkedIn says Jane Doe → Flag for review
    - BuiltWith detects QuickBooks, job posting mentions NetSuite migration → Both valid (transition signal!)
    """
    
    def resolve_company(self, enrichments: dict) -> ResolvedAccount:
        # Domain normalization: rillet.com, www.rillet.com, app.rillet.com → rillet.com
        # Name normalization: "Rillet" vs "Rillet, Inc." vs "Rillet Inc"
        # Headcount: Take most recent source, flag if >20% discrepancy
        # Funding: Crunchbase is authoritative for this
        # Contacts: Merge by name+company, flag conflicts
        pass
    
    def resolve_contacts(self, contacts: list[ContactRecord]) -> list[ContactRecord]:
        # Fuzzy name matching across sources
        # Email validation / dedup
        # Title normalization: "VP, Finance" vs "Vice President of Finance" vs "VP Finance"
        pass
```

---

## Phase 3: ANALYZE Agent — Content Intelligence Layer

### Purpose
This is the proprietary engine. Processes the assembled content corpus through multiple analytical lenses to extract organizational signals invisible to structured data analysis.

### Architecture

```
Content Corpus (from Branch 2D)
         │
         ▼
┌─────────────────────┐
│ CORPUS PREPROCESSOR  │
│                     │
│ - Chronological sort │
│ - Author attribution │
│ - Source weighting   │
│ - Min corpus check   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────────────────────────────┐
│           LLM ANALYSIS CHAIN (Sequential)            │
│                                                     │
│  Stage 1: Per-Item Extraction                        │
│  ├── Semantic layer (stated facts, announcements)    │
│  ├── Pragmatic layer (why saying this now)           │
│  ├── Tonal layer (confidence/stress/urgency)         │
│  └── Structural layer (emphasis distribution)        │
│                                                     │
│  Stage 2: Cross-Corpus Synthesis                     │
│  ├── Trajectory analysis (how language changes)      │
│  ├── Absence analysis (what's NOT being said)        │
│  ├── Coherence scoring (pain signal consistency)     │
│  ├── Org stress indicators (compression patterns)    │
│  └── Stated vs actual priority alignment             │
│                                                     │
│  Stage 3: Person-Level Analysis                      │
│  ├── Per-contact language analysis (LinkedIn posts)   │
│  ├── Buying readiness per individual                 │
│  ├── Messaging resonance vectors (per person)        │
│  ├── Champion identification / confidence            │
│  └── Committee alignment assessment                  │
│                                                     │
│  Stage 4: Synthesis & Scoring                        │
│  ├── Buying journey position (0.0-1.0)              │
│  ├── Composite signal score                         │
│  ├── "Why now" hypothesis generation                │
│  ├── Confidence classification per signal            │
│  └── Counter-signal identification                  │
└─────────────────────────────────────────────────────┘
```

### Stage 1: Per-Item Extraction

Each content item gets processed individually first. This is parallelizable.

**Prompt Template (per content item):**
```
SYSTEM: You are an organizational intelligence analyst. You extract 
structured signals from company-generated content at multiple layers 
beyond surface meaning. You report what's there, not what's expected.
Do not editorialize. Do not speculate beyond what the text supports.

INPUT CONTEXT:
- Company: {company_name}
- Source type: {source_type}
- Author: {author} ({author_role})
- Published: {publish_date}
- Content: {raw_text}

EXTRACT THE FOLLOWING LAYERS:

SEMANTIC (what they literally say):
- Key announcements, claims, or stated positions
- Named products, metrics, or milestones

PRAGMATIC (why they're saying this now):
- What business context would motivate publishing this?
- What audience is this for? (customers, investors, recruits, industry)
- Is this reactive (responding to something) or proactive?

TONAL (confidence/stress/urgency markers):
- Overall tone: confident | aspirational | defensive | urgent | neutral
- Language certainty level: definitive | hedged | vague | contradictory
- Emotional register: calm | excited | stressed | performative

STRUCTURAL (what gets emphasis):
- What topics get the most space/detail?
- What's mentioned briefly or in passing?
- What's conspicuously absent given the context?

OUTPUT FORMAT: JSON
{
  "semantic": {"announcements": [], "metrics": [], "claims": []},
  "pragmatic": {"likely_motivation": "", "target_audience": "", "reactive_or_proactive": ""},
  "tonal": {"overall_tone": "", "certainty_level": "", "emotional_register": ""},
  "structural": {"emphasized_topics": [], "minimized_topics": [], "notable_absences": []},
  "raw_signals": []  // Any other notable patterns
}
```

### Stage 2: Cross-Corpus Synthesis

Takes all per-item extractions and analyzes patterns ACROSS the corpus.

**Prompt Template:**
```
SYSTEM: You are an organizational intelligence analyst performing 
longitudinal analysis on a company's public communications. You've 
been provided per-item extractions from {n_items} pieces of content 
spanning {date_range}. Your job is to identify patterns that are 
only visible across multiple documents over time.

Do not summarize individual items. Analyze the TRAJECTORY and 
PATTERNS across the corpus.

PER-ITEM EXTRACTIONS:
{serialized_extractions_chronological}

ANALYZE:

1. TRAJECTORY: How has their language/tone/emphasis changed over the 
   time period? Is the organization becoming more confident or more 
   stressed? More focused or more scattered? More urgent or more settled?

2. ABSENCE ANALYSIS: Given what this company does and their market 
   position, what topics would you EXPECT to see discussed but are 
   missing or avoided? What does the absence likely indicate?

3. PAIN SIGNAL COHERENCE: Are pain points scattered across many 
   domains, or crystallized around specific themes? Rate 0-1 where 
   1 = highly coherent pain signal around a defined problem.

4. ORGANIZATIONAL STRESS INDICATORS: Look at language compression 
   patterns. Are posts getting shorter, more defensive, more 
   product-focused over time? Is there a shift from exploratory/
   aspirational language to operational/urgent language?

5. STATED vs ACTUAL PRIORITIES: Based on what gets emphasized and 
   what gets buried, do their stated priorities align with where 
   they actually invest communication energy?

6. SOLUTION SOPHISTICATION: How articulate is the org about their 
   own problems? Are they at "this is frustrating" or at "we 
   understand the structural reasons this is broken and what a 
   fix looks like"?

OUTPUT FORMAT: JSON
{
  "trajectory": {
    "direction": "improving | stable | declining | volatile",
    "confidence_trend": "increasing | stable | decreasing",
    "urgency_trend": "increasing | stable | decreasing",
    "key_shifts": [{"date_approx": "", "description": ""}]
  },
  "absences": [{"expected_topic": "", "likely_reason": "", "confidence": 0.0}],
  "pain_coherence": {"score": 0.0, "primary_pain_themes": [], "scattered_complaints": []},
  "stress_indicators": {"level": "low | moderate | elevated | high", "evidence": []},
  "priority_alignment": {"aligned": true/false, "stated": [], "actual": [], "gaps": []},
  "solution_sophistication": {"level": "unaware | frustrated | articulate | evaluating | decided", "evidence": ""},
  "meta_signals": []  // Anything else the pattern reveals
}
```

### Stage 3: Person-Level Analysis

For each identified contact in the buying committee, analyze their personal content.

**Prompt Template:**
```
SYSTEM: You are analyzing public communications from {contact_name}, 
{contact_title} at {company_name}. Extract signals relevant to their 
buying readiness, communication style, and likely decision-making approach.

THEIR RECENT LINKEDIN POSTS / PUBLIC CONTENT:
{contact_corpus}

COMPANY CONTEXT (from org-level analysis):
{company_analysis_summary}

ANALYZE:

1. INDIVIDUAL PAIN SIGNALS: What problems are they personally 
   talking about? How does their pain language compare to the 
   company's official language? (Ahead of the org? Behind? Aligned?)

2. BUYING READINESS: Based on their language, where are they in 
   their personal journey with this problem?
   - Unaware (not discussing relevant problems)
   - Problem-aware (feeling pain, not solution-seeking)
   - Solution-exploring (researching, asking questions)
   - Active evaluation (comparing, requesting demos)
   - Decision-ready (outcome-focused language, urgency)

3. MESSAGING RESONANCE: What narrative patterns dominate their 
   communication? Map to:
   - Builder: Focused on creating, building, transforming systems
   - Optimizer: Focused on efficiency, measurement, best practices
   - Risk-manager: Focused on compliance, security, reliability
   - Visionary: Focused on future-state, innovation, competitive edge
   - Pragmatist: Focused on ROI, cost, practical outcomes

4. INFLUENCE MAPPING: Based on how they communicate, what's their 
   likely role in buying decisions?
   - Language suggesting authority: "I decided", "we're implementing"
   - Language suggesting influence: "I recommended", "I'm pushing for"
   - Language suggesting evaluation: "I'm looking at", "comparing"
   - Language suggesting execution: "Setting up", "rolling out"

OUTPUT FORMAT: JSON
{
  "pain_alignment": {"ahead_of_org": bool, "aligned": bool, "personal_pain_themes": []},
  "buying_readiness": {"stage": "", "confidence": 0.0, "evidence": []},
  "messaging_resonance": {"primary": "", "secondary": "", "avoid": ""},
  "influence_level": {"inferred_role": "", "authority_signals": [], "confidence": 0.0},
  "recommended_approach": "",  // How to talk to THIS person
  "recommended_avoid": ""  // What NOT to say to this person
}
```

### Stage 4: Synthesis & Composite Scoring

Combines all analysis into actionable output.

```python
class AnalyzedAccount(BaseModel):
    """Complete analysis output for a single account."""
    
    account_id: str
    analysis_date: date
    
    # Composite Scores
    icp_fit_score: float  # 0-1, weighted firmographic + technographic fit
    buying_readiness_score: float  # 0-1, from content intelligence
    timing_score: float  # 0-1, signal recency + urgency indicators
    composite_priority_score: float  # Weighted combination
    priority_tier: str  # "tier_1" | "tier_2" | "tier_3" | "not_qualified"
    
    # Buying Journey Position
    journey_position: float  # 0.0-1.0 (maps from RPMS narrative phase)
    journey_position_label: str  # "status_quo" | "problem_aware" | "solution_exploring" | "active_evaluation" | "decision_ready"
    journey_velocity: str  # "accelerating" | "stable" | "stalling" | "regressing"
    
    # Why Now Hypothesis
    why_now: WhyNowHypothesis
    
    # Buying Committee
    buying_committee: BuyingCommittee  # From Phase 2C, enriched with Stage 3 analysis
    
    # Competitive Context
    competitive_context: CompetitiveIntel  # From Phase 2E
    
    # Content Intelligence Summary
    content_intelligence: ContentIntelligenceSummary
    
    # Confidence & Counter-Signals
    confidence: ConfidenceAssessment
    
class WhyNowHypothesis(BaseModel):
    """The synthesized narrative of why this account is ready to buy NOW."""
    
    headline: str  # One sentence: "New VP Finance at scaling Series B with legacy accounting stack"
    supporting_signals: list[Signal]
    
    # Temporal signals
    trigger_event: Optional[str]  # The specific event that opened the window
    trigger_date: Optional[date]
    window_estimate: str  # "30 days", "60 days", "90 days"
    
    narrative: str  # 2-3 paragraph synthesis for the AE to read
    
class Signal(BaseModel):
    signal_type: str  # "funding" | "hiring" | "tech_change" | "leadership" | "content" | "intent" | "competitive"
    description: str
    source: str  # Where this signal came from
    detected_date: date
    decay_weight: float  # 0-1, decreases with age
    confidence: str  # "extracted" | "interpolated" | "generated"
    
class ContentIntelligenceSummary(BaseModel):
    """Summary of proprietary content analysis."""
    
    pain_coherence_score: float  # 0-1
    primary_pain_themes: list[str]
    org_stress_level: str  # "low" | "moderate" | "elevated" | "high"
    solution_sophistication: str
    stated_vs_actual_alignment: bool
    trajectory_direction: str
    notable_absences: list[str]
    
class ConfidenceAssessment(BaseModel):
    """Honest assessment of signal quality."""
    
    overall_confidence: str  # "high" | "medium" | "low"
    
    extracted_signals: list[str]  # Structurally present, multi-source corroborated
    interpolated_signals: list[str]  # Pattern-consistent, single-source
    generated_signals: list[str]  # Plausible but unverified
    
    counter_signals: list[str]  # What contradicts the hypothesis
    unknowns: list[str]  # What we couldn't determine
    
    # Corpus quality
    corpus_size: int
    corpus_quality: str  # "high" | "medium" | "low"
    corpus_sufficient: bool
```

### Signal Decay Weighting

```python
SIGNAL_DECAY_CONFIG = {
    # Signal type: (peak_days, half_life_days, max_relevance_days)
    "funding_round":        (30, 90, 180),   # Peaks at 30d, halves at 90d, dead at 180d
    "new_executive":        (60, 120, 240),   # New leaders take time to buy
    "job_posting_finance":  (14, 45, 90),     # Active hiring = active now
    "job_posting_tech":     (14, 45, 90),
    "tech_stack_change":    (7, 30, 60),      # Migration in progress
    "pricing_page_visit":   (1, 7, 21),       # Decays fast
    "content_engagement":   (3, 14, 30),
    "blog_post_pain":       (7, 30, 90),      # Slower decay, represents ongoing state
    "linkedin_post_pain":   (3, 14, 30),
    "competitor_evaluation": (7, 30, 60),
    "earnings_mention":     (14, 45, 90),
    "glassdoor_trend":      (30, 90, 180),    # Slow-moving signal
}

def calculate_decay_weight(signal_type: str, signal_date: date, current_date: date) -> float:
    """Returns 0-1 weight based on signal freshness."""
    peak, half_life, max_days = SIGNAL_DECAY_CONFIG[signal_type]
    age_days = (current_date - signal_date).days
    
    if age_days > max_days:
        return 0.0
    if age_days <= peak:
        return min(1.0, age_days / peak)  # Ramp up to peak
    
    # Exponential decay after peak
    decay_age = age_days - peak
    return 0.5 ** (decay_age / half_life)
```

---

## Phase 4: ACTIVATE Agent

### Purpose
Convert analyzed accounts into actionable sales materials: play selection, personalized angles, CRM-ready records, and routing.

### Play Selection Matrix

```python
PLAY_MATRIX = {
    # (competitive_context, journey_position, org_stress) → play
    
    ("greenfield", "problem_aware", "elevated"): {
        "play": "educational_urgency",
        "description": "They feel the pain but don't know solutions exist. Educate + create urgency.",
        "sequence": ["thought_leadership_email", "case_study_share", "demo_offer"],
        "timeline": "2-week sequence"
    },
    
    ("greenfield", "solution_exploring", "high"): {
        "play": "direct_solution",
        "description": "They're actively looking and stressed. Skip education, go direct.",
        "sequence": ["personalized_demo_offer", "roi_calculator", "reference_call"],
        "timeline": "3-day accelerated"
    },
    
    ("competitive_displacement", "active_evaluation", "moderate"): {
        "play": "competitive_wedge",
        "description": "They use a competitor and are evaluating alternatives. Lead with differentiators.",
        "sequence": ["competitive_comparison", "migration_ease_pitch", "pilot_offer"],
        "timeline": "1-week sequence"
    },
    
    ("greenfield", "status_quo", "low"): {
        "play": "long_nurture",
        "description": "Not ready now. Stay visible for when trigger event hits.",
        "sequence": ["add_to_newsletter", "quarterly_check_in", "monitor_for_triggers"],
        "timeline": "3-month nurture"
    },
    
    # ... Additional play combinations
}
```

### Angle Generation

**Prompt Template:**
```
SYSTEM: You are a sales strategist generating a personalized outreach 
angle for a specific contact at a target account. You have deep 
intelligence on both the company and the individual. Generate an 
approach that is specific, relevant, and non-generic.

RULES:
- NO "Hi {first_name}, I noticed {company} just..." openings
- Reference specific signals you've detected
- Match the messaging resonance profile of the contact
- Be concise — this is the ANGLE, not the full email
- Include what to say AND what NOT to say

ACCOUNT INTELLIGENCE:
{analyzed_account_summary}

CONTACT PROFILE:
{person_level_analysis}

PLAY SELECTED: {play_name}
PLAY DESCRIPTION: {play_description}

GENERATE:

1. OPENING ANGLE: What's the specific hook for this person? 
   (Reference a real signal — their LinkedIn post, a company 
   announcement, a detected pain point)

2. VALUE PROPOSITION: How do you connect their specific situation 
   to your product? (Not generic features — specific to their context)

3. ASK: What's the specific call-to-action? (Calibrated to their 
   buying readiness — don't ask for a demo if they're still problem-aware)

4. AVOID: What topics or approaches would backfire with this person? 
   (Based on their messaging resonance profile and detected sensitivities)

5. OBJECTION PREP: What's the most likely pushback and how to handle it?

OUTPUT FORMAT: JSON
{
  "opening_angle": "",
  "value_prop": "",
  "call_to_action": "",
  "avoid_topics": [],
  "likely_objection": "",
  "objection_response": "",
  "confidence": "high | medium | low",
  "notes_for_ae": ""  // Any additional context the rep should know
}
```

### CRM Output Formatting

```python
class CRMRecord(BaseModel):
    """Final output record, formatted for CRM ingestion."""
    
    # Account fields
    company_name: str
    domain: str
    industry: str
    employee_count: int
    funding_stage: str
    total_raised: int
    hq_location: str
    
    # PRISM custom fields
    sigint_priority_tier: str  # "tier_1" | "tier_2" | "tier_3"
    sigint_composite_score: float
    sigint_buying_journey: str
    sigint_why_now: str  # One-line headline
    sigint_play: str
    sigint_confidence: str
    sigint_last_analyzed: date
    
    # Contacts (associated)
    contacts: list[CRMContact]
    
    # Attachments
    account_brief_url: str  # Link to full account brief (rendered markdown or PDF)
    
    # Routing
    assigned_rep: Optional[str]  # Based on territory/vertical/capacity rules
    
class CRMContact(BaseModel):
    name: str
    title: str
    email: Optional[str]
    linkedin_url: Optional[str]
    buying_role: str
    outreach_angle: str  # Personalized angle for this specific person
    messaging_resonance: str  # "builder" | "optimizer" | "risk_manager" | etc.
    avoid_topics: list[str]

class AccountBrief(BaseModel):
    """The full brief an AE reads before engaging. This is the money output."""
    
    # Header
    company_name: str
    priority_tier: str
    composite_score: float
    one_line_why_now: str
    
    # Company Snapshot (2-3 sentences)
    company_summary: str
    
    # Why Now (2-3 paragraphs)
    why_now_narrative: str
    supporting_signals: list[Signal]
    signal_confidence: str
    counter_signals: list[str]
    
    # Buying Committee Map
    contacts: list[dict]  # Name, role, approach, avoid
    recommended_entry_point: str  # Who to contact first and why
    
    # Competitive Context
    competitive_situation: str
    known_alternatives_in_play: list[str]
    
    # Recommended Play
    play_name: str
    play_description: str
    suggested_sequence: list[str]
    
    # AE Cheat Sheet
    talking_points: list[str]
    questions_to_ask: list[str]
    objection_prep: list[dict]
    
    # Confidence & Caveats
    overall_confidence: str
    what_we_dont_know: list[str]
    recommended_discovery_questions: list[str]  # To fill gaps
```

### Routing Logic

```python
class RoutingEngine:
    """Determines which rep gets which account."""
    
    def route(self, account: AnalyzedAccount, team: list[Rep]) -> str:
        """
        Routing factors:
        1. Territory (if geographic routing exists)
        2. Vertical expertise (rep has closed in this industry before)
        3. Deal size match (junior reps get smaller accounts)
        4. Current capacity (don't overload top performers)
        5. Competitive experience (rep has displaced this competitor before)
        """
        pass
```

---

## Phase 5: FEEDBACK Loop

### Purpose
Track outcomes, recalibrate scoring weights, identify which signals actually predict conversion, and manage re-engagement of dormant accounts.

### Outcome Tracking

```python
class DealOutcome(BaseModel):
    account_id: str
    
    # Pipeline progression
    meeting_booked: bool
    meeting_date: Optional[date]
    opportunity_created: bool
    opportunity_amount: Optional[int]
    
    # Resolution
    outcome: str  # "closed_won" | "closed_lost" | "stalled" | "no_response" | "disqualified"
    outcome_date: Optional[date]
    days_to_outcome: Optional[int]
    
    # Attribution
    entry_point_contact: str  # Who did we reach out to
    actual_champion: Optional[str]  # Who actually drove the deal
    actual_economic_buyer: Optional[str]
    
    # Signal validation
    why_now_accurate: Optional[bool]  # Was our hypothesis right?
    buying_committee_accurate: Optional[bool]  # Did we map the right people?
    play_effective: Optional[bool]
    
    # Loss reasons (if closed_lost or stalled)
    loss_reason: Optional[str]  # "timing" | "budget" | "competitor" | "no_decision" | "bad_fit" | "champion_left"
    
    # Rep feedback
    rep_notes: Optional[str]
    signal_quality_rating: Optional[int]  # 1-5, how useful was the brief?
    brief_accuracy_rating: Optional[int]  # 1-5, how accurate was the analysis?
```

### Score Recalibration

```python
class RecalibrationEngine:
    """
    Uses closed deal data to adjust signal weights.
    
    After N deals (minimum 30 for statistical significance):
    
    1. For each signal type, calculate:
       - Presence rate in closed_won vs. closed_lost
       - Correlation with deal velocity (faster close = stronger signal)
       - False positive rate (signal present but no engagement)
    
    2. Adjust ICP scoring weights based on actual conversion patterns
    
    3. Adjust Content Intelligence weights:
       - Which pain_coherence_score ranges predict conversion?
       - Does org_stress_level correlate with deal velocity?
       - Which journey_position labels have highest conversion?
       - Do counter_signals actually predict losses?
    
    4. Adjust play effectiveness:
       - Which plays convert best for which contexts?
       - Which messaging resonance profiles respond to which angles?
       - Which entry points (champion vs economic buyer) work better?
    
    Output: Updated weight configuration for next scoring cycle.
    """
    
    def recalibrate(self, outcomes: list[DealOutcome], current_weights: dict) -> dict:
        pass
```

### Re-engagement Monitor

```python
class ReengagementMonitor:
    """
    Watches dormant accounts for new trigger events.
    
    Runs on schedule (daily or weekly) against accounts in these states:
    - "no_response" (never engaged)
    - "stalled" (engaged but went quiet)  
    - "closed_lost_timing" (said "not now")
    - "closed_lost_budget" (couldn't afford it then)
    
    Trigger events that resurface an account:
    - New funding round
    - New executive in key role
    - Champion from lost deal moved to new company (GOLD)
    - Competitor in their stack had outage/bad press
    - Job posting indicating the pain got worse
    - Content signals showing increased urgency
    """
    
    def scan_dormant_accounts(self, accounts: list[DormantAccount]) -> list[ResurfacedAccount]:
        pass
    
    class ResurfacedAccount(BaseModel):
        account_id: str
        original_outcome: str
        dormant_since: date
        new_trigger: str
        trigger_date: date
        recommended_reengagement_play: str
        previous_contacts: list[str]  # Who we talked to before
        new_contacts: list[str]  # New people in relevant roles
```

---

## Database Schema (Core Tables)

```sql
-- Core entities
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'discovered',
    -- discovered → enriching → analyzed → activated → monitoring → feedback
    
    -- Firmographics
    headcount INT,
    funding_stage VARCHAR(50),
    total_raised BIGINT,
    industry VARCHAR(100),
    hq_location VARCHAR(255),
    
    -- Scores (updated by analysis)
    icp_fit_score FLOAT,
    buying_readiness_score FLOAT,
    timing_score FLOAT,
    composite_score FLOAT,
    priority_tier VARCHAR(20),
    
    -- Journey
    journey_position FLOAT,
    journey_label VARCHAR(50),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_analyzed_at TIMESTAMPTZ,
    icp_filter_version VARCHAR(50)
);

CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES accounts(id),
    name VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    email VARCHAR(255),
    linkedin_url VARCHAR(500),
    
    -- Buying role
    buying_role VARCHAR(50),
    buying_role_confidence FLOAT,
    
    -- Analysis
    buying_readiness VARCHAR(50),
    messaging_resonance VARCHAR(50),
    influence_level VARCHAR(50),
    
    -- Outreach
    outreach_angle TEXT,
    avoid_topics JSONB,
    
    -- Metadata
    is_new_in_role BOOLEAN,
    start_date_current_role DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE content_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES accounts(id),
    contact_id UUID REFERENCES contacts(id),  -- NULL if company-level content
    
    source_type VARCHAR(50) NOT NULL,
    url TEXT,
    title VARCHAR(500),
    author VARCHAR(255),
    publish_date DATE,
    raw_text TEXT,
    word_count INT,
    
    -- Per-item extraction (Stage 1 output)
    extraction JSONB,  -- Full per-item analysis
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES accounts(id),
    contact_id UUID REFERENCES contacts(id),  -- NULL if account-level
    
    signal_type VARCHAR(50) NOT NULL,
    description TEXT,
    source VARCHAR(255),
    detected_date DATE NOT NULL,
    decay_weight FLOAT,
    confidence VARCHAR(20),  -- extracted | interpolated | generated
    
    -- For recalibration
    predicted_positive BOOLEAN,  -- Did we think this was a buying signal?
    actual_outcome VARCHAR(50),  -- What actually happened?
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES accounts(id),
    analysis_date DATE NOT NULL,
    
    -- Full analysis output
    content_intelligence JSONB,  -- Cross-corpus synthesis
    why_now_hypothesis JSONB,
    buying_committee JSONB,
    confidence_assessment JSONB,
    
    -- Play
    selected_play VARCHAR(100),
    play_config JSONB,
    
    -- Account brief (rendered)
    account_brief JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES accounts(id),
    analysis_id UUID REFERENCES analyses(id),
    
    -- Pipeline
    meeting_booked BOOLEAN,
    meeting_date DATE,
    opportunity_created BOOLEAN,
    opportunity_amount INT,
    
    -- Resolution
    outcome VARCHAR(50),
    outcome_date DATE,
    loss_reason VARCHAR(100),
    
    -- Validation
    why_now_accurate BOOLEAN,
    committee_accurate BOOLEAN,
    play_effective BOOLEAN,
    signal_quality_rating INT,
    brief_accuracy_rating INT,
    rep_notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Recalibration weights (versioned)
CREATE TABLE scoring_weights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(50) NOT NULL,
    effective_date DATE NOT NULL,
    
    -- Signal weights
    signal_weights JSONB,  -- {signal_type: weight}
    -- ICP weights
    icp_weights JSONB,
    -- Content intelligence weights
    content_weights JSONB,
    
    -- Recalibration metadata
    based_on_n_deals INT,
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Re-engagement monitoring
CREATE TABLE dormant_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES accounts(id),
    dormant_since DATE,
    original_outcome VARCHAR(50),
    
    -- Monitoring config
    watch_signals JSONB,  -- What trigger events to watch for
    last_checked DATE,
    
    -- Resurfacing
    resurfaced BOOLEAN DEFAULT FALSE,
    resurface_trigger TEXT,
    resurface_date DATE
);
```

---

## Cost Modeling

### LLM API Costs Per Account (Estimated)

| Stage | Calls | Avg Tokens (in+out) | Cost (Claude Sonnet) |
|-------|-------|---------------------|---------------------|
| Stage 1: Per-item extraction | ~20 items | ~3K per item = 60K | ~$0.18 |
| Stage 2: Cross-corpus synthesis | 1 call | ~30K in + 4K out | ~$0.12 |
| Stage 3: Person-level (3-5 people) | ~4 calls | ~5K per call = 20K | ~$0.06 |
| Stage 4: Synthesis + scoring | 1 call | ~15K in + 3K out | ~$0.06 |
| Activation: Angle generation | ~4 calls | ~3K per call = 12K | ~$0.04 |
| **TOTAL PER ACCOUNT** | | | **~$0.46** |

**At scale:**
- 100 accounts/week = ~$46/week = ~$200/month
- 500 accounts/week = ~$230/week = ~$1,000/month
- 1000 accounts/week = ~$460/week = ~$2,000/month

This is extremely cost-effective vs. hiring SDRs ($5K-8K/month each).

### External API Costs

| Service | Tier | Cost | Volume |
|---------|------|------|--------|
| Crunchbase Pro | Monthly | $49/mo | Sufficient for discovery |
| Proxycurl | Credits | ~$0.01/profile | LinkedIn enrichment |
| Apollo | Free/paid | $0-49/mo | Contact discovery |
| BuiltWith | API | $295/mo | Tech stack detection |
| NewsAPI | Developer | Free (limited) / $449 | Press/news scraping |
| Hunter.io | Starter | $49/mo | Email verification |
| **Total infrastructure** | | **~$500-900/month** | |

---

## Build Phases

### Phase 0: Portfolio Demo (1-3 days with Claude Code)
**Goal:** Demonstrate the full pipeline concept on 5-10 manually selected accounts.

**Build:**
- Hardcoded ICP filter (no Crunchbase API yet — manually supply 10 companies)
- Content scraping for those 10 companies (blog + LinkedIn)
- Full Content Intelligence analysis chain (Stages 1-4)
- Account brief generation
- Simple CLI or Streamlit dashboard showing results

**Skip:** CRM integration, routing, feedback loop, automated discovery, contact email lookup

**Demo output:** 5-10 fully analyzed account briefs showing the Content Intelligence layer in action, with confidence scoring and counter-signals. This is what you show in the interview.

### Phase 1: Functional MVP (1-2 weeks with Claude Code)
**Goal:** End-to-end pipeline working on real data.

**Add:**
- Crunchbase API integration for discovery
- Automated blog scraping (RSS + BeautifulSoup)
- Apollo integration for contact discovery
- BuiltWith integration for tech stack
- PostgreSQL persistence
- Basic FastAPI endpoints
- Simple Next.js dashboard

**Skip:** Feedback loop, re-engagement monitor, advanced routing

### Phase 2: Production System (2-4 weeks with Claude Code)
**Goal:** Deployable system with full pipeline.

**Add:**
- Full content corpus assembly (all source types)
- Celery task queue for async processing
- Signal decay engine
- Play selection matrix
- CRM export (HubSpot API or Salesforce API)
- Feedback tracking
- Rate limiting and cost management
- Docker Compose deployment
- Testing suite

### Phase 3: Learning System (Ongoing)
**Goal:** System that improves with every deal.

**Add:**
- Recalibration engine (requires 30+ deal outcomes)
- Re-engagement monitor
- A/B testing on plays and angles
- Advanced routing with rep performance data
- Reporting dashboard (pipeline attribution, signal accuracy)

---

## Open Questions / Decisions Needed

1. **LinkedIn data access**: Proxycurl ($) vs. PhantomBuster vs. manual export? TOS implications?
2. **Target CRM**: HubSpot vs. Salesforce? Affects integration work.
3. **Dashboard priority**: Is a dashboard needed for the portfolio piece, or is CLI + generated briefs sufficient?
4. **Multi-tenancy**: Is this a single-deployment tool or a SaaS product? Affects architecture.
5. **ICP configurability**: Hardcoded for fintech initially, or configurable from day one?
6. **Content scraping legality**: Blog scraping is generally fine. LinkedIn scraping is gray area. Glassdoor scraping is gray area. Establish boundaries.
7. **LLM selection**: Claude Sonnet for cost efficiency vs. Claude Opus for analysis quality? Tiered approach? (Sonnet for Stage 1 extraction, Opus for Stage 2-4 synthesis?)
8. **Naming**: PRISM has military intelligence connotations. Keep it as internal codename or rename for public?

---

## File Structure (Proposed)

```
sigint/
├── docker-compose.yml
├── pyproject.toml
├── README.md
│
├── sigint/
│   ├── __init__.py
│   ├── config.py                 # Settings, API keys, ICP config
│   ├── main.py                   # FastAPI app
│   ├── models/
│   │   ├── __init__.py
│   │   ├── account.py            # Account, Contact, Signal models
│   │   ├── content.py            # ContentItem, ContentCorpus models
│   │   ├── analysis.py           # Analysis output models
│   │   └── activation.py         # Play, Angle, CRM output models
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # Pipeline coordinator
│   │   ├── discover.py           # Discovery agent
│   │   ├── enrich/
│   │   │   ├── __init__.py
│   │   │   ├── company.py        # Branch 2A
│   │   │   ├── tech.py           # Branch 2B
│   │   │   ├── contacts.py       # Branch 2C
│   │   │   ├── content.py        # Branch 2D (corpus assembly)
│   │   │   └── competitive.py    # Branch 2E
│   │   │
│   │   ├── analyze/
│   │   │   ├── __init__.py
│   │   │   ├── content_intel.py  # THE proprietary layer
│   │   │   ├── prompts.py        # All LLM prompt templates
│   │   │   ├── scoring.py        # ICP scoring, composite scoring
│   │   │   ├── signal_decay.py   # Temporal weighting
│   │   │   └── synthesis.py      # Why-now, account brief generation
│   │   │
│   │   ├── activate/
│   │   │   ├── __init__.py
│   │   │   ├── plays.py          # Play selection matrix
│   │   │   ├── angles.py         # Angle generation
│   │   │   ├── crm_export.py     # CRM formatting + push
│   │   │   └── routing.py        # Rep routing logic
│   │   │
│   │   └── feedback/
│   │       ├── __init__.py
│   │       ├── tracking.py       # Outcome tracking
│   │       ├── recalibrate.py    # Weight recalibration
│   │       └── reengage.py       # Dormant account monitoring
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm.py                # Claude/OpenAI API wrapper
│   │   ├── crunchbase.py         # Crunchbase API client
│   │   ├── apollo.py             # Apollo API client
│   │   ├── builtwith.py          # BuiltWith API client
│   │   ├── scraper.py            # Blog/content scraper
│   │   ├── linkedin.py           # LinkedIn data (Proxycurl or similar)
│   │   └── entity_resolver.py    # Deduplication/reconciliation
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py            # Database connection
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   └── migrations/           # Alembic migrations
│   │
│   └── api/
│       ├── __init__.py
│       ├── routes/
│       │   ├── accounts.py       # Account CRUD + pipeline triggers
│       │   ├── analysis.py       # Analysis results + briefs
│       │   ├── dashboard.py      # Aggregated views
│       │   └── feedback.py       # Outcome recording
│       └── schemas.py            # API request/response schemas
│
├── frontend/                     # Next.js dashboard
│   ├── package.json
│   ├── app/
│   │   ├── page.tsx              # Dashboard home
│   │   ├── accounts/
│   │   │   ├── page.tsx          # Account list
│   │   │   └── [id]/page.tsx     # Account detail + brief
│   │   └── settings/
│   │       └── page.tsx          # ICP config, weights, API keys
│   └── components/
│       ├── AccountBrief.tsx       # The money component
│       ├── SignalTimeline.tsx     # Visual signal history
│       ├── BuyingCommittee.tsx    # Committee map visualization
│       └── PipelineDashboard.tsx  # Aggregate metrics
│
└── tests/
    ├── conftest.py
    ├── test_discover.py
    ├── test_enrich.py
    ├── test_content_intel.py     # Critical: test the proprietary layer
    ├── test_scoring.py
    ├── test_activation.py
    └── fixtures/
        ├── sample_corpus/        # Real blog posts for testing
        └── sample_accounts.json  # Test account data
```

---

## What's Still Missing (Known Gaps)

1. **Authentication & authorization** — Multi-user access, API keys management
2. **Monitoring & alerting** — System health, API rate limit warnings, processing failures
3. **Data retention policy** — How long to keep content corpuses, analysis history
4. **GDPR/privacy considerations** — Especially for EU-based contacts
5. **Webhook integrations** — Slack notifications for Tier 1 accounts, new trigger events
6. **Bulk import** — Upload existing account lists from CSV
7. **Manual override** — AE can flag "this analysis is wrong" for specific accounts
8. **Competitive intelligence refresh** — How often to re-check tech stack changes
9. **Content corpus refresh scheduling** — Weekly? Monthly? On-demand?
10. **Error handling & retry logic** — What happens when Crunchbase is down?
11. **Audit trail** — Who changed what, when, why (for the scoring weights especially)
12. **Export formats** — PDF briefs? Markdown? Integration with Google Docs?
13. **Demo/sandbox mode** — For showing to prospects without real data

---

*This is a living document. Version 0.1. Will iterate as build progresses.*
