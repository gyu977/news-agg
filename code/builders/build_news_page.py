"""
Builds the rich interactive web dashboard (news.html)
loaded exclusively with the LAST 3 MONTHS (90 days) of articles
for maximum performance and responsiveness, injecting valid JSON via json.dumps().
"""

import os
import json
import sys
import re
import base64
from datetime import datetime, timedelta
from typing import Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
code_root = os.path.abspath(os.path.join(current_dir, ".."))
project_root = os.path.abspath(os.path.join(code_root, ".."))

for p in [code_root, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.base_scraper import BaseScraper

sys.path.insert(0, current_dir)
from builder_core import warn_if_stale

def build_news_page(days_window: int = 90, source_id: Optional[str] = None) -> str:
    # The canonical template is required; falling back to the generated news.html
    # would silently re-inject into stale output and compound drift.
    template_path = os.path.join(current_dir, "news_template.html")
    if not os.path.exists(template_path):
        raise FileNotFoundError(
            f"Canonical HTML template not found at {template_path}. "
            "news.html is generated output and cannot be used as a template."
        )

    output_path = os.path.join(project_root, "news.html")

    with open(template_path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    icon_path = os.path.join(project_root, "news-icon.svg")
    if not os.path.exists(icon_path):
        raise FileNotFoundError(f"Dashboard icon not found at {icon_path}.")
    with open(icon_path, "rb") as f:
        icon_data_uri = (
            "data:image/svg+xml;base64,"
            + base64.b64encode(f.read()).decode("ascii")
        )
    html = html.replace("{{NEWS_ICON_DATA_URI}}", icon_data_uri)

    # 1. Collect all articles from data-sources/*/data.json
    sources_dir = os.path.join(project_root, "data-sources")
    all_source_articles = []
    has_refreshable_source = False

    for entry in sorted(os.listdir(sources_dir)):
        if source_id and entry != source_id:
            continue
        src_folder = os.path.join(sources_dir, entry)
        data_file = os.path.join(src_folder, "data.json")
        def_file = os.path.join(src_folder, "definition.json")
        def_data = {}
        
        if os.path.isdir(src_folder) and os.path.exists(data_file):
            quote_map = {}
            if os.path.exists(def_file):
                with open(def_file, "r", encoding="utf-8") as df:
                    def_data = json.load(df)
                    if not def_data.get("static") and def_data.get("refresh_enabled", True):
                        has_refreshable_source = True
                    issues_list = def_data.get("parsed_issues", {}).get("issues", [])
                    for iss in issues_list:
                        iss_key = str(iss.get("id"))
                        quotes = iss.get("quotes", [])
                        if quotes:
                            quote_map[iss_key] = quotes[0]

            with open(data_file, "r", encoding="utf-8") as f:
                src_articles = json.load(f)
                for a in src_articles:
                    if a.get("hide", False):
                        continue
                    a["source_id"] = def_data.get("source_id", entry)
                    a["source_short_name"] = (
                        def_data.get("short_name")
                        or def_data.get("name")
                        or a.get("newsletter", "")
                    )

                    iss_key = str(a.get("issue_number"))
                    if iss_key in quote_map and not a.get("quote"):
                        a["quote"] = quote_map[iss_key].get("text", "")
                        a["quote_author"] = quote_map[iss_key].get("author", "")

                    all_source_articles.append(a)

    # 2. Collapse cross-source duplicates: the same article recommended by several
    #    newsletters should appear once, credited to whoever ran it first, with the
    #    other sources listed. Deduping here (rather than in data.json) keeps each
    #    source's own archive complete.
    by_link = {}
    deduped = []
    for art in all_source_articles:
        canon = BaseScraper.canonical_link(art.get("link") or "")
        if not canon:
            deduped.append(art)
            continue
        first = by_link.get(canon)
        if first is None:
            by_link[canon] = art
            deduped.append(art)
            continue
        # Keep the earliest-dated record; credit the later one as an "also in" source.
        earlier, later = (first, art)
        if str(art.get("date", "")) < str(first.get("date", "")):
            earlier, later = (art, first)
            deduped[deduped.index(first)] = art
            by_link[canon] = art
        others = earlier.setdefault("also_in", [])
        name = later.get("newsletter", "")
        if name and name != earlier.get("newsletter") and name not in others:
            others.append(name)

    dupes_removed = len(all_source_articles) - len(deduped)

    # 3. Re-assign sequential integer IDs for table selection & pinning
    final_articles = []
    for idx, art in enumerate(deduped, 1):
        clean_art = {
            "id": idx,
            "source_id": art.get("source_id", ""),
            "source_short_name": art.get("source_short_name") or art.get("newsletter", ""),
            "newsletter": art.get("newsletter", ""),
            "issue_number": art.get("issue_number"),
            "issue_title": art.get("issue_title", ""),
            "issue_link": art.get("issue_link", ""),
            "date": art.get("date", ""),
            "date_str": art.get("date_str", ""),
            "title": art.get("title", ""),
            "link": art.get("link", ""),
            "author": art.get("author") or None,
            "description": art.get("description", ""),
            "category": art.get("category", ""),
            "is_spotlight": bool(art.get("is_spotlight", False)),
            "type": art.get("type", "article")
        }
        if "quote" in art:
            clean_art["quote"] = art["quote"]
            clean_art["quote_author"] = art.get("quote_author", "")
        if art.get("also_in"):
            clean_art["also_in"] = art["also_in"]

        final_articles.append(clean_art)

    # 4. Calculate the cutoff for the LAST 3 MONTHS (90 days), anchored to *now* rather
    #    than to the newest article — a data-relative anchor hides a scraping outage.
    cutoff_str = (datetime.now() - timedelta(days=days_window)).strftime("%Y-%m-%d")
    latest_articles = [a for a in final_articles if a.get("date", "") >= cutoff_str]
    if has_refreshable_source:
        warn_if_stale(final_articles, "news dashboard")

    # Sort descending by ISO date
    latest_articles.sort(key=lambda x: str(x.get("date", "")), reverse=True)

    # 5. Clean JSON serialization
    json_articles_formatted = json.dumps(latest_articles, indent=4, ensure_ascii=False)
    new_articles_js = f"/* ARTICLES_START */\n    const articles = {json_articles_formatted};\n    /* ARTICLES_END */"
    
    # Locate replacement zone using explicit markers or fallback regex
    start_marker = "/* ARTICLES_START */"
    end_marker = "/* ARTICLES_END */"
    
    if start_marker in html and end_marker in html:
        start_idx = html.find(start_marker)
        end_idx = html.find(end_marker) + len(end_marker)
        new_html = html[:start_idx] + new_articles_js + html[end_idx:]
    else:
        # Fallback to regex pattern matching
        pattern = re.compile(r'(\s*const articles = )\[.*?\];', re.DOTALL)
        new_html = pattern.sub(f"\\1{json_articles_formatted};", html, count=1)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(new_html)

    dedupe_note = f", {dupes_removed} cross-source duplicates merged" if dupes_removed else ""
    print(f"[BuildNewsPage] Generated -> {output_path} "
          f"({len(latest_articles)} articles from last {days_window} days{dedupe_note})")
    return new_html

if __name__ == "__main__":
    build_news_page()
