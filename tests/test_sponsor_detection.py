"""Tests for sponsor/advertising link detection (issue H13)."""

import json
import unittest
from types import SimpleNamespace

from helpers import StubScraper, iter_source_dirs
from common.constants import SPONSOR_DOMAINS, SPONSOR_WHITELIST_TERMS

KEPT_SPONSOR = "certification.qconferences.com"
KEPT_HONEYCOMB_IDS = {"da-301-d19d25", "da-300-3fb81f", "da-254-6afc01"}


class IsSponsorLinkTests(unittest.TestCase):
    def setUp(self):
        self.s = StubScraper()

    def test_ad_network_domains_are_sponsors(self):
        for url in ("https://fnf.dev/41ZL6Rc", "https://fandf.co/3TqhbPK",
                    "http://fnf.dev/3SXUJK8", "https://go.rbrk.co/16wh7v",
                    "https://theaiplatform.app"):
            self.assertTrue(self.s.is_sponsor_link(url, "Anything"), url)

    def test_link_shorteners_are_sponsors(self):
        for url in ("https://bit.ly/4aCn0xZ", "https://tinyurl.com/abc", "https://lnkd.in/abc"):
            self.assertTrue(self.s.is_sponsor_link(url, "Anything"), url)

    def test_whitelisted_sponsor_is_kept(self):
        self.assertFalse(
            self.s.is_sponsor_link(f"https://{KEPT_SPONSOR}/architecture", "Architecture cohort")
        )

    def test_whitelist_matches_url_not_just_title(self):
        # The carve-out is expressed as a domain, so an empty title must still match.
        self.assertFalse(self.s.is_sponsor_link(f"https://{KEPT_SPONSOR}/", ""))

    def test_honeycomb_observability_placements_are_kept(self):
        self.assertFalse(
            self.s.is_sponsor_link(
                "https://fandf.co/3TqhbPK",
                "The Observability Engineering Masterclass with Liz Fong-Jones",
            )
        )
        self.assertFalse(
            self.s.is_sponsor_link(
                "https://bit.ly/example",
                "Mark your calendar: the Observability Day is here!",
            )
        )

    def test_ordinary_articles_are_not_sponsors(self):
        for url in ("https://martinfowler.com/articles/x.html",
                    "https://youtu.be/abc", "https://infoq.com/articles/y"):
            self.assertFalse(self.s.is_sponsor_link(url, "Real article"), url)

    def test_empty_url_is_not_a_sponsor(self):
        self.assertFalse(self.s.is_sponsor_link("", ""))

    def test_explicit_whitelist_argument_overrides_default(self):
        self.assertFalse(self.s.is_sponsor_link("https://bit.ly/x", "Keep me",
                                                whitelist_terms=["bit.ly"]))

    def test_empty_whitelist_argument_is_respected(self):
        # `whitelist_terms=[]` must NOT fall back to the defaults (the difference
        # between `whitelist_terms or DEFAULT` and `if whitelist_terms is not None`).
        # Use a source that declares the whitelisted domain as its own sponsor.
        scoped = StubScraper()
        scoped.definition = SimpleNamespace(sponsor_domains=[KEPT_SPONSOR])
        url = f"https://{KEPT_SPONSOR}/"
        self.assertFalse(scoped.is_sponsor_link(url, ""), "default whitelist should spare it")
        self.assertTrue(scoped.is_sponsor_link(url, "", whitelist_terms=[]),
                        "an explicit empty whitelist must not fall back to the defaults")

    def test_whitelist_constant_is_not_empty(self):
        self.assertTrue(SPONSOR_WHITELIST_TERMS)
        self.assertTrue(SPONSOR_DOMAINS)


class StoredDataSponsorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = []
        for sid, path in iter_source_dirs():
            with open(f"{path}/data.json", encoding="utf-8") as f:
                for rec in json.load(f):
                    cls.records.append((sid, rec))

    def test_no_visible_sponsor_links_remain(self):
        probe = StubScraper()
        leaked = [
            (sid, rec["id"], rec["link"])
            for sid, rec in self.records
            if not rec["hide"] and probe.is_sponsor_link(rec.get("link") or "", rec.get("title") or "")
        ]
        self.assertEqual(leaked, [], f"visible sponsor links: {leaked[:5]}")

    def test_the_whitelisted_sponsor_is_still_visible(self):
        kept = [rec for _sid, rec in self.records if KEPT_SPONSOR in (rec.get("link") or "")]
        self.assertTrue(kept, "expected the whitelisted sponsor records to exist")
        for rec in kept:
            self.assertFalse(rec["hide"], f"{rec['id']} was hidden but should be kept")

    def test_honeycomb_records_are_restored(self):
        kept = {
            rec["id"]: rec
            for _sid, rec in self.records
            if rec["id"] in KEPT_HONEYCOMB_IDS
        }
        self.assertEqual(set(kept), KEPT_HONEYCOMB_IDS)
        for rec in kept.values():
            self.assertFalse(rec["hide"], f"{rec['id']} should be visible")

    def test_no_leaked_html_whitespace_in_text_fields(self):
        for sid, rec in self.records:
            for field in ("title", "description", "author", "issue_title"):
                value = rec.get(field)
                if isinstance(value, str):
                    self.assertEqual(value, " ".join(value.split()),
                                     f"{sid}/{rec['id']} has raw whitespace in {field}")


if __name__ == "__main__":
    unittest.main()
