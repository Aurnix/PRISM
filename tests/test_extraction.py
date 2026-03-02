"""Tests for the extraction pipeline models and service."""

import pytest

from prism.models.extraction import (
    CompetitorMentionData,
    ExtractionResult,
    ExtractedContent,
    ExtractedSignal,
    ExtractedTechSignal,
    FundingRoundData,
    JobPostingData,
    KeyHireData,
    PageClassification,
    TechDetectedData,
    TechMigrationData,
    map_signal_type,
)
from prism.services.extraction import (
    ExtractionService,
    detect_tech_from_text,
    preprocess_html,
)


# ── Model Tests ──────────────────────────────────────────────────────────────


class TestPageClassification:
    def test_defaults(self):
        pc = PageClassification()
        assert pc.page_type == "unknown"
        assert pc.content_category == "unknown"
        assert pc.relevance == "medium"

    def test_full_construction(self):
        pc = PageClassification(
            page_type="blog_post",
            content_category="technical",
            relevance="high",
        )
        assert pc.page_type == "blog_post"


class TestExtractedContent:
    def test_minimal(self):
        content = ExtractedContent(body_text="Hello world", word_count=2)
        assert content.word_count == 2
        assert content.title is None

    def test_full(self):
        from datetime import date

        content = ExtractedContent(
            title="Test Title",
            author="Jane",
            publish_date=date(2026, 1, 1),
            body_text="Full text here",
            word_count=3,
        )
        assert content.author == "Jane"


class TestExtractedSignal:
    def test_basic_signal(self):
        sig = ExtractedSignal(
            signal_type="funding_round",
            summary="$10M raised",
            confidence=0.9,
        )
        assert sig.signal_type == "funding_round"
        assert sig.confidence == 0.9

    def test_with_typed_data(self):
        sig = ExtractedSignal(
            signal_type="funding_round",
            summary="$10M Series A",
            confidence=0.85,
            typed_data={"amount": 10_000_000, "round": "Series A"},
        )
        assert sig.typed_data["amount"] == 10_000_000


class TestTypedDataModels:
    def test_funding_round_data(self):
        data = FundingRoundData(
            amount=28_000_000,
            round="Series B",
            lead_investor="Sequoia",
        )
        assert data.amount == 28_000_000

    def test_job_posting_data(self):
        data = JobPostingData(
            role_title="Senior Accountant",
            department="Finance",
            seniority="mid",
        )
        assert data.department == "Finance"

    def test_key_hire_data(self):
        data = KeyHireData(
            person_name="Jane Smith",
            title="VP Finance",
            previous_company="Stripe",
        )
        assert data.previous_company == "Stripe"

    def test_tech_detected_data(self):
        data = TechDetectedData(
            technology="QuickBooks",
            category="erp",
        )
        assert data.category == "erp"

    def test_tech_migration_data(self):
        data = TechMigrationData(
            from_tech="QuickBooks",
            to_tech="NetSuite",
        )
        assert data.from_tech == "QuickBooks"

    def test_competitor_mention_data(self):
        data = CompetitorMentionData(
            competitor="Rillet",
            context="evaluation",
        )
        assert data.context == "evaluation"


class TestSignalTypeMapping:
    def test_known_types(self):
        assert map_signal_type("funding_round") == "funding_round"
        assert map_signal_type("key_hire") == "new_executive_other"
        assert map_signal_type("tech_detected") == "tech_stack_change"
        assert map_signal_type("competitor_mention") == "competitor_evaluation"

    def test_unknown_type_passthrough(self):
        assert map_signal_type("something_custom") == "something_custom"


# ── Service Tests ────────────────────────────────────────────────────────────


