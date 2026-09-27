#!/usr/bin/env python3
"""
Source Scaffolding CLI for News Aggregator.
Automates creating a new data source module with correct directory structure,
definition.json, data.json, scraper.py, and README.md.

Usage:
  python3 code/tools/scaffold_source.py --id martin-fowler --name "Martin Fowler" \
      --author "Martin Fowler" --type rss --url "https://martinfowler.com/feed.atom" \
      --prefix mf --description "Essays on software design and architecture."
"""

import os
import sys
import json
import argparse
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
code_root = os.path.abspath(os.path.join(current_dir, ".."))
project_root = os.path.abspath(os.path.join(code_root, ".."))

for p in [code_root, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)


SUBSTACK_SCRAPER_TEMPLATE = '''import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
code_root = os.path.abspath(os.path.join(current_dir, "..", "..", "code"))
project_root = os.path.abspath(os.path.join(code_root, ".."))

for p in [code_root, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.substack_scraper import SubstackScraper


class {class_name}Scraper(SubstackScraper):
    base_url = "{url}"
    newsletter_name = "{name}"
    article_id_prefix = "{prefix}"
    log_name = "{class_name}"

    def __init__(self):
        super().__init__(source_dir=current_dir)


if __name__ == "__main__":
    scraper = {class_name}Scraper()
    scraper.discover_and_ingest_posts()
'''


RSS_SCRAPER_TEMPLATE = '''import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
code_root = os.path.abspath(os.path.join(current_dir, "..", "..", "code"))
project_root = os.path.abspath(os.path.join(code_root, ".."))

for p in [code_root, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.rss_feed_scraper import RSSFeedScraper


class {class_name}Scraper(RSSFeedScraper):
    feed_url = "{url}"
    newsletter_name = "{name}"
    article_id_prefix = "{prefix}"
    log_name = "{class_name}"
    default_author = "{author}"

    def __init__(self):
        super().__init__(source_dir=current_dir)


if __name__ == "__main__":
    scraper = {class_name}Scraper()
    scraper.discover_and_ingest_feed()
'''


CUSTOM_SCRAPER_TEMPLATE = '''import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
code_root = os.path.abspath(os.path.join(current_dir, "..", "..", "code"))
project_root = os.path.abspath(os.path.join(code_root, ".."))

for p in [code_root, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.base_scraper import BaseScraper


class {class_name}Scraper(BaseScraper):
    def __init__(self):
        super().__init__(source_dir=current_dir)

    def scrape(self):
        print(f"[{class_name}] Scraping...")
        # Implement discovery and parsing logic here
        pass


if __name__ == "__main__":
    scraper = {class_name}Scraper()
    scraper.scrape()
'''


def to_pascal_case(slug: str) -> str:
    """Converts a slug like 'martin-fowler' into 'MartinFowler'."""
    return "".join(word.capitalize() for word in slug.replace("_", "-").split("-"))


def scaffold(args: argparse.Namespace) -> None:
    source_id = args.id.lower().strip()
    target_dir = os.path.join(project_root, "data-sources", source_id)

    if os.path.exists(target_dir):
        print(f"Error: Target directory already exists: {target_dir}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(target_dir, exist_ok=True)
    class_name = to_pascal_case(source_id)
    url = args.url.rstrip("/")

    # 1. Write definition.json
    definition = {
        "source_id": source_id,
        "name": args.name,
        "author": args.author,
        "official_site": url,
        "archive_url": url,
        "default_header": args.name,
        "short_name": args.name,
        "article_id_prefix": args.prefix,
        "description": args.description,
        "refresh_enabled": True,
        "refresh_disabled_reason": "",
        "static": False,
        "has_archive": True,
        "archive_retention_days": None,
        "parsed_issues": {
            "count": 0,
            "issues": [],
            "last_parsed_issue": "",
            "last_parsed_date": ""
        }
    }
    def_path = os.path.join(target_dir, "definition.json")
    with open(def_path, "w", encoding="utf-8") as f:
        json.dump(definition, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # 2. Write data.json
    data_path = os.path.join(target_dir, "data.json")
    with open(data_path, "w", encoding="utf-8") as f:
        f.write("[]\n")

    # 3. Write scraper.py
    if args.type == "substack":
        scraper_code = SUBSTACK_SCRAPER_TEMPLATE.format(
            class_name=class_name,
            url=url,
            name=args.name,
            prefix=args.prefix
        )
    elif args.type == "rss":
        scraper_code = RSS_SCRAPER_TEMPLATE.format(
            class_name=class_name,
            url=url,
            name=args.name,
            prefix=args.prefix,
            author=args.author
        )
    else:
        scraper_code = CUSTOM_SCRAPER_TEMPLATE.format(
            class_name=class_name
        )

    scraper_path = os.path.join(target_dir, "scraper.py")
    with open(scraper_path, "w", encoding="utf-8") as f:
        f.write(scraper_code)

    # 4. Write README.md
    readme_content = f"""# {args.name}

- **Source ID:** `{source_id}`
- **Author:** {args.author}
- **Website / Feed:** {url}
- **Type:** {args.type}
- **Article ID Prefix:** `{args.prefix}`
- **Description:** {args.description}

## Data Pipeline

Run this source scraper individually:
```bash
python3 data-sources/{source_id}/scraper.py
```

Or refresh all sources via the master orchestrator:
```bash
python3 code/build.py --refresh --source {source_id}
```
"""
    readme_path = os.path.join(target_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"✓ Successfully scaffolded data source: '{source_id}'")
    print(f"  • {def_path}")
    print(f"  • {data_path}")
    print(f"  • {scraper_path}")
    print(f"  • {readme_path}")
    print(f"\nNext step: Run 'python3 data-sources/{source_id}/scraper.py' to ingest articles!")


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new newsletter / blog data source.")
    parser.add_argument("--id", required=True, help="Slug identifier for the source (e.g. 'martin-fowler')")
    parser.add_argument("--name", required=True, help="Display name (e.g. 'Martin Fowler')")
    parser.add_argument("--author", required=True, help="Author name (e.g. 'Martin Fowler')")
    parser.add_argument("--type", choices=["substack", "rss", "custom"], default="rss", help="Source scraper archetype")
    parser.add_argument("--url", required=True, help="Source URL or feed URL")
    parser.add_argument("--prefix", required=True, help="Article ID prefix (e.g. 'mf')")
    parser.add_argument("--description", default="", help="Short description for UI dashboard")

    args = parser.parse_args()
    scaffold(args)


if __name__ == "__main__":
    main()
