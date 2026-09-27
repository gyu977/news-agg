"""
Shared core logic for all presentation builders.
Provides source loading, article filtering, issue grouping, and source discovery
so that individual builders only need to implement their rendering logic.
"""

import os
import re
import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
code_root = os.path.abspath(os.path.join(current_dir, ".."))
project_root = os.path.abspath(os.path.join(code_root, ".."))

for p in [code_root, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from common.constants import VISUAL_MARKERS
except ImportError:
    from code.common.constants import VISUAL_MARKERS


def escape_markdown_text(text: str) -> str:
    """Escape scraped text used inside Markdown labels/emphasis."""
    if not text:
        return ""
    value = str(text).replace("\\", "\\\\")
    for marker in ("`", "*", "_", "[", "]", "$"):
        value = value.replace(marker, f"\\{marker}")
    return value


def escape_markdown_math(text: str) -> str:
    """Backward-compatible alias for the full Markdown text escaper."""
    return escape_markdown_text(text)


def escape_markdown_url(url: str) -> str:
    """Escape characters that terminate a Markdown inline-link destination."""
    if not url:
        return ""
    return (
        str(url)
        .replace("\\", "%5C")
        .replace(" ", "%20")
        .replace("(", "%28")
        .replace(")", "%29")
    )


def load_source(source_id: str) -> Optional[Tuple[Dict, List[Dict], Dict]]:
    """
    Load a source's definition.json and data.json.
    Returns (definition, raw_articles, issue_metadata_by_id) or None if files don't exist.
    """
    source_dir = os.path.join(project_root, "data-sources", source_id)
    def_path = os.path.join(source_dir, "definition.json")
    data_path = os.path.join(source_dir, "data.json")

    if not os.path.exists(def_path) or not os.path.exists(data_path):
        return None

    with open(def_path, "r", encoding="utf-8") as f:
        definition = json.load(f)

    with open(data_path, "r", encoding="utf-8") as f:
        raw_articles = json.load(f)

    # Build issue metadata lookup from definition
    issue_metadata_by_id = {}
    for iss in definition.get("parsed_issues", {}).get("issues", []):
        issue_metadata_by_id[str(iss.get("id"))] = iss

    return definition, raw_articles, issue_metadata_by_id


def filter_visible(raw_articles: List[Dict]) -> List[Dict]:
    """Filter out articles marked with hide: true."""
    return [a for a in raw_articles if not a.get("hide", False)]


def apply_time_window(articles: List[Dict], days_window: int = 90) -> List[Dict]:
    """
    Apply a rolling time window cutoff (e.g. 90 days), anchored to *now*.

    The anchor used to be `max(article date)`, which made the window data-relative: if
    scraping stalled, "last 90 days" kept showing the same frozen slice forever and the
    outage stayed invisible. Anchoring to the clock means a stale feed visibly empties.
    Future-dated events (conferences) are always kept.
    """
    if not articles:
        return articles

    now = datetime.now()
    cutoff_str = (now - timedelta(days=days_window)).strftime("%Y-%m-%d")
    return [a for a in articles if a.get("date", "") >= cutoff_str]


def staleness_days(articles: List[Dict]) -> Optional[int]:
    """Days between now and the newest non-future article date, or None if unknown."""
    now = datetime.now()
    dates = []
    for a in articles:
        try:
            dates.append(datetime.strptime(a["date"], "%Y-%m-%d"))
        except (KeyError, ValueError, TypeError):
            continue
    past = [d for d in dates if d <= now + timedelta(days=3)]
    if not past:
        return None
    return (now - max(past)).days


def warn_if_stale(articles: List[Dict], label: str, threshold_days: int = 30) -> Optional[int]:
    """Print a build-time warning when a feed has clearly stopped updating (H8)."""
    days = staleness_days(articles)
    if days is not None and days > threshold_days:
        print(f"  [stale] {label}: newest article is {days} days old — scraping may have stalled.")
    return days


def apply_archive_retention(articles: List[Dict], definition: Dict) -> List[Dict]:
    """
    Apply archive_retention_days from definition if configured.
    Used by archive builders to limit historical depth for sources like LinkedIn Pulse.
    """
    retention_days = definition.get("archive_retention_days")
    if not retention_days or not articles:
        return articles

    dates = [datetime.strptime(a["date"], "%Y-%m-%d") for a in articles if a.get("date")]
    if not dates:
        return articles

    cutoff_dt = datetime.now() - timedelta(days=retention_days)
    cutoff_str = cutoff_dt.strftime("%Y-%m-%d")
    return [a for a in articles if a.get("date", "") >= cutoff_str]


def group_and_sort_issues(articles: List[Dict], issue_metadata_by_id: Dict) -> Tuple[Dict, List[str]]:
    """
    Group articles by issue_id/date and sort issues chronologically descending.
    Returns (issues_dict, sorted_issue_ids).
    """
    issues = {}
    for a in articles:
        iss_id = str(a.get("issue_number")) if a.get("issue_number") is not None else a.get("date", "unknown")
        if iss_id not in issues:
            def_iss = issue_metadata_by_id.get(iss_id, {})
            issues[iss_id] = {
                "issue_number": a.get("issue_number"),
                "issue_title": a.get("issue_title"),
                "issue_link": a.get("issue_link"),
                "date": a.get("date", ""),
                "date_str": a.get("date_str", ""),
                "quotes": def_iss.get("quotes", []),
                "articles": []
            }
        issues[iss_id]["articles"].append(a)

    sorted_issue_ids = sorted(
        issues.keys(),
        key=lambda k: issues[k].get("date", ""),
        reverse=True
    )
    return issues, sorted_issue_ids


def render_issue_header(iss: Dict) -> str:
    """Render the markdown header line for an issue."""
    num = iss.get("issue_number")
    num_prefix = f"#{num} - " if num is not None else ""
    title = escape_markdown_text(iss.get("issue_title", ""))
    date_str = escape_markdown_text(iss.get("date_str", ""))
    if iss.get("issue_link"):
        return (
            f"**[{num_prefix}{title}]({escape_markdown_url(iss['issue_link'])})** "
            f"- {date_str}"
        )
    else:
        return f"**{num_prefix}{title}** - {date_str}"


def render_quotes(iss: Dict) -> List[str]:
    """Render blockquote lines for an issue's quotes."""
    lines = []
    for q in iss.get("quotes", []):
        lines.append(
            f'> "{escape_markdown_text(q["text"])}" — '
            f'{escape_markdown_text(q["author"])}'
        )
    return lines


def render_article_line_full(a: Dict) -> List[str]:
    """Render a full article entry with description and category tag."""
    lines = []
    author = a.get("author")
    author_prefix = f"**{escape_markdown_text(author)}** - " if author else ""

    icon_str = ""
    atype = a.get("type", "article")
    if atype in VISUAL_MARKERS and VISUAL_MARKERS[atype]:
        icon_str = f"{VISUAL_MARKERS[atype]} "

    spotlight_str = " - In the spotlight" if a.get("is_spotlight") else ""
    cat_str = f" - [Category: {a.get('category')}]" if a.get('category') else ""

    title_escaped = escape_markdown_text(a.get("title", ""))
    lines.append(
        f"{author_prefix}{icon_str}[{title_escaped}]"
        f"({escape_markdown_url(a['link'])}){spotlight_str}{cat_str}"
    )
    lines.append("")

    desc = escape_markdown_text(a.get("description", "").strip())
    if desc:
        lines.append(f"*{desc}*")
        lines.append("")

    return lines


def render_article_line_compact(a: Dict) -> str:
    """Render a compact bullet-list article entry."""
    author = a.get("author")
    author_prefix = f"**{escape_markdown_text(author)}** - " if author else ""

    icon_str = ""
    atype = a.get("type", "article")
    if atype in VISUAL_MARKERS and VISUAL_MARKERS[atype]:
        icon_str = f"{VISUAL_MARKERS[atype]} "

    spotlight_str = " - In the spotlight" if a.get("is_spotlight") else ""
    title_escaped = escape_markdown_text(a.get("title", ""))
    return (
        f"- {author_prefix}{icon_str}[{title_escaped}]"
        f"({escape_markdown_url(a['link'])}){spotlight_str}"
    )


def output_path_for(source_id: str, suffix: str) -> str:
    """Get the output file path for a given source and suffix."""
    return os.path.join(project_root, "generated", f"{source_id}{suffix}.md")


def write_output(path: str, content: str):
    """Write content to output file, creating directories as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def discover_sources() -> List[str]:
    """Auto-discover all source IDs that have a definition.json."""
    sources_dir = os.path.join(project_root, "data-sources")
    result = []
    for entry in sorted(os.listdir(sources_dir)):
        full_path = os.path.join(sources_dir, entry)
        if os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, "definition.json")):
            result.append(entry)
    return result
