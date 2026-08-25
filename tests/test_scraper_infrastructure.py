"""Offline guards for H9, H12, M4 and M5."""

import json
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta
from unittest import mock

from helpers import CODE_DIR, REPO_ROOT, StubScraper
from common.base_scraper import BaseScraper
from common.mailerlite_scraper import MailerLiteScraper
from common.models import ParsedIssuesTrack, SourceDefinition
from builders.builder_core import (
    apply_archive_retention,
    escape_markdown_text,
    escape_markdown_url,
)

if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)
import build


def load_source_module(source_id):
    path = os.path.join(REPO_ROOT, "data-sources", source_id, "scraper.py")
    spec = importlib.util.spec_from_file_location(
        f"test_source_{source_id.replace('-', '_')}", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def definition(**overrides):
    values = dict(
        source_id="test",
        name="Test",
        author="Test",
        official_site="https://example.com",
        archive_url="https://example.com/archive",
        parsed_issues=ParsedIssuesTrack(),
        default_header="### Test",
    )
    values.update(overrides)
    return SourceDefinition(**values)


class PublicationDateTests(unittest.TestCase):
    def test_parses_api_date_shapes(self):
        cases = {
            "2026-08-22T08:30:00Z": date(2026, 8, 22),
            "2026-08-22 08:30:00": date(2026, 8, 22),
            "22 August 2026": date(2026, 8, 22),
            "Sat, 22 Aug 2026 08:30:00 +0000": date(2026, 8, 22),
            1787387400: date(2026, 8, 22),
            1787387400000: date(2026, 8, 22),
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(
                    MailerLiteScraper.parse_publication_date(value).date(),
                    expected,
                )

    def test_reads_mailerlite_date_fields_without_weekly_arithmetic(self):
        for key in ("date", "sent_at", "sentAt", "send_at", "published_at", "created_at"):
            with self.subTest(key=key):
                parsed = MailerLiteScraper.publication_date_from_mail(
                    {key: "2026-08-22T08:30:00Z"}
                )
                self.assertEqual(parsed.date(), date(2026, 8, 22))

    def test_reads_page_metadata_with_stdlib_parser(self):
        samples = [
            '<meta property="article:published_time" content="2026-08-22T08:30:00Z">',
            '<time datetime="2026-08-22">22 August 2026</time>',
            (
                '<script type="application/ld+json">'
                '{"@type":"Article","datePublished":"2026-08-22T08:30:00Z"}'
                "</script>"
            ),
        ]
        for html in samples:
            with self.subTest(html=html):
                parsed = MailerLiteScraper.publication_date_from_html(html)
                self.assertEqual(parsed.date(), date(2026, 8, 22))

    def test_missing_metadata_is_not_guessed(self):
        self.assertIsNone(MailerLiteScraper.publication_date_from_mail({"subject": "#1"}))
        self.assertIsNone(MailerLiteScraper.publication_date_from_html("<html></html>"))

    def test_ingest_refuses_an_arithmetic_fallback(self):
        scraper = MailerLiteScraper.__new__(MailerLiteScraper)
        scraper.log_name = "Test"
        scraper.fetch_html = lambda _url: "<html><h1>No date</h1></html>"
        with self.assertRaisesRegex(ValueError, "refusing arithmetic fallback"):
            scraper.ingest_issue(1, "Issue 1", "https://example.com/1")

    def test_duplicate_issue_numbers_are_reported_not_silently_dropped(self):
        issues = [
            {"num": 260, "url": "https://example.com/a"},
            {"num": 260, "url": "https://example.com/b"},
        ]
        with self.assertRaisesRegex(ValueError, "Duplicate issue numbers"):
            MailerLiteScraper._deduplicate_discovered(issues)

    def test_known_historical_duplicate_does_not_block_new_issue(self):
        issues = [
            {"num": 305, "url": "https://example.com/305"},
            {"num": 260, "url": "https://example.com/known-260"},
            {"num": 260, "url": "https://example.com/ambiguous-260"},
        ]
        with redirect_stdout(io.StringIO()):
            deduped = MailerLiteScraper._deduplicate_discovered(
                issues, {"260": "https://example.com/known-260"}
            )
        self.assertEqual(
            {(issue["num"], issue["url"]) for issue in deduped},
            {
                (305, "https://example.com/305"),
                (260, "https://example.com/known-260"),
            },
        )


class CrawlPolicyTests(unittest.TestCase):
    def setUp(self):
        self.scraper = BaseScraper.__new__(BaseScraper)
        self.scraper._robots = {}
        self.scraper._last_request_at = 0.0

    def test_honest_user_agent(self):
        self.assertIn("news-agg", BaseScraper.USER_AGENT)
        self.assertNotIn("Mozilla", BaseScraper.USER_AGENT)

    def test_robots_disallow_prevents_network_request(self):
        parser = mock.Mock()
        parser.can_fetch.return_value = False
        self.scraper._robots["https://example.com"] = parser
        with mock.patch("urllib.request.urlopen") as urlopen:
            with self.assertRaisesRegex(PermissionError, "robots.txt disallows"):
                self.scraper.fetch_url("https://example.com/private")
            urlopen.assert_not_called()

    def test_request_uses_shared_user_agent(self):
        parser = mock.Mock()
        parser.can_fetch.return_value = True
        self.scraper._robots["https://example.com"] = parser
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"ok"
        with mock.patch("urllib.request.urlopen", return_value=response) as urlopen:
            self.assertEqual(self.scraper.fetch_url("https://example.com/a"), b"ok")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("User-agent"), BaseScraper.USER_AGENT)


class RefreshModeTests(unittest.TestCase):
    def test_definition_round_trip_preserves_refresh_policy(self):
        original = definition(
            short_name="Short",
            static=True,
            refresh_enabled=False,
            refresh_disabled_reason="curated",
        )
        restored = SourceDefinition.from_dict(original.to_dict())
        self.assertTrue(restored.static)
        self.assertEqual(restored.short_name, "Short")
        self.assertFalse(restored.refresh_enabled)
        self.assertEqual(restored.refresh_disabled_reason, "curated")

    def test_static_source_is_skipped_without_starting_a_subprocess(self):
        with mock.patch("subprocess.run") as run:
            self.assertTrue(build.refresh_sources("future-software-development"))
            run.assert_not_called()

    def test_linkedin_source_is_skipped_without_starting_a_subprocess(self):
        with mock.patch("subprocess.run") as run:
            self.assertTrue(build.refresh_sources("andriy-burkov-ai"))
            run.assert_not_called()


class ConcreteSourceAdapterTests(unittest.TestCase):
    def test_pragmatic_engineer_parses_a_valid_post(self):
        module = load_source_module("pragmatic-engineer")
        scraper = module.PragmaticEngineerScraper()
        article = scraper.parse_post_payload({
            "title": "A valid post",
            "canonical_url": "https://newsletter.pragmaticengineer.com/p/a-valid-post",
            "post_date": "2026-08-20T12:00:00Z",
            "slug": "a-valid-post",
            "audience": "everyone",
        })
        self.assertEqual(article.metadata["slug"], "a-valid-post")
        self.assertEqual(article.date, "2026-08-20")

    def test_pragmatic_engineer_rejects_invalid_dates(self):
        module = load_source_module("pragmatic-engineer")
        scraper = module.PragmaticEngineerScraper()
        with self.assertRaisesRegex(ValueError, "invalid post_date"):
            scraper.parse_post_payload({
                "title": "Bad date",
                "canonical_url": "https://example.com/bad-date",
                "post_date": "not-a-date",
                "slug": "bad-date",
            })

    def test_pragmatic_engineer_propagates_api_failure(self):
        module = load_source_module("pragmatic-engineer")
        scraper = module.PragmaticEngineerScraper()
        scraper.fetch_json = mock.Mock(side_effect=OSError("offline"))
        with self.assertRaisesRegex(OSError, "offline"):
            scraper.discover_and_ingest_posts()

    def test_addy_fails_when_every_listing_request_fails(self):
        module = load_source_module("addy-osmani")
        scraper = module.AddyOsmaniScraper()
        scraper.fetch_page_html = mock.Mock(side_effect=OSError("offline"))
        with redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "every listing-page request failed"):
                scraper.extract_issues()

    def test_mailerlite_adapters_are_concrete(self):
        dear = load_source_module("dear-architects").DearArchitectsScraper()
        token = load_source_module("token-by-token").TokenByTokenScraper()
        self.assertEqual(dear.parse_subject("#305 - New issue")[0], 305)
        self.assertEqual(token.parse_subject("New issue - #20")[0], 20)
        self.assertTrue(dear.api_endpoint)
        self.assertTrue(token.api_endpoint)
        self.assertFalse(token.extract_article_authors)

    def test_mailerlite_adapter_parses_html_fixture_when_bs4_is_available(self):
        try:
            import bs4  # noqa: F401
        except ImportError:
            self.skipTest("beautifulsoup4 is unavailable in this environment")
        dear = load_source_module("dear-architects").DearArchitectsScraper()
        articles = dear.parse_issue_html(
            '<h2><a href="https://example.com/post">A fixture article</a></h2>',
            305,
            "Issue 305",
            "https://preview.mailerlite.io/305",
            "2026-08-22",
            "22 August 2026",
        )
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "A fixture article")

    def test_collected_articles_adapter_imports_without_bs4_at_module_load(self):
        module = load_source_module("my-collected-articles")
        self.assertTrue(hasattr(module, "MyCollectedArticlesScraper"))

    def test_collected_articles_metadata_parser_uses_stdlib(self):
        module = load_source_module("my-collected-articles")
        scraper = module.MyCollectedArticlesScraper()
        scraper.fetch_html = mock.Mock(return_value="""
            <html>
              <head>
                <title>Fallback title</title>
                <meta property="og:title" content="Article &amp; Title">
                <meta property="og:description" content="Description">
                <meta name="author" content="Ada Lovelace">
                <meta property="article:published_time" content="2026-08-25T10:00:00Z">
              </head>
            </html>
        """)
        metadata = scraper.extract_web_metadata("https://example.com/article")
        self.assertEqual(metadata["title"], "Article & Title")
        self.assertEqual(metadata["description"], "Description")
        self.assertEqual(metadata["author"], "Ada Lovelace")
        self.assertEqual(metadata["date"], "2026-08-25")

    def test_collected_articles_ignores_inbox_placeholder_as_title(self):
        module = load_source_module("my-collected-articles")
        scraper = module.MyCollectedArticlesScraper()
        scraper.extract_web_metadata = mock.Mock(return_value={
            "title": "Home | Quantum for Programmers",
            "description": "",
            "author": None,
            "date": "2026-08-25",
            "date_str": "25 August 2026",
        })
        with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8") as inbox:
            inbox.write(
                "## 📥 Articles to Process\n\n"
                "*(Drop new articles here)*\n"
                "https://example.com/quantum-programming\n\n"
                "## ✅ Processed Articles\n"
            )
            inbox.flush()
            articles = scraper.parse_inbox_file(inbox.name)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "Quantum for Programmers")


