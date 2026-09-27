#!/usr/bin/env python3
"""
InfoQ - The Software Architects' Newsletter Scraper.
Discovers and ingests issues from InfoQ's public archives and sample issues.
"""

import os
import re
import sys
import json
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
code_dir = os.path.join(project_root, "code")

for p in [code_dir, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.base_scraper import BaseScraper
from common.models import Article, ParsedIssueInfo

ARCHIVE_PAST_ISSUES_URL = "https://assets.infoq.com/newsletter/architect/en/template/architect_infoq_pastIssues_desktop.html"
BASE_URL = "https://www.infoq.com"


class InfoQArchitectureScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_dir=current_dir)

    def clean_url(self, url: str) -> str:
        """
        Removes InfoQ tracking parameters (architectureutm_*, utm_*, etc.)
        and normalizes trailing slashes.
        """
        if not url:
            return ""
        parsed = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        filtered_params = {
            k: v for k, v in query_params.items()
            if not (k.lower().startswith("utm_") or k.lower().startswith("architectureutm_") or self._is_tracking_param(k))
        }
        clean_query = urllib.parse.urlencode(filtered_params, doseq=True)
        path = parsed.path
        if not path.endswith("/") and not any(path.endswith(ext) for ext in [".html", ".pdf", ".action"]):
            path += "/"
        return urllib.parse.urlunparse((
            parsed.scheme, parsed.netloc, path, parsed.params, clean_query, ""
        ))

    def discover_past_issues(self) -> List[Dict[str, Any]]:
        """
        Fetches the desktop archive template and returns parsed issue metadata.
        """
        print(f"[InfoQ] Fetching past issues list from: {ARCHIVE_PAST_ISSUES_URL}")
        html = self.fetch_html(ARCHIVE_PAST_ISSUES_URL)
        if not html:
            print("[InfoQ] Failed to fetch past issues.")
            return []

        # Each issue has:
        # <a target="_blank" href="https://assets.infoq.com/.../110Architects_NL_September-2026.html" class="architect-item">
        # <h3>Issue 110 - Building Data and AI Platforms.
        # <br/><span>Case Study: Implementing Durable Workflows on Postgres Without an External Orchestrator.</span></h3>
        pattern = re.compile(
            r'<a[^>]+href="([^"]+)"[^>]*class="architect-item"[^>]*>\s*'
            r'<h3>Issue\s*(\d+)\s*-\s*([^.<]+)\.?\s*'
            r'(?:<br\s*/?>\s*<span>Case Study:\s*([^<]+)</span>)?\s*</h3>',
            re.IGNORECASE | re.DOTALL
        )

        issues = []
        for match in pattern.finditer(html):
            url = match.group(1).strip()
            num = int(match.group(2))
            theme = match.group(3).strip()
            case_study = (match.group(4) or "").strip()

            # Infer approximate date from URL filename (e.g. 110Architects_NL_September-2026.html)
            date_iso = ""
            date_str = ""
            date_match = re.search(r'([A-Za-z]+)-(\d{4})', url)
            if date_match:
                month_name, year_str = date_match.group(1), date_match.group(2)
                try:
                    dt = datetime.strptime(f"25 {month_name} {year_str}", "%d %B %Y")
                    date_iso = dt.strftime("%Y-%m-%d")
                    date_str = dt.strftime("%-d %B %Y")
                except ValueError:
                    pass

            issues.append({
                "number": num,
                "theme": theme,
                "case_study": case_study,
                "url": url,
                "date": date_iso,
                "date_str": date_str
            })

        print(f"[InfoQ] Discovered {len(issues)} past issues.")
        return issues


if __name__ == "__main__":
    scraper = InfoQArchitectureScraper()
    issues = scraper.discover_past_issues()
    print(f"Total discovered issues: {len(issues)}")
    if issues:
        print(f"Latest issue: #{issues[0]['number']} - {issues[0]['theme']} ({issues[0]['url']})")
