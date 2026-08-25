"""Tests for BaseScraper.merge_articles and _article_key (regression cover for issue H4)."""

import unittest

from helpers import StubScraper, make_article


class ArticleKeyTests(unittest.TestCase):
    def setUp(self):
        self.s = StubScraper()

    def test_prefers_link(self):
        art = make_article(link="https://a.co/x", id="zzz", title="T")
        self.assertEqual(self.s._article_key(art), "link:https://a.co/x")

    def test_falls_back_to_id_without_link(self):
        art = make_article(link="", id="zzz")
        self.assertEqual(self.s._article_key(art), "id:zzz")

    def test_falls_back_to_title_without_link_or_id(self):
        art = make_article(link="", id="", title="  Mixed Case  ")
        self.assertEqual(self.s._article_key(art), "title:mixed case")


class MergeArticlesTests(unittest.TestCase):
    def merge(self, existing, incoming):
        s = StubScraper(existing)
        count = s.merge_articles(incoming)
        return s, count

    def test_new_article_is_appended(self):
        s, count = self.merge([], [make_article()])
        self.assertEqual(count, 1)
        self.assertEqual(len(s.articles), 1)

    def test_matching_article_is_updated_not_duplicated(self):
        old = make_article(description="old")
        new = make_article(description="new")
        s, count = self.merge([old], [new])
        self.assertEqual(count, 1)
        self.assertEqual(len(s.articles), 1)
        self.assertEqual(s.articles[0].description, "new")

    # --- H4: empty scrape results must not clobber good data ---

    def test_empty_string_does_not_clobber_description(self):
        old = make_article(description="a good description")
        new = make_article(description="")
        s, _ = self.merge([old], [new])
        self.assertEqual(s.articles[0].description, "a good description")

    def test_whitespace_only_does_not_clobber_title(self):
        old = make_article(title="Real Title")
        new = make_article(title="   ")
        s, _ = self.merge([old], [new])
        self.assertEqual(s.articles[0].title, "Real Title")

    def test_none_does_not_clobber_author(self):
        old = make_article(author="Jane")
        new = make_article(author=None)
        s, _ = self.merge([old], [new])
        self.assertEqual(s.articles[0].author, "Jane")

    def test_hidden_article_is_never_auto_unhidden(self):
        old = make_article(hide=True)
        new = make_article(hide=False)
        s, _ = self.merge([old], [new])
        self.assertTrue(s.articles[0].hide)

    def test_hide_can_still_be_set_to_true(self):
        old = make_article(hide=False)
        new = make_article(hide=True)
        s, _ = self.merge([old], [new])
        self.assertTrue(s.articles[0].hide)

    # --- user_overrides must always win ---

    def test_user_override_blocks_update(self):
        old = make_article(category="Tech Industry, Jobs & Careers",
                           user_overrides=["category"])
        new = make_article(category="Cloud Infrastructure & System Reliability")
        s, _ = self.merge([old], [new])
        self.assertEqual(s.articles[0].category, "Tech Industry, Jobs & Careers")

    def test_user_override_is_field_scoped(self):
        old = make_article(category="Tech Industry, Jobs & Careers",
                           description="old",
                           user_overrides=["category"])
        new = make_article(category="Cloud Infrastructure & System Reliability",
                           description="new")
        s, _ = self.merge([old], [new])
        self.assertEqual(s.articles[0].category, "Tech Industry, Jobs & Careers")
        self.assertEqual(s.articles[0].description, "new")

    # --- ordering ---

    def test_articles_are_sorted_by_date_descending(self):
        s, _ = self.merge([], [
            make_article(link="https://a.co/1", date="2026-01-01"),
            make_article(link="https://a.co/3", date="2026-03-01"),
            make_article(link="https://a.co/2", date="2026-02-01"),
        ])
        self.assertEqual([a.date for a in s.articles],
                         ["2026-03-01", "2026-02-01", "2026-01-01"])

    def test_merge_is_idempotent(self):
        incoming = [make_article(link="https://a.co/1"), make_article(link="https://a.co/2")]
        s = StubScraper()
        s.merge_articles(incoming)
        s.merge_articles(incoming)
        self.assertEqual(len(s.articles), 2)


if __name__ == "__main__":
    unittest.main()
