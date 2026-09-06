"""
Reusable base scraper for RSS 2.0 and Atom feeds.
Uses Python standard library xml.etree.ElementTree for robust, zero-dependency feed parsing.
"""

import os
import sys
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Any

current_dir = os.path.dirname(os.path.abspath(__file__))
code_root = os.path.abspath(os.path.join(current_dir, ".."))
project_root = os.path.abspath(os.path.join(code_root, ".."))

for p in [code_root, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.base_scraper import BaseScraper
from common.models import Article, ParsedIssueInfo


class RSSFeedScraper(BaseScraper):
    """
    Standard base class for any newsletter or blog providing RSS or Atom feeds.
    Subclasses only need to define:
        feed_url = "https://example.com/feed.xml"
        newsletter_name = "Example Publication"
        article_id_prefix = "ex"
        default_author = "Jane Doe"
    """

    feed_url: str = ""
    newsletter_name: str = ""
    article_id_prefix: str = ""
    log_name: str = "RSSFeed"
    default_author: str = ""

    def __init__(self, source_dir: str):
        super().__init__(source_dir=source_dir)

    @staticmethod
    def _strip_html_tags(text: str) -> str:
        """Removes HTML tags and normalizes whitespace."""
        if not text:
            return ""
        clean = re.sub(r"<[^>]+>", " ", text)
        return " ".join(clean.split()).strip()

    @staticmethod
    def parse_feed_date(date_str: str) -> tuple[str, str]:
        """
        Parses RFC 822 / RFC 2822 / ISO 8601 dates into (iso_date, formatted_date_str).
        """
        if not date_str:
            return "", ""
        date_str = date_str.strip()

        # 1. Try RFC 822 / RFC 2822 (common in RSS 2.0: 'Wed, 02 Oct 2024 13:00:00 GMT')
        try:
            dt = parsedate_to_datetime(date_str)
            iso_date = dt.strftime("%Y-%m-%d")
            date_display = dt.strftime("%d %B %Y").lstrip("0")
            return iso_date, date_display
        except Exception:
            pass

        # 2. Try ISO 8601 formats (common in Atom: '2024-10-02T13:00:00Z' or '2024-10-02')
        iso_clean = re.sub(r"Z$", "+00:00", date_str)
        try:
            dt = datetime.fromisoformat(iso_clean)
            iso_date = dt.strftime("%Y-%m-%d")
            date_display = dt.strftime("%d %B %Y").lstrip("0")
            return iso_date, date_display
        except Exception:
            pass

        # 3. YYYY-MM-DD fallback
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", date_str)
        if m:
            y, mo, d = m.groups()
            try:
                dt = datetime(int(y), int(mo), int(d))
                return f"{y}-{mo}-{d}", dt.strftime("%d %B %Y").lstrip("0")
            except Exception:
                return f"{y}-{mo}-{d}", f"{int(d)} {mo} {y}"

        return "", ""

    @staticmethod
    def _find_elem(parent: ET.Element, tags: List[str]) -> Optional[ET.Element]:
        """Finds the first matching element from a list of tag candidates."""
        for t in tags:
            el = parent.find(t)
            if el is not None:
                return el
        return None

    def parse_feed_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        """
        Extracts items from either RSS 2.0 (<item>) or Atom (<entry>) XML feeds.
        """
        items = []
        try:
            # Strip XML namespace declarations so standard tag search works uniformly
            xml_clean = re.sub(r'\s+xmlns(:\w+)?="[^"]+"', '', xml_text)
            # Remove namespace prefixes from closing and opening tags e.g. <dc:creator> -> <creator>
            xml_clean = re.sub(r'<(/)?\w+:(\w+)', r'<\1\2', xml_clean)
            root = ET.fromstring(xml_clean)
        except ET.ParseError as e:
            print(f"[{self.log_name}] XML Parse Error: {e}")
            return items

        tag = root.tag.lower()
        if "feed" in tag:
            # Atom Feed
            entries = root.findall(".//entry")
            for entry in entries:
                title_elem = self._find_elem(entry, ["title"])
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

                link = ""
                link_elem = self._find_elem(entry, ["link"])
                if link_elem is not None:
                    link = link_elem.attrib.get("href") or (link_elem.text or "").strip()

                published_elem = self._find_elem(entry, ["published", "updated"])
                date_raw = published_elem.text.strip() if published_elem is not None and published_elem.text else ""

                summary_elem = self._find_elem(entry, ["summary", "content"])
                summary = self._strip_html_tags(summary_elem.text if summary_elem is not None and summary_elem.text else "")

                author_elem = self._find_elem(entry, [".//author/name", "author", "creator"])
                author = author_elem.text.strip() if author_elem is not None and author_elem.text else self.default_author

                if link and title:
                    items.append({
                        "title": title,
                        "link": link,
                        "date_raw": date_raw,
                        "description": summary,
                        "author": author or self.default_author
                    })
        else:
            # RSS 2.0 Feed (<rss><channel><item>)
            for item in root.findall(".//item"):
                title_elem = self._find_elem(item, ["title"])
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

                link_elem = self._find_elem(item, ["link"])
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""

                pub_elem = self._find_elem(item, ["pubDate", "date"])
                date_raw = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""

                desc_elem = self._find_elem(item, ["description", "summary"])
                summary = self._strip_html_tags(desc_elem.text if desc_elem is not None and desc_elem.text else "")

                author_elem = self._find_elem(item, ["creator", "author"])
                author = author_elem.text.strip() if author_elem is not None and author_elem.text else self.default_author

                if link and title:
                    items.append({
                        "title": title,
                        "link": link,
                        "date_raw": date_raw,
                        "description": summary,
                        "author": author or self.default_author
                    })

        return items

    def discover_and_ingest_feed(self) -> int:
        """
        Fetches the RSS/Atom feed, parses items, generates articles, and persists data.
        Returns the number of newly ingested articles.
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

        existing_links = {self.clean_url(a.link) for a in self.articles if a.link}
        new_articles = []
        new_issues_map = {}

        for item in raw_items:
            c_link = self.clean_url(item["link"])
            if not c_link or c_link in existing_links:
                continue

            iso_date, date_str = self.parse_feed_date(item["date_raw"])
            if not iso_date:
                continue

            year_month = iso_date[:7]
            prefix = self.article_id_prefix or self.definition.source_id.split("-")[0]
            art_id = self.make_article_id(prefix, year_month, c_link, item["title"])

            category = self.auto_categorize(item["title"], item["description"])
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
                description=item.get("description", ""),
                category=category,
                type=content_type,
                issue_title=item["title"],
                issue_link=c_link,
                is_spotlight=False
            )
            new_articles.append(article)
            existing_links.add(c_link)

            if year_month not in new_issues_map:
                new_issues_map[year_month] = ParsedIssueInfo(
                    id=year_month,
                    date=iso_date,
                    date_str=date_str,
                    title=f"{self.newsletter_name} - {date_str}",
                    url=c_link,
                    quotes=[]
                )

        if not new_articles:
            print(f"[{self.log_name}] Up to date. No new articles found.")
            return 0

        print(f"[{self.log_name}] Ingested {len(new_articles)} new article(s).")
        merged = self.merge_articles(new_articles)
        self.articles = merged

        # Sync parsed issues
        if self.definition and self.definition.parsed_issues:
            curr_issues = {str(i.id): i for i in self.definition.parsed_issues.issues}
            for k, v in new_issues_map.items():
                if k not in curr_issues:
                    curr_issues[k] = v
            self.sync_parsed_issues(list(curr_issues.values()))

        self.save_data()
        return len(new_articles)
