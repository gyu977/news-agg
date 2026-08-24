"""
Dear Architects Scraper & Parser using BeautifulSoup4 and dynamic MailerLite JSON API discovery.
Extracts H1 spotlight articles, H2/H3 regular articles, and quotes from blockquotes & styled tags.
"""

import os
import re
import sys
import json
import urllib.request
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

class DearArchitectsScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_dir=current_dir)

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
        Parses a Dear Architects MailerLite HTML email issue using BeautifulSoup.
        """
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        
        # 1. Extract Quotes
        quotes = []
        for bq in soup.find_all("blockquote"):
            text = bq.get_text(separator=" ", strip=True)
            if "—" in text or "-" in text:
                parts = re.split(r'[-—–]\s*', text, maxsplit=1)
                q_text = parts[0].strip('“"” ')
                q_author = parts[1].strip() if len(parts) > 1 else "Unknown"
                quotes.append(Quote(text=q_text, author=q_author))

        # Check for quote in H2/P tags if no blockquote was used
        if not quotes:
            for tag in soup.find_all(["h2", "p"]):
                txt = tag.get_text(separator=" ", strip=True)
                if (txt.startswith('"') or txt.startswith('“')) and len(txt) > 25 and not tag.find("a"):
                    parent = tag.find_parent("table") or tag.find_parent("div")
                    if parent:
                        all_p = [p.get_text(strip=True) for p in parent.find_all(["p", "div", "h2", "h3"]) if p.get_text(strip=True)]
                        idx = -1
                        for i, p_str in enumerate(all_p):
                            if txt in p_str:
                                idx = i
                                break
                        author = "Unknown"
                        if idx != -1 and idx + 1 < len(all_p):
                            next_cand = all_p[idx+1]
                            if len(next_cand.split()) <= 5 and not next_cand.startswith('"') and not next_cand.startswith('“'):
                                author = next_cand.strip("—–- ")
                        quotes.append(Quote(text=txt.strip('“"” '), author=author))
                        break

        # Update definition with issue quotes if found
        if quotes and self.definition:
            str_id = str(issue_number) if issue_number is not None else date_iso
            for iss in self.definition.parsed_issues.issues:
                if iss.id == str_id:
                    iss.quotes = quotes
                    break

        # 2. Extract Articles (finding H1 for Spotlight and H2/H3 for regular articles)
        headers = soup.find_all(["h1", "h2", "h3"])
        
        item_idx = 1
        seen_links = set()

        for h in headers:
            a_tag = h.find("a")
            if not a_tag or not a_tag.get("href"):
                continue

            raw_link = a_tag["href"].strip()
            clean_link = self.clean_url(raw_link)
            
            # Skip anchor jumps, unsubs, or mailerlite tracking
            if (not clean_link or 
                "unsubscribe" in clean_link or 
                "mailerlite.com" in clean_link or 
                "deararchitects.xyz" in clean_link or 
                clean_link in seen_links):
                continue

            title = a_tag.get_text(strip=True)
            title = title.replace('&amp;', 'and').replace('&', 'and')
            if not title or len(title) < 3 or title.lower() == "in the spotlight":
                continue

            # Check for sponsor link
            if self.is_sponsor_link(clean_link, title):
                print(f"[DearArchitects] Skipping sponsored affiliate link: {title} ({clean_link})")
                continue

            # Check for spotlight (H1 or "in the spotlight" indicator)
            is_spotlight = False
            if h.name == "h1" or "in the spotlight" in title.lower():
                is_spotlight = True
                title = re.sub(r'\s*-\s*in the spotlight', '', title, flags=re.IGNORECASE).strip()

            parent = h.find_parent("table") or h.find_parent("div")
            description = ""
            author = None
            
            if parent:
                parent_text = parent.get_text(separator=" ", strip=True)
                if "spotlight" in parent_text.lower():
                    is_spotlight = True
                
                strong_tags = parent.find_all("strong")
                for st in strong_tags:
                    st_text = st.get_text(strip=True)
                    if 0 < len(st_text.split()) <= 4 and st_text.lower() not in title.lower() and "spotlight" not in st_text.lower():
                        author = st_text
                        break

                p_tags = parent.find_all("p")
                desc_parts = []
                for p in p_tags:
                    p_text = p.get_text(separator=" ", strip=True)
                    p_text = p_text.replace('&amp;', 'and')
                    if len(p_text) > 20 and title.lower() not in p_text.lower() and "mailerlite" not in p_text.lower():
                        desc_parts.append(p_text)
                
                description = " ".join(desc_parts)

            content_type = self.detect_content_type(clean_link)
            category = self.auto_categorize(title, description)

            art_id = f"da-{issue_number}-{item_idx}"
            article = Article(
                id=art_id,
                newsletter="Dear Architects",
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
                is_spotlight=is_spotlight,
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
        Fetches, parses, and merges a single Dear Architects issue in-memory.
        """
        print(f"[DearArchitects] Ingesting Issue #{issue_number}: {issue_title} ({issue_url})...")
        html = self.fetch_html(issue_url)
        
        parsed_articles = self.parse_issue_html(
            html, issue_number, issue_title, issue_url, date_iso, date_str
        )
        
        if not parsed_articles:
            print(f"[DearArchitects] Warning: No articles extracted for Issue #{issue_number}!")
            return 0

        print(f"[DearArchitects] Extracted {len(parsed_articles)} articles.")
        
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
            
            # Sort issues descending by date
            self.definition.parsed_issues.issues.sort(key=lambda x: x.date, reverse=True)
            self.definition.parsed_issues.count = len(self.definition.parsed_issues.issues)
            if self.definition.parsed_issues.issues:
                self.definition.parsed_issues.last_parsed_issue = str(self.definition.parsed_issues.issues[0].id)
                self.definition.parsed_issues.last_parsed_date = self.definition.parsed_issues.issues[0].date

        self.save_data()
        print(f"[DearArchitects] Saved and synced {len(self.articles)} total articles.")
        return merged_count

    def discover_and_ingest_new_issues(self, reparse_all: bool = False) -> int:
        """
        Discovers and ingests new issues from the dynamic MailerLite JSON API and the archive page.
        """
        print("[DearArchitects] Checking MailerLite dynamic endpoint and website for new issues...")
        
        discovered_issues = []
        known_ids = set()
        if self.definition and not reparse_all:
            known_ids = {str(iss.id) for iss in self.definition.parsed_issues.issues}

        # 1. Query the dynamic MailerLite JSON API endpoint
        api_endpoint = "https://assets.mailerlite.com/jsonp/1235400/recent-emails/c6c6dffbc838e26c96033e6029092723e53f2a0f7ec2b099bd6dd294a0b33e00?limit=50&offset=0"
        try:
            req = urllib.request.Request(api_endpoint, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_text = resp.read().decode("utf-8").strip()
                if raw_text.startswith("callback(") or (not raw_text.startswith("{") and "(" in raw_text):
                    raw_text = re.sub(r'^[a-zA-Z0-9_\$]+\((.*)\);?$', r'\1', raw_text, flags=re.DOTALL)
                data = json.loads(raw_text)
                for m in data.get("mails", []):
                    subject = m.get("subject", "")
                    preview_path = m.get("preview_path")
                    if preview_path:
                        url = f"https://preview.mailerlite.io/{preview_path}"
                        match = re.search(r'#(\d+)\s*[-—–]?\s*(.*)', subject)
                        if match:
                            num = int(match.group(1))
                            title = match.group(2).strip() or f"Dear Architects #{num}"
                            if str(num) not in known_ids and not any(d["num"] == num for d in discovered_issues):
                                discovered_issues.append({
                                    "num": num,
                                    "title": title,
                                    "url": url
                                })
        except Exception as e:
            print(f"[DearArchitects] Error querying MailerLite JSON endpoint: {e}")

        # 2. Fallback check on static HTML pages
        for page_url in ["https://deararchitects.xyz/", "https://www.deararchitects.xyz/archive"]:
            try:
                html = self.fetch_html(page_url)
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all("a"):
                    href = a.get("href", "").strip()
                    text = a.get_text(strip=True)
                    if "preview.mailerlite.io" in href:
                        match = re.search(r'#(\d+)\s*[-—–]?\s*(.*)', text)
                        if match:
                            num = int(match.group(1))
                            title = match.group(2).strip() or f"Dear Architects #{num}"
                            if str(num) not in known_ids and not any(d["num"] == num for d in discovered_issues):
                                discovered_issues.append({
                                    "num": num,
                                    "title": title,
                                    "url": href
                                })
            except Exception as e:
                print(f"[DearArchitects] Error scanning {page_url}: {e}")

        if not discovered_issues:
            print("[DearArchitects] No new unparsed issues found.")
            return 0

        # Sort discovered issues ascending to ingest chronologically
        discovered_issues.sort(key=lambda x: x["num"])
        print(f"[DearArchitects] Ingesting {len(discovered_issues)} issues: {[d['num'] for d in discovered_issues]}")
        
        anchor_dt = datetime(2026, 7, 25)
        anchor_issue = 300
        
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
    scraper = DearArchitectsScraper()
    scraper.discover_and_ingest_new_issues(reparse_all=True)
