"""
Builds compact markdown bullet lists ([source]-compact.md) for the LAST 3 MONTHS (90 days).
Auto-discovers and builds all sources in sources/ by default.
"""

import sys
from typing import Optional

from builder_core import (
    load_source, filter_visible, apply_time_window, group_and_sort_issues,
    render_issue_header, render_quotes, render_article_line_compact,
    output_path_for, write_output, discover_sources
)


def build_single_latest_compact(source_id: str, days_window: int = 90) -> Optional[str]:
    loaded = load_source(source_id)
    if not loaded:
        return None

    definition, raw_articles, issue_metadata = loaded
    articles = filter_visible(raw_articles)
    if not articles:
        print(f"[BuildLatestCompact] No visible articles found for {source_id}.")
        return None

    articles = apply_time_window(articles, days_window)
    issues, sorted_issue_ids = group_and_sort_issues(articles, issue_metadata)

    lines = [definition.get("default_header", f"### {definition.get('name', source_id)}"), ""]

    for iss_id in sorted_issue_ids:
        iss = issues[iss_id]
        lines.append(render_issue_header(iss))
        lines.append("")

        quote_lines = render_quotes(iss)
        if quote_lines:
            lines.extend(quote_lines)
            lines.append("")

        for a in iss["articles"]:
            lines.append(render_article_line_compact(a))

        lines.append("")

    output_content = "\n".join(lines).strip() + "\n"
    out_path = output_path_for(source_id, "-compact")
    write_output(out_path, output_content)

    print(f"[BuildLatestCompact] Generated -> {out_path} ({len(articles)} visible articles across {len(sorted_issue_ids)} issues)")
    return output_content


def build_latest_compact(source_id: Optional[str] = None):
    if source_id:
        build_single_latest_compact(source_id)
    else:
        for sid in discover_sources():
            build_single_latest_compact(sid)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    build_latest_compact(target)
