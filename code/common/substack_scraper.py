"""Shared Substack newsletter discovery, API pagination, and parsing."""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from common.base_scraper import BaseScraper
    from common.models import Article, ParsedIssueInfo, Quote
except ImportError:
    from code.common.base_scraper import BaseScraper
    from code.common.models import Article, ParsedIssueInfo, Quote


class SubstackScraper(BaseScraper):
    """
    Common implementation for newsletters and publications published on Substack.
    Uses Substack's public JSON API endpoint (/api/v1/archive?sort=new).
    """

    base_url: str = ""
    newsletter_name: str = ""
    article_id_prefix: str = ""
    log_name: str = "Substack"
    max_posts_to_fetch: int = 200
    page_limit: int = 50

    def __init__(self, source_dir: str):
        super().__init__(source_dir=source_dir)

    def extract_guest_author(self, title: str) -> Tuple[str, Optional[str]]:
        """
        Extracts guest author from title (e.g. 'Formal methods with Hillel Wayne' -> 'with Hillel Wayne').
        """
        author = None
        cleaned_title = title

        # Pattern 1: ", with [Guest Name]" or " - with [Guest Name]"
        match1 = re.search(r'[,–—\-]\s*(with\s+([A-Z][A-Za-z\s\.\,\'\-]+))$', title, re.IGNORECASE)
        if match1:
            author = match1.group(1).strip()
            cleaned_title = title[:match1.start()].strip()
            return cleaned_title, author

        # Pattern 2: "with [Guest Name]" at the end
        match2 = re.search(r'\b(with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+))$', title, re.IGNORECASE)
        if match2:
            author = match2.group(1).strip()
            return cleaned_title, author

        return cleaned_title, author

    def detect_content_type(self, post: Dict[str, Any], raw_title: str) -> str:
        """
        Detect content type: pulse, video (podcast/AMA), or article.
        """
        if raw_title.lower().startswith("the pulse:") or "pulse" in raw_title.lower():
            return "pulse"
        if post.get("podcast_url") or post.get("type") == "podcast" or "ama" in raw_title.lower():
            return "video"
        return "article"

    def parse_post_payload(self, post: Dict[str, Any]) -> Optional[Article]:
        """
        Parses a single Substack post object from the API into an Article domain model.
        """
        raw_title = post.get("title", "").strip()
        if not raw_title:
            return None

        canonical_url = post.get("canonical_url", "")
        if not canonical_url and post.get("slug"):
            canonical_url = f"{self.base_url.rstrip('/')}/p/{post['slug']}"

        clean_link = self.clean_url(canonical_url)
        if not clean_link:
            return None

        # Parse date from post_date (ISO 8601 string, e.g. 2026-08-20T17:53:01.239Z)
        post_date_str = post.get("post_date", "")
        try:
            dt = datetime.fromisoformat(post_date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError) as exc:
            identity = post.get("id") or post.get("slug") or raw_title
            raise ValueError(
                f"{self.newsletter_name or 'Substack'} post {identity!r} has invalid post_date "
                f"{post_date_str!r}"
            ) from exc

        date_iso = dt.strftime("%Y-%m-%d")
        date_str = dt.strftime("%d %B %Y").lstrip("0")

        subtitle = post.get("subtitle", "") or ""
        subtitle = subtitle.strip().replace('&amp;', 'and')

        content_type = self.detect_content_type(post, raw_title)
        _, guest_author = self.extract_guest_author(raw_title)

        category = self.auto_categorize(raw_title, subtitle)
        art_id = self.make_article_id(self.article_id_prefix, date_iso[:7], clean_link, raw_title)

        return Article(
            id=art_id,
            newsletter=self.newsletter_name,
            issue_number=None,
            issue_title=self.newsletter_name,
            issue_link=f"{self.base_url.rstrip('/')}/archive",
            date=date_iso,
            date_str=date_str,
            title=raw_title,
            link=clean_link,
            author=guest_author,
            description=subtitle,
            category=category,
            is_spotlight=False,
            type=content_type,
            hide=False,
            user_overrides=[],
            metadata={
                "audience": post.get("audience", "everyone"),
                "slug": post.get("slug", "")
            }
        )

    def discover_and_ingest_posts(self) -> int:
        """
        Fetches all published posts from Substack's API and merges into data.json.
        """
        print(f"[{self.log_name}] Querying Substack API for {self.newsletter_name} articles...")
        all_posts = []
        offset = 0
        limit = self.page_limit

        while True:
            api_url = f"{self.base_url.rstrip('/')}/api/v1/archive?sort=new&limit={limit}&offset={offset}"
            data = self.fetch_json(api_url)
            if not isinstance(data, list):
                raise ValueError(
                    f"{self.newsletter_name} archive API returned {type(data).__name__}, expected list"
                )
            if not data:
                break
            all_posts.extend(data)
            offset += len(data)
            if len(data) < limit or offset >= self.max_posts_to_fetch:
                break

        print(f"[{self.log_name}] Retrieved {len(all_posts)} posts from Substack.")

        parsed_articles = []
        for p in all_posts:
            try:
                art = self.parse_post_payload(p)
            except ValueError as exc:
                print(f"[{self.log_name}] Skipping malformed post: {exc}")
                continue
            if art:
                parsed_articles.append(art)

        if all_posts and not parsed_articles:
            raise RuntimeError(
                f"{self.newsletter_name} API returned posts, but none could be parsed"
            )

        print(f"[{self.log_name}] Prepared {len(parsed_articles)} articles.")
        merged_count = self.merge_articles(parsed_articles)

        if self.definition and self.articles:
            self.sync_parsed_issues([
                {
                    "id": a.id,
                    "date": a.date,
                    "date_str": a.date,
                    "title": a.title,
                    "url": a.link,
                    "quotes": [],
                }
                for a in self.articles
            ])

        self.save_data()
        print(f"[{self.log_name}] Saved and synced {len(self.articles)} total articles.")
        return merged_count
