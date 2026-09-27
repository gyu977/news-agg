import os
import sys
import re
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


class SimonWillisonScraper(RSSFeedScraper):
    feed_url = "https://simonwillison.net/atom/entries/"
    newsletter_name = "Simon Willison's Weblog"
    article_id_prefix = "sw"
    log_name = "SimonWillison"
    default_author = "Simon Willison"

    def __init__(self):
        super().__init__(source_dir=current_dir)

    def parse_feed_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        """
        Extract items from Atom feed.
        We capture category tags for auto-categorization, but keep description empty
        per editorial policy (avoiding arbitrary truncation of full essays).
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
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

            link = ""
            link_elem = self._find_elem(entry, ["link"])
            if link_elem is not None:
                link = link_elem.attrib.get("href") or (link_elem.text or "").strip()

            published_elem = self._find_elem(entry, ["published", "updated"])
            date_raw = published_elem.text.strip() if published_elem is not None and published_elem.text else ""

            # Extract category terms from <category term="..."/> tags to enrich auto-categorization
            tags = [cat.attrib.get("term", "") for cat in entry.findall(".//category") if cat.attrib.get("term")]
            tag_context = " ".join(tags)

            if link and title:
                items.append({
                    "title": title,
                    "link": link,
                    "date_raw": date_raw,
                    "description": "",  # Intentionally empty per editorial policy
                    "tag_context": tag_context,
                    "author": self.default_author
                })

        return items

    def discover_and_ingest_feed(self) -> int:
        """
        Fetches feed, parses items, auto-categorizes using title + tag_context, and persists articles.
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
            prefix = self.article_id_prefix or "sw"
            art_id = self.make_article_id(prefix, year_month, c_link, item["title"])

            # Pass tag_context to auto_categorize for high-accuracy initial tagging
            category = self.auto_categorize(item["title"], item.get("tag_context", ""))
            content_type = self.detect_content_type(c_link)

            article = Article(
                id=art_id,
                newsletter=self.newsletter_name,
                issue_number=None,
                date=iso_date,
                date_str=date_str,
                title=item["title"],
                author=self.default_author,
                link=c_link,
                description="",
                category=category,
                type=content_type,
                issue_title=item["title"],
                issue_link=c_link,
                is_spotlight=False
            )
            new_articles.append(article)
            existing_links.add(c_link)

            if year_month not in new_issues_map:
                try:
                    month_dt = datetime.strptime(year_month, "%Y-%m")
                    month_name = month_dt.strftime("%B %Y")
                    month_url = f"https://simonwillison.net/{month_dt.strftime('%Y/%b')}/"
                except Exception:
                    month_name = year_month
                    month_url = "https://simonwillison.net/"

                new_issues_map[year_month] = ParsedIssueInfo(
                    id=year_month,
                    date=iso_date,
                    date_str=date_str,
                    title=f"{month_name} Blog Posts",
                    url=month_url,
                    quotes=[]
                )

        if not new_articles:
            print(f"[{self.log_name}] Up to date. No new articles found.")
            return 0

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
    scraper = SimonWillisonScraper()
    scraper.discover_and_ingest_feed()
