"""
Guards for the content-quality and tracker-consistency fixes (M9, M2, H10, H8).
"""

import datetime
import unittest

from helpers import StubScraper
from common.models import SourceDefinition, ParsedIssuesTrack
from common.constants import SPONSOR_DOMAINS


def make_definition(**overrides) -> SourceDefinition:
    defaults = dict(
        source_id="s", name="S", author="A", official_site="", archive_url="",
        parsed_issues=ParsedIssuesTrack(), default_header="### S",
    )
    defaults.update(overrides)
    return SourceDefinition(**defaults)

from builders.builder_core import apply_time_window, staleness_days


class BoilerplateTests(unittest.TestCase):
    def setUp(self):
        self.s = StubScraper()

    def test_denylisted_titles_are_boilerplate(self):
        for title in [
            "Subscribe to receive an email when this happens",
            "Read more",
            "View in browser",
            "Until next week!",
        ]:
            self.assertTrue(self.s.is_boilerplate(title, "https://example.com"), title)

    def test_matching_ignores_case_whitespace_and_trailing_punctuation(self):
        self.assertTrue(self.s.is_boilerplate("  SUBSCRIBE   NOW  ...", "https://x.com"))

    def test_non_article_schemes_are_boilerplate(self):
        for link in ["mailto:hello@truepositive.ca", "tel:+15551234", "javascript:void(0)"]:
            self.assertTrue(self.s.is_boilerplate("A perfectly fine title", link), link)

    def test_empty_title_is_boilerplate(self):
        self.assertTrue(self.s.is_boilerplate("   ", "https://example.com"))

    def test_real_articles_are_not_boilerplate(self):
        for title in [
            "GLM-5.2",                       # short but real
            "Kimi K3",
            "Reddit",
            "Why microservices fail at scale",
            "Subscribe pricing models compared",  # contains a denylist word, not equal to it
        ]:
            self.assertFalse(self.s.is_boilerplate(title, "https://example.com"), title)

    def test_short_titles_are_suspicious_but_never_boilerplate(self):
        # A truncated title still points at a real article, so it must not be hidden.
        self.assertTrue(self.s.is_suspicious_title("Flint"))
        self.assertFalse(self.s.is_boilerplate("Flint", "https://example.com"))

    def test_long_titles_are_not_suspicious(self):
        self.assertFalse(self.s.is_suspicious_title("Why microservices fail at scale"))


class SponsorDomainScopeTests(unittest.TestCase):
    def test_source_list_extends_rather_than_shadows_the_global_list(self):
        # A stale one-entry per-source list used to replace the global list wholesale,
        # silently re-enabling every globally-known ad domain.
        defn = make_definition(sponsor_domains=["fandf.co"])
        s = StubScraper(definition=defn)
        self.assertTrue(s.is_sponsor_link("https://fandf.co/x"))
        self.assertTrue(s.is_sponsor_link("https://fnf.dev/x"), "global domain must still apply")

    def test_source_specific_domain_is_honoured(self):
        defn = make_definition(sponsor_domains=["only-here.example"])
        s = StubScraper(definition=defn)
        self.assertTrue(s.is_sponsor_link("https://only-here.example/x"))

    def test_global_domains_apply_without_a_definition(self):
        s = StubScraper()
        self.assertTrue(s.is_sponsor_link(f"https://{SPONSOR_DOMAINS[0]}/x"))


