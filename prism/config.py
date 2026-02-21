"""PRISM configuration — all weights, thresholds, and decay parameters.

All scoring weights, ICP definitions, and signal decay parameters are
centralized here. The scoring engine reads from this module so weights
can be changed without touching analysis code.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ─── Paths ──────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = PROJECT_ROOT / "fixtures"
COMPANIES_DIR = FIXTURES_DIR / "companies"
SCRAPED_CONTENT_DIR = FIXTURES_DIR / "scraped_content"
OUTPUT_DIR = PROJECT_ROOT / "output"
DOSSIERS_DIR = OUTPUT_DIR / "dossiers"
PROMPTS_DIR = Path(__file__).parent / "prompts"

# ─── Environment ────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PRISM_MODEL = os.getenv("PRISM_MODEL", "claude-sonnet-4-20250514")
PRISM_PROMPT_VERSION = os.getenv("PRISM_PROMPT_VERSION", "v1")
PRISM_MAX_CORPUS_ITEMS = int(os.getenv("PRISM_MAX_CORPUS_ITEMS", "30"))
PRISM_MAX_PERSON_POSTS = int(os.getenv("PRISM_MAX_PERSON_POSTS", "20"))
PRISM_LOG_LEVEL = os.getenv("PRISM_LOG_LEVEL", "INFO")

# ─── ICP Fit Weights (v1.0) ────────────────────────────────────────────────

ICP_WEIGHTS = {
    "funding_stage_fit": 0.25,
    "growth_rate": 0.20,
    "tech_stack_fit": 0.20,
    "headcount_fit": 0.15,
    "industry_fit": 0.10,
    "geo_fit": 0.10,
}

# ─── Buying Readiness Weights (v1.0) ───────────────────────────────────────

READINESS_WEIGHTS = {
    "journey_position": 0.20,
    "pain_coherence": 0.20,
    "new_leader_signal": 0.20,
    "org_stress_indicators": 0.15,
    "solution_sophistication": 0.15,
    "active_evaluation_signals": 0.10,
}

# ─── Timing Weights (v1.0) ─────────────────────────────────────────────────

TIMING_WEIGHTS = {
    "trigger_event_recency": 0.35,
    "signal_freshness_avg": 0.25,
    "urgency_indicators": 0.25,
    "window_closing_signals": 0.15,
}

# ─── Composite Weights (v1.0) ──────────────────────────────────────────────

COMPOSITE_WEIGHTS = {
    "icp_fit": 0.25,
    "buying_readiness": 0.50,
    "timing": 0.25,
}

# ─── Tier Thresholds ───────────────────────────────────────────────────────

TIER_THRESHOLDS = {
    "tier_1": 0.70,
    "tier_2": 0.45,
    "tier_3": 0.25,
}

# ─── Signal Decay Configuration ────────────────────────────────────────────
# signal_type: (peak_days, half_life_days, max_relevance_days)

SIGNAL_DECAY_CONFIG: dict[str, tuple[int, int, int]] = {
    "funding_round": (30, 90, 180),
    "new_executive_finance": (60, 150, 365),
    "new_executive_other": (45, 90, 180),
    "champion_departed": (7, 30, 60),
    "job_posting_finance": (14, 45, 90),
    "job_posting_technical": (14, 45, 90),
    "job_posting_urgent": (7, 21, 45),
    "tech_stack_change": (7, 30, 60),
    "migration_signal": (14, 45, 90),
    "blog_post_pain": (7, 30, 90),
    "linkedin_post_pain": (3, 14, 30),
    "earnings_mention": (14, 45, 90),
    "press_release_relevant": (7, 30, 60),
    "pricing_page_visit": (1, 7, 21),
    "content_engagement": (3, 14, 30),
    "g2_research_activity": (7, 21, 45),
    "competitor_evaluation": (7, 30, 60),
    "competitor_contract_renewal": (30, 60, 120),
    "glassdoor_trend": (30, 90, 180),
}

# ─── Funding Stage Scoring ─────────────────────────────────────────────────

FUNDING_STAGE_SCORES: dict[str, float] = {
    "Series B": 1.0,
    "Series C": 0.95,
    "Series A": 0.70,
    "Series D": 0.50,
    "Seed": 0.30,
    "Pre-seed": 0.10,
    "Bootstrapped": 0.10,
    "Public": 0.20,
}

# ─── Industry Scoring ──────────────────────────────────────────────────────

INDUSTRY_SCORES: dict[str, float] = {
    "SaaS": 1.0,
    "Fintech": 0.95,
    "E-commerce": 0.90,
    "Marketplace": 0.90,
    "B2B Services": 0.75,
    "Healthcare": 0.70,
    "Life Sciences": 0.70,
    "Other tech": 0.60,
    "Non-tech": 0.30,
}

# ─── Geo Scoring ────────────────────────────────────────────────────────────

MAJOR_TECH_HUBS = {
    "San Francisco", "SF", "New York", "NYC", "Austin", "Seattle",
    "Boston", "Los Angeles", "LA", "Denver", "Chicago", "Miami",
    "Palo Alto", "Mountain View", "Menlo Park", "San Jose",
    "Sunnyvale", "Cupertino", "Redwood City", "South San Francisco",
}

# ─── Play Matrix ────────────────────────────────────────────────────────────

PLAY_MATRIX: dict[tuple[str, str, str], dict] = {
    ("greenfield", "problem_aware", "elevated"): {
        "play": "educational_urgency",
        "description": "They feel the pain but don't know solutions exist. Educate + create urgency.",
        "sequence": ["thought_leadership_email", "case_study_share", "demo_offer"],
        "timeline": "2-week sequence",
    },
    ("greenfield", "solution_exploring", "high"): {
        "play": "direct_solution",
        "description": "They're actively looking and stressed. Skip education, go direct.",
        "sequence": ["personalized_demo_offer", "roi_calculator", "reference_call"],
        "timeline": "3-day accelerated",
    },
    ("greenfield", "solution_exploring", "elevated"): {
        "play": "direct_solution",
        "description": "They're exploring solutions with urgency. Go direct with value.",
        "sequence": ["personalized_demo_offer", "roi_calculator", "reference_call"],
        "timeline": "1-week sequence",
    },
    ("greenfield", "active_evaluation", "high"): {
        "play": "accelerated_close",
        "description": "They're evaluating and stressed. Fast-track to decision.",
        "sequence": ["competitive_comparison", "personalized_demo_offer", "pilot_offer"],
        "timeline": "3-day accelerated",
    },
    ("greenfield", "active_evaluation", "elevated"): {
        "play": "accelerated_close",
        "description": "Active evaluation with urgency. Help them decide fast.",
        "sequence": ["personalized_demo_offer", "roi_calculator", "pilot_offer"],
        "timeline": "1-week sequence",
    },
    ("competitive_displacement", "active_evaluation", "moderate"): {
        "play": "competitive_wedge",
        "description": "They use a competitor and are evaluating alternatives. Lead with differentiators.",
        "sequence": ["competitive_comparison", "migration_ease_pitch", "pilot_offer"],
        "timeline": "1-week sequence",
    },
    ("competitive_displacement", "active_evaluation", "elevated"): {
        "play": "competitive_wedge",
        "description": "Active eval with competitor in play. Wedge in with urgency.",
        "sequence": ["competitive_comparison", "migration_ease_pitch", "pilot_offer"],
        "timeline": "3-day accelerated",
    },
    ("competitive_displacement", "solution_exploring", "moderate"): {
        "play": "competitive_education",
        "description": "They have a competitor but are exploring. Educate on gaps.",
        "sequence": ["thought_leadership_email", "competitive_comparison", "demo_offer"],
        "timeline": "2-week sequence",
    },
    ("greenfield", "status_quo", "low"): {
        "play": "long_nurture",
        "description": "Not ready now. Stay visible for when trigger event hits.",
        "sequence": ["add_to_newsletter", "quarterly_check_in", "monitor_for_triggers"],
        "timeline": "3-month nurture",
    },
    ("greenfield", "problem_aware", "low"): {
        "play": "educational_nurture",
        "description": "Aware of pain but no urgency. Educate and stay top of mind.",
        "sequence": ["thought_leadership_email", "content_drip", "quarterly_check_in"],
        "timeline": "6-week sequence",
    },
    ("greenfield", "problem_aware", "moderate"): {
        "play": "educational_urgency",
        "description": "Aware of pain with moderate urgency. Educate and nudge.",
        "sequence": ["thought_leadership_email", "case_study_share", "demo_offer"],
        "timeline": "2-week sequence",
    },
}

# ─── LLM Cost Estimates (per 1K tokens) ────────────────────────────────────

LLM_COST_PER_1K_INPUT = 0.003  # Claude Sonnet
LLM_COST_PER_1K_OUTPUT = 0.015  # Claude Sonnet

# ─── Scraper Configuration ──────────────────────────────────────────────────

SCRAPER_USER_AGENT = "PRISM/0.1 (research; +https://github.com/Aurnix/prism)"
SCRAPER_TIMEOUT = 10
SCRAPER_RATE_LIMIT = 1.0  # seconds between requests
SCRAPER_MAX_PAGES = 5
