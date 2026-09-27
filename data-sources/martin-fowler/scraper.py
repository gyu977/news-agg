import os
import sys
import re
import html
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Any

current_dir = os.path.dirname(os.path.abspath(__file__))
code_root = os.path.abspath(os.path.join(current_dir, "..", "..", "code"))
project_root = os.path.abspath(os.path.join(code_root, ".."))

for p in [code_root, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.rss_feed_scraper import RSSFeedScraper
from common.models import Article, ParsedIssueInfo


class MartinFowlerScraper(RSSFeedScraper):
    feed_url = "https://martinfowler.com/feed.atom"
    newsletter_name = "Martin Fowler"
    article_id_prefix = "mf"
    log_name = "MartinFowler"
    default_author = "Martin Fowler"

    def __init__(self):
        super().__init__(source_dir=current_dir)

    def parse_feed_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        """
        Extract items from Martin Fowler's Atom feed.
        Keeps description empty per editorial policy (basic information only).
        Extracts collaborator authors either from <author><name> or <b class="author"> in content.
        """
        items = []
        try:
            xml_clean = re.sub(r'\s+xmlns(:\w+)?="[^"]+"', '', xml_text)
            xml_clean = re.sub(r'<(/)?\w+:(\w+)', r'<\1\2', xml_clean)
            root = ET.fromstring(xml_clean)
        except ET.ParseError as e:
            print(f"[{self.log_name}] XML Parse Error: {e}")
            return items

        for entry in root.findall(".//entry"):
            title_elem = self._find_elem(entry, ["title"])
            title = " ".join((title_elem.text or "").split()) if title_elem is not None else ""

            link = ""
            link_elem = self._find_elem(entry, ["link"])
            if link_elem is not None:
                link = link_elem.attrib.get("href") or (link_elem.text or "").strip()

            published_elem = self._find_elem(entry, ["published", "updated"])
            date_raw = published_elem.text.strip() if published_elem is not None and published_elem.text else ""

            # 1. Start with default or entry author
            author = self.default_author
            author_elem = self._find_elem(entry, [".//author/name", "author", "creator"])
            if author_elem is not None and author_elem.text:
                candidate = " ".join(author_elem.text.split())
                if candidate and candidate.lower() != "martin fowler":
                    author = candidate

            # 2. Check if entry content explicitly names a guest/collaborator author: <b class="author">...</b>
            content_elem = self._find_elem(entry, ["content", "summary"])
            if content_elem is not None and content_elem.text:
                collab_match = re.search(r'<b\s+class\s*=\s*[\'"]author[\'"]\s*>([^<]+)</b>', content_elem.text, re.IGNORECASE)
                if collab_match:
                    raw_collab = html.unescape(collab_match.group(1))
                    cleaned_collab = " ".join(raw_collab.split())
                    if cleaned_collab:
                        author = cleaned_collab

            if link and title:
                items.append({
                    "title": title,
                    "link": link,
                    "date_raw": date_raw,
                    "description": "",  # Basic information only per user instructions
                    "author": author or self.default_author
                })

        return items

    def discover_and_ingest_feed(self) -> int:
        """
        Fetches feed, parses items, auto-categorizes, groups monthly, and persists data.
        """
        if not self.feed_url:
            print(f"[{self.log_name}] No feed_url configured. Skipping.")
            return 0

        print(f"[{self.log_name}] Fetching feed from {self.feed_url}...")
        response = self.fetch_url(self.feed_url)
        if not response:
            print(f"[{self.log_name}] Failed to fetch feed.")
            return 0

        xml_text = response.decode("utf-8", errors="replace")
        raw_items = self.parse_feed_xml(xml_text)
        if not raw_items:
            print(f"[{self.log_name}] No items found in feed.")
            return 0

        existing_articles = {self.clean_url(a.link): a for a in self.articles if a.link}
        new_articles = []
        updated_count = 0
        new_issues_map = {}

        for item in raw_items:
            c_link = self.clean_url(item["link"])
            if not c_link:
                continue

            if c_link in existing_articles:
                existing = existing_articles[c_link]
                if item.get("author") and existing.author != item["author"]:
                    existing.author = item["author"]
                    updated_count += 1
                continue

            iso_date, date_str = self.parse_feed_date(item["date_raw"])
            if not iso_date:
                continue

            year_month = iso_date[:7]
            prefix = self.article_id_prefix or "mf"
            art_id = self.make_article_id(prefix, year_month, c_link, item["title"])

            category = self.auto_categorize(item["title"])
            content_type = self.detect_content_type(c_link)

            article = Article(
                id=art_id,
                newsletter=self.newsletter_name,
                issue_number=None,
                date=iso_date,
                date_str=date_str,
                title=item["title"],
                author=item.get("author") or self.default_author,
                link=c_link,
                description="",
                category=category,
                type=content_type,
                issue_title=item["title"],
                issue_link=c_link,
                is_spotlight=False
            )
            new_articles.append(article)
            existing_articles[c_link] = article

            if year_month not in new_issues_map:
                try:
                    month_dt = datetime.strptime(year_month, "%Y-%m")
                    month_name = month_dt.strftime("%B %Y")
                except Exception:
                    month_name = year_month

                new_issues_map[year_month] = ParsedIssueInfo(
                    id=year_month,
                    date=iso_date,
                    date_str=date_str,
                    title=f"{month_name} Essays",
                    url="https://martinfowler.com/articles.html",
                    quotes=[]
                )

        if not new_articles and not updated_count:
            print(f"[{self.log_name}] Up to date. No new or updated articles found.")
            return 0

        if updated_count:
            print(f"[{self.log_name}] Updated {updated_count} article author(s).")
        if new_articles:
            print(f"[{self.log_name}] Ingested {len(new_articles)} new article(s).")
            self.merge_articles(new_articles)

        # Sync parsed issues
        if self.definition and self.definition.parsed_issues:
            curr_issues = {str(i.id): i for i in self.definition.parsed_issues.issues}
            for k, v in new_issues_map.items():
                if k not in curr_issues:
                    curr_issues[k] = v
            self.sync_parsed_issues(list(curr_issues.values()))

        self.save_data()
        return len(new_articles)


if __name__ == "__main__":
    scraper = MartinFowlerScraper()
    scraper.discover_and_ingest_feed()