class SponsorPrecedenceTests(unittest.TestCase):
    """H10: `A or B and C` parsed as `A or (B and C)`, dropping real articles."""

    @staticmethod
    def _decide(line, link, title, whitelist=()):
        s = StubScraper()
        marked = s.has_sponsor_marker(line)
        whitelisted = any(t.lower() in f"{link} {title}".lower() for t in whitelist)
        return (marked and not whitelisted) or s.is_sponsor_link(link, title)

    def test_article_merely_discussing_sponsorship_is_kept(self):
        self.assertFalse(self._decide(
            "How open source sponsorship actually works",
            "https://realblog.example/sponsorship", "How open source sponsorship works",
        ))

    def test_explicitly_marked_sponsor_is_dropped(self):
        self.assertTrue(self._decide(
            "[Sponsored] Try our observability platform",
            "https://vendor.example/x", "Try our platform",
        ))

    def test_ad_domain_is_dropped_even_without_a_marker(self):
        self.assertTrue(self._decide(
            "A totally normal looking headline", "https://fnf.dev/abc", "Normal headline",
        ))

    def test_whitelist_rescues_a_marked_sponsor(self):
        self.assertFalse(self._decide(
            "[Sponsored] Architecture cohort",
            "https://certification.qconferences.com/architecture", "Architecture cohort",
            whitelist=("qconferences.com",),
        ))

    def test_recognised_marker_labels(self):
        s = StubScraper()
        for line in [
            "[Sponsored] Try our platform",
            "[sponsor] Try our platform",
            "(Sponsored) Try our platform",
            "Sponsored: Try our platform",
            "Sponsored by Honeycomb",
            "Presented by Atlassian",
            "In partnership with Postman",
            "Paid promotion",
        ]:
            self.assertTrue(s.has_sponsor_marker(line), line)

    def test_prose_about_sponsorship_is_not_a_marker(self):
        s = StubScraper()
        for line in [
            "How open source sponsorship actually works",
            "We lost our sponsor and survived",
            "Sponsorship models for maintainers",
        ]:
            self.assertFalse(s.has_sponsor_marker(line), line)


class ParsedIssueTrackerTests(unittest.TestCase):
    """M2: the four tracker fields must always agree."""

    def _scraper(self):
        return StubScraper(definition=make_definition())

    @staticmethod
    def _issue(i, date):
        return {"id": str(i), "date": date, "date_str": date, "title": f"Issue {i}",
                "url": f"https://example.com/{i}", "quotes": []}

    def test_count_matches_issue_list_length(self):
        s = self._scraper()
        s.sync_parsed_issues([self._issue(1, "2026-01-01"), self._issue(2, "2026-01-08")])
        track = s.definition.parsed_issues
        self.assertEqual(track.count, 2)
        self.assertEqual(len(track.issues), 2)

    def test_last_parsed_fields_describe_the_newest_issue(self):
        s = self._scraper()
        s.sync_parsed_issues([
            self._issue(1, "2026-01-01"),
            self._issue(3, "2026-01-15"),
            self._issue(2, "2026-01-08"),
        ])
        track = s.definition.parsed_issues
        self.assertEqual(track.last_parsed_issue, "3")
        self.assertEqual(track.last_parsed_date, "2026-01-15")
        self.assertEqual([i.id for i in track.issues], ["3", "2", "1"])

    def test_empty_input_clears_the_tracker_consistently(self):
        s = self._scraper()
        s.sync_parsed_issues([])
        track = s.definition.parsed_issues
        self.assertEqual((track.count, track.issues, track.last_parsed_issue), (0, [], ""))

    def test_no_definition_is_a_safe_noop(self):
        StubScraper().sync_parsed_issues([self._issue(1, "2026-01-01")])


class TimeWindowTests(unittest.TestCase):
    """H8: the window must be clock-relative, not data-relative."""

    @staticmethod
    def _art(days_ago):
        d = datetime.datetime.now() - datetime.timedelta(days=days_ago)
        return {"date": d.strftime("%Y-%m-%d")}

    def test_stale_feed_empties_instead_of_freezing(self):
        # Every article is ~2 years old. A data-relative anchor would still show them.
        stale = [self._art(700), self._art(710), self._art(720)]
        self.assertEqual(apply_time_window(stale, 90), [])

    def test_recent_articles_are_kept(self):
        fresh = [self._art(1), self._art(30), self._art(200)]
        self.assertEqual(len(apply_time_window(fresh, 90)), 2)

    def test_future_dated_events_are_kept(self):
        self.assertEqual(len(apply_time_window([self._art(-120)], 90)), 1)

    def test_empty_input_is_returned_unchanged(self):
        self.assertEqual(apply_time_window([], 90), [])

    def test_staleness_ignores_future_events(self):
        # A conference 100 days out must not mask a feed that stopped 60 days ago.
        self.assertEqual(staleness_days([self._art(-100), self._art(60)]), 60)

    def test_staleness_is_none_without_usable_dates(self):
        self.assertIsNone(staleness_days([{"date": "not-a-date"}, {}]))


if __name__ == "__main__":
    unittest.main()
