"""
The Pragmatic Engineer Scraper & Parser using Substack API.
Extracts articles, podcast episodes, and Pulse digests from newsletter.pragmaticengineer.com.
"""

import os
import re
import sys
import json
from datetime import datetime
from typing import List, Optional, Dict

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
code_dir = os.path.join(project_root, "code")

for p in [code_dir, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.base_scraper import BaseScraper
from common.models import Article, Quote, ParsedIssueInfo

class PragmaticEngineerScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_dir=current_dir)

    def extract_guest_author(self, title: str) -> tuple[str, Optional[str]]:
        """
        Extracts guest name from title (e.g., 'Formal methods with Hillel Wayne' -> author: 'with Hillel Wayne').
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

    def parse_post_payload(self, post: Dict) -> Optional[Article]:
        """
        Parses a single Substack post object into an Article domain model.
        """
        raw_title = post.get("title", "").strip()
        if not raw_title:
            return None

        canonical_url = post.get("canonical_url", "")
        if not canonical_url and post.get("slug"):
            canonical_url = f"https://newsletter.pragmaticengineer.com/p/{post['slug']}"

        clean_link = self.clean_url(canonical_url)
        if not clean_link:
            return None

        # Parse date from post_date (ISO 8601 string, e.g. 2026-08-20T17:53:01.239Z)
        post_date_str = post.get("post_date", "")
        try:
            dt = datetime.fromisoformat(post_date_str.replace("Z", "+00:00"))
        except ValueError as exc:
            identity = post.get("id") or post.get("slug") or raw_title
            raise ValueError(
                f"Pragmatic Engineer post {identity!r} has invalid post_date "
                f"{post_date_str!r}"
            ) from exc
        date_iso = dt.strftime("%Y-%m-%d")
        date_str = dt.strftime("%d %B %Y").lstrip("0")

        subtitle = post.get("subtitle", "") or ""
        subtitle = subtitle.strip().replace('&amp;', 'and')

        # Detect Content Type
        content_type = "article"
        if raw_title.lower().startswith("the pulse:") or "pulse" in raw_title.lower():
            content_type = "pulse"
        elif post.get("podcast_url") or post.get("type") == "podcast" or "ama" in raw_title.lower():
            content_type = "video"

        # Detect guest author
        title_for_display, guest_author = self.extract_guest_author(raw_title)

        category = self.auto_categorize(raw_title, subtitle)
        art_id = self.make_article_id("pe", date_iso[:7], clean_link, raw_title)

        return Article(
            id=art_id,
            newsletter="The Pragmatic Engineer",
            issue_number=None,
            issue_title="The Pragmatic Engineer",
            issue_link="https://newsletter.pragmaticengineer.com/archive",
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
        print("[PragmaticEngineer] Querying Substack API for Pragmatic Engineer articles...")
        all_posts = []
        offset = 0
        limit = 50

        while True:
            api_url = f"https://newsletter.pragmaticengineer.com/api/v1/archive?sort=new&limit={limit}&offset={offset}"
            data = self.fetch_json(api_url)
            if not isinstance(data, list):
                raise ValueError(
                    f"Pragmatic Engineer archive API returned {type(data).__name__}, expected list"
                )
            if not data:
                break
            all_posts.extend(data)
            offset += len(data)
            if len(data) < limit or offset >= 200:
                break

        print(f"[PragmaticEngineer] Retrieved {len(all_posts)} posts from Substack.")

        parsed_articles = []
        for p in all_posts:
            try:
                art = self.parse_post_payload(p)
            except ValueError as exc:
                print(f"[PragmaticEngineer] Skipping malformed post: {exc}")
                continue
            if art:
                parsed_articles.append(art)
        if all_posts and not parsed_articles:
            raise RuntimeError(
                "Pragmatic Engineer API returned posts, but none could be parsed"
            )

        # Also merge any baseline from data-sources/pragmatic-engineer/full.md if available
        baseline_file = os.path.join(project_root, "data-sources", "pragmatic-engineer", "full.md")
        if os.path.exists(baseline_file):
            with open(baseline_file, "r", encoding="utf-8") as f:
                baseline_content = f.read()
            for line in baseline_content.split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    m = re.search(r'\[(.*?)\]\((https://newsletter\.pragmaticengineer\.com/p/[^\)]+)\)', line)
                    if m:
                        t = m.group(1).strip()
                        u = m.group(2).strip()
                        clean_u = self.clean_url(u)
                        # Find matching article to enrich category/author if present
                        match = next((a for a in parsed_articles if a.link == clean_u), None)
                        if match:
                            cat_m = re.search(r'\[Category:\s*(.*?)\]', line)
                            if cat_m:
                                match.category = cat_m.group(1).strip()
                            if "- **" in line:
                                auth_m = re.search(r'-\s*\*\*(.*?)\*\*', line)
                                if auth_m:
                                    match.author = auth_m.group(1).strip()

        print(f"[PragmaticEngineer] Prepared {len(parsed_articles)} articles.")
        merged_count = self.merge_articles(parsed_articles)
        
        # Update definition tracking. This source has no issue numbering — each post is
        # its own "issue" — so the tracker is built from the articles themselves. It
        # previously wrote an *article* count into `count`, left `issues` empty, and put
        # an article id in `last_parsed_issue`, so the three fields disagreed.
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
        print(f"[PragmaticEngineer] Saved and synced {len(self.articles)} total articles.")
        return merged_count

if __name__ == "__main__":
    scraper = PragmaticEngineerScraper()
    scraper.discover_and_ingest_posts()
