"""
Builds the rich interactive web dashboard (news.html)
loaded exclusively with the LAST 3 MONTHS (90 days) of articles
for maximum performance and responsiveness, injecting valid JSON via json.dumps().
"""

import os
import json
import sys
import re
from datetime import datetime, timedelta
from typing import Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
code_root = os.path.abspath(os.path.join(current_dir, ".."))
project_root = os.path.abspath(os.path.join(code_root, ".."))

for p in [code_root, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

def build_news_page(days_window: int = 90) -> str:
    # Look for canonical template first, then fallback candidates
    candidates = [
        os.path.join(current_dir, "news_template.html"),
        os.path.join(project_root, "news.html"),
        os.path.join(project_root, "old", "all-news-enhanced.html")
    ]
    template_path = None
    for cand in candidates:
        if os.path.exists(cand):
            template_path = cand
            break

    if not template_path:
        raise FileNotFoundError("Could not find a valid HTML template for news.html.")

    output_path = os.path.join(project_root, "news.html")

    with open(template_path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    # 1. Collect all articles from sources/*/data.json
    sources_dir = os.path.join(project_root, "sources")
    all_source_articles = []
    managed_sources = set()

    for entry in sorted(os.listdir(sources_dir)):
        src_folder = os.path.join(sources_dir, entry)
        data_file = os.path.join(src_folder, "data.json")
        def_file = os.path.join(src_folder, "definition.json")
        
        if os.path.isdir(src_folder) and os.path.exists(data_file):
            quote_map = {}
            if os.path.exists(def_file):
                try:
                    with open(def_file, "r", encoding="utf-8") as df:
                        def_data = json.load(df)
                        issues_list = def_data.get("parsed_issues", {}).get("issues", [])
                        for iss in issues_list:
                            iss_num = iss.get("id")
                            quotes = iss.get("quotes", [])
                            if quotes:
                                quote_map[iss_num] = quotes[0]
                except Exception as e:
                    print(f"[BuildNewsPage] Warning parsing definition.json for {entry}: {e}")

            with open(data_file, "r", encoding="utf-8") as f:
                try:
                    src_articles = json.load(f)
                    for a in src_articles:
                        if a.get("hide", False):
                            continue
                        
                        iss_num = a.get("issue_number")
                        if iss_num in quote_map and not a.get("quote"):
                            a["quote"] = quote_map[iss_num].get("text", "")
                            a["quote_author"] = quote_map[iss_num].get("author", "")

                        all_source_articles.append(a)
                        managed_sources.add(a.get("newsletter"))
                except Exception as e:
                    print(f"[BuildNewsPage] Error reading {data_file}: {e}")

    # 2. Re-assign sequential integer IDs for table selection & pinning
    final_articles = []
    for idx, art in enumerate(all_source_articles, 1):
        clean_art = {
            "id": idx,
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

        final_articles.append(clean_art)

    # 3. Calculate dynamic cutoff date for LAST 3 MONTHS (90 days)
    now = datetime.now()
    dates = [datetime.strptime(a["date"], "%Y-%m-%d") for a in final_articles if a.get("date")]
    past_or_current = [d for d in dates if d <= now + timedelta(days=3)]
    ref_dt = max(past_or_current) if past_or_current else (max(dates) if dates else now)
    cutoff_dt = ref_dt - timedelta(days=days_window)
    cutoff_str = cutoff_dt.strftime("%Y-%m-%d")
    latest_articles = [a for a in final_articles if a.get("date", "") >= cutoff_str]

    # Sort descending by ISO date
    latest_articles.sort(key=lambda x: str(x.get("date", "")), reverse=True)

    # 4. Clean JSON serialization
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

    print(f"[BuildNewsPage] Generated -> {output_path} ({len(latest_articles)} articles from last {days_window} days)")
    return new_html

if __name__ == "__main__":
    build_news_page()
