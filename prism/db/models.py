"""SQLAlchemy ORM models for the 9-table PRISM schema.

Uses SQLAlchemy 2.0 Mapped[] annotations. Separate from Pydantic models —
converters.py handles the mapping between layers.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class RawResponseRow(Base):
    """Audit trail for raw HTTP responses. Append-only."""

    __tablename__ = "raw_responses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    http_status: Mapped[Optional[int]] = mapped_column(Integer)
    raw_headers: Mapped[Optional[dict]] = mapped_column(JSONB)
    raw_body: Mapped[Optional[str]] = mapped_column(Text)
    response_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_raw_responses_account", "account_id"),
        Index("idx_raw_responses_url", "url"),
    )


class AccountRow(Base):
    """One row per tracked company."""

    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    blog_url: Mapped[Optional[str]] = mapped_column(Text)
    blog_rss: Mapped[Optional[str]] = mapped_column(Text)
    firmographics: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    tech_stack: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    last_enriched: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_analyzed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    contacts: Mapped[list["ContactRow"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    signals: Mapped[list["SignalRow"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    content_items: Mapped[list["ContentItemRow"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    analyses: Mapped[list["AnalysisRow"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    dossiers: Mapped[list["DossierRow"]] = relationship(back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_accounts_status", "status"),
        Index("idx_accounts_domain", "domain"),
    )


class ContactRow(Base):
    """One row per person at a tracked company."""

    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(Text)
    linkedin_url: Mapped[Optional[str]] = mapped_column(Text)
    start_date_current_role: Mapped[Optional[date]] = mapped_column(Date)
    previous_company: Mapped[Optional[str]] = mapped_column(Text)
    previous_title: Mapped[Optional[str]] = mapped_column(Text)
    buying_role: Mapped[str] = mapped_column(Text, nullable=False, server_default="unknown")
    buying_role_confidence: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.5")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    account: Mapped["AccountRow"] = relationship(back_populates="contacts")
    linkedin_posts: Mapped[list["LinkedInPostRow"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("account_id", "name", "title", name="uq_contact_identity"),
        Index("idx_contacts_account", "account_id"),
    )


class LinkedInPostRow(Base):
    """One row per LinkedIn post from a contact."""

    __tablename__ = "linkedin_posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    post_date: Mapped[date] = mapped_column(Date, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    contact: Mapped["ContactRow"] = relationship(back_populates="linkedin_posts")

    __table_args__ = (
        Index("idx_linkedin_posts_contact", "contact_id"),
    )


class SignalRow(Base):
    """Append-only signal observations."""

    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    signal_type: Mapped[str] = mapped_column(Text, nullable=False)
    signal_category: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[str]] = mapped_column(Text)
    typed_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="manual")
    detected_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_date: Mapped[Optional[date]] = mapped_column(Date)
    confidence: Mapped[str] = mapped_column(Text, nullable=False, server_default="extracted")
    source_content_ids: Mapped[Optional[list]] = mapped_column(ARRAY(UUID(as_uuid=True)))
    decay_profile: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    superseded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("signals.id")
    )
    raw_response_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_responses.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    account: Mapped["AccountRow"] = relationship(back_populates="signals")

    __table_args__ = (
        Index("idx_signals_account", "account_id"),
        Index("idx_signals_type", "signal_type"),
        Index("idx_signals_date", "detected_date"),
    )


class ContentItemRow(Base):
    """Blog posts, press releases, job listings — append-only."""

    __tablename__ = "content_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    content_category: Mapped[Optional[str]] = mapped_column(Text)
    relevance: Mapped[Optional[str]] = mapped_column(Text, server_default="medium")
    url: Mapped[Optional[str]] = mapped_column(Text)
    title: Mapped[Optional[str]] = mapped_column(Text)
    author: Mapped[Optional[str]] = mapped_column(Text)
    author_role: Mapped[Optional[str]] = mapped_column(Text)
    publish_date: Mapped[date] = mapped_column(Date, nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    is_authored: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    extracted_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    extraction_model: Mapped[Optional[str]] = mapped_column(Text)
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Float)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    raw_response_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_responses.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    account: Mapped["AccountRow"] = relationship(back_populates="content_items")

    __table_args__ = (
        Index("idx_content_account", "account_id"),
        Index("idx_content_type", "source_type"),
        Index("idx_content_date", "publish_date"),
    )


class AnalysisRow(Base):
    """One row per analysis run — full history preserved."""

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False, server_default="v1")
    llm_backend: Mapped[Optional[str]] = mapped_column(Text)
    stage1_results: Mapped[Optional[dict]] = mapped_column(JSONB)
    stage2_result: Mapped[Optional[dict]] = mapped_column(JSONB)
    stage3_results: Mapped[Optional[dict]] = mapped_column(JSONB)
    stage4_result: Mapped[Optional[dict]] = mapped_column(JSONB)
    scores: Mapped[Optional[dict]] = mapped_column(JSONB)
    why_now: Mapped[Optional[dict]] = mapped_column(JSONB)
    confidence: Mapped[Optional[dict]] = mapped_column(JSONB)
    journey_position: Mapped[Optional[float]] = mapped_column(Float)
    journey_label: Mapped[Optional[str]] = mapped_column(Text)
    journey_velocity: Mapped[Optional[str]] = mapped_column(Text)
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_api_calls: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    limited_analysis: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    limited_reason: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    account: Mapped["AccountRow"] = relationship(back_populates="analyses")
    dossiers: Mapped[list["DossierRow"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_analyses_account", "account_id"),
        Index("idx_analyses_status", "status"),
        Index("idx_analyses_created", "created_at"),
    )


class DossierRow(Base):
    """Rendered dossier markdown — linked to the analysis that produced it."""

    __tablename__ = "dossiers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    dossier_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    account: Mapped["AccountRow"] = relationship(back_populates="dossiers")
    analysis: Mapped["AnalysisRow"] = relationship(back_populates="dossiers")

    __table_args__ = (
        Index("idx_dossiers_account", "account_id"),
        Index("idx_dossiers_analysis", "analysis_id"),
    )


class EnrichmentLogRow(Base):
    """Tracks every enrichment attempt for debugging and audit."""

    __tablename__ = "enrichment_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    items_added: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_enrichment_account", "account_id"),
    )
