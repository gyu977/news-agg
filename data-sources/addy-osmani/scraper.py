"""
Addy Osmani's Personal Blog Scraper & Extractor.
Extracts 2026 blog essays from https://addyosmani.com/blog/ and https://addyosmani.com/blog/page2/.
Restricts strictly to addyosmani.com domain articles (excluding Substack, LeadDev, etc.).
"""

import os
import re
import sys
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict

# Rolling ingest window. Replaces a hardcoded year check that would have expired.
RECENT_WINDOW_DAYS = 730

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
code_dir = os.path.join(project_root, "code")

for p in [code_dir, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.base_scraper import BaseScraper
from common.models import Article, ParsedIssueInfo

MONTH_MAP = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
}

class AddyOsmaniScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_dir=current_dir)

    def fetch_page_html(self, url: str) -> str:
        return self.fetch_html(url)

    def fetch_post_metadata(self, url: str) -> Dict[str, str]:
        """
        Fetch individual post page to retrieve the accurate title and description.
        """
        meta = {"title": "", "description": ""}
        try:
            from bs4 import BeautifulSoup

            html = self.fetch_page_html(url)
            soup = BeautifulSoup(html, "html.parser")
            
            # Title
            h1 = soup.find("h1")
            if h1 and h1.get_text(strip=True):
                meta["title"] = h1.get_text(strip=True)
                
            # Description from meta tag
            desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if desc_tag and desc_tag.get("content"):
                meta["description"] = desc_tag.get("content", "").strip()
            else:
                # Fallback to first substantive paragraph
                wrapper = soup.find("section", id="wrapper") or soup.find("article") or soup.find("body")
                if wrapper:
                    for p in wrapper.find_all("p"):
                        txt = p.get_text(strip=True)
                        if len(txt) > 50 and not txt.startswith("Home") and not "Substack" in txt:
                            meta["description"] = txt
                            break
        except Exception as e:
            print(f"[AddyOsmani] Warning fetching metadata for {url}: {e}")
        return meta

    @staticmethod
    def normalize_title(title: str) -> str:
        """Strip non-alphanumeric characters and normalize spaces for semantic identity."""
        if not title:
            return ""
        return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()

    def extract_issues(self) -> List[Article]:
        pages = [
            "https://addyosmani.com/blog/",
            "https://addyosmani.com/blog/page2/"
        ]
        
        print("[AddyOsmani] Crawling primary blog pages...")
        extracted_posts = []
        seen_links = set()
        seen_titles = set()
        successful_pages = 0

        for page_url in pages:
            print(f"[AddyOsmani] Fetching listing: {page_url}")
            try:
                from bs4 import BeautifulSoup

                html = self.fetch_page_html(page_url)
            except Exception as e:
                print(f"[AddyOsmani] Error fetching {page_url}: {e}")
                continue
            successful_pages += 1

            soup = BeautifulSoup(html, "html.parser")

            # Look for blog post links
            for a in soup.find_all("a", href=re.compile(r"^/blog/[^/]+/?$")):
                href = a.get("href", "")
                title_listing = a.get_text(strip=True)
                
                if not title_listing or "page" in href or href == "/blog/":
                    continue

                full_link = "https://addyosmani.com" + href if href.startswith("/") else href
                if full_link in seen_links:
                    continue

                # Find parent container for date
                parent = a.find_parent(["li", "article", "div", "section"])
                text = parent.get_text(separator=" ", strip=True) if parent else ""

                date_match = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s+(\d{4})\b", text)
                if not date_match:
                    continue

                month_str, day_str, year_str = date_match.groups()
                dt = datetime.strptime(f"{month_str} {int(day_str):02d} {year_str}", "%b %d %Y")

                # Keep a rolling window rather than a hardcoded year. `year_str != "2026"`
                # would have yielded zero articles from 2027-01-01, and any January would
                # have discarded December's posts.
                if dt < datetime.now() - timedelta(days=RECENT_WINDOW_DAYS):
                    continue

                date_iso = dt.strftime("%Y-%m-%d")
                date_str = dt.strftime("%d %B %Y").lstrip("0")

                seen_links.add(full_link)
                norm_t = self.normalize_title(title_listing)
                if norm_t:
                    seen_titles.add(norm_t)
                extracted_posts.append({
                    "title": title_listing,
                    "link": full_link,
                    "date": date_iso,
                    "date_str": date_str
                })

        if successful_pages == 0:
            raise RuntimeError("Addy Osmani: every listing-page request failed")

        # Multi-Channel Contract: Query Substack archive strictly as a fallback channel
        # for essays that have not yet been published to addyosmani.com/blog/
        try:
            print("[AddyOsmani] Querying fallback Substack archive...")
            substack_api = "https://addyo.substack.com/api/v1/archive?sort=new&limit=50"
            raw = self.fetch_url(substack_api, accept="application/json")
            posts = json.loads(raw.decode("utf-8"))
            fallback_added = 0
            for p in posts:
                canonical = p.get("canonical_url")
                if not canonical or canonical in seen_links:
                    continue
                title = p.get("title", "").strip()
                norm_t = self.normalize_title(title)
                # If already ingested via primary blog, do not duplicate!
                if norm_t and norm_t in seen_titles:
                    continue

                post_date_raw = p.get("post_date")
                if not post_date_raw:
                    continue
                dt = datetime.fromisoformat(post_date_raw.replace("Z", "+00:00"))
                if dt.tzinfo:
                    dt = dt.astimezone()
                dt_naive = dt.replace(tzinfo=None)
                if dt_naive < datetime.now() - timedelta(days=RECENT_WINDOW_DAYS):
                    continue
                date_iso = dt_naive.strftime("%Y-%m-%d")
                date_str = dt_naive.strftime("%d %B %Y").lstrip("0")
                desc = (p.get("subtitle") or p.get("description") or "").strip()
                seen_links.add(canonical)
                if norm_t:
                    seen_titles.add(norm_t)
                extracted_posts.append({
                    "title": title,
                    "link": canonical,
                    "date": date_iso,
                    "date_str": date_str,
                    "description": desc,
                })
                fallback_added += 1
            print(f"[AddyOsmani] Ingested {fallback_added} fallback essay(s) from Substack.")
        except Exception as e:
            print(f"[AddyOsmani] Warning: could not fetch Substack archive: {e}")

        print(
            f"[AddyOsmani] Found {len(extracted_posts)} articles in the rolling "
            f"{RECENT_WINDOW_DAYS}-day window. Fetching metadata..."
        )

        articles = []
        issue_groups: Dict[str, Dict] = {}
        existing_by_link = {a.link: a for a in self.articles if a.link}

        for idx, post in enumerate(extracted_posts, 1):
            url = post["link"]
            date_iso = post["date"]
            date_str = post["date_str"]

            existing = existing_by_link.get(url)
            if existing and existing.description:
                title = existing.title
                description = existing.description
                cat = existing.category
            elif post.get("description") and post.get("title"):
                title = post["title"]
                description = post["description"]
                cat = None
            else:
                meta = self.fetch_post_metadata(url)
                title = meta["title"] or post["title"]
                description = meta["description"]
                cat = None

            # Generate monthly issue grouping
            month_year = datetime.strptime(date_iso, "%Y-%m-%d").strftime("%B %Y")
            issue_title = f"{month_year} Blog Essays"
            issue_id = f"addy-{datetime.strptime(date_iso, '%Y-%m-%d').strftime('%Y-%m')}"

            if issue_id not in issue_groups:
                issue_groups[issue_id] = {
                    "id": issue_id,
                    "date": date_iso,
                    "date_str": date_str,
                    "title": issue_title,
                    "url": "https://addyosmani.com/blog/",
                    "quotes": []
                }

            # Generate a stable unique ID keyed on the canonical post URL
            month_key = datetime.strptime(date_iso, "%Y-%m-%d").strftime("%Y-%m")
            art_id = self.make_article_id("addy", month_key, url, title)

            # Auto-categorize based on title and description
            if cat is None:
                cat = self.auto_categorize(title, description)
                if "agent" in title.lower() or "factory" in title.lower() or "loop" in title.lower() or "spec" in title.lower():
                    cat = "AI-Native & Agentic Software Engineering"
                elif "eval" in title.lower() or "gemini" in title.lower() or "model" in title.lower():
                    cat = "Large Language Models & Evaluation Infrastructure"
                elif "architecture" in title.lower() or "comprehension" in title.lower() or "orchestra" in title.lower():
                    cat = "Software Architecture & Distributed Systems"
                elif "review" in title.lower() or "quality" in title.lower():
                    cat = "Software Testing, Quality & Observability"
                elif "lessons" in title.lower() or "career" in title.lower() or "action" in title.lower() or "efficiency" in title.lower():
                    cat = "Tech Industry, Jobs & Careers"

            article = Article(
                id=art_id,
                newsletter="Addy Osmani",
                issue_number=None,
                issue_title=issue_title,
                issue_link="https://addyosmani.com/blog/",
                date=date_iso,
                date_str=date_str,
                title=title,
                link=url,
                author="Addy Osmani",
                description=description,
                category=cat,
                is_spotlight=False,
                type="article",
                hide=False,
                user_overrides=[],
                metadata={}
            )
            articles.append(article)

        # Update definition.json parsed issues tracking. `last_parsed_issue` and
        # `last_parsed_date` were never set here (both stayed ""), so incremental
        # resumption had nothing to resume from.
        if self.definition:
            self.sync_parsed_issues(list(issue_groups.values()))

        return articles

    def merge_articles(self, incoming_articles: List[Article]) -> int:
        """
        Multi-Channel Article Contract:
        Matches articles by normalized title so personal blog and Substack syndicate to the same record.
        Promotes fallback Substack URLs to primary blog URLs when published to addyosmani.com/blog/.
        """
        existing_by_title = {self.normalize_title(a.title): a for a in self.articles if a.title}
        updated_count = 0
        for new_art in incoming_articles:
            t_key = self.normalize_title(new_art.title)
            match = existing_by_title.get(t_key)
            if match:
                # If existing record used fallback Substack link and new record has primary blog link, promote!
                if "addyosmani.com" in (new_art.link or "") and "substack.com" in (match.link or ""):
                    match.link = new_art.link
                    match.id = new_art.id
                    match.issue_title = new_art.issue_title
                    match.issue_link = new_art.issue_link
                # Update fields while strictly preserving user overrides
                for field in ["category", "hide", "description", "author", "type", "is_spotlight"]:
                    if field in match.user_overrides:
                        continue
                    new_val = getattr(new_art, field)
                    if new_val and (not isinstance(new_val, str) or new_val.strip()):
                        setattr(match, field, new_val)
                updated_count += 1
            else:
                self.articles.append(new_art)
                existing_by_title[t_key] = new_art
                updated_count += 1

        self.articles.sort(key=lambda x: str(x.date or ""), reverse=True)
        return updated_count

    def run(self):
        new_articles = self.extract_issues()
        if new_articles:
            updated = self.merge_articles(new_articles)
            self.save_data()
            print(f"[AddyOsmani] Successfully saved {len(self.articles)} total articles ({updated} updated/added).")
        else:
            print("[AddyOsmani] No articles extracted.")

if __name__ == "__main__":
    scraper = AddyOsmaniScraper()
    scraper.run()
