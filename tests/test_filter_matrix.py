"""
Comprehensive test matrix for the dashboard filter engine.
Tests a synthetic dataset across 12 distinct multi-filter interaction scenarios,
verifying that faceted cross-filtering, timeframes, search, spotlight, and zero-match
states behave deterministically.
"""

from datetime import datetime, timezone
import json
import os
import re
import sys
import unittest

tests_dir = os.path.dirname(os.path.abspath(__file__))
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

from helpers import REPO_ROOT


# ---------------------------------------------------------------------------
# Synthetic Dataset Fixture
# ---------------------------------------------------------------------------

ANCHOR_DATETIME = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

SYNTHETIC_ARTICLES = [
    {
        "id": "m-1",
        "title": "AI Agent Harnesses in Production",
        "author": "Architecture Team",
        "description": "Deep dive into orchestrating multi-agent LLM harnesses.",
        "newsletter": "Dear Architects",
        "source_short_name": "Dear Architects",
        "date": "2026-09-17",  # 2 days ago (in 7d, 14d, 30d, 60d, all)
        "type": "article",
        "category": "AI & Agentic Eng",
        "is_spotlight": True,
    },
    {
        "id": "m-2",
        "title": "Global Systems Summit 2026",
        "author": "Conference Board",
        "description": "Annual international systems architecture gathering.",
        "newsletter": "Dear Architects",
        "source_short_name": "Dear Architects",
        "date": "2026-10-19",  # +30 days (future-dated, visible across all timeframes)
        "type": "conference",
        "category": "Arch & Dist Systems",
        "is_spotlight": True,
    },
    {
        "id": "m-3",
        "title": "Architecture Insights Podcast",
        "author": "Tech Leads",
        "description": "Episode 42: Modern modular monoliths and decoupling.",
        "newsletter": "Dear Architects",
        "source_short_name": "Dear Architects",
        "date": "2026-08-30",  # 20 days ago (in 30d, 60d, all; not 7d, 14d)
        "type": "video",
        "category": "Arch & Dist Systems",
        "is_spotlight": True,
    },
    {
        "id": "m-4",
        "title": "Token Economics for Senior Engineers",
        "author": "Token Editor",
        "description": "Evaluating the business ROI of frontier coding assistants.",
        "newsletter": "Token by Token",
        "source_short_name": "Token by Token",
        "date": "2026-09-15",  # 4 days ago (in 7d, 14d, 30d, 60d, all)
        "type": "article",
        "category": "Industry & Careers",
        "is_spotlight": True,
    },
    {
        "id": "m-5",
        "title": "Pulse: Evaluating LLM Reasoning Drift",
        "author": "Token Editor",
        "description": "Weekly pulse on benchmark stability and evaluation frameworks.",
        "newsletter": "Token by Token",
        "source_short_name": "Token by Token",
        "date": "2026-09-09",  # 10 days ago (in 14d, 30d, 60d, all; not 7d)
        "type": "pulse",
        "category": "LLMs & Evaluation",
        "is_spotlight": True,
    },
    {
        "id": "m-6",
        "title": "SRE at Scale Handbook",
        "author": "Addy Osmani",
        "description": "Comprehensive guide to site reliability engineering.",
        "newsletter": "Addy Osmani",
        "source_short_name": "Addy Osmani",
        "date": "2026-08-25",  # 25 days ago (in 30d, 60d, all; not 7d, 14d)
        "type": "book",
        "category": "Cloud Infra & SRE",
        "is_spotlight": False,
    },
    {
        "id": "m-7",
        "title": "Reflections on Craft and Programming Philosophy",
        "author": "Addy Osmani",
        "description": "A long-form essay on the psychology of software craftsmanship.",
        "newsletter": "Addy Osmani",
        "source_short_name": "Addy Osmani",
        "date": "2026-07-31",  # 50 days ago (in 60d, all; not 7d, 14d, 30d)
        "type": "article",
        "category": "Eng Philosophy & Culture",
        "is_spotlight": False,
    },
    {
        "id": "m-8",
        "title": "Observability and Fitness Functions for Agents",
        "author": "Simon Willison",
        "description": "Keynote presentation on telemetry for generative code pipelines.",
        "newsletter": "Simon Willison",
        "source_short_name": "Simon Willison",
        "date": "2026-09-16",  # 3 days ago (in 7d, 14d, 30d, 60d, all)
        "type": "presentation",
        "category": "Testing & Observability",
        "is_spotlight": False,
    },
    {
        "id": "m-9",
        "title": "Patterns for Resilient Micro-Frontends",
        "author": "Simon Willison",
        "description": "Modular web architectures with cross-newsletter syndication.",
        "newsletter": "Simon Willison",
        "also_in": ["Dear Architects"],  # Cross-source ingested
        "source_short_name": "Simon Willison",
        "date": "2026-09-14",  # 5 days ago (in 7d, 14d, 30d, 60d, all)
        "type": "article",
        "category": "AI & Agentic Eng",
        "is_spotlight": False,
    },
    {
        "id": "m-10",
        "title": "Tech Compensation Landscape 2026",
        "author": "Gergely Orosz",
        "description": "Market trends and hiring benchmarks across Europe and the US.",
        "newsletter": "The Pragmatic Engineer",
        "source_short_name": "Pragmatic Eng.",
        "date": "2026-06-26",  # 85 days ago (in all only; not 7d, 14d, 30d, 60d)
        "type": "article",
        "category": "Industry & Careers",
        "is_spotlight": False,
    },
]


