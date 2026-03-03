"""Blog scraper enrichment — wraps existing BlogScraper as an EnrichmentSource."""

import logging
from typing import Optional

from prism.models.account import Account
from prism.services.enrichment.base import EnrichmentResult, EnrichmentSource

logger = logging.getLogger(__name__)


class BlogScraperEnrichment(EnrichmentSource):
    """Blog content enrichment via RSS/HTML scraping.

    Wraps the existing ``services/scraper.py`` BlogScraper and runs the
    extraction pipeline over scraped content to produce signals.
    """

    def source_name(self) -> str:
        return "blog_scraper"

    def is_available(self) -> bool:
        return True  # No API key needed

    async def enrich(
        self,
        domain: str,
        existing_account: Optional[Account] = None,
    ) -> EnrichmentResult:
        from prism.services.scraper import BlogScraper

        result = EnrichmentResult(source=self.source_name())

        blog_url: Optional[str] = None
        blog_rss: Optional[str] = None
        slug: Optional[str] = None

        if existing_account:
            blog_url = existing_account.blog_url
            blog_rss = existing_account.blog_rss
            slug = existing_account.slug

        if not blog_url and not blog_rss:
            # Try common blog paths
            blog_url = f"https://{domain}/blog"

        scraper = BlogScraper()
        try:
            posts = await scraper.scrape(
                blog_url=blog_url or "",
                blog_rss=blog_rss,
                slug=slug or domain,
                use_cache=True,
            )
            for post in posts:
                result.content_items.append(post)

            logger.info(
                "Blog scraper found %d posts for %s",
                len(posts),
                domain,
            )
        except Exception as e:
            msg = f"Blog scraper failed for {domain}: {e}"
            logger.warning(msg)
            result.errors.append(msg)

        return result
