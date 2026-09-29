"""
The Week Ahead (by Above) Newsletter & Event Radar Scraper.
Provides curated ingestion for the weekly "The Week Ahead in Media + Tech" edition.
Automated LinkedIn crawling is disabled to respect LinkedIn terms of service and avoid HTTP 999.
"""

import os
import sys
from typing import List, Optional, Dict, Any

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
code_dir = os.path.join(project_root, "code")

for p in [code_dir, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.base_scraper import BaseScraper
from common.models import Article, ParsedIssueInfo


class TheWeekAheadScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_dir=current_dir)

    def ingest_issue_data(
        self,
        issue_number: int,
        issue_title: str,
        issue_url: str,
        date_iso: str,
        date_str: str,
        raw_items: List[Dict[str, Any]]
    ) -> int:
        """
        Programmatically ingests a curated issue without web scraping.
        """
        print(f"[TheWeekAhead] Ingesting Issue #{issue_number}: {issue_title}...")
        parsed_articles = []
        for item in raw_items:
            art_id = self.make_article_id("twa", issue_number, item["link"], item["title"])
            article = Article(
                id=art_id,
                newsletter="The Week Ahead",
                issue_number=issue_number,
                issue_title=issue_title,
                issue_link=issue_url,
                date=date_iso,
                date_str=date_str,
                title=item["title"],
                link=item["link"],
                author=item.get("author", "Above"),
                description=item.get("description", ""),
                category=item.get("category", "Software Architecture & Distributed Systems"),
                is_spotlight=item.get("is_spotlight", False),
                type=item.get("type", "conference"),
                hide=item.get("hide", False),
                user_overrides=["hide"] if item.get("hide", False) else [],
                metadata=item.get("metadata", {})
            )
            parsed_articles.append(article)

        merged_count = self.merge_articles(parsed_articles)

        existing = list(self.definition.parsed_issues.issues) if self.definition else []
        issue_id = str(issue_number)
        by_id = {issue.id: issue for issue in existing}
        by_id[issue_id] = ParsedIssueInfo(
            id=issue_id,
            date=date_iso,
            date_str=date_str,
            title=issue_title,
            url=issue_url,
        )
        self.sync_parsed_issues(list(by_id.values()))
        self.save_data()
        print(f"[TheWeekAhead] Saved and synced {len(self.articles)} total articles.")
        return merged_count

    def discover_and_ingest_new_issues(self, reparse_all: bool = False) -> int:
        raise RuntimeError(
            "Automated LinkedIn crawling is disabled: The Week Ahead is curated from "
            "LinkedIn updates, where automated crawling is blocked and prohibited. "
            "Ingest curated weekly issues programmatically instead."
        )


if __name__ == "__main__":
    print("[TheWeekAhead] Curated imported dataset; automated LinkedIn refresh is disabled.")
