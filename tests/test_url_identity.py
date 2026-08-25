"""Tests for URL cleaning, canonicalisation and id minting (issues H3, C5, D7)."""

import unittest

from helpers import StubScraper
from common.base_scraper import BaseScraper


class CleanUrlTests(unittest.TestCase):
    def setUp(self):
        self.s = StubScraper()

    def test_empty_url(self):
        self.assertEqual(self.s.clean_url(""), "")

    def test_strips_utm_params(self):
        self.assertEqual(
            self.s.clean_url("https://a.com/x?utm_source=nl&utm_medium=email"),
            "https://a.com/x",
        )

    # --- H3: the deny-list used to be backwards ---

    def test_preserves_legitimate_search_param_s(self):
        url = "https://site.com/search?s=query"
        self.assertEqual(self.s.clean_url(url), url)

    def test_strips_youtube_si_param(self):
        self.assertEqual(
            self.s.clean_url("https://youtu.be/abc?si=8pJAfud7AAortv5D"),
            "https://youtu.be/abc",
        )

    def test_strips_social_click_ids(self):
        for param in ("fbclid", "gclid", "msclkid", "igshid", "twclid"):
            self.assertEqual(
                self.s.clean_url(f"https://a.com/x?{param}=123"), "https://a.com/x",
                f"{param} survived",
            )

    def test_keeps_meaningful_params(self):
        url = "https://a.com/watch?v=dQw4w9WgXcQ&t=42"
        self.assertEqual(self.s.clean_url(url), url)

    def test_keeps_id_alongside_stripped_tracking(self):
        self.assertEqual(
            self.s.clean_url("https://a.com/x?utm_source=nl&id=5"), "https://a.com/x?id=5"
        )

    def test_is_idempotent(self):
        once = self.s.clean_url("https://a.com/x?utm_source=nl&si=1&id=5")
        self.assertEqual(self.s.clean_url(once), once)


class CanonicalLinkTests(unittest.TestCase):
    canon = staticmethod(BaseScraper.canonical_link)

    def test_empty(self):
        self.assertEqual(self.canon(""), "")

    def test_lowercases_host_only(self):
        self.assertEqual(self.canon("https://EXAMPLE.com/Post"), "https://example.com/Post")

    def test_drops_www(self):
        self.assertEqual(self.canon("https://www.a.com/x"), "https://a.com/x")

    def test_normalises_scheme(self):
        self.assertEqual(self.canon("http://a.com/x"), self.canon("https://a.com/x"))

    def test_drops_fragment_and_trailing_slash(self):
        self.assertEqual(self.canon("https://a.com/x/#top"), "https://a.com/x")

    def test_sorts_query_params(self):
        self.assertEqual(self.canon("https://a.com/x?b=2&a=1"), self.canon("https://a.com/x?a=1&b=2"))

    def test_collapses_tracking_variants(self):
        self.assertEqual(
            self.canon("https://youtu.be/abc?si=XYZ"), self.canon("https://youtu.be/abc")
        )

    def test_distinct_articles_stay_distinct(self):
        self.assertNotEqual(self.canon("https://a.com/x"), self.canon("https://a.com/y"))

    def test_is_idempotent(self):
        once = self.canon("http://WWW.A.com/x/?b=2&utm_source=n#f")
        self.assertEqual(self.canon(once), once)


class MakeArticleIdTests(unittest.TestCase):
    mk = staticmethod(BaseScraper.make_article_id)

    def test_format(self):
        self.assertRegex(self.mk("da", 304, "https://a.com/x"), r"^da-304-[0-9a-f]{6}$")

    def test_stable_across_tracking_variants(self):
        self.assertEqual(
            self.mk("da", 304, "https://youtu.be/abc?si=X"),
            self.mk("da", 304, "https://youtu.be/abc"),
        )

    def test_differs_for_different_links(self):
        self.assertNotEqual(self.mk("da", 304, "https://a.com/x"),
                            self.mk("da", 304, "https://a.com/y"))

    def test_differs_across_issues(self):
        self.assertNotEqual(self.mk("da", 304, "https://a.com/x"),
                            self.mk("da", 305, "https://a.com/x"))

    def test_position_independent(self):
        # The whole point of D7: the id must not depend on ordering or index.
        first = self.mk("da", 304, "https://a.com/x", "Title")
        again = self.mk("da", 304, "https://a.com/x", "Title")
        self.assertEqual(first, again)

    def test_falls_back_to_title_without_a_link(self):
        self.assertRegex(self.mk("fose", None, "", "Some Title"), r"^fose-x-[0-9a-f]{6}$")

    def test_title_fallback_is_whitespace_insensitive(self):
        self.assertEqual(self.mk("fose", None, "", "Some  Title"),
                         self.mk("fose", None, "", " some title "))

    def test_year_month_issue_segment(self):
        self.assertRegex(self.mk("addy", "2026-01", "https://a.com/x"),
                         r"^addy-2026-01-[0-9a-f]{6}$")


if __name__ == "__main__":
    unittest.main()
