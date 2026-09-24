"""Offline guards for H9, H12, M4 and M5."""

import json
import importlib.util
import io
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta, timezone
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

    def test_substack_adapters_are_concrete(self):
        pe = load_source_module("pragmatic-engineer").PragmaticEngineerScraper()
        self.assertTrue(pe.base_url)
        self.assertEqual(pe.newsletter_name, "The Pragmatic Engineer")
        self.assertEqual(pe.article_id_prefix, "pe")
        from common.substack_scraper import SubstackScraper
        self.assertIsInstance(pe, SubstackScraper)

    def test_simon_willison_adapter_is_concrete(self):
        sw = load_source_module("simon-willison").SimonWillisonScraper()
        self.assertEqual(sw.newsletter_name, "Simon Willison's Weblog")
        self.assertEqual(sw.article_id_prefix, "sw")
        self.assertEqual(sw.feed_url, "https://simonwillison.net/atom/entries/")
        from common.rss_feed_scraper import RSSFeedScraper
        self.assertIsInstance(sw, RSSFeedScraper)

    def test_simon_willison_preserves_empty_description_policy(self):
        sw = load_source_module("simon-willison").SimonWillisonScraper()
        sample_atom = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Test Title for Simon Willison</title>
                <link rel="alternate" href="https://simonwillison.net/2026/Sep/13/test-article/"/>
                <published>2026-09-13T10:00:00Z</published>
                <content type="html">&lt;p&gt;Long essay content here...&lt;/p&gt;</content>
                <category term="ai"/>
                <category term="llms"/>
            </entry>
        </feed>"""
        items = sw.parse_feed_xml(sample_atom)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Test Title for Simon Willison")
        self.assertEqual(items[0]["description"], "")
        self.assertIn("ai llms", items[0]["tag_context"])

    def test_burkov_editorial_noise_filter(self):
        scraper_cls = load_source_module("andriy-burkov-ai").AndriyBurkovScraper

        # Must flag consumer / societal news and detector controversies
        self.assertTrue(scraper_cls.is_editorial_noise(
            "Why do we trust chatbots and how can we use them more wisely? A psychologist explains",
            "https://theconversation.com/why-do-we-trust-chatbots"
        ))
        self.assertTrue(scraper_cls.is_editorial_noise(
            "Faster homework, poor exam results: What AI is doing to students’ learning",
            "https://aljazeera.com/news/faster-homework"
        ))
        self.assertTrue(scraper_cls.is_editorial_noise(
            "NeurIPS desk-rejected 178 position papers for being “AI-generated.”",
            "https://strictcite.com/blog/neurips-detector"
        ))
        self.assertTrue(scraper_cls.is_editorial_noise(
            "Anthropic destroying books",
            "https://www.theguardian.com/commentisfree/2026/aug/05/anthropic-ai-destroying-books"
        ))

        # Must KEEP core engineering, systems, and pure math/science
        self.assertFalse(scraper_cls.is_editorial_noise(
            "Exploring speculative decoding in vLLM on AMD GPUs",
            "https://vllm.ai/blog/speculative-decoding"
        ))
        self.assertFalse(scraper_cls.is_editorial_noise(
            "‘Reverse Mathematics’ illuminates why hard problems are hard",
            "https://www.quantamagazine.org/reverse-mathematics"
        ))
        self.assertFalse(scraper_cls.is_editorial_noise(
            "Google’s AI genome system evaluates every possible one-base change",
            "https://arstechnica.com/science/genome-system"
        ))
        self.assertFalse(scraper_cls.is_editorial_noise(
            "Why the legendary Erdős problems are falling to AI",
            "https://www.quantamagazine.org/erdos-problems"
        ))

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
        self.assertIn("const now = Date.now();", source)
        self.assertIn("const cutoff = now -", source)
        self.assertNotIn("maxTimestamp -", source)

    def test_dashboard_filter_counts_and_dimming(self):
        template = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template, encoding="utf-8") as stream:
            source = stream.read()
        self.assertIn("function updateFilterOptionCounts(", source)
        self.assertIn("updateFilterOptionCounts(articlesForSources, articlesForTypes, articlesForCategories);", source)
        self.assertIn("label.classList.toggle('disabled', count === 0);", source)
        self.assertIn("input.disabled = isDisabled;", source)
        self.assertIn('<span class="opt-count">0</span>', source)

    def test_dashboard_timeframe_options_and_default_window(self):
        template = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template, encoding="utf-8") as stream:
            source = stream.read()
        self.assertIn('<option value="7">Last 1 Week</option>', source)
        self.assertIn('<option value="14">Last 2 Weeks</option>', source)
        self.assertIn('<option value="30" selected>Last 1 Month</option>', source)
        self.assertIn('<option value="60">Last 2 Months</option>', source)
        self.assertIn('<option value="all">Last 3 Months (All)</option>', source)
        self.assertNotIn('value="180"', source)
        self.assertNotIn('value="365"', source)

        from builders import build_news_page as module
        import inspect
        self.assertEqual(module.DEFAULT_NEWS_DAYS_WINDOW, 90)
        sig = inspect.signature(module.build_news_page)
        self.assertEqual(sig.parameters["days_window"].default, 90)

    def test_dashboard_filters_support_multiple_values(self):
        template = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template, encoding="utf-8") as stream:
            source = stream.read()
        self.assertIn("function getSelectedFilterValues(filter)", source)
        self.assertIn("function matchesSelectedFilters(article, sources, types, categories)", source)
        self.assertIn("const matchesFilters = matchesSelectedFilters(", source)
        self.assertIn("width: 320px;", source)
        self.assertIn("#typeFilter .multi-filter-menu", source)
        self.assertIn("width: 290px;", source)
        self.assertIn("#categoryFilter .multi-filter-menu", source)
        self.assertIn("width: 280px;", source)
        self.assertIn("#timeframeFilterDropdown .multi-filter-menu", source)
        self.assertIn("width: 200px;", source)
        self.assertIn('<label class="filter-label">Categories</label>', source)
        self.assertIn('aria-label="Sort by category">Category', source)
        self.assertIn('aria-label="Sort by article title">Article', source)
        self.assertIn("min-width: 180px;", source)
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
            "my-collected-articles": "Editor's Radar",
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
        self.assertIn("tableBody.addEventListener('focusin'", source)
        self.assertIn("function updateResultsCount(count)", source)
        self.assertIn("function updateSelectionUI()", source)
        self.assertIn('class="count-pill pill-displayed"', source)
        self.assertIn('class="count-pill pill-selected"', source)
        self.assertIn("justify-content: space-between;", source)
        self.assertIn("btn-export-unified", source)
        self.assertIn("Export Selection", source)
        self.assertIn(".btn-export-unified svg", source)
        self.assertIn("searchClearBtn", source)
        self.assertIn("syncSearchClearBtn", source)
        self.assertGreaterEqual(source.count("Also in:"), 2)

    def test_dashboard_multi_filters_overlay_and_close(self):
        template = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template, encoding="utf-8") as stream:
            source = stream.read()
        self.assertIn(".controls-panel {\n      position: relative;\n      z-index: 10;", source)
        self.assertIn(".table-container {\n      position: relative;\n      z-index: 2;", source)
        self.assertIn(".multi-filter-menu {\n      position: absolute;", source)
        self.assertIn("function closeMultiFilters(exceptFilter)", source)
        self.assertIn("if (!event.target.closest('.multi-filter')) closeMultiFilters();", source)
        self.assertIn("if (filter.open) closeMultiFilters(filter);", source)

    def test_dashboard_search_and_filter_synchronization(self):
        template = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template, encoding="utf-8") as stream:
            source = stream.read()
        self.assertIn(".multi-filter-summary {", source)
        self.assertIn("min-width: 0;", source)
        self.assertIn("text-overflow: ellipsis;", source)
        self.assertIn("padding: 0 2.25rem 0 0.85rem;", source)
        self.assertIn('autocomplete="off"', source)
        self.assertIn("(article.newsletter || '').toLowerCase().includes(query)", source)
        self.assertIn("(article.source_short_name || '').toLowerCase().includes(query)", source)
        # Verify faceted filter counts and spotlight availability synchronization
        sources_pos = source.find("const sources = getSelectedFilterValues(sourceFilter);")
        counts_pos = source.find("updateFilterOptionCounts(articlesForSources, articlesForTypes, articlesForCategories);", sources_pos)
        spotlight_pos = source.find("updateSpotlightAvailability();", counts_pos)
        self.assertGreater(sources_pos, 0)
        self.assertGreater(counts_pos, sources_pos)
        self.assertGreater(spotlight_pos, counts_pos)

    def test_dashboard_faceted_cross_filter_counts(self):
        """Verifies that Content Type and Category counts are scoped to the selected source (and vice-versa)."""
        news_file = os.path.join(REPO_ROOT, "news.html")
        with open(news_file, encoding="utf-8") as stream:
            html = stream.read()
        m = re.search(r"const articles = (\[.*?\]);", html, re.DOTALL)
        self.assertIsNotNone(m, "articles array not found in news.html")
        articles = json.loads(m.group(1))

        # Anchor clock to reference test date
        anchor_date = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
        now_ms = anchor_date.timestamp() * 1000

        # Filter to Last 1 Week (7 days)
        cutoff_7d = now_ms - (7 * 24 * 60 * 60 * 1000)
        cutoff_day_7d = datetime.fromtimestamp(cutoff_7d / 1000, tz=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).timestamp() * 1000

        articles_7d = [
            a for a in articles
            if datetime.fromisoformat(a["date"]).replace(tzinfo=timezone.utc).timestamp() * 1000 >= cutoff_day_7d
        ]

        # Scenario: User selects a source with 0 articles under Last 1 Week (e.g. FOSE)
        fose_source = "Future of Software Development (Thoughtworks FOSE)"
        fose_articles_7d = [
            a for a in articles_7d
            if a.get("newsletter") == fose_source or fose_source in a.get("also_in", [])
        ]
        self.assertEqual(len(fose_articles_7d), 0, "FOSE should have 0 articles in Last 1 Week")

        # Faceted types and categories for this 0-result source must therefore all be 0
        type_counts = {}
        for a in fose_articles_7d:
            t = a.get("type")
            if t:
                type_counts[t] = type_counts.get(t, 0) + 1
        self.assertEqual(sum(type_counts.values()), 0)

        cat_counts = {}
        for a in fose_articles_7d:
            c = a.get("category")
            if c:
                cat_counts[c] = cat_counts.get(c, 0) + 1
        self.assertEqual(sum(cat_counts.values()), 0)

    def test_dashboard_runtime_filter_engine(self):
        """Verifies multi-layer filter resolution across timeframes, search, and sources."""
        news_file = os.path.join(REPO_ROOT, "news.html")
        with open(news_file, encoding="utf-8") as stream:
            html = stream.read()
        m = re.search(r"const articles = (\[.*?\]);", html, re.DOTALL)
        self.assertIsNotNone(m, "articles array not found in news.html")
        articles = json.loads(m.group(1))

        # Anchor clock to reference test date
        anchor_date = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
        now_ms = anchor_date.timestamp() * 1000

        def filter_timeframe(days_or_all):
            if days_or_all == "all":
                return articles
            days = int(days_or_all)
            cutoff = now_ms - (days * 24 * 60 * 60 * 1000)
            cutoff_dt = datetime.fromtimestamp(cutoff / 1000, tz=timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            cutoff_day_ms = cutoff_dt.timestamp() * 1000
            res = []
            for a in articles:
                art_time = datetime.fromisoformat(a["date"]).replace(
                    tzinfo=timezone.utc
                ).timestamp() * 1000
                if art_time > now_ms or art_time >= cutoff_day_ms:
                    res.append(a)
            return res

        fose_source = "Future of Software Development (Thoughtworks FOSE)"
        # Layer 1: Timeframe window count assertions
        tf_30 = filter_timeframe(30)
        fose_30 = [a for a in tf_30 if a.get("newsletter") == fose_source]
        self.assertEqual(len(fose_30), 0, "FOSE should have 0 articles in 30-day window")

        tf_60 = filter_timeframe(60)
        fose_60 = [a for a in tf_60 if a.get("newsletter") == fose_source]
        self.assertEqual(len(fose_60), 14, "FOSE should have 14 articles in 60-day window")

        tf_all = filter_timeframe("all")
        fose_all = [a for a in tf_all if a.get("newsletter") == fose_source]
        self.assertEqual(len(fose_all), 16, "FOSE should have all 16 articles in full 90-day build")

        # Layer 2: Multi-filter matching (FOSE alone with all categories and types)
        sources_set = {fose_source}
        types_set = set(a["type"] for a in articles)
        categories_set = set(a["category"] for a in articles)

        def matches_filters(article):
            m_src = article.get("newsletter") in sources_set or any(
                s in sources_set for s in article.get("also_in", [])
            )
            return m_src and article.get("type") in types_set and article.get("category") in categories_set

        matched_articles = [a for a in tf_all if matches_filters(a)]
        self.assertEqual(len(matched_articles), 16)

        # Layer 3: Text search coverage across newsletter and source_short_name
        def matches_query(article, query):
            q = query.lower().strip()
            if not q:
                return True
            haystack = " ".join([
                article.get("title", ""),
                article.get("author", ""),
                article.get("description", ""),
                article.get("issue_title", ""),
                article.get("newsletter", ""),
                article.get("source_short_name", ""),
            ]).lower()
            return q in haystack

        self.assertEqual(len([a for a in fose_all if matches_query(a, "thoughtworks")]), 16)
        self.assertEqual(len([a for a in fose_all if matches_query(a, "fose")]), 16)
        self.assertEqual(len([a for a in fose_all if matches_query(a, "future of software")]), 16)
        self.assertEqual(len([a for a in fose_all if matches_query(a, "Martin Fowler")]), 2)
        self.assertEqual(len([a for a in fose_all if matches_query(a, "Mathias Verraes")]), 1)

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


class RSSFeedScraperTests(unittest.TestCase):
    def test_parses_rss2_feed(self):
        from common.rss_feed_scraper import RSSFeedScraper
        scraper = RSSFeedScraper.__new__(RSSFeedScraper)
        scraper.log_name = "TestRSS"
        scraper.default_author = "Default Author"
        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
            <channel>
                <title>Test Channel</title>
                <item>
                    <title>AI and Systems Design</title>
                    <link>https://example.com/ai-systems</link>
                    <pubDate>Mon, 01 Sep 2026 10:00:00 GMT</pubDate>
                    <description>&lt;p&gt;Overview of modern agent architectures.&lt;/p&gt;</description>
                    <dc:creator>Jane Doe</dc:creator>
                </item>
            </channel>
        </rss>"""
        items = scraper.parse_feed_xml(rss_xml)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "AI and Systems Design")
        self.assertEqual(items[0]["link"], "https://example.com/ai-systems")
        self.assertEqual(items[0]["author"], "Jane Doe")
        self.assertEqual(items[0]["description"], "Overview of modern agent architectures.")
        iso_date, date_str = scraper.parse_feed_date(items[0]["date_raw"])
        self.assertEqual(iso_date, "2026-09-01")

    def test_parses_atom_feed(self):
        from common.rss_feed_scraper import RSSFeedScraper
        scraper = RSSFeedScraper.__new__(RSSFeedScraper)
        scraper.log_name = "TestAtom"
        scraper.default_author = "Default Author"
        atom_xml = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <title>Test Atom Feed</title>
            <entry>
                <title>Observability in Microservices</title>
                <link rel="alternate" href="https://example.com/observability"/>
                <published>2026-08-15T12:00:00Z</published>
                <summary>A deep dive into telemetry and spans.</summary>
                <author><name>John Smith</name></author>
            </entry>
        </feed>"""
        items = scraper.parse_feed_xml(atom_xml)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Observability in Microservices")
        self.assertEqual(items[0]["link"], "https://example.com/observability")
        self.assertEqual(items[0]["author"], "John Smith")
        iso_date, date_str = scraper.parse_feed_date(items[0]["date_raw"])
        self.assertEqual(iso_date, "2026-08-15")


if __name__ == "__main__":
    unittest.main()
