"""
Builds full cumulative markdown archives ([source]-archive.md) with categories,
quotes, and italicized descriptions, containing all historical issues.
Respects archive_retention_days and has_archive settings from definition.json.
Auto-discovers and builds all sources in sources/ by default.
"""

import sys
from typing import Optional

from builder_core import (
    load_source, filter_visible, apply_archive_retention, group_and_sort_issues,
    render_issue_header, render_quotes, render_article_line_full,
    output_path_for, write_output, discover_sources
)


def build_single_archive(source_id: str) -> Optional[str]:
    loaded = load_source(source_id)
    if not loaded:
        return None

    definition, raw_articles, issue_metadata = loaded

    if not definition.get("has_archive", True):
        return None

    articles = filter_visible(raw_articles)
    articles = apply_archive_retention(articles, definition)

    if not articles:
        print(f"[BuildArchive] No visible articles found for {source_id}.")
        return None

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
            lines.extend(render_article_line_full(a))

        lines.append("---")
        lines.append("")

    # Remove trailing separator
    if len(lines) >= 2 and lines[-2] == "---":
        lines = lines[:-2]

    output_content = "\n".join(lines).strip() + "\n"
    out_path = output_path_for(source_id, "-archive")
    write_output(out_path, output_content)

    print(f"[BuildArchive] Generated -> {out_path} ({len(articles)} visible articles across {len(sorted_issue_ids)} issues)")
    return output_content


def build_archive(source_id: Optional[str] = None):
    if source_id:
        build_single_archive(source_id)
    else:
        for sid in discover_sources():
            build_single_archive(sid)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    build_archive(target)
