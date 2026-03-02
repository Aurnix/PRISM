"""Production DAL backed by PostgreSQL via async SQLAlchemy.

All database operations go through this class. The DAL owns the
session and handles all SQL — callers never touch SQLAlchemy directly.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, func, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from prism.data.dal import DataAccessLayer
from prism.db.converters import (
    account_to_row_dict,
    contact_to_row_dict,
    content_item_to_row_dict,
    row_to_account,
    row_to_contact,
    row_to_content_item,
    row_to_signal,
    signal_to_row_dict,
)
from prism.db.models import (
    AccountRow,
    AnalysisRow,
    ContactRow,
    ContentItemRow,
    DossierRow,
    EnrichmentLogRow,
    LinkedInPostRow,
    RawResponseRow,
    SignalRow,
)
from prism.models.account import Account
from prism.models.contact import ContactRecord, LinkedInPost
from prism.models.content import ContentItem
from prism.models.signal import Signal

logger = logging.getLogger(__name__)


class DatabaseDAL(DataAccessLayer):
    """Production DAL backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ─── Accounts ───────────────────────────────────────────────

    async def get_account(self, slug: str) -> Optional[Account]:
        result = await self._session.execute(
            select(AccountRow).where(AccountRow.slug == slug)
        )
        row = result.scalar_one_or_none()
        return row_to_account(row) if row else None

    async def get_account_by_id(self, account_id: UUID) -> Optional[Account]:
        result = await self._session.execute(
            select(AccountRow).where(AccountRow.id == account_id)
        )
        row = result.scalar_one_or_none()
        return row_to_account(row) if row else None

    async def get_account_by_domain(self, domain: str) -> Optional[Account]:
        result = await self._session.execute(
            select(AccountRow).where(AccountRow.domain == domain)
        )
        row = result.scalar_one_or_none()
        return row_to_account(row) if row else None

    async def list_accounts(
        self, status: str = "active", limit: int = 100, offset: int = 0
    ) -> list[Account]:
        result = await self._session.execute(
            select(AccountRow)
            .where(AccountRow.status == status)
            .order_by(AccountRow.company_name)
            .limit(limit)
            .offset(offset)
        )
        return [row_to_account(row) for row in result.scalars().all()]

    async def upsert_account(self, account: Account) -> UUID:
        data = account_to_row_dict(account)
        stmt = insert(AccountRow).values(**data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["slug"],
            set_={k: v for k, v in data.items() if k != "slug"},
        )
        stmt = stmt.returning(AccountRow.id)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.scalar_one()

    async def update_account_status(self, slug: str, status: str) -> None:
        await self._session.execute(
            update(AccountRow).where(AccountRow.slug == slug).values(status=status)
        )
        await self._session.commit()

    # ─── Contacts ───────────────────────────────────────────────

    async def get_contacts(self, account_id: UUID) -> list[ContactRecord]:
        result = await self._session.execute(
            select(ContactRow)
            .where(ContactRow.account_id == account_id)
            .options(selectinload(ContactRow.linkedin_posts))
        )
        return [row_to_contact(row) for row in result.scalars().all()]

    async def upsert_contact(self, account_id: UUID, contact: ContactRecord) -> UUID:
        data = contact_to_row_dict(account_id, contact)
        stmt = insert(ContactRow).values(**data)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_contact_identity",
            set_={k: v for k, v in data.items() if k not in ("account_id", "name", "title")},
        )
        stmt = stmt.returning(ContactRow.id)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.scalar_one()

    async def add_linkedin_posts(self, contact_id: UUID, posts: list[LinkedInPost]) -> int:
        added = 0
        for post in posts:
            text_hash = hashlib.md5(post.text.encode()).hexdigest()
            # Check for duplicate
            existing = await self._session.execute(
                select(LinkedInPostRow).where(
                    LinkedInPostRow.contact_id == contact_id,
                    LinkedInPostRow.post_date == post.date,
                    func.md5(LinkedInPostRow.text) == text_hash,
                )
            )
            if existing.scalar_one_or_none() is None:
                row = LinkedInPostRow(
                    contact_id=contact_id,
                    post_date=post.date,
                    text=post.text,
                )
                self._session.add(row)
                added += 1
        if added:
            await self._session.commit()
        return added

    # ─── Signals ────────────────────────────────────────────────

    async def get_signals(self, account_id: UUID) -> list[Signal]:
        result = await self._session.execute(
            select(SignalRow)
            .where(SignalRow.account_id == account_id, SignalRow.is_active.is_(True))
            .order_by(SignalRow.detected_date.desc())
        )
        return [row_to_signal(row) for row in result.scalars().all()]

    async def add_signals(self, account_id: UUID, signals: list[Signal]) -> int:
        added = 0
        for signal in signals:
            data = signal_to_row_dict(account_id, signal)
            summary_hash = hashlib.md5(signal.description.encode()).hexdigest()
            existing = await self._session.execute(
                select(SignalRow).where(
                    SignalRow.account_id == account_id,
                    SignalRow.signal_type == signal.signal_type,
                    SignalRow.detected_date == signal.detected_date,
                    func.md5(SignalRow.summary) == summary_hash,
                )
            )
            if existing.scalar_one_or_none() is None:
                self._session.add(SignalRow(**data))
                added += 1
        if added:
            await self._session.commit()
        return added

    # ─── Content ────────────────────────────────────────────────

    async def get_content(
        self, account_id: UUID, source_type: Optional[str] = None, limit: int = 30
    ) -> list[ContentItem]:
        stmt = (
            select(ContentItemRow)
            .where(
                ContentItemRow.account_id == account_id,
                ContentItemRow.status == "active",
            )
            .order_by(ContentItemRow.publish_date.desc())
            .limit(limit)
        )
        if source_type:
            stmt = stmt.where(ContentItemRow.source_type == source_type)
        result = await self._session.execute(stmt)
        return [row_to_content_item(row) for row in result.scalars().all()]

    async def add_content(self, account_id: UUID, items: list[ContentItem]) -> int:
        added = 0
        for item in items:
            data = content_item_to_row_dict(account_id, item)
            text_hash = hashlib.md5(item.raw_text.encode()).hexdigest()
            existing = await self._session.execute(
                select(ContentItemRow).where(
                    ContentItemRow.account_id == account_id,
                    ContentItemRow.source_type == item.source_type,
                    ContentItemRow.publish_date == item.publish_date,
                    func.md5(ContentItemRow.body_text) == text_hash,
                )
            )
            if existing.scalar_one_or_none() is None:
                self._session.add(ContentItemRow(**data))
                added += 1
        if added:
            await self._session.commit()
        return added

    async def get_content_by_url(self, url: str) -> Optional[ContentItem]:
        result = await self._session.execute(
            select(ContentItemRow).where(ContentItemRow.url == url)
        )
        row = result.scalar_one_or_none()
        return row_to_content_item(row) if row else None

    async def update_content_status(self, content_id: UUID, status: str) -> None:
        await self._session.execute(
            update(ContentItemRow)
            .where(ContentItemRow.id == content_id)
            .values(status=status)
        )
        await self._session.commit()

    # ─── Analyses ───────────────────────────────────────────────

    async def create_analysis(self, account_id: UUID, prompt_version: str) -> UUID:
        row = AnalysisRow(
            account_id=account_id,
            prompt_version=prompt_version,
            status="pending",
            started_at=datetime.now(timezone.utc),
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row.id

    async def update_analysis(self, analysis_id: UUID, **kwargs) -> None:
        values = {k: v for k, v in kwargs.items() if v is not None}
        if values:
            await self._session.execute(
                update(AnalysisRow).where(AnalysisRow.id == analysis_id).values(**values)
            )
            await self._session.commit()

    async def get_latest_analysis(self, account_id: UUID) -> Optional[dict]:
        result = await self._session.execute(
            select(AnalysisRow)
            .where(AnalysisRow.account_id == account_id, AnalysisRow.status == "complete")
            .order_by(AnalysisRow.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _analysis_row_to_dict(row)

    async def get_analysis_history(self, account_id: UUID, limit: int = 10) -> list[dict]:
        result = await self._session.execute(
            select(AnalysisRow)
            .where(AnalysisRow.account_id == account_id)
            .order_by(AnalysisRow.created_at.desc())
            .limit(limit)
        )
        return [_analysis_row_to_dict(row) for row in result.scalars().all()]

    # ─── Dossiers ───────────────────────────────────────────────

    async def save_dossier(
        self, dossier_id: str, account_id: UUID, analysis_id: UUID, markdown_content: str
    ) -> UUID:
        row = DossierRow(
            dossier_id=dossier_id,
            account_id=account_id,
            analysis_id=analysis_id,
            markdown_content=markdown_content,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row.id

    async def get_dossier(self, dossier_id: str) -> Optional[str]:
        result = await self._session.execute(
            select(DossierRow.markdown_content).where(DossierRow.dossier_id == dossier_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_dossier(self, account_id: UUID) -> Optional[str]:
        result = await self._session.execute(
            select(DossierRow.markdown_content)
            .where(DossierRow.account_id == account_id)
            .order_by(DossierRow.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ─── Raw Responses ──────────────────────────────────────────

    async def write_raw_response(
        self, account_id, source_type, url, http_status,
        raw_headers, raw_body, response_size_bytes=None,
    ) -> UUID:
        row = RawResponseRow(
            account_id=account_id,
            source_type=source_type,
            url=url,
            http_status=http_status,
            raw_headers=raw_headers,
            raw_body=raw_body,
            response_size_bytes=response_size_bytes,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row.id

    # ─── Enrichment Log ─────────────────────────────────────────

    async def log_enrichment(
        self, account_id, source, status, items_added=0, error=None,
    ) -> None:
        row = EnrichmentLogRow(
            account_id=account_id,
            source=source,
            status=status,
            items_added=items_added,
            error=error,
        )
        self._session.add(row)
        await self._session.commit()

    # ─── Scheduler Queries ──────────────────────────────────────

    async def get_accounts_for_reanalysis(self, max_signal_age_days: int = 7) -> list[Account]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_signal_age_days)
        result = await self._session.execute(
            select(AccountRow)
            .where(AccountRow.status == "active")
            .where(
                AccountRow.id.in_(
                    select(SignalRow.account_id)
                    .where(SignalRow.created_at >= cutoff)
                    .distinct()
                )
            )
        )
        return [row_to_account(row) for row in result.scalars().all()]

    async def get_stale_accounts(self, stale_after_days: int = 30) -> list[Account]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=stale_after_days)
        result = await self._session.execute(
            select(AccountRow)
            .where(AccountRow.status == "active")
            .where(
                (AccountRow.last_analyzed.is_(None)) | (AccountRow.last_analyzed < cutoff)
            )
        )
        return [row_to_account(row) for row in result.scalars().all()]


def _analysis_row_to_dict(row: AnalysisRow) -> dict:
    """Convert AnalysisRow to a dict representation."""
    return {
        "id": str(row.id),
        "account_id": str(row.account_id),
        "status": row.status,
        "prompt_version": row.prompt_version,
        "scores": row.scores,
        "why_now": row.why_now,
        "confidence": row.confidence,
        "journey_position": row.journey_position,
        "journey_label": row.journey_label,
        "journey_velocity": row.journey_velocity,
        "total_input_tokens": row.total_input_tokens,
        "total_output_tokens": row.total_output_tokens,
        "total_api_calls": row.total_api_calls,
        "estimated_cost_usd": row.estimated_cost_usd,
        "limited_analysis": row.limited_analysis,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }
