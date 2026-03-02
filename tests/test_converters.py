"""Tests for Pydantic <-> SQLAlchemy conversion utilities."""

import uuid
from datetime import date

import pytest

from prism.db.converters import (
    account_to_row_dict,
    contact_to_row_dict,
    content_item_to_row_dict,
    signal_to_row_dict,
)
from prism.models.account import Account, Firmographics, TechStack
from prism.models.contact import ContactRecord, LinkedInPost
from prism.models.content import ContentItem
from prism.models.signal import Signal


class TestAccountToRowDict:
    def test_basic_account(self, sample_account):
        d = account_to_row_dict(sample_account)

        assert d["slug"] == "test_company"
        assert d["company_name"] == "Test Corp"
        assert d["domain"] == "testcorp.com"
        assert d["firmographics"]["industry"] == "SaaS"
        assert d["tech_stack"]["erp_accounting"] == "QuickBooks Online"

    def test_minimal_account(self):
        acct = Account(
            slug="minimal",
            company_name="Min Corp",
            domain="min.com",
            firmographics=Firmographics(),
            tech_stack=TechStack(),
        )
        d = account_to_row_dict(acct)
        assert d["slug"] == "minimal"
        assert "firmographics" in d
        assert "tech_stack" in d


class TestContactToRowDict:
    def test_contact_with_all_fields(self, sample_contacts):
        contact = sample_contacts[0]  # Jane Smith
        account_id = uuid.uuid4()
        d = contact_to_row_dict(account_id, contact)

        assert d["account_id"] == account_id
        assert d["name"] == "Jane Smith"
        assert d["title"] == "VP Finance"
        assert d["buying_role"] == "champion"

    def test_contact_minimal(self):
        contact = ContactRecord(name="Test Person", title="Engineer")
        d = contact_to_row_dict(uuid.uuid4(), contact)
        assert d["name"] == "Test Person"


class TestSignalToRowDict:
    def test_signal_conversion(self, sample_signals):
        signal = sample_signals[0]  # funding_round
        account_id = uuid.uuid4()
        d = signal_to_row_dict(account_id, signal)

        assert d["account_id"] == account_id
        assert d["signal_type"] == "funding_round"
        assert d["summary"] == "$28M Series B closed"
        assert d["detected_date"] == date(2025, 9, 15)


class TestContentItemToRowDict:
    def test_content_item_conversion(self):
        item = ContentItem(
            source_type="blog_post",
            title="Building Better Infrastructure",
            author="Jane Smith",
            publish_date=date(2026, 2, 1),
            raw_text="Full blog post content here...",
            url="https://testcorp.com/blog/building-better",
        )
        account_id = uuid.uuid4()
        d = content_item_to_row_dict(account_id, item)

        assert d["account_id"] == account_id
        assert d["source_type"] == "blog_post"
        assert d["title"] == "Building Better Infrastructure"
        assert d["author"] == "Jane Smith"
