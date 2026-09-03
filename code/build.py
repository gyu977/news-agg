"""
Master CLI Build Orchestrator.
Builds the 3-Month Latest Markdown files, Compact Lists, Cumulative Archives (Full & Compact), and Interactive News Page.
Optionally crawls online data sources (--refresh) or processes inbox items (--inbox).
"""

import sys
import os
import argparse
import json
import subprocess

current_dir = os.path.dirname(os.path.abspath(__file__))
code_root = current_dir
project_root = os.path.abspath(os.path.join(code_root, ".."))
builders_dir = os.path.join(code_root, "builders")

for p in [current_dir, builders_dir, code_root, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from builders.build_latest import build_latest
    from builders.build_latest_compact import build_latest_compact
    from builders.build_archive import build_archive
    from builders.build_archive_compact import build_archive_compact
    from builders.build_news_page import build_news_page
except ImportError:
    from build_latest import build_latest
    from build_latest_compact import build_latest_compact
    from build_archive import build_archive
    from build_archive_compact import build_archive_compact
    from build_news_page import build_news_page

def refresh_sources(source_id: str = None) -> bool:
    """
    Crawls online sources to fetch and sync latest newsletter issues.
    Returns True if every scraper that ran exited successfully.
    """
    sources_dir = os.path.join(project_root, "data-sources")
    if not os.path.exists(sources_dir):
        print(f"[Refresh] Sources directory not found: {sources_dir}")
        return False

    if source_id:
        targets = [source_id]
    else:
        print("\n[Refresh] Crawling all active data sources...")
        targets = sorted(os.listdir(sources_dir))

    ran, failed = 0, []
    for entry in targets:
        definition_path = os.path.join(sources_dir, entry, "definition.json")
        if os.path.isfile(definition_path):
            with open(definition_path, "r", encoding="utf-8") as f:
                definition = json.load(f)
            if definition.get("static") or not definition.get("refresh_enabled", True):
                reason = definition.get("refresh_disabled_reason") or "source is static"
                print(f"[Refresh] Skipping {entry}: {reason}")
                continue

        scraper_path = os.path.join(sources_dir, entry, "scraper.py")
        if not os.path.exists(scraper_path):
            if source_id:
                print(f"[Refresh] No scraper found for source: {source_id} at {scraper_path}")
                return False
            continue

        print(f"\n--- [Refresh] Running {entry} scraper ---")
        result = subprocess.run([sys.executable, scraper_path])
        ran += 1
        if result.returncode != 0:
            failed.append((entry, result.returncode))
            print(f"[Refresh] ✗ {entry} scraper failed (exit code {result.returncode})")

    if failed:
        print(f"\n[Refresh] ✗ {len(failed)} of {ran} scraper(s) failed: " + ", ".join(name for name, _ in failed))
        print("[Refresh] If this is an ImportError, install dependencies: pip install -r requirements.txt")
        return False

    print(f"\n✓ Data sources refresh completed! ({ran} scraper(s))")
    return True


def available_sources():
    sources_dir = os.path.join(project_root, "data-sources")
    if not os.path.isdir(sources_dir):
        return []
    return sorted(
        entry
        for entry in os.listdir(sources_dir)
        if os.path.isfile(os.path.join(sources_dir, entry, "definition.json"))
    )


def positive_days(value: str) -> int:
    try:
        days = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("days must be an integer") from exc
    if days < 1:
        raise argparse.ArgumentTypeError("days must be at least 1")
    return days


def main():
    parser = argparse.ArgumentParser(description="Master Presentation Build Runner for news-agg")
    parser.add_argument("--refresh", action="store_true", help="Crawl online sources and refresh local data.json before building")
    parser.add_argument("--source", type=str, help="Specific source_id to build/refresh (e.g. dear-architects)")
    parser.add_argument("--latest", action="store_true", help="Build only 3-month full detailed markdown ([source].md)")
    parser.add_argument("--compact", action="store_true", help="Build only 3-month compact markdown ([source]-compact.md)")
    parser.add_argument("--archive", action="store_true", help="Build only cumulative archive markdown ([source]-archive.md)")
    parser.add_argument("--archive-compact", action="store_true", help="Build only cumulative compact archive markdown ([source]-archive-compact.md)")
    parser.add_argument("--news-page", action="store_true", help="Build only interactive dashboard (news.html)")
    parser.add_argument("--all", action="store_true", help="Build all presentation formats (default)")
    parser.add_argument("--inbox", action="store_true", help="Process and ingest pending articles from inbox.md before building")
    parser.add_argument("--days", type=positive_days, default=90, help="Days window for latest items (default: 90)")

    args = parser.parse_args()

    if args.source and args.source not in available_sources():
        parser.error(
            f"unknown source {args.source!r}; choose from: {', '.join(available_sources())}"
        )

    refresh_ok = True
    if args.refresh:
        refresh_ok = refresh_sources(args.source)
        if not refresh_ok:
            print("\n✗ Refresh failed; generated artifacts were left untouched.")
            return 1

    if args.inbox:
        if args.refresh:
            print("\n[Build] --inbox: my-collected-articles was already refreshed above; ingesting any remaining inbox items...")
        try:
            import importlib.util
            scraper_path = os.path.join(project_root, "data-sources", "my-collected-articles", "scraper.py")
            spec = importlib.util.spec_from_file_location("my_scraper", scraper_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            scraper = mod.MyCollectedArticlesScraper()
            scraper.process_all_inboxes()
        except Exception as e:
            print(f"[Build] Error running inbox processor: {e}")
            return 1

    run_all = args.all or (not args.latest and not args.compact and not args.archive and not args.archive_compact and not args.news_page)

    print("\n[Build] Building presentation deliverables...")
    if run_all or args.latest:
        build_latest(args.source, args.days)

    if run_all or args.compact:
        build_latest_compact(args.source, args.days)

    if run_all or args.archive:
        build_archive(args.source)

    if run_all or args.archive_compact:
        build_archive_compact(args.source)

    if run_all or args.news_page:
        news_days = args.days if any(arg.startswith("--days") for arg in sys.argv) else None
        build_news_page(news_days, args.source)

    print("\n✓ All presentation builds completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
