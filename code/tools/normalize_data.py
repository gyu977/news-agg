"""
Normalize data-sources/*/data.json in place.

Fixes the link-identity defects tracked as C5/H3/D6/D7:

  1. Rewrites every `link` through the corrected tracking-parameter deny-list, so
     `?si=`, `?fbclid=` and friends no longer fork one article into two records.
  2. Collapses records that share a canonical link *within the same issue*. These
     are always the same article scraped twice; the surviving record keeps the
     richest value for each field and the union of `user_overrides`.
  3. Re-mints every `id` as `{prefix}-{issue}-{hash6}`, replacing the positional
     `{prefix}-{issue}-{index}` scheme whose restarting index produced collisions.
  4. Collapses runs of whitespace in `title`/`description`/`author`/`issue_title`,
     where HTML source indentation leaked into the scraped text.
  5. Sets `hide: true` on sponsor/advertising links (see `SPONSOR_DOMAINS`), which the
     original single-domain deny-list missed. Hiding is non-destructive: the record
     stays in `data.json` and `merge_articles()` will never un-hide it.

Records that share a link across *different* issues are deliberately left alone:
two newsletters (or two weeks) recommending the same article is real signal.

The script is idempotent — running it twice makes no further changes — so it is
safe to re-run after any scrape. Use --check to report without writing.
"""

