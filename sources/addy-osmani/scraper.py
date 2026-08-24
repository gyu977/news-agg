"""
Addy Osmani's Personal Blog Scraper & Extractor.
Extracts 2026 blog essays from https://addyosmani.com/blog/ and https://addyosmani.com/blog/page2/.
Restricts strictly to addyosmani.com domain articles (excluding Substack, LeadDev, etc.).
"""

import os
import re
import sys
import json
import urllib.request
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Optional, Dict

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
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.read().decode("utf-8", errors="replace")

    def fetch_post_metadata(self, url: str) -> Dict[str, str]:
        """
        Fetch individual post page to retrieve the accurate title and description.
        """
        meta = {"title": "", "description": ""}
        try:
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

    def extract_issues(self) -> List[Article]:
        pages = [
            "https://addyosmani.com/blog/",
            "https://addyosmani.com/blog/page2/"
        ]
        
        print("[AddyOsmani] Crawling blog pages...")
        extracted_posts = []
        seen_links = set()

        for page_url in pages:
            print(f"[AddyOsmani] Fetching listing: {page_url}")
            try:
                html = self.fetch_page_html(page_url)
            except Exception as e:
                print(f"[AddyOsmani] Error fetching {page_url}: {e}")
                continue

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
                # Filter strictly for 2026
                if year_str != "2026":
                    continue

                dt = datetime.strptime(f"{month_str} {int(day_str):02d} {year_str}", "%b %d %Y")
                date_iso = dt.strftime("%Y-%m-%d")
                date_str = dt.strftime("%d %B %Y").lstrip("0")

                seen_links.add(full_link)
                extracted_posts.append({
                    "title": title_listing,
                    "link": full_link,
                    "date": date_iso,
                    "date_str": date_str
                })

        print(f"[AddyOsmani] Found {len(extracted_posts)} articles from 2026. Fetching metadata...")

        articles = []
        issue_groups: Dict[str, Dict] = {}

        for idx, post in enumerate(extracted_posts, 1):
            url = post["link"]
            meta = self.fetch_post_metadata(url)
            
            title = meta["title"] or post["title"]
            description = meta["description"]
            date_iso = post["date"]
            date_str = post["date_str"]

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

            # Generate clean unique ID
            slug = url.rstrip("/").split("/")[-1]
            art_id = f"addy-{slug}"

            # Auto-categorize based on title and description
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

        # Update definition.json parsed issues tracking
        if self.definition:
            sorted_issues = sorted(issue_groups.values(), key=lambda x: x["date"], reverse=True)
            self.definition.parsed_issues.issues = [
                ParsedIssueInfo(
                    id=iss["id"],
                    date=iss["date"],
                    date_str=iss["date_str"],
                    title=iss["title"],
                    url=iss["url"],
                    quotes=[]
                )
                for iss in sorted_issues
            ]
            self.definition.parsed_issues.count = len(sorted_issues)

        return articles

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
