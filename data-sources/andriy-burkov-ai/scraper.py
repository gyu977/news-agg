"""
Andriy Burkov's Artificial Intelligence LinkedIn Newsletter Scraper & Parser.
Extracts articles from LinkedIn Pulse issues, unquotes LinkedIn redirect URLs,
correctly splits <br>-separated lines, reconstructs complete titles from partial hyperlinks,
and applies the 3-month archive retention property.
"""

import os
import re
import sys
import urllib.parse
from typing import List, Optional, Dict

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
code_dir = os.path.join(project_root, "code")

for p in [code_dir, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.base_scraper import BaseScraper
from common.mailerlite_scraper import MailerLiteScraper
from common.models import Article, Quote, ParsedIssueInfo
from common.constants import SPONSOR_WHITELIST_TERMS

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
        from bs4 import BeautifulSoup

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

                # `A or B` must be grouped before the whitelist test: written
                # unparenthesised this read as `A or (B and C)`, so *any* line mentioning
                # "Sponsored" was dropped regardless of destination, discarding real
                # now label-based rather than a bare substring, so headlines *about*
                # sponsorship survive; the ad-network domain is an independent signal.
                marked_sponsor = self.has_sponsor_marker(matched_line)
                is_ad_domain = self.is_sponsor_link(clean_link, anchor_text)
                whitelisted = any(t.lower() in f"{clean_link} {anchor_text}".lower() for t in SPONSOR_WHITELIST_TERMS)
                if (marked_sponsor and not whitelisted) or is_ad_domain:
                    continue
                if self.is_boilerplate(anchor_text, clean_link):
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

                art_id = self.make_article_id("ab", issue_number, clean_link, title)
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
        issue_url: str
    ) -> int:
        """
        Fetches a manually supplied issue and reads its publication date from metadata.

        Automated LinkedIn discovery is intentionally disabled below. This method is
        retained for a future authorised importer and never invents a weekly date.
        """
        print(f"[AndriyBurkov] Ingesting Issue #{issue_number}: {issue_title} ({issue_url})...")
        html = self.fetch_html(issue_url)
        published_at = MailerLiteScraper.publication_date_from_html(html)
        if not published_at:
            raise ValueError(
                f"LinkedIn issue #{issue_number} has no datePublished/time metadata; "
                "refusing arithmetic fallback."
            )
        date_iso, date_str = MailerLiteScraper.format_publication_date(published_at)

        parsed_articles = self.parse_issue_html(
            html, issue_number, issue_title, issue_url, date_iso, date_str
        )
        
        if not parsed_articles:
            print(f"[AndriyBurkov] Warning: No articles extracted for Issue #{issue_number}!")
            return 0

        print(f"[AndriyBurkov] Extracted {len(parsed_articles)} articles.")
        
        merged_count = self.merge_articles(parsed_articles)
        
        existing = list(self.definition.parsed_issues.issues) if self.definition else []
        issue_id = str(issue_number) if issue_number is not None else date_iso
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
        print(f"[AndriyBurkov] Saved and synced {len(self.articles)} total articles.")
        return merged_count

    def discover_and_ingest_new_issues(self, reparse_all: bool = False) -> int:
        raise RuntimeError(
            "Automated LinkedIn crawling is disabled: the source blocks unauthenticated "
            "automation and its terms do not permit this scraper. Import authorised "
            "exports manually instead."
        )

if __name__ == "__main__":
    print(
        "[AndriyBurkov] Static imported dataset; automated LinkedIn refresh is disabled."
    )
