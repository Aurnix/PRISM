"""Content item and corpus data models."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ContentItem(BaseModel):
    """A single piece of content for analysis."""

    source_type: str  # blog | linkedin | press | job_posting | earnings | changelog
    url: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    author_role: Optional[str] = None
    publish_date: date
    raw_text: str
    word_count: int = 0
    is_authored: bool = False
    signal_density_estimate: str = "medium"  # high | medium | low

    def model_post_init(self, __context: object) -> None:
        """Calculate word count if not set."""
        if self.word_count == 0 and self.raw_text:
            self.word_count = len(self.raw_text.split())


class ContentCorpus(BaseModel):
    """Assembled content corpus for a single account."""

    account_slug: str
    assembly_date: date
    items: list[ContentItem] = Field(default_factory=list)
    total_items: int = 0
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    source_distribution: dict[str, int] = Field(default_factory=dict)
    estimated_density: str = "medium"  # high | medium | low
    meets_minimum: bool = False

    def model_post_init(self, __context: object) -> None:
        """Update corpus metadata from items."""
        if self.items and self.total_items == 0:
            self._update_metadata()

    def _update_metadata(self) -> None:
        """Recalculate metadata from items."""
        self.total_items = len(self.items)
        if self.items:
            dates = sorted(item.publish_date for item in self.items)
            self.date_range_start = dates[0]
            self.date_range_end = dates[-1]

            dist: dict[str, int] = {}
            for item in self.items:
                dist[item.source_type] = dist.get(item.source_type, 0) + 1
            self.source_distribution = dist

            # Minimum: 5+ items across 2+ months
            if self.total_items >= 5 and self.date_range_start and self.date_range_end:
                span_days = (self.date_range_end - self.date_range_start).days
                self.meets_minimum = span_days >= 60
            else:
                self.meets_minimum = False
