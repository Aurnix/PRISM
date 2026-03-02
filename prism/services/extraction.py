"""Extraction service — transforms raw content into structured signals.

Multi-path preprocessing:
  Path A: trafilatura for clean article text (when available)
  Path B: BeautifulSoup for HTML structure, meta tags, scripts
  Path C: Pattern library for zero-cost tech detection

Then LLM extraction via Haiku-tier backend for structured signal extraction.
"""

import logging
import re
from typing import Optional

from prism.models.extraction import (
    ExtractionResult,
    ExtractedContent,
    ExtractedSignal,
    ExtractedTechSignal,
    PageClassification,
    map_signal_type,
)
from prism.services.llm_backend import LLMBackend

logger = logging.getLogger(__name__)

# ─── Pattern Library (zero-cost tech detection) ────────────────────────────

TECH_PATTERNS: dict[str, dict[str, str]] = {
    # ERP/Accounting
    "quickbooks": {"technology": "QuickBooks", "category": "erp"},
    "netsuite": {"technology": "NetSuite", "category": "erp"},
    "xero": {"technology": "Xero", "category": "erp"},
    "sage intacct": {"technology": "Sage Intacct", "category": "erp"},
    "sap": {"technology": "SAP", "category": "erp"},
    "oracle financials": {"technology": "Oracle Financials", "category": "erp"},
    # CRM
    "salesforce": {"technology": "Salesforce", "category": "crm"},
    "hubspot": {"technology": "HubSpot", "category": "crm"},
    # Cloud
    "amazon web services": {"technology": "AWS", "category": "cloud"},
    "aws": {"technology": "AWS", "category": "cloud"},
    "google cloud": {"technology": "GCP", "category": "cloud"},
    "microsoft azure": {"technology": "Azure", "category": "cloud"},
    # Payment
    "stripe": {"technology": "Stripe", "category": "payment"},
    "braintree": {"technology": "Braintree", "category": "payment"},
    "adyen": {"technology": "Adyen", "category": "payment"},
    # BI/Analytics
    "looker": {"technology": "Looker", "category": "analytics"},
    "tableau": {"technology": "Tableau", "category": "analytics"},
    "metabase": {"technology": "Metabase", "category": "analytics"},
    # Competitors (Ledgerflow context)
    "rillet": {"technology": "Rillet", "category": "competitor"},
    "puzzle": {"technology": "Puzzle", "category": "competitor"},
    "digits": {"technology": "Digits", "category": "competitor"},
    "numeric": {"technology": "Numeric", "category": "competitor"},
}


def detect_tech_from_text(text: str) -> list[ExtractedTechSignal]:
    """Zero-cost tech detection via pattern matching."""
    text_lower = text.lower()
    found: list[ExtractedTechSignal] = []
    seen: set[str] = set()

    for pattern, info in TECH_PATTERNS.items():
        if pattern in text_lower and info["technology"] not in seen:
            # Find the surrounding context
            idx = text_lower.index(pattern)
            start = max(0, idx - 50)
            end = min(len(text), idx + len(pattern) + 50)
            evidence = text[start:end].strip()

            found.append(ExtractedTechSignal(
                technology=info["technology"],
                category=info["category"],
                evidence=evidence,
                confidence=0.7,
            ))
            seen.add(info["technology"])

    return found


def preprocess_html(html: str) -> ExtractedContent:
    """Path B: Extract content from HTML using BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return ExtractedContent(body_text=html, word_count=len(html.split()))

    soup = BeautifulSoup(html, "lxml")

    # Remove nav, footer, sidebar, script, style
    for tag in soup.find_all(["nav", "footer", "aside", "script", "style", "header"]):
        tag.decompose()

    # Extract title
    title = None
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    # Extract author from meta
    author = None
    author_meta = soup.find("meta", attrs={"name": "author"})
    if author_meta:
        author = author_meta.get("content", "")

    # Extract publish date from meta or time tag
    pub_date = None
    for meta_name in ["article:published_time", "datePublished", "date"]:
        meta = soup.find("meta", attrs={"property": meta_name}) or soup.find("meta", attrs={"name": meta_name})
        if meta:
            pub_date_str = meta.get("content", "")
            if pub_date_str:
                try:
                    from datetime import date as dt_date
                    pub_date = dt_date.fromisoformat(pub_date_str[:10])
                except ValueError:
                    pass
            break

    body_text = soup.get_text(separator="\n", strip=True)
    # Clean up excessive whitespace
    body_text = re.sub(r"\n{3,}", "\n\n", body_text)

    return ExtractedContent(
        title=title,
        author=author,
        publish_date=pub_date,
        body_text=body_text,
        word_count=len(body_text.split()),
    )


class ExtractionService:
    """Orchestrates the multi-path extraction pipeline.

    1. Preprocess raw content (HTML → text)
    2. Pattern-based tech detection (zero-cost)
    3. LLM extraction for signals (Haiku-tier)
    4. Validate and return ExtractionResult
    """

    def __init__(self, llm: LLMBackend) -> None:
        self.llm = llm

    async def extract(
        self,
        raw_content: str,
        source_type: str = "blog_post",
        url: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> ExtractionResult:
        """Extract structured data from raw content.

        Args:
            raw_content: Raw HTML or text content.
            source_type: Type of source (blog_post, job_listing, etc).
            url: Original URL of the content.
            company_name: Name of the company being analyzed.

        Returns:
            ExtractionResult with classified content and extracted signals.
        """
        # Path B: HTML preprocessing
        content = preprocess_html(raw_content)

        # Path C: Pattern-based tech detection
        tech_signals = detect_tech_from_text(content.body_text)

        # Path A: LLM extraction (if content is substantial enough)
        llm_signals: list[ExtractedSignal] = []
        page_class = PageClassification(page_type=source_type)
        entities: list[str] = []

        if content.word_count >= 50:
            llm_result = await self._llm_extract(
                content.body_text[:5000],
                source_type=source_type,
                company_name=company_name or "Unknown",
            )
            if llm_result:
                if "page_classification" in llm_result:
                    pc = llm_result["page_classification"]
                    page_class = PageClassification(
                        page_type=pc.get("page_type", source_type),
                        content_category=pc.get("content_category", "unknown"),
                        relevance=pc.get("relevance", "medium"),
                    )
                if "signals" in llm_result:
                    for s in llm_result["signals"]:
                        llm_signals.append(ExtractedSignal(
                            signal_type=s.get("signal_type", "unknown"),
                            summary=s.get("summary", ""),
                            evidence=s.get("evidence"),
                            confidence=s.get("confidence", 0.5),
                            typed_data=s.get("typed_data"),
                        ))
                entities = llm_result.get("entities_mentioned", [])

        return ExtractionResult(
            page_classification=page_class,
            content=content,
            tech_signals=tech_signals,
            signals=llm_signals,
            entities_mentioned=entities,
        )

    async def _llm_extract(
        self,
        text: str,
        source_type: str,
        company_name: str,
    ) -> Optional[dict]:
        """Run LLM extraction on preprocessed text."""
        system_prompt = (
            "You are a business intelligence extraction engine. Extract structured "
            "signals from the provided text. Focus on: hiring signals, technology "
            "mentions, financial indicators, organizational changes, competitive "
            "intelligence, and pain signals.\n\n"
            "OUTPUT FORMAT: JSON with keys: page_classification, signals, entities_mentioned"
        )

        user_prompt = (
            f"Company: {company_name}\n"
            f"Source type: {source_type}\n\n"
            f"TEXT:\n{text}\n\n"
            "Extract all relevant business signals. For each signal provide:\n"
            "- signal_type: funding_round | job_posting | key_hire | tech_detected | "
            "tech_migration | leadership_change | competitor_mention | blog_post_pain | "
            "partner_announced | revenue_milestone\n"
            "- summary: One-line description\n"
            "- evidence: Supporting quote from text\n"
            "- confidence: 0.0-1.0\n"
            "- typed_data: Signal-specific fields (amount, department, technology, etc)\n\n"
            "Also classify the page and list entities mentioned."
        )

        return await self.llm.query_json(system_prompt, user_prompt)