class BuilderSafetyTests(unittest.TestCase):
    def test_days_must_be_positive(self):
        self.assertEqual(build.positive_days("1"), 1)
        with self.assertRaises(Exception):
            build.positive_days("0")
        with self.assertRaises(Exception):
            build.positive_days("-1")

    def test_unknown_source_exits_before_building(self):
        with mock.patch.object(sys, "argv", ["build.py", "--source", "missing", "--latest"]):
            with self.assertRaises(SystemExit) as raised:
                build.main()
        self.assertEqual(raised.exception.code, 2)

    def test_failed_refresh_aborts_before_builders(self):
        with mock.patch.object(sys, "argv", ["build.py", "--refresh"]):
            with mock.patch.object(build, "refresh_sources", return_value=False):
                with mock.patch.object(build, "build_latest") as latest:
                    self.assertEqual(build.main(), 1)
                    latest.assert_not_called()

    def test_dashboard_json_errors_propagate(self):
        from builders import build_news_page as module

        with mock.patch.object(
            module.json,
            "load",
            side_effect=json.JSONDecodeError("bad", "x", 0),
        ):
            with self.assertRaises(json.JSONDecodeError):
                module.build_news_page()

    def test_archive_retention_is_clock_relative(self):
        old = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        less_old = (datetime.now() - timedelta(days=350)).strftime("%Y-%m-%d")
        articles = [{"date": old}, {"date": less_old}]
        self.assertEqual(
            apply_archive_retention(articles, {"archive_retention_days": 90}),
            [],
        )

    def test_markdown_escaping(self):
        self.assertEqual(
            escape_markdown_text(r"A *title* [x] $5"),
            r"A \*title\* \[x\] \$5",
        )
        self.assertEqual(
            escape_markdown_url("https://example.com/a (b)"),
            "https://example.com/a%20%28b%29",
        )

    def test_dashboard_timeframe_uses_clock(self):
        template = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template, encoding="utf-8") as stream:
            source = stream.read()
        self.assertIn("const cutoff = now -", source)
        self.assertNotIn("maxTimestamp -", source)

    def test_dashboard_filters_support_multiple_values(self):
        template = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template, encoding="utf-8") as stream:
            source = stream.read()
        self.assertIn("function getSelectedFilterValues(filter)", source)
        self.assertIn("function matchesSelectedFilters(article, sources, types, categories)", source)
        self.assertIn("const matchesFilters = matchesSelectedFilters(", source)
        self.assertIn("container.classList.toggle('scrollable', options.length > 10)", source)
        self.assertIn("width: 320px;", source)
        self.assertIn("#typeFilter .multi-filter-menu", source)
        self.assertIn("width: 260px;", source)
        self.assertIn('<label class="filter-label">Categories</label>', source)
        self.assertIn('aria-label="Sort by category">Category', source)
        self.assertIn('aria-label="Sort by article title">Article', source)
        self.assertIn("min-width: 230px;", source)
        self.assertIn("function compareArticlesForSort(a, b, column, direction)", source)
        self.assertIn("String(a[column] ?? '').trim()", source)
        self.assertIn(".sort((a, b) => a.label.localeCompare(b.label))", source)
        self.assertIn("sourceDesc.querySelectorAll('li[data-source]')", source)
        self.assertIn("categoryDesc.querySelectorAll('li[data-cat]')", source)
        self.assertEqual(source.count('data-filter-action="all"'), 3)
        self.assertEqual(source.count('data-filter-action="clear"'), 3)

    def test_dashboard_uses_definition_short_names_for_table_badges(self):
        expected = {
            "addy-osmani": "Addy Osmani",
            "andriy-burkov-ai": "Burkov AI",
            "dear-architects": "Dear Architects",
            "future-software-development": "Thoughtworks FOSE",
            "my-collected-articles": "On My Radar",
            "pragmatic-engineer": "Pragmatic Eng.",
            "token-by-token": "Token by Token",
        }
        for source_id, short_name in expected.items():
            path = os.path.join(REPO_ROOT, "data-sources", source_id, "definition.json")
            with open(path, encoding="utf-8") as stream:
                self.assertEqual(json.load(stream)["short_name"], short_name)

        template = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template, encoding="utf-8") as stream:
            source = stream.read()
        self.assertIn("const sourceLabel = article.source_short_name || article.newsletter", source)
        self.assertIn("badgeClasses[article.source_id]", source)
        self.assertIn(
            '<link rel="icon" type="image/svg+xml" href="{{NEWS_ICON_DATA_URI}}">',
            source,
        )
        self.assertIn(
            '<img class="brand-icon" src="{{NEWS_ICON_DATA_URI}}" alt="">',
            source,
        )

    def test_generated_dashboard_embeds_icon(self):
        build.build_news_page()
        output = os.path.join(REPO_ROOT, "news.html")
        with open(output, encoding="utf-8") as stream:
            html = stream.read()
        self.assertNotIn('href="news-icon.svg"', html)
        self.assertNotIn('src="news-icon.svg"', html)
        self.assertEqual(html.count("data:image/svg+xml;base64,"), 2)

    def test_dashboard_explains_and_exports_cross_source_attribution(self):
        template = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template, encoding="utf-8") as stream:
            source = stream.read()
        self.assertIn("function additionalSourceNames(article)", source)
        self.assertIn("new Set([a.newsletter, ...additionalSourceNames(a)])", source)
        self.assertIn(">Also in ${alsoInNames.length}</span>", source)
        self.assertIn("function showCrossSourceTooltip(marker)", source)
        self.assertIn("}, 100);", source)
        self.assertIn("alsoInMarker.addEventListener('focus'", source)
        self.assertIn("function updateResultsCount(count)", source)
        self.assertIn("function updateSelectionCount(count)", source)
        self.assertIn('class="cat-count results-count-badge"', source)
        self.assertIn('class="cat-count selection-count-badge"', source)
        self.assertIn("justify-content: space-between;", source)
        self.assertNotIn("? Export Selection", source)
        self.assertIn("Export Current View", source)
        self.assertIn(".export-action svg", source)
        self.assertIn("flex: 0 0 auto;", source)
        self.assertGreaterEqual(source.count("Also in:"), 3)

    def test_dashboard_multi_filters_overlay_and_close(self):
        template = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template, encoding="utf-8") as stream:
            source = stream.read()
        self.assertIn(".controls-panel {\n      position: relative;\n      z-index: 10;", source)
        self.assertIn(".multi-filter-menu {\n      position: absolute;", source)
        self.assertIn("function closeMultiFilters(exceptFilter)", source)
        self.assertIn("if (!event.target.closest('.multi-filter')) closeMultiFilters();", source)
        self.assertIn("if (filter.open) closeMultiFilters(filter);", source)

    def test_spotlight_requires_a_supported_source(self):
        template = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template, encoding="utf-8") as stream:
            source = stream.read()
        self.assertIn("const spotlightSources = new Set(['Dear Architects', 'Token by Token'])", source)
        self.assertIn("function hasSpotlightSource(selectedSources)", source)
        self.assertIn("spotlightToggle.disabled = !available", source)
        self.assertIn("if (!available) spotlightToggle.checked = false", source)

    def test_static_source_does_not_emit_scraping_staleness_warning(self):
        from builders import build_latest as module

        with mock.patch.object(module, "warn_if_stale") as warn:
            with mock.patch.object(module, "write_output"):
                module.build_single_latest("future-software-development")
        warn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