class TestDetectTechFromText:
    def test_detects_quickbooks(self):
        text = "We currently use QuickBooks for our accounting needs."
        results = detect_tech_from_text(text)
        assert any(r.technology == "QuickBooks" for r in results)

    def test_detects_multiple_techs(self):
        text = "We use Salesforce for CRM and AWS for hosting. Also evaluating NetSuite."
        results = detect_tech_from_text(text)
        techs = {r.technology for r in results}
        assert "Salesforce" in techs
        assert "AWS" in techs
        assert "NetSuite" in techs

    def test_detects_competitors(self):
        text = "Looking at solutions like Rillet and Puzzle for our accounting."
        results = detect_tech_from_text(text)
        techs = {r.technology for r in results}
        assert "Rillet" in techs
        assert "Puzzle" in techs

    def test_no_duplicates(self):
        text = "We use AWS. Our AWS deployment is great. AWS is our cloud."
        results = detect_tech_from_text(text)
        aws_results = [r for r in results if r.technology == "AWS"]
        assert len(aws_results) == 1

    def test_no_matches(self):
        text = "This is a generic text with no technology mentions."
        results = detect_tech_from_text(text)
        assert len(results) == 0

    def test_confidence_is_set(self):
        text = "We use Stripe for payments."
        results = detect_tech_from_text(text)
        assert all(r.confidence == 0.7 for r in results)

    def test_evidence_is_captured(self):
        text = "Our company switched to Stripe for all payment processing last quarter."
        results = detect_tech_from_text(text)
        stripe_result = next(r for r in results if r.technology == "Stripe")
        assert "Stripe" in stripe_result.evidence


class TestPreprocessHtml:
    def test_extracts_body_text(self):
        html = "<html><body><p>Hello world</p></body></html>"
        content = preprocess_html(html)
        assert "Hello world" in content.body_text
        assert content.word_count >= 2

    def test_extracts_title(self):
        html = "<html><head><title>My Page</title></head><body><h1>Main Heading</h1><p>text</p></body></html>"
        content = preprocess_html(html)
        assert content.title == "Main Heading"  # h1 takes precedence

    def test_removes_nav_footer(self):
        html = """
        <html><body>
            <nav>Navigation here</nav>
            <main><p>Main content</p></main>
            <footer>Footer here</footer>
        </body></html>
        """
        content = preprocess_html(html)
        assert "Navigation here" not in content.body_text
        assert "Footer here" not in content.body_text
        assert "Main content" in content.body_text

    def test_removes_script_style(self):
        html = """
        <html><body>
            <script>var x = 1;</script>
            <style>.foo { color: red; }</style>
            <p>Visible content</p>
        </body></html>
        """
        content = preprocess_html(html)
        assert "var x" not in content.body_text
        assert "color: red" not in content.body_text
        assert "Visible content" in content.body_text

    def test_extracts_author_meta(self):
        html = '<html><head><meta name="author" content="Jane Doe"></head><body><p>text</p></body></html>'
        content = preprocess_html(html)
        assert content.author == "Jane Doe"

    def test_extracts_publish_date(self):
        html = '<html><head><meta property="article:published_time" content="2026-02-15T10:00:00Z"></head><body><p>text</p></body></html>'
        content = preprocess_html(html)
        from datetime import date
        assert content.publish_date == date(2026, 2, 15)

    def test_handles_plain_text(self):
        # When no HTML tags at all
        text = "Just plain text without HTML"
        content = preprocess_html(text)
        assert "plain text" in content.body_text


class TestExtractionResult:
    def test_default_construction(self):
        content = ExtractedContent(body_text="test", word_count=1)
        result = ExtractionResult(
            page_classification=PageClassification(),
            content=content,
        )
        assert result.tech_signals == []
        assert result.signals == []
        assert result.entities_mentioned == []

    def test_full_construction(self):
        content = ExtractedContent(body_text="test", word_count=1)
        result = ExtractionResult(
            page_classification=PageClassification(page_type="blog_post"),
            content=content,
            tech_signals=[
                ExtractedTechSignal(
                    technology="Stripe",
                    category="payment",
                    evidence="uses Stripe",
                    confidence=0.7,
                )
            ],
            signals=[
                ExtractedSignal(
                    signal_type="funding_round",
                    summary="Raised money",
                    confidence=0.8,
                )
            ],
            entities_mentioned=["Stripe", "Sequoia"],
        )
        assert len(result.tech_signals) == 1
        assert len(result.signals) == 1
        assert len(result.entities_mentioned) == 2
