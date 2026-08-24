"""
Andriy Burkov's Artificial Intelligence LinkedIn Newsletter Scraper & Parser.
Extracts articles from LinkedIn Pulse issues, unquotes LinkedIn redirect URLs,
correctly splits <br>-separated lines, reconstructs complete titles from partial hyperlinks,
and applies the 3-month archive retention property.
"""

import os
import re
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import List, Optional, Dict

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
code_dir = os.path.join(project_root, "code")

for p in [code_dir, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.base_scraper import BaseScraper
from common.models import Article, Quote, ParsedIssueInfo

class AndriyBurkovScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_dir=current_dir)

    def unwrap_linkedin_url(self, href: str) -> str:
        """
        Unwraps LinkedIn redirect URLs (e.g. /redir/redirect?url=... or /redir/suspicious-page?url=...)
        to reveal the genuine destination URL.
        """
        if "linkedin.com/redir/" in href or "url=" in href:
            match = re.search(r'url=([^&]+)', href)
            if match:
                return urllib.parse.unquote(match.group(1))
        return href

    def parse_issue_html(
        self, 
        html: str, 
        issue_number: Optional[int], 
        issue_title: str, 
        issue_link: str, 
        date_iso: str, 
        date_str: str
    ) -> List[Article]:
        """
        Parses a LinkedIn Pulse newsletter issue using BeautifulSoup,
        correctly handling line breaks within paragraphs and reconstructing full titles.
        """
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        
        article_body = soup.find("article") or soup.find("main") or soup
        
        seen_links = set()
        item_idx = 1
        
        # Replace <br> tags with line breaks so get_text preserves line boundaries
        for br in article_body.find_all("br"):
            br.replace_with("\n")

        for p in article_body.find_all(["p", "li"]):
            p_full_text = p.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in p_full_text.split("\n") if line.strip()]
            
            a_tags = p.find_all("a")
            if not a_tags:
                continue

            for a in a_tags:
                raw_href = a.get("href", "").strip()
                unwrapped_href = self.unwrap_linkedin_url(raw_href)
                clean_link = self.clean_url(unwrapped_href)

                if (not clean_link or 
                    "linkedin.com" in clean_link or 
                    "fandf.co" in clean_link or 
                    clean_link in seen_links):
                    continue

                anchor_text = a.get_text(strip=True)
                anchor_text = anchor_text.replace('&amp;', 'and').replace('&', 'and')
                if not anchor_text or len(anchor_text) < 3 or anchor_text.lower() in ["report this article", "unsubscribe"]:
                    continue

                if self.is_sponsor_link(clean_link, anchor_text):
                    print(f"[AndriyBurkov] Skipping sponsor link: {anchor_text} ({clean_link})")
                    continue

                # Find the specific line that contains this anchor text
                matched_line = anchor_text
                for line in lines:
                    if anchor_text in line or any(word in line for word in anchor_text.split() if len(word) > 4):
                        matched_line = line
                        break

                if "[Sponsored]" in matched_line or "sponsor" in matched_line.lower() and "fandf.co" in clean_link:
                    continue

                author = None
                description = ""
                title = anchor_text

                # Extract author from format like [Nature] or [Google]
                m = re.match(r"^\[(.*?)\]\s*(.*)", matched_line)
                if m:
                    tag = m.group(1).strip()
                    rest = m.group(2).strip()
                    if tag.lower() not in ["explained", "project", "paper", "book", "tool", "sponsored", "open model"]:
                        author = tag
                    elif tag.lower() == "open model":
                        author = "Open model"
                    
                    if ":" in rest:
                        t_cand, d_cand = rest.split(":", 1)
                        t_cand = t_cand.strip()
                        d_cand = d_cand.strip()
                        if len(t_cand) > len(title) and (anchor_text in t_cand or len(anchor_text.split()) <= 4):
                            title = t_cand
                        elif len(t_cand) > 0:
                            title = t_cand
                        description = d_cand
                    else:
                        if len(rest) > len(title) and (anchor_text in rest or len(anchor_text.split()) <= 4):
                            title = rest
                elif " - " in matched_line[:50]:
                    parts = matched_line.split(" - ", 1)
                    cand_author = parts[0].strip('*- ')
                    rest = parts[1].strip()
                    if len(cand_author.split()) <= 4:
                        author = cand_author
                    if len(rest) > len(title) and anchor_text in rest:
                        title = rest
                else:
                    if len(matched_line) > len(title) and anchor_text in matched_line and len(matched_line.split()) < 25:
                        title = matched_line

                # Clean up title formatting
                title = re.sub(r'\s*\?\s*$', '?', title)
                title = re.sub(r'\s*\:\s*$', '', title)
                title = title.replace('&amp;', 'and').replace('&', 'and')
                title = title.strip(' -–—:;,')

                content_type = self.detect_content_type(clean_link)
                category = self.auto_categorize(title, description)

                art_id = f"ab-{issue_number}-{item_idx}"
                article = Article(
                    id=art_id,
                    newsletter="Artificial Intelligence (Andriy Burkov)",
                    issue_number=issue_number,
                    issue_title=issue_title,
                    issue_link=issue_link,
                    date=date_iso,
                    date_str=date_str,
                    title=title,
                    link=clean_link,
                    author=author,
                    description=description,
                    category=category,
                    is_spotlight=False,
                    type=content_type,
                    hide=False,
                    user_overrides=[],
                    metadata={}
                )
                articles.append(article)
                seen_links.add(clean_link)
                item_idx += 1

        return articles

    def ingest_issue(
        self, 
        issue_number: Optional[int], 
        issue_title: str, 
        issue_url: str, 
        date_iso: str, 
        date_str: str
    ) -> int:
        """
        Fetches, parses, and merges a single LinkedIn issue in-memory.
        """
        print(f"[AndriyBurkov] Ingesting Issue #{issue_number}: {issue_title} ({issue_url})...")
        html = self.fetch_html(issue_url)
        
        parsed_articles = self.parse_issue_html(
            html, issue_number, issue_title, issue_url, date_iso, date_str
        )
        
        if not parsed_articles:
            print(f"[AndriyBurkov] Warning: No articles extracted for Issue #{issue_number}!")
            return 0

        print(f"[AndriyBurkov] Extracted {len(parsed_articles)} articles.")
        
        merged_count = self.merge_articles(parsed_articles)
        
        # Update definition tracking
        if self.definition:
            str_id = str(issue_number) if issue_number is not None else date_iso
            existing_issue = next((iss for iss in self.definition.parsed_issues.issues if iss.id == str_id), None)
            if existing_issue:
                existing_issue.title = issue_title
                existing_issue.date = date_iso
                existing_issue.date_str = date_str
                existing_issue.url = issue_url
            else:
                new_iss_info = ParsedIssueInfo(
                    id=str_id,
                    date=date_iso,
                    date_str=date_str,
                    title=issue_title,
                    url=issue_url
                )
                self.definition.parsed_issues.issues.insert(0, new_iss_info)
            
            self.definition.parsed_issues.issues.sort(key=lambda x: x.date, reverse=True)
            self.definition.parsed_issues.count = len(self.definition.parsed_issues.issues)
            if self.definition.parsed_issues.issues:
                self.definition.parsed_issues.last_parsed_issue = str(self.definition.parsed_issues.issues[0].id)
                self.definition.parsed_issues.last_parsed_date = self.definition.parsed_issues.issues[0].date

        self.save_data()
        print(f"[AndriyBurkov] Saved and synced {len(self.articles)} total articles.")
        return merged_count

    def discover_and_ingest_new_issues(self, reparse_all: bool = False) -> int:
        """
        Scrapes the LinkedIn newsletter overview page to discover recent issues.
        """
        print("[AndriyBurkov] Checking LinkedIn newsletter homepage for recent issues...")
        homepage_url = "https://www.linkedin.com/newsletters/artificial-intelligence-6598352935271358464/"
        
        discovered_issues = []
        known_ids = set()
        if self.definition and not reparse_all:
            known_ids = {str(iss.id) for iss in self.definition.parsed_issues.issues}

        try:
            html = self.fetch_html(homepage_url)
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a"):
                href = a.get("href", "").strip()
                if "/pulse/" in href:
                    clean_url = href.split("?")[0]
                    m = re.search(r'artificial-intelligence-(\d+)', clean_url)
                    if m:
                        num = int(m.group(1))
                        if str(num) not in known_ids and not any(d["num"] == num for d in discovered_issues):
                            discovered_issues.append({
                                "num": num,
                                "title": f"Artificial Intelligence #{num}",
                                "url": clean_url
                            })
        except Exception as e:
            print(f"[AndriyBurkov] Error scraping overview page: {e}")

        # Known historical issues (333-336)
        known_historical = [
            (336, "https://www.linkedin.com/pulse/artificial-intelligence-336-andriy-burkov-vdfjc/"),
            (335, "https://www.linkedin.com/pulse/artificial-intelligence-335-andriy-burkov-iu7ac/"),
            (334, "https://www.linkedin.com/pulse/artificial-intelligence-334-andriy-burkov-m4xcc/"),
            (333, "https://www.linkedin.com/pulse/artificial-intelligence-333-andriy-burkov-bnjbf/")
        ]
        for num, url in known_historical:
            if str(num) not in known_ids and not any(d["num"] == num for d in discovered_issues):
                discovered_issues.append({
                    "num": num,
                    "title": f"Artificial Intelligence #{num}",
                    "url": url
                })

        if not discovered_issues:
            print("[AndriyBurkov] No new unparsed issues found.")
            return 0

        discovered_issues.sort(key=lambda x: x["num"])
        print(f"[AndriyBurkov] Ingesting {len(discovered_issues)} issues: {[d['num'] for d in discovered_issues]}")
        
        # Anchor: Issue #336 was Saturday 25 July 2026
        anchor_dt = datetime(2026, 7, 25)
        anchor_issue = 336
        
        new_count = 0
        for item in discovered_issues:
            diff_weeks = item["num"] - anchor_issue
            dt = anchor_dt + timedelta(weeks=diff_weeks)
            date_iso = dt.strftime("%Y-%m-%d")
            date_str = dt.strftime("%-d %B %Y")
            
            count = self.ingest_issue(
                issue_number=item["num"],
                issue_title=item["title"],
                issue_url=item["url"],
                date_iso=date_iso,
                date_str=date_str
            )
            new_count += count

        return new_count

if __name__ == "__main__":
    scraper = AndriyBurkovScraper()
    scraper.discover_and_ingest_new_issues(reparse_all=True)
