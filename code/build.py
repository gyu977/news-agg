"""
Master CLI Build Orchestrator.
Builds the 3-Month Latest Markdown files, Compact Lists, Cumulative Archives (Full & Compact), and Interactive News Page.
Optionally crawls online data sources (--refresh) or processes inbox items (--inbox).
"""

import sys
import os
import argparse
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

def refresh_sources(source_id: str = None):
    """
    Crawls online sources to fetch and sync latest newsletter issues.
    """
    sources_dir = os.path.join(project_root, "sources")
    if not os.path.exists(sources_dir):
        print(f"[Refresh] Sources directory not found: {sources_dir}")
        return

    if source_id:
        scraper_path = os.path.join(sources_dir, source_id, "scraper.py")
        if os.path.exists(scraper_path):
            print(f"\n[Refresh] Crawling source: {source_id}...")
            subprocess.run([sys.executable, scraper_path])
        else:
            print(f"[Refresh] No scraper found for source: {source_id} at {scraper_path}")
    else:
        print("\n[Refresh] Crawling all active data sources...")
        for entry in sorted(os.listdir(sources_dir)):
            scraper_path = os.path.join(sources_dir, entry, "scraper.py")
            if os.path.exists(scraper_path):
                print(f"\n--- [Refresh] Running {entry} scraper ---")
                subprocess.run([sys.executable, scraper_path])
        print("\n✓ Data sources refresh completed!")

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
    parser.add_argument("--days", type=int, default=90, help="Days window for latest items (default: 90)")

    args = parser.parse_args()

    if args.refresh:
        refresh_sources(args.source)

    if args.inbox and not args.refresh:
        try:
            import importlib.util
            scraper_path = os.path.join(project_root, "sources", "my-collected-articles", "scraper.py")
            spec = importlib.util.spec_from_file_location("my_scraper", scraper_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            scraper = mod.MyCollectedArticlesScraper()
            scraper.process_all_inboxes()
        except Exception as e:
            print(f"[Build] Error running inbox processor: {e}")

    run_all = args.all or (not args.latest and not args.compact and not args.archive and not args.archive_compact and not args.news_page)

    print("\n[Build] Building presentation deliverables...")
    if run_all or args.latest:
        build_latest(args.source)

    if run_all or args.compact:
        build_latest_compact(args.source)

    if run_all or args.archive:
        build_archive(args.source)

    if run_all or args.archive_compact:
        build_archive_compact(args.source)

    if run_all or args.news_page:
        build_news_page(args.days)

    print("\n✓ All presentation builds completed successfully!")

if __name__ == "__main__":
    main()