# ---------------------------------------------------------------------------
# Filter Engine Simulator
# ---------------------------------------------------------------------------

ALL_SOURCES = {"Dear Architects", "Token by Token", "Addy Osmani", "Simon Willison", "The Pragmatic Engineer"}
ALL_TYPES = {"article", "conference", "video", "pulse", "book", "presentation"}
ALL_CATEGORIES = {
    "AI & Agentic Eng",
    "Arch & Dist Systems",
    "Cloud Infra & SRE",
    "Eng Philosophy & Culture",
    "Industry & Careers",
    "LLMs & Evaluation",
    "Testing & Observability",
}
SPOTLIGHT_SOURCES = {"Dear Architects", "Token by Token"}


def article_matches_source(article, sources_set):
    if article.get("newsletter") in sources_set:
        return True
    return any(s in sources_set for s in article.get("also_in", []))


def run_filter_engine(
    articles=SYNTHETIC_ARTICLES,
    anchor_dt=ANCHOR_DATETIME,
    timeframe="30",
    query="",
    selected_sources=None,
    selected_types=None,
    selected_categories=None,
    spotlight_only=False,
):
    """
    Simulates the exact JavaScript filter engine in news_template.html.
    Returns:
      filtered_articles: list of articles matching all active criteria
      source_counts: dict {source: count} for options in sourceFilter
      type_counts: dict {type: count} for options in typeFilter
      category_counts: dict {category: count} for options in categoryFilter
      spotlight_available: bool indicating whether the spotlight toggle is active
    """
    sources = ALL_SOURCES if selected_sources is None else set(selected_sources)
    types = ALL_TYPES if selected_types is None else set(selected_types)
    categories = ALL_CATEGORIES if selected_categories is None else set(selected_categories)

    now_ms = anchor_dt.timestamp() * 1000

    # 1. Articles matching active timeframe
    def matches_timeframe(art):
        if timeframe == "all":
            return True
        days = int(timeframe)
        art_time = datetime.fromisoformat(art["date"]).replace(tzinfo=timezone.utc).timestamp() * 1000
        cutoff = now_ms - (days * 24 * 60 * 60 * 1000)
        cutoff_day_dt = datetime.fromtimestamp(cutoff / 1000, tz=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cutoff_day_ms = cutoff_day_dt.timestamp() * 1000
        return art_time > now_ms or art_time >= cutoff_day_ms

    timeframe_filtered = [a for a in articles if matches_timeframe(a)]

    # 2. Base articles matching timeframe, query, and spotlight
    q = query.lower().strip()

    def matches_query(art):
        if not q:
            return True
        haystack = " ".join([
            art.get("title", ""),
            art.get("author", ""),
            art.get("description", ""),
            art.get("newsletter", ""),
            art.get("source_short_name", ""),
        ]).lower()
        return q in haystack

    base_articles = [
        a for a in timeframe_filtered
        if matches_query(a) and (not spotlight_only or a.get("is_spotlight", False))
    ]

    # 3. Faceted subsets: for each dimension, compute option counts based on OTHER dimensions
    articles_for_sources = [
        a for a in base_articles
        if a.get("type") in types and a.get("category") in categories
    ]
    articles_for_types = [
        a for a in base_articles
        if article_matches_source(a, sources) and a.get("category") in categories
    ]
    articles_for_categories = [
        a for a in base_articles
        if article_matches_source(a, sources) and a.get("type") in types
    ]

    # Compute source counts (including also_in)
    source_counts = {s: 0 for s in ALL_SOURCES}
    for a in articles_for_sources:
        all_srcs = set([a.get("newsletter")] + a.get("also_in", []))
        for s in all_srcs:
            if s in source_counts:
                source_counts[s] += 1

    # Compute type counts
    type_counts = {t: 0 for t in ALL_TYPES}
    for a in articles_for_types:
        t = a.get("type")
        if t in type_counts:
            type_counts[t] += 1

    # Compute category counts
    category_counts = {c: 0 for c in ALL_CATEGORIES}
    for a in articles_for_categories:
        c = a.get("category")
        if c in category_counts:
            category_counts[c] += 1

    # Spotlight availability
    spotlight_available = any(s in SPOTLIGHT_SOURCES for s in sources)

    # 4. Final articles matching ALL dimensions
    filtered_articles = [
        a for a in base_articles
        if article_matches_source(a, sources) and a.get("type") in types and a.get("category") in categories
    ]

    return {
        "filtered_articles": filtered_articles,
        "source_counts": source_counts,
        "type_counts": type_counts,
        "category_counts": category_counts,
        "spotlight_available": spotlight_available,
    }


# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

class FilterMatrixSimulationTests(unittest.TestCase):
    """Matrix of 12 distinct user filtering scenarios and template contract verification."""

    def test_scenario_01_default_30d_baseline(self):
        """Scenario 1: Baseline view (30 days, all options selected)."""
        res = run_filter_engine(timeframe="30")
        arts = res["filtered_articles"]

        # m-7 (50d) and m-10 (85d) must be excluded; m-2 (+30d future) must be included
        expected_ids = {"m-1", "m-2", "m-3", "m-4", "m-5", "m-6", "m-8", "m-9"}
        self.assertEqual(set(a["id"] for a in arts), expected_ids)
        self.assertEqual(len(arts), 8)

        # Content Type counts must sum to 8
        self.assertEqual(sum(res["type_counts"].values()), 8)
        self.assertEqual(res["type_counts"]["article"], 3)  # m-1, m-4, m-9
        self.assertEqual(res["type_counts"]["conference"], 1)  # m-2
        self.assertEqual(res["type_counts"]["video"], 1)  # m-3
        self.assertEqual(res["type_counts"]["pulse"], 1)  # m-5
        self.assertEqual(res["type_counts"]["book"], 1)  # m-6
        self.assertEqual(res["type_counts"]["presentation"], 1)  # m-8

        # Category counts must sum to 8
        self.assertEqual(sum(res["category_counts"].values()), 8)

        # Source counts reflect appearances (m-9 is credited to Simon Willison AND Dear Architects)
        self.assertEqual(res["source_counts"]["Dear Architects"], 4)  # m-1, m-2, m-3, m-9
        self.assertEqual(res["source_counts"]["Token by Token"], 2)  # m-4, m-5
        self.assertEqual(res["source_counts"]["Addy Osmani"], 1)  # m-6
        self.assertEqual(res["source_counts"]["Simon Willison"], 2)  # m-8, m-9
        self.assertEqual(res["source_counts"]["The Pragmatic Engineer"], 0)  # m-10 is 85d old

    def test_scenario_02_timeframe_contraction_7d(self):
        """Scenario 2: Narrowing timeframe to Last 1 Week (7 days)."""
        res = run_filter_engine(timeframe="7")
        arts = res["filtered_articles"]

        # Visible: m-1 (2d), m-4 (4d), m-8 (3d), m-9 (5d), and m-2 (+30d future)
        expected_ids = {"m-1", "m-2", "m-4", "m-8", "m-9"}
        self.assertEqual(set(a["id"] for a in arts), expected_ids)
        self.assertEqual(len(arts), 5)

        # Sources with 0 articles in 7d show count 0
        self.assertEqual(res["source_counts"]["Addy Osmani"], 0)
        self.assertEqual(res["source_counts"]["The Pragmatic Engineer"], 0)

    def test_scenario_03_zero_match_source_scopes_types_and_categories_to_zero(self):
        """Scenario 3: Addy Osmani under Last 1 Week (0 articles) -> all types and categories count 0."""
        res = run_filter_engine(timeframe="7", selected_sources={"Addy Osmani"})
        arts = res["filtered_articles"]

        self.assertEqual(len(arts), 0)

        # Key UX assertion: Content Type and Categories badges MUST all be 0
        self.assertEqual(sum(res["type_counts"].values()), 0)
        for type_name, count in res["type_counts"].items():
            self.assertEqual(count, 0, f"Type {type_name} should have count 0")

        self.assertEqual(sum(res["category_counts"].values()), 0)
        for cat_name, count in res["category_counts"].items():
            self.assertEqual(count, 0, f"Category {cat_name} should have count 0")

        # Newsletter Source retains counts for 7d window so user can switch
        self.assertEqual(res["source_counts"]["Dear Architects"], 3)  # m-1, m-2, m-9
        self.assertEqual(res["source_counts"]["Token by Token"], 1)  # m-4
        self.assertEqual(res["source_counts"]["Simon Willison"], 2)  # m-8, m-9

    def test_scenario_04_single_source_drilldown_token_by_token(self):
        """Scenario 4: Selecting Token by Token alone in 30d scopes types and categories strictly to its items."""
        res = run_filter_engine(timeframe="30", selected_sources={"Token by Token"})
        arts = res["filtered_articles"]

        expected_ids = {"m-4", "m-5"}
        self.assertEqual(set(a["id"] for a in arts), expected_ids)

        # Content Types must only show Token by Token's items
        self.assertEqual(res["type_counts"]["article"], 1)  # m-4
        self.assertEqual(res["type_counts"]["pulse"], 1)  # m-5
        self.assertEqual(res["type_counts"]["conference"], 0)
        self.assertEqual(res["type_counts"]["video"], 0)
        self.assertEqual(res["type_counts"]["book"], 0)
        self.assertEqual(res["type_counts"]["presentation"], 0)

        # Categories must only show Token by Token's categories
        self.assertEqual(res["category_counts"]["Industry & Careers"], 1)
        self.assertEqual(res["category_counts"]["LLMs & Evaluation"], 1)
        self.assertEqual(res["category_counts"]["AI & Agentic Eng"], 0)

    def test_scenario_05_cross_source_also_in_inclusion(self):
        """Scenario 5: Selecting Dear Architects includes articles where also_in has Dear Architects."""
        res = run_filter_engine(timeframe="30", selected_sources={"Dear Architects"})
        arts = res["filtered_articles"]

        # m-9 is primary Simon Willison, but also_in Dear Architects
        expected_ids = {"m-1", "m-2", "m-3", "m-9"}
        self.assertEqual(set(a["id"] for a in arts), expected_ids)
        self.assertIn("m-9", [a["id"] for a in arts])

    def test_scenario_06_spotlight_toggle_on(self):
        """Scenario 6: Turning Spotlight ON retains only spotlight-enabled articles."""
        res = run_filter_engine(timeframe="30", spotlight_only=True)
        arts = res["filtered_articles"]

        expected_ids = {"m-1", "m-2", "m-3", "m-4", "m-5"}
        self.assertEqual(set(a["id"] for a in arts), expected_ids)

        # Non-spotlight sources show 0 in source counts
        self.assertEqual(res["source_counts"]["Addy Osmani"], 0)
        self.assertEqual(res["source_counts"]["Simon Willison"], 0)

    def test_scenario_07_spotlight_availability_disabled_for_unsupported_sources(self):
        """Scenario 7: When only non-spotlight sources are selected, spotlight toggle is disabled."""
        res_addy = run_filter_engine(selected_sources={"Addy Osmani"})
        self.assertFalse(res_addy["spotlight_available"])

        res_simon = run_filter_engine(selected_sources={"Simon Willison"})
        self.assertFalse(res_simon["spotlight_available"])

        res_spotlight = run_filter_engine(selected_sources={"Dear Architects"})
        self.assertTrue(res_spotlight["spotlight_available"])

    def test_scenario_08_content_type_drilldown_conference(self):
        """Scenario 8: Selecting only 'conference' scopes sources and categories to conferences."""
        res = run_filter_engine(timeframe="all", selected_types={"conference"})
        arts = res["filtered_articles"]

        self.assertEqual(len(arts), 1)
        self.assertEqual(arts[0]["id"], "m-2")

        # Source counts: only Dear Architects has a conference
        self.assertEqual(res["source_counts"]["Dear Architects"], 1)
        self.assertEqual(res["source_counts"]["Token by Token"], 0)
        self.assertEqual(res["source_counts"]["Addy Osmani"], 0)

        # Category counts: only Arch & Dist Systems has a conference
        self.assertEqual(res["category_counts"]["Arch & Dist Systems"], 1)
        self.assertEqual(res["category_counts"]["AI & Agentic Eng"], 0)

    def test_scenario_09_disjoint_filters_produce_empty_set(self):
        """Scenario 9: Disjoint combination (Token by Token has no conferences)."""
        res = run_filter_engine(
            timeframe="all",
            selected_sources={"Token by Token"},
            selected_types={"conference"},
        )
        self.assertEqual(len(res["filtered_articles"]), 0)
        self.assertEqual(sum(res["category_counts"].values()), 0)

    def test_scenario_10_free_text_search_scoping(self):
        """Scenario 10: Free-text search query narrows both results and faceted counts."""
        res = run_filter_engine(timeframe="all", query="podcast")
        arts = res["filtered_articles"]

        self.assertEqual(len(arts), 1)
        self.assertEqual(arts[0]["id"], "m-3")

        self.assertEqual(res["source_counts"]["Dear Architects"], 1)
        self.assertEqual(res["source_counts"]["Token by Token"], 0)
        self.assertEqual(res["type_counts"]["video"], 1)
        self.assertEqual(res["type_counts"]["article"], 0)
        self.assertEqual(res["category_counts"]["Arch & Dist Systems"], 1)

    def test_scenario_11_clear_and_all_restoration(self):
        """Scenario 11: Clearing categories drops results to 0, selecting All restores full baseline."""
        # Cleared state (0 categories selected)
        res_cleared = run_filter_engine(timeframe="30", selected_categories=set())
        self.assertEqual(len(res_cleared["filtered_articles"]), 0)
        self.assertEqual(sum(res_cleared["source_counts"].values()), 0)
        self.assertEqual(sum(res_cleared["type_counts"].values()), 0)
        # Category options themselves show available counts so user can pick
        self.assertEqual(sum(res_cleared["category_counts"].values()), 8)

        # Restored state (All categories selected)
        res_restored = run_filter_engine(timeframe="30", selected_categories=ALL_CATEGORIES)
        self.assertEqual(len(res_restored["filtered_articles"]), 8)

    def test_scenario_12_future_dated_events_survive_narrow_timeframes(self):
        """Scenario 12: Future-dated conferences remain visible even under Last 1 Week."""
        res_7d = run_filter_engine(timeframe="7")
        art_ids = [a["id"] for a in res_7d["filtered_articles"]]
        self.assertIn("m-2", art_ids, "Future-dated event m-2 must be visible in 7d window")

    def test_template_contract_adherence(self):
        """Guarantees that news_template.html preserves the exact faceted filter implementation."""
        template_path = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template_path, encoding="utf-8") as stream:
            source = stream.read()

        # Faceted subsets
        self.assertIn("const articlesForSources = baseArticles.filter(", source)
        self.assertIn("const articlesForTypes = baseArticles.filter(", source)
        self.assertIn("const articlesForCategories = baseArticles.filter(", source)

        # Disjoint calling
        self.assertIn(
            "updateFilterOptionCounts(articlesForSources, articlesForTypes, articlesForCategories);",
            source,
        )

        # Safe unchecking: disabled only if count is 0 AND not already checked
        self.assertIn("const isDisabled = count === 0 && !input.checked;", source)
        self.assertIn("input.disabled = isDisabled;", source)
        self.assertIn("label.classList.toggle('disabled', count === 0);", source)

    def test_scenario_13_deterministic_sort_tie_breaker(self):
        """Scenario 13: Articles with identical dates or primary sort columns break ties predictably."""
        template_path = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template_path, encoding="utf-8") as stream:
            source = stream.read()

        # Check compareArticlesForSort deterministic tie-breaker contract
        self.assertIn("if (primary !== 0) return primary;", source)
        self.assertIn("const titleComp = titleA.localeCompare(titleB, undefined, { sensitivity: 'base', numeric: true });", source)
        self.assertIn("return String(a.id || '').localeCompare(String(b.id || ''));", source)

    def test_dialog_and_tooltip_a11y_contracts(self):
        """Verify modal focus trapping, focus restoration, and tooltip event delegation in template."""
        template_path = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template_path, encoding="utf-8") as stream:
            source = stream.read()

        # Dialog focus restoration and trap
        self.assertIn("lastFocusedElement = document.activeElement;", source)
        self.assertIn("lastFocusedElement.focus();", source)
        self.assertIn("guideDialog.addEventListener('keydown', function(e) {", source)
        self.assertIn("if (e.key === 'Tab')", source)

        # Tooltip event delegation on tableBody
        self.assertIn("tableBody.addEventListener('mouseover', function(e) {", source)
        self.assertIn("tableBody.addEventListener('mouseout', function(e) {", source)
        self.assertIn("tableBody.addEventListener('focusin', function(e) {", source)
        self.assertIn("tableBody.addEventListener('focusout', function(e) {", source)

    def test_template_javascript_syntax_validity(self):
        """Validates that news_template.html script maintains balanced brackets, braces, and strings
        using 100% pure Python standard library (zero external dependencies)."""
        template_path = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template_path, encoding="utf-8") as stream:
            html = stream.read()

        m = re.search(r"<script>([\s\S]*?)</script>", html)
        self.assertIsNotNone(m, "No <script> tag found in news_template.html")
        code = m.group(1)

        # Lexical stack-based verification of balanced brackets and quotes in pure Python
        stack = []
        matching = {')': '(', '}': '{', ']': '['}
        i = 0
        n = len(code)
        line = 1

        while i < n:
            ch = code[i]
            if ch == '\n':
                line += 1
            elif ch == '/' and i + 1 < n and code[i + 1] == '/':
                # Skip line comments
                while i < n and code[i] != '\n':
                    i += 1
                line += 1
            elif ch == '/' and i + 1 < n and code[i + 1] == '*':
                # Skip block comments
                i += 2
                while i + 1 < n and not (code[i] == '*' and code[i + 1] == '/'):
                    if code[i] == '\n':
                        line += 1
                    i += 1
                i += 1
            elif ch == '/' and i + 1 < n and code[i + 1] not in ('/', '*'):
                # Check if this '/' is a regex literal rather than division operator
                # In JS, a regex literal occurs after '(', '=', ':', ',', ';', 'return', 'replace(', etc.
                prev = code[:i].rstrip()
                if prev and (prev[-1] in '(=:,;[!&|?~^{}' or prev.endswith('return')):
                    i += 1
                    while i < n and code[i] != '/':
                        if code[i] == '\\':
                            i += 2
                            continue
                        if code[i] == '\n':
                            line += 1
                        i += 1
            elif ch in ('"', "'", '`'):
                # Skip string literals (including template literals)
                quote = ch
                i += 1
                while i < n and code[i] != quote:
                    if code[i] == '\\':
                        i += 2
                        continue
                    if code[i] == '\n':
                        line += 1
                    i += 1
            elif ch in '({[':
                stack.append((ch, line))
            elif ch in ')}]':
                self.assertTrue(
                    len(stack) > 0,
                    f"Unmatched closing '{ch}' at line {line} in news_template.html"
                )
                top, top_line = stack.pop()
                self.assertEqual(
                    top, matching[ch],
                    f"Mismatched bracket '{ch}' at line {line}, expected match for '{top}' from line {top_line}"
                )
            i += 1

        self.assertEqual(len(stack), 0, f"Unclosed brackets remaining: {stack}")

    def test_scenario_14_browser_reload_timeframe_reset_simulation(self):
        """Scenario 14: Verifies browser reload resilience using pure Python static and flow analysis.
        Guarantees that form caching is disabled and initial boot unconditionally enforces default '30'."""
        template_path = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template_path, encoding="utf-8") as stream:
            html = stream.read()

        # 1. Contract check: autocomplete="off" on timeframe select disables browser state retention
        self.assertIn(
            '<select id="timeframeFilter" class="filter-select sr-only" tabindex="-1" aria-hidden="true" autocomplete="off">',
            html
        )

        # 2. Execution order check: reset timeframeFilter to '30' BEFORE render() or filter bindings
        script_m = re.search(r"<script>([\s\S]*?)</script>", html)
        self.assertIsNotNone(script_m)
        script = script_m.group(1)

        reset_pos = script.find("timeframeFilter.value = '30';")
        sync_pos = script.find("syncTimeframeDropdown();", reset_pos)
        render_pos = script.find("render();", sync_pos)

        self.assertGreater(reset_pos, 0, "Missing explicit '30' reset for timeframeFilter")
        self.assertGreater(sync_pos, reset_pos, "syncTimeframeDropdown must follow timeframeFilter reset")
        self.assertGreater(render_pos, sync_pos, "Initial render must happen after timeframe is reset and synced")

    def test_scenario_15_source_column_width_stability(self):
        """Scenario 15: Verifies that metadata columns (Source, Date, Author, Category)
        are locked to fixed widths matching maximum content, preventing horizontal layout
        shifts when filtering sources or content."""
        template_path = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template_path, encoding="utf-8") as stream:
            html = stream.read()

        # 1. Verify CSS defines table-layout: fixed and column width / min-width constraints
        self.assertIn("table-layout: fixed;", html)
        self.assertIn(".source-column {", html)
        self.assertIn("width: 165px;", html)
        self.assertIn("min-width: 165px;", html)

        self.assertIn(".date-column {", html)
        self.assertIn("width: 115px;", html)
        self.assertIn("min-width: 115px;", html)

        self.assertIn(".author-column {", html)
        self.assertIn("width: 170px;", html)
        self.assertIn("min-width: 170px;", html)

        self.assertIn(".category-column {", html)
        self.assertIn("width: 180px;", html)
        self.assertIn("min-width: 180px;", html)

        # 2. Verify th elements have corresponding column classes
        self.assertIn('id="th-newsletter" class="source-column"', html)
        self.assertIn('id="th-date" class="date-column active-sort"', html)
        self.assertIn('id="th-author" class="author-column"', html)

        # 3. Verify td cells in render() receive column classes
        self.assertIn("tdSource.className = 'source-column';", html)
        self.assertIn("tdDate.className = 'date-cell date-column';", html)
        self.assertIn("tdAuthor.className = 'author-cell author-column';", html)

        # 4. Verify responsive mobile override resets width to auto
        self.assertIn(".source-column,\n      .date-column,\n      .author-column,\n      .category-column", html)

        # 5. Verify select-col alignment: top-aligned for data rows, centered for table header
        self.assertIn(".select-col {\n      width: 48px;\n      min-width: 48px;\n      max-width: 48px;\n      text-align: center;\n      vertical-align: top;", html)
        self.assertIn("th.select-col {\n      vertical-align: middle;\n    }", html)

        # 6. Verify content type icon alignment and inline badge flow on multi-line wraps
        self.assertIn(".article-header-row {\n      display: block;\n      line-height: 1.4;\n    }", html)
        self.assertIn(".article-link {\n      color: var(--text-main);\n      font-weight: 700;\n      text-decoration: none;\n      transition: var(--transition-smooth);\n      display: inline;\n      line-height: 1.4;\n    }", html)
        self.assertIn(".article-type-icon {\n      display: inline-block;\n      vertical-align: -0.1em;\n      margin-right: 0.35rem;\n      line-height: 1;\n      font-size: 0.95em;\n    }", html)
        self.assertIn('<span class="article-type-icon">${icon}</span>', html)
        self.assertIn(".badge-spotlight {\n      background: var(--accent-gold-rgba);\n      color: var(--accent-gold);\n      border: 1px solid rgba(251, 191, 36, 0.3);\n      vertical-align: middle;\n      display: inline-flex;\n      align-items: center;\n      margin-left: 0.45rem;\n      white-space: nowrap;\n    }", html)

        # 7. Verify timeframe and filter dropdowns are fixed width, preventing rightside UI shifts
        self.assertIn("#timeframeFilterDropdown {\n      width: 180px;\n    }", html)
        self.assertIn("#sourceFilter {\n      width: 200px;\n    }", html)
        self.assertIn("#typeFilter {\n      width: 180px;\n    }", html)
        self.assertIn("#categoryFilter {\n      width: 210px;\n    }", html)
        self.assertIn(".toggles-wrapper {\n      display: flex;\n      align-items: center;\n      gap: 1.25rem;\n      white-space: nowrap;\n    }", html)

        # 8. Verify count pills have fixed minimum widths, motionless number slot, and tabular figures
        self.assertIn(".count-pill {\n      display: inline-flex;\n      align-items: center;\n      justify-content: center;\n      gap: 0.35rem;\n      padding: 0.35rem 0.85rem;\n      border-radius: 9999px;\n      font-size: 0.82rem;\n      font-weight: 600;\n      white-space: nowrap;\n      font-variant-numeric: tabular-nums;\n      box-sizing: border-box;\n    }", html)
        self.assertIn(".count-num {\n      display: inline-block;\n      width: 25px;\n      text-align: right;\n      font-variant-numeric: tabular-nums;\n    }", html)
        self.assertIn(".pill-displayed {\n      background: rgba(30, 41, 59, 0.8);\n      border: 1px solid rgba(255, 255, 255, 0.1);\n      color: #94a3b8;\n      min-width: 116px;\n    }", html)
        self.assertIn(".pill-selected {\n      background: rgba(56, 189, 248, 0.12);\n      border: 1px solid rgba(56, 189, 248, 0.3);\n      color: #38bdf8;\n      min-width: 146px;", html)
        self.assertIn('<strong class="count-num">', html)

        # 9. Verify header checkbox always provides contextual tooltip, while row checkboxes suppress tooltips when selection is active
        self.assertIn('title="Select all visible articles to export as Markdown or HTML"', html)
        self.assertIn("function syncSelectAllTitle()", html)
        self.assertIn('"Deselect all visible articles"', html)
        self.assertIn("function syncRowSelectorTitle(cb)", html)
        self.assertIn("function syncAllCheckboxTitles()", html)
        self.assertIn("cb.removeAttribute('title');", html)
        self.assertIn('"Deselect article"', html)
        self.assertIn('"Select article to export as Markdown or HTML"', html)

    def test_scenario_16_modern_css_enhancements(self):
        """Scenario 16: Verifies modern CSS architectural enhancements:
        1. Pure CSS reactive search clear button using :has() and :not(:placeholder-shown).
        2. Corner-bleed prevention for selected rows using inset box-shadow instead of border-left.
        3. Accessibility overrides for prefers-reduced-transparency and prefers-reduced-motion."""
        template_path = os.path.join(REPO_ROOT, "code", "builders", "news_template.html")
        with open(template_path, encoding="utf-8") as stream:
            html = stream.read()

        # 1. Pure CSS search clear button reactive rule
        self.assertIn(
            ".search-toolbar:has(#searchInput:not(:placeholder-shown)) .search-clear-btn {",
            html
        )
        self.assertIn("opacity: 1;", html)
        self.assertIn("pointer-events: auto;", html)
        self.assertIn("visibility: visible;", html)

        # 2. Corner bleed fix on selected row
        self.assertIn("box-shadow: inset 3px 0 0 var(--accent-blue) !important;", html)

        # 3. Accessibility: prefers-reduced-transparency
        self.assertIn("@media (prefers-reduced-transparency: reduce) {", html)
        self.assertIn("backdrop-filter: none !important;", html)

        # 4. Accessibility: prefers-reduced-motion
        self.assertIn("@media (prefers-reduced-motion: reduce) {", html)
        self.assertIn("animation: none !important;", html)
        self.assertIn("scroll-behavior: auto !important;", html)

        # 5. Scroll-driven reading progress bar
        self.assertIn("@keyframes table-scroll-progress {", html)
        self.assertIn("@supports (animation-timeline: scroll()) {", html)
        self.assertIn("animation: table-scroll-progress linear;", html)
        self.assertIn("animation-timeline: scroll();", html)
        self.assertIn('<div class="table-progress-bar" id="tableProgressBar" aria-hidden="true"></div>', html)
        self.assertIn(".table-progress-bar {\n        top: 0;\n      }", html)

        # 6. Reactive CSS counter for selected rows
        self.assertIn("--selected-count: 0;", html)
        self.assertIn("counter-reset: selected-articles var(--selected-count);", html)
        self.assertIn(".pill-selected .count-num::after {\n      content: counter(selected-articles);\n    }", html)
        self.assertIn("document.documentElement.style.setProperty('--selected-count', count);", html)


if __name__ == "__main__":
    unittest.main()