import argparse
import collections
import json
import os
import re
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(CODE_DIR)
for _p in (CODE_DIR, PROJECT_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common.base_scraper import BaseScraper  # noqa: E402

SOURCES_DIR = os.path.join(PROJECT_ROOT, "data-sources")


class _SponsorProbe(BaseScraper):
    """BaseScraper with no source_dir, used only for its sponsor-detection logic."""

    def __init__(self):
        self.definition = None
        self.articles = []


_sponsor_probe = _SponsorProbe()

# Maps a source directory to the short prefix used in its article ids.
ID_PREFIXES = {
    "addy-osmani": "addy",
    "andriy-burkov-ai": "ab",
    "dear-architects": "da",
    "future-software-development": "fose",
    "my-collected-articles": "others",
    "pragmatic-engineer": "pe",
    "token-by-token": "tbt",
}

# Author values that are publisher credits or scraping noise rather than a person.
_NOT_AN_AUTHOR = re.compile(r"^(published on|posted on|via|source)\b", re.I)


def _is_plausible_author(value):
    """An author must contain letters and must not be a publisher credit."""
    return bool(re.search(r"[^\W\d_]", value)) and not _NOT_AN_AUTHOR.match(value)


# Fields where a longer value is assumed to be the better one when merging.
_RICHER_IF_LONGER = ("title", "description", "author", "issue_title")


def issue_segment(record):
    """The `{issue}` part of an id: the issue number, or year-month for sources without one."""
    issue = record.get("issue_number")
    if issue not in (None, ""):
        return str(issue)
    return (record.get("date") or "")[:7] or "x"


def identity_of(record):
    """Records sharing this identity are the same article scraped twice."""
    link = BaseScraper.canonical_link(record.get("link") or "")
    basis = link or " ".join((record.get("title") or "").lower().split())
    return (issue_segment(record), basis)


def merge_records(primary, duplicate):
    """Fold `duplicate` into `primary`, keeping the richest value for each field."""
    for key, dup_value in duplicate.items():
        if key == "user_overrides":
            continue
        cur = primary.get(key)
        if dup_value in (None, "", [], {}):
            continue
        if cur in (None, "", [], {}):
            primary[key] = dup_value
        elif key in _RICHER_IF_LONGER and len(str(dup_value)) > len(str(cur)):
            primary[key] = dup_value
        elif key in ("hide", "is_spotlight") and dup_value:
            primary[key] = True
    overrides = list(primary.get("user_overrides") or [])
    for name in duplicate.get("user_overrides") or []:
        if name not in overrides:
            overrides.append(name)
    primary["user_overrides"] = overrides
    return primary


# Counters that describe the data without modifying it.
REPORT_ONLY_STATS = {"suspicious_titles"}


def normalize_source(source_id, records):
    """Return (new_records, stats) without mutating the input list."""
    stats = collections.Counter()
    prefix = ID_PREFIXES.get(source_id, source_id)

    cleaned = []
    for rec in records:
        rec = dict(rec)
        old_link = rec.get("link") or ""
        new_link = BaseScraper.clean_url(BaseScraper, old_link) if old_link else ""
        if new_link != old_link:
            rec["link"] = new_link
            stats["links_cleaned"] += 1
        # HTML source indentation leaks into scraped text as runs of newlines and
        # spaces, which then render literally in the dashboard and Markdown digests.
        for field in ("title", "description", "author", "issue_title"):
            value = rec.get(field)
            if isinstance(value, str):
                collapsed = " ".join(value.split())
                if collapsed != value:
                    rec[field] = collapsed
                    stats["text_normalized"] += 1
        # `author` must name a person. Publisher credits and stray punctuation are
        # scraping artifacts, and an empty author renders better than a wrong one.
        author = rec.get("author")
        if isinstance(author, str) and author and not _is_plausible_author(author):
            rec["author"] = None
            stats["authors_cleared"] += 1
        cleaned.append(rec)

    # Collapse same-issue duplicates, preserving the original ordering.
    by_identity = {}
    result = []
    for rec in cleaned:
        identity = identity_of(rec)
        existing = by_identity.get(identity)
        if existing is None:
            by_identity[identity] = rec
            result.append(rec)
        else:
            merge_records(existing, rec)
            stats["duplicates_merged"] += 1

    for rec in result:
        new_id = BaseScraper.make_article_id(
            prefix, issue_segment(rec), rec.get("link") or "", rec.get("title") or ""
        )
        if new_id != rec.get("id"):
            rec["id"] = new_id
            stats["ids_rewritten"] += 1

    # Hide advertising slots. `hide` is only ever set, never cleared, so a manual
    # decision to un-hide something survives future runs.
    for rec in result:
        if rec.get("hide"):
            continue
        if _sponsor_probe.is_sponsor_link(rec.get("link") or "", rec.get("title") or ""):
            rec["hide"] = True
            stats["sponsors_hidden"] += 1

    # Hide newsletter chrome captured as articles (subscribe prompts, mailto links).
    for rec in result:
        if rec.get("hide"):
            continue
        if _sponsor_probe.is_boilerplate(rec.get("title") or "", rec.get("link") or ""):
            rec["hide"] = True
            stats["boilerplate_hidden"] += 1

    # Truncated titles are reported, not hidden — the article behind them is real.
    for rec in result:
        if not rec.get("hide") and _sponsor_probe.is_suspicious_title(rec.get("title") or ""):
            stats["suspicious_titles"] += 1

    collisions = [i for i, c in collections.Counter(r["id"] for r in result).items() if c > 1]
    if collisions:
        raise SystemExit(f"[normalize] {source_id}: id collisions remain: {collisions}")

    return result, stats


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check", action="store_true",
                        help="Report what would change without writing any files")
    parser.add_argument("--source", type=str, help="Limit to a single source_id")
    args = parser.parse_args()

    total = collections.Counter()
    changed_sources = 0

    for name in sorted(os.listdir(SOURCES_DIR)):
        if args.source and name != args.source:
            continue
        path = os.path.join(SOURCES_DIR, name, "data.json")
        if not os.path.isfile(path):
            continue

        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)

        new_records, stats = normalize_source(name, records)
        total.update(stats)

        # Report-only counters must not mark a source as modified, or `--check` would
        # never reach a fixed point.
        mutating = sum(v for k, v in stats.items() if k not in REPORT_ONLY_STATS)

        if mutating:
            changed_sources += 1
            print(f"[normalize] {name}: {len(records)} -> {len(new_records)} records "
                  f"(links_cleaned={stats['links_cleaned']}, "
                  f"duplicates_merged={stats['duplicates_merged']}, "
                  f"ids_rewritten={stats['ids_rewritten']}, "
                  f"sponsors_hidden={stats['sponsors_hidden']}, "
                  f"text_normalized={stats['text_normalized']}, "
                  f"authors_cleared={stats['authors_cleared']}, "
                  f"boilerplate_hidden={stats['boilerplate_hidden']})")
            if not args.check:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(new_records, f, indent=2, ensure_ascii=False)
        else:
            print(f"[normalize] {name}: already normalized ({len(records)} records)")

    verb = "would change" if args.check else "changed"
    print(f"\n[normalize] {verb} {changed_sources} source(s): "
          f"{total['links_cleaned']} links cleaned, "
          f"{total['duplicates_merged']} duplicates merged, "
          f"{total['ids_rewritten']} ids rewritten, "
          f"{total['sponsors_hidden']} sponsor links hidden, "
          f"{total['text_normalized']} text fields de-whitespaced, "
          f"{total['authors_cleared']} bogus authors cleared, "
          f"{total['boilerplate_hidden']} boilerplate records hidden.")
    if total["suspicious_titles"]:
        print(f"[normalize] note: {total['suspicious_titles']} visible records have a "
              f"suspiciously short title (possible truncation) — reported, not changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
