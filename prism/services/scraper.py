"""Blog scraper with RSS detection and HTML fallback.

Scrapes company blog content for the Content Intelligence pipeline.
Respects robots.txt, rate limits, and caches results.
"""

import asyncio
import json
import logging
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

from prism.config import (
    SCRAPED_CONTENT_DIR,
    SCRAPER_MAX_PAGES,
    SCRAPER_RATE_LIMIT,
    SCRAPER_TIMEOUT,
    SCRAPER_USER_AGENT,
)
from prism.models.content import ContentItem

logger = logging.getLogger(__name__)

# Common RSS feed paths to try
RSS_PATHS = ["/feed", "/rss", "/blog/feed", "/blog/rss.xml", "/blog/rss", "/feed.xml", "/rss.xml", "/atom.xml"]


class BlogScraper:
    """Scrapes blog content via RSS or HTML parsing."""

    def __init__(self) -> None:
        self._last_request_time: dict[str, float] = {}
        self._robots_cache: dict[str, Optional[str]] = {}
        self._rate_lock = asyncio.Lock()

    async def scrape(
        self,
        slug: str,
        blog_url: Optional[str] = None,
        blog_rss: Optional[str] = None,
        domain: Optional[str] = None,
        use_cache: bool = True,
    ) -> list[ContentItem]:
        """Scrape blog posts for a company.

        Tries RSS first, falls back to HTML scraping.
        Caches results to fixtures/scraped_content/<slug>/.

        Args:
            slug: Company slug for caching.
            blog_url: Blog page URL.
            blog_rss: Known RSS feed URL.
            domain: Company domain (for RSS discovery).
            use_cache: Whether to use cached results.

        Returns:
            List of ContentItem models.
        """
        # Check cache first
        if use_cache:
            cached = self._load_cache(slug)
            if cached:
                logger.info("Using cached blog content for %s (%d posts)", slug, len(cached))
                return cached

        items: list[ContentItem] = []

        async with httpx.AsyncClient(
            headers={"User-Agent": SCRAPER_USER_AGENT},
            timeout=SCRAPER_TIMEOUT,
            follow_redirects=True,
        ) as client:
            # Try RSS first
            if blog_rss:
                items = await self._scrape_rss(client, blog_rss, slug)

            if not items and domain:
                # Try common RSS paths
                for path in RSS_PATHS:
                    rss_url = f"https://{domain}{path}"
                    items = await self._scrape_rss(client, rss_url, slug)
                    if items:
                        break

            # Fallback to HTML scraping
            if not items and blog_url:
                if await self._check_robots(client, blog_url):
                    items = await self._scrape_html(client, blog_url, slug)
                else:
                    logger.warning("robots.txt disallows scraping %s", blog_url)

        # Cache results
        if items:
            self._save_cache(slug, items)
            logger.info("Scraped %d blog posts for %s", len(items), slug)
        else:
            logger.warning("No blog content found for %s", slug)

        return items

    async def _scrape_rss(
        self,
        client: httpx.AsyncClient,
        rss_url: str,
        slug: str,
    ) -> list[ContentItem]:
        """Attempt to parse an RSS/Atom feed."""
        try:
            await self._rate_limit(rss_url)
            response = await client.get(rss_url)
            if response.status_code != 200:
                return []

            content_type = response.headers.get("content-type", "")
            if "xml" not in content_type and "rss" not in content_type and "<rss" not in response.text[:200] and "<feed" not in response.text[:200]:
                return []

            root = ElementTree.fromstring(response.text)
            items: list[ContentItem] = []

            # RSS 2.0
            for item in root.findall(".//item"):
                title = _xml_text(item, "title")
                link = _xml_text(item, "link")
                pub_date = _xml_text(item, "pubDate")
                description = _xml_text(item, "description")
                author = _xml_text(item, "author") or _xml_text(item, "{http://purl.org/dc/elements/1.1/}creator")

                parsed_date = _parse_rss_date(pub_date)
                if not parsed_date:
                    parsed_date = date.today()

                text = _clean_html(description) if description else ""
                if not text:
                    continue

                items.append(ContentItem(
                    source_type="blog",
                    url=link,
                    title=title,
                    author=author,
                    publish_date=parsed_date,
                    raw_text=text,
                    is_authored=bool(author),
                ))

            # Atom
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns):
                title = _xml_text(entry, "atom:title", ns)
                link_el = entry.find("atom:link", ns)
                link = link_el.get("href", "") if link_el is not None else ""
                pub_date = _xml_text(entry, "atom:published", ns) or _xml_text(entry, "atom:updated", ns)
                content_el = entry.find("atom:content", ns)
                summary_el = entry.find("atom:summary", ns)
                text_raw = (content_el.text if content_el is not None else "") or (summary_el.text if summary_el is not None else "")
                author_el = entry.find("atom:author/atom:name", ns)
                author = author_el.text if author_el is not None else None

                parsed_date = _parse_rss_date(pub_date)
                if not parsed_date:
                    parsed_date = date.today()

                text = _clean_html(text_raw)
                if not text:
                    continue

                items.append(ContentItem(
                    source_type="blog",
                    url=link,
                    title=title,
                    author=author,
                    publish_date=parsed_date,
                    raw_text=text,
                    is_authored=bool(author),
                ))

            return items[:30]  # Cap at max corpus items

        except (httpx.HTTPError, ElementTree.ParseError, ValueError, KeyError) as e:
            logger.debug("RSS scrape failed for %s: %s", rss_url, e)
            return []

    async def _scrape_html(
        self,
        client: httpx.AsyncClient,
        blog_url: str,
        slug: str,
    ) -> list[ContentItem]:
        """Scrape blog via HTML parsing."""
        items: list[ContentItem] = []
        visited: set[str] = set()
        urls_to_scrape = [blog_url]
        page_count = 0

        while urls_to_scrape and page_count < SCRAPER_MAX_PAGES:
            url = urls_to_scrape.pop(0)
            if url in visited:
                continue
            visited.add(url)
            page_count += 1

            try:
                await self._rate_limit(url)
                response = await client.get(url)
                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, "lxml")

                # Remove non-content elements
                for tag in soup.find_all(["nav", "footer", "sidebar", "header", "script", "style", "noscript"]):
                    tag.decompose()

                # Find blog post links
                post_links = self._find_post_links(soup, url)

                for link in post_links:
                    if link in visited:
                        continue
                    visited.add(link)

                    try:
                        await self._rate_limit(link)
                        post_response = await client.get(link)
                        if post_response.status_code != 200:
                            continue

                        post_soup = BeautifulSoup(post_response.text, "lxml")
                        item = self._extract_post(post_soup, link)
                        if item:
                            items.append(item)
                    except (httpx.HTTPError, ValueError, AttributeError) as e:
                        logger.debug("Failed to scrape post %s: %s", link, e)

                # Find next page
                next_link = self._find_next_page(soup, url)
                if next_link and next_link not in visited:
                    urls_to_scrape.append(next_link)

            except (httpx.HTTPError, ValueError, AttributeError) as e:
                logger.debug("Failed to scrape page %s: %s", url, e)

        return items[:30]

    def _find_post_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """Find links to individual blog posts on a listing page."""
        links: list[str] = []
        article_tags = soup.find_all("article") or soup.find_all("div", class_=re.compile(r"post|blog|article|entry"))

        for article in article_tags:
            a_tag = article.find("a", href=True)
            if a_tag:
                href = urljoin(base_url, a_tag["href"])
                if self._looks_like_post_url(href, base_url):
                    links.append(href)

        # Fallback: look for common blog post link patterns
        if not links:
            for a_tag in soup.find_all("a", href=True):
                href = urljoin(base_url, a_tag["href"])
                if self._looks_like_post_url(href, base_url):
                    links.append(href)

        return list(dict.fromkeys(links))[:20]  # Dedupe, cap at 20

    def _looks_like_post_url(self, url: str, base_url: str) -> bool:
        """Heuristic check if a URL looks like a blog post."""
        parsed = urlparse(url)
        base_parsed = urlparse(base_url)

        if parsed.netloc != base_parsed.netloc:
            return False

        path = parsed.path.rstrip("/")
        # Skip common non-post pages
        if path in ("", "/blog", "/posts", "/articles", "/news"):
            return False
        if any(path.endswith(ext) for ext in [".css", ".js", ".png", ".jpg", ".gif", ".svg"]):
            return False

        # Look for patterns like /blog/some-post-title or /2024/01/post-title
        return bool(re.search(r"/blog/.+|/posts?/.+|/\d{4}/.+|/articles?/.+", path))

    def _extract_post(self, soup: BeautifulSoup, url: str) -> Optional[ContentItem]:
        """Extract blog post content from a page."""
        # Remove non-content elements
        for tag in soup.find_all(["nav", "footer", "sidebar", "header", "script", "style", "noscript", "aside"]):
            tag.decompose()

        # Try to find the main content
        article = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", class_=re.compile(r"post-content|article-content|blog-content|entry-content|post-body"))
        )

        if article:
            text = article.get_text(separator="\n", strip=True)
        else:
            body = soup.find("body")
            text = body.get_text(separator="\n", strip=True) if body else ""

        if len(text) < 100:
            return None

        # Extract title
        title = None
        title_tag = soup.find("h1")
        if title_tag:
            title = title_tag.get_text(strip=True)
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title:
                title = og_title.get("content", "")

        # Extract date
        pub_date = None
        time_tag = soup.find("time", datetime=True)
        if time_tag:
            pub_date = _parse_rss_date(time_tag["datetime"])
        if not pub_date:
            date_meta = soup.find("meta", property="article:published_time")
            if date_meta:
                pub_date = _parse_rss_date(date_meta.get("content", ""))
        if not pub_date:
            pub_date = date.today()

        # Extract author
        author = None
        author_tag = soup.find(class_=re.compile(r"author"))
        if author_tag:
            author = author_tag.get_text(strip=True)

        return ContentItem(
            source_type="blog",
            url=url,
            title=title,
            author=author,
            publish_date=pub_date,
            raw_text=text[:10000],  # Cap text length
            is_authored=bool(author),
        )

    def _find_next_page(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """Find 'next page' or 'older posts' link."""
        patterns = [
            re.compile(r"next|older|more", re.IGNORECASE),
        ]

        for pattern in patterns:
            for a_tag in soup.find_all("a", string=pattern, href=True):
                return urljoin(current_url, a_tag["href"])

            for a_tag in soup.find_all("a", class_=pattern, href=True):
                return urljoin(current_url, a_tag["href"])

        # Check rel="next"
        next_link = soup.find("a", rel="next", href=True)
        if next_link:
            return urljoin(current_url, next_link["href"])

        return None

    async def _check_robots(self, client: httpx.AsyncClient, url: str) -> bool:
        """Check robots.txt for scraping permission."""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        if robots_url in self._robots_cache:
            robots_text = self._robots_cache[robots_url]
        else:
            try:
                response = await client.get(robots_url)
                robots_text = response.text if response.status_code == 200 else None
                self._robots_cache[robots_url] = robots_text
            except Exception:
                self._robots_cache[robots_url] = None
                return True

        if not robots_text:
            return True

        # Simple robots.txt parsing
        path = parsed.path or "/"
        disallowed = False
        applies = False

        for line in robots_text.split("\n"):
            line = line.strip()
            if line.lower().startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip().lower()
                applies = agent == "*" or "prism" in agent
            elif applies and line.lower().startswith("disallow:"):
                disallowed_path = line.split(":", 1)[1].strip()
                if disallowed_path and path.startswith(disallowed_path):
                    disallowed = True

        return not disallowed

    async def _rate_limit(self, url: str) -> None:
        """Enforce rate limiting per domain."""
        async with self._rate_lock:
            domain = urlparse(url).netloc
            now = time.time()

            if domain in self._last_request_time:
                elapsed = now - self._last_request_time[domain]
                if elapsed < SCRAPER_RATE_LIMIT:
                    await asyncio.sleep(SCRAPER_RATE_LIMIT - elapsed)

            self._last_request_time[domain] = time.time()

    def _load_cache(self, slug: str) -> Optional[list[ContentItem]]:
        """Load cached blog posts."""
        cache_file = SCRAPED_CONTENT_DIR / slug / "blog_posts.json"
        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text())
            return [
                ContentItem(
                    source_type="blog",
                    url=post.get("url"),
                    title=post.get("title"),
                    author=post.get("author"),
                    publish_date=date.fromisoformat(post["date"]),
                    raw_text=post["text"],
                    is_authored=bool(post.get("author")),
                )
                for post in data
            ]
        except Exception as e:
            logger.warning("Failed to load cache for %s: %s", slug, e)
            return None

    def _save_cache(self, slug: str, items: list[ContentItem]) -> None:
        """Cache scraped blog posts."""
        cache_dir = SCRAPED_CONTENT_DIR / slug
        cache_dir.mkdir(parents=True, exist_ok=True)

        data = [
            {
                "url": item.url,
                "title": item.title,
                "author": item.author,
                "date": item.publish_date.isoformat(),
                "text": item.raw_text,
            }
            for item in items
        ]

        (cache_dir / "blog_posts.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False)
        )


def _xml_text(element: ElementTree.Element, tag: str, ns: Optional[dict] = None) -> Optional[str]:
    """Extract text from an XML element."""
    child = element.find(tag, ns) if ns else element.find(tag)
    return child.text if child is not None and child.text else None


def _clean_html(html: str) -> str:
    """Strip HTML tags and clean up text."""
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator="\n", strip=True)


def _parse_rss_date(date_str: Optional[str]) -> Optional[date]:
    """Parse various date formats from RSS feeds."""
    if not date_str:
        return None

    date_str = date_str.strip()

    formats = [
        "%a, %d %b %Y %H:%M:%S %z",  # RFC 822
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d",
        "%B %d, %Y",
        "%b %d, %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    # Try ISO format directly
    try:
        return date.fromisoformat(date_str[:10])
    except ValueError:
        return None
