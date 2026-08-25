"""
Data-lint tests over every data-sources/*/data.json.

These assert the invariants the pipeline already upholds, so a regression in a
scraper is caught without a network round-trip. Known-defective invariants that
are deferred to docs/DATA-DISCREPANCIES.md are covered by *ratchet* tests: they
pin the current defect count so the situation cannot silently get worse, and
they fail loudly (asking to be tightened) once the defect is fixed.
"""

import collections
import datetime
import json
import re
import unittest
from pathlib import Path

from helpers import iter_source_dirs, StubScraper

try:
    from common.constants import CATEGORIES, CONTENT_TYPES
    from common.base_scraper import BaseScraper
    from tools.normalize_data import normalize_source, REPORT_ONLY_STATS
except ImportError:  # pragma: no cover
    CATEGORIES, CONTENT_TYPES = [], []

REQUIRED_KEYS = {
    "id", "newsletter", "issue_number", "issue_title", "issue_link", "date",
    "date_str", "title", "link", "author", "description", "category",
    "is_spotlight", "type", "hide", "user_overrides", "metadata",
}

# Duplicate ids are now impossible by construction: ids are minted as
# {prefix}-{issue}-{hash6} from the canonical link (see code/tools/normalize_data.py).
KNOWN_DUPLICATE_IDS = {}
# Links may legitimately repeat across issues (two newsletters recommending the same
# article is real signal), but never twice within the same issue.
KNOWN_DUPLICATE_LINKS = {"andriy-burkov-ai": 2, "dear-architects": 2}

# Visible records whose title looks truncated (D8). Reported, never auto-hidden.
KNOWN_TRUNCATED_TITLES = 13


def load_sources():
    sources = []
    for sid, path in iter_source_dirs():
        with open(f"{path}/data.json", encoding="utf-8") as f:
            sources.append((sid, json.load(f)))
    return sources


class DataLintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load_sources()
        cls.assertTrue(cls, cls.sources, "no sources found")

    def test_every_record_has_the_full_schema(self):
        for sid, records in self.sources:
            for i, rec in enumerate(records):
                missing = REQUIRED_KEYS - set(rec)
                self.assertFalse(missing, f"{sid}[{i}] missing keys: {sorted(missing)}")

    def test_categories_are_canonical(self):
        for sid, records in self.sources:
            for i, rec in enumerate(records):
                self.assertIn(rec["category"], CATEGORIES, f"{sid}[{i}] bad category")

    def test_types_are_known(self):
        for sid, records in self.sources:
            for i, rec in enumerate(records):
                self.assertIn(rec["type"], CONTENT_TYPES, f"{sid}[{i}] bad type")

    def test_dates_are_iso_yyyy_mm_dd(self):
        for sid, records in self.sources:
            for i, rec in enumerate(records):
                try:
                    datetime.datetime.strptime(rec["date"], "%Y-%m-%d")
                except ValueError:
                    self.fail(f"{sid}[{i}] bad date {rec['date']!r}")

    def test_no_tracking_params_survive(self):
        for sid, records in self.sources:
            for i, rec in enumerate(records):
                link = rec.get("link") or ""
                for marker in ("utm_", "ml_subscriber", "li_fat_id"):
                    self.assertNotIn(marker, link, f"{sid}[{i}] tracking param {marker}")

    def test_ids_and_titles_are_non_empty(self):
        for sid, records in self.sources:
            for i, rec in enumerate(records):
                self.assertTrue(str(rec["id"]).strip(), f"{sid}[{i}] empty id")
                self.assertTrue(rec["title"].strip(), f"{sid}[{i}] empty title")

    def test_user_overrides_name_real_fields(self):
        for sid, records in self.sources:
            for i, rec in enumerate(records):
                for field_name in rec["user_overrides"]:
                    self.assertIn(field_name, REQUIRED_KEYS,
                                  f"{sid}[{i}] override names unknown field {field_name!r}")

    # --- link identity (C5 / H3 / D6 / D7) ---

    def test_ids_are_globally_unique(self):
        seen = collections.Counter()
        for _sid, records in self.sources:
            seen.update(r["id"] for r in records)
        dups = [i for i, c in seen.items() if c > 1]
        self.assertEqual(dups, [], f"duplicate article ids: {dups[:10]}")

    def test_ids_follow_the_prefix_issue_hash_format(self):
        pattern = re.compile(r"^[a-z]+-(\d+|\d{4}-\d{2}|x)-[0-9a-f]{6}$")
        for sid, records in self.sources:
            for i, rec in enumerate(records):
                self.assertRegex(rec["id"], pattern, f"{sid}[{i}] malformed id")

    def test_no_duplicate_links_within_an_issue(self):
        for sid, records in self.sources:
            seen = collections.Counter(
                (r.get("issue_number"), BaseScraper.canonical_link(r["link"]))
                for r in records if r.get("link")
            )
            dups = [k for k, c in seen.items() if c > 1]
            self.assertEqual(dups, [], f"{sid} repeats a link inside one issue: {dups[:5]}")

    def test_normalizer_is_a_fixed_point(self):
        # Committed data must already be normalized, so a rebuild never rewrites it.
        # Report-only counters describe the data without changing it, so they are
        # excluded — otherwise this test could never pass while any defect is merely
        # being tracked rather than auto-corrected.
        for sid, records in self.sources:
            _new, stats = normalize_source(sid, records)
            mutating = {k: v for k, v in stats.items() if k not in REPORT_ONLY_STATS}
            self.assertEqual(mutating, {}, f"{sid} is not normalized: {mutating}")

    def test_no_boilerplate_is_visible(self):
        # Subscribe prompts and mailto links must never render as articles (M9).
        probe = StubScraper()
        offenders = [
            (sid, r["id"], r.get("title", ""))
            for sid, records in self.sources
            for r in records
            if not r.get("hide") and probe.is_boilerplate(r.get("title", ""), r.get("link", ""))
        ]
        self.assertEqual(offenders, [], f"boilerplate rendered as articles: {offenders[:5]}")

    def test_truncated_titles_do_not_increase(self):
        # Ratchet for the 13 known truncated titles (D8). These are reported, never
        # hidden, because the underlying article is real. Tighten when titles are fixed.
        probe = StubScraper()
        count = sum(
            1
            for _sid, records in self.sources
            for r in records
            if not r.get("hide") and probe.is_suspicious_title(r.get("title", ""))
        )
        self.assertLessEqual(
            count, KNOWN_TRUNCATED_TITLES,
            f"{count} truncated titles, expected at most {KNOWN_TRUNCATED_TITLES}",
        )
        if count < KNOWN_TRUNCATED_TITLES:
            self.fail(
                f"Only {count} truncated titles remain (was {KNOWN_TRUNCATED_TITLES}). "
                f"Tighten KNOWN_TRUNCATED_TITLES to {count}."
            )

    def test_dear_architects_dates_match_mailbox_ground_truth(self):
        source_path = Path(__file__).resolve().parents[1] / "data-sources" / "dear-architects"
        ground_truth = json.loads((source_path / "issue_dates.json").read_text())
        definition = json.loads((source_path / "definition.json").read_text())
        records = json.loads((source_path / "data.json").read_text())

        issue_mismatches = [
            (issue["id"], issue["date"], ground_truth[str(issue["id"])])
            for issue in definition["parsed_issues"]["issues"]
            if ground_truth.get(str(issue["id"]))
            and issue["date"] != ground_truth[str(issue["id"])]
        ]
        article_mismatches = [
            (record["id"], record["date"], ground_truth[str(record["issue_number"])])
            for record in records
            if ground_truth.get(str(record.get("issue_number")))
            and record["date"] != ground_truth[str(record["issue_number"])]
        ]
        self.assertEqual(issue_mismatches, [])
        self.assertEqual(article_mismatches, [])

    def test_definition_trackers_are_self_consistent(self):
        root = Path(__file__).resolve().parents[1] / "data-sources"
        for definition_path in root.glob("*/definition.json"):
            definition = json.loads(definition_path.read_text())
            tracker = definition.get("parsed_issues", {})
            issues = tracker.get("issues", [])
            self.assertEqual(
                tracker.get("count"),
                len(issues),
                f"{definition_path.parent.name}: tracker count mismatch",
            )
            expected = sorted(
                issues,
                key=lambda issue: (issue.get("date", ""), str(issue.get("id", ""))),
                reverse=True,
            )
            self.assertEqual(
                issues,
                expected,
                f"{definition_path.parent.name}: issues are not newest-first",
            )
            if issues:
                self.assertEqual(
                    str(tracker.get("last_parsed_issue")),
                    str(issues[0].get("id")),
                    f"{definition_path.parent.name}: last issue mismatch",
                )
                self.assertEqual(
                    tracker.get("last_parsed_date"),
                    issues[0].get("date"),
                    f"{definition_path.parent.name}: last date mismatch",
                )

    def test_observability_masterclass_is_a_presentation_override(self):
        records = dict(self.sources)["dear-architects"]
        article = next(record for record in records if record["id"] == "da-301-d19d25")
        self.assertEqual(article["type"], "presentation")
        self.assertIn("type", article["user_overrides"])

    def test_programming_books_article_is_a_book_override(self):
        records = dict(self.sources)["my-collected-articles"]
        article = next(
            record
            for record in records
            if record["id"] == "others-2026-08-45fd3c"
        )
        self.assertEqual(article["type"], "book")
        self.assertIn("type", article["user_overrides"])

        token_records = {
            record["id"]: record
            for record in dict(self.sources)["token-by-token"]
        }
        expected_authors = {
            "tbt-13-4ab35d": "Alfonso Graziano",
            "tbt-11-f141aa": "Zohar Einy",
            "tbt-10-a66288": None,
            "tbt-10-90a706": None,
            "tbt-8-5aa759": None,
            "tbt-4-66fce5": None,
            "tbt-4-4393f7": None,
        }
        for article_id, author in expected_authors.items():
            self.assertEqual(token_records[article_id]["author"], author)
            self.assertIn("author", token_records[article_id]["user_overrides"])

    def test_cross_issue_duplicate_links_do_not_increase(self):
        # Ratchet: repeats across issues are legitimate but should not proliferate.
        for sid, records in self.sources:
            counts = collections.Counter(
                BaseScraper.canonical_link(r["link"]) for r in records if r.get("link")
            )
            dups = sum(v - 1 for v in counts.values() if v > 1)
            expected = KNOWN_DUPLICATE_LINKS.get(sid, 0)
            self.assertLessEqual(dups, expected, f"{sid} gained duplicate links")
            self.assertEqual(dups, expected,
                             f"{sid} duplicate links dropped to {dups}; tighten "
                             f"KNOWN_DUPLICATE_LINKS in this test")


if __name__ == "__main__":
    unittest.main()
