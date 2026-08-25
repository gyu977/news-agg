"""Tests for BaseScraper.auto_categorize (regression cover for issue H2)."""

import unittest

from helpers import StubScraper

try:
    from common.constants import CATEGORIES
except ImportError:  # pragma: no cover
    CATEGORIES = []

AI = "AI-Native & Agentic Software Engineering"
LLM = "Large Language Models & Evaluation Infrastructure"
ARCH = "Software Architecture & Distributed Systems"
TEST = "Software Testing, Quality & Observability"
CLOUD = "Cloud Infrastructure & System Reliability"
JOBS = "Tech Industry, Jobs & Careers"
PHIL = "Engineering Philosophy & Estimation"


class AutoCategorizeTests(unittest.TestCase):
    def setUp(self):
        self.s = StubScraper()

    def cat(self, title, description=""):
        return self.s.auto_categorize(title, description)

    def test_returns_a_known_category(self):
        self.assertIn(self.cat("Anything at all"), CATEGORIES)

    # --- H2: substring matches across word boundaries must not fire ---

    def test_latest_does_not_match_test(self):
        self.assertNotEqual(self.cat("The latest release of Postgres"), TEST)

    def test_contest_does_not_match_test(self):
        self.assertNotEqual(self.cat("Contest results"), TEST)

    def test_modeling_does_not_match_model(self):
        self.assertNotEqual(self.cat("Modeling the market"), LLM)

    def test_developers_substring_does_not_leak(self):
        # "loop" (AI-Native) must not match inside "loophole".
        self.assertNotEqual(self.cat("Closing a contract loophole"), AI)

    # --- Positive classification ---

    def test_testing_wins_over_incidental_architecture_mention(self):
        self.assertEqual(self.cat("Testing microservices with contract tests"), TEST)

    def test_llm_evaluation(self):
        self.assertEqual(self.cat("Evaluating open-weight models and benchmarks"), LLM)

    def test_architecture(self):
        self.assertEqual(self.cat("An ADR approach to microservice architecture"), ARCH)

    def test_agentic(self):
        self.assertEqual(self.cat("Agentic coding with Claude Code"), AI)

    def test_cloud(self):
        self.assertEqual(self.cat("Load balancing and multi-region cloud security"), CLOUD)

    def test_jobs(self):
        self.assertEqual(self.cat("Hiring managers and the job market"), JOBS)

    def test_philosophy(self):
        self.assertEqual(self.cat("Napkin math for engineers"), PHIL)

    def test_fallback_when_nothing_matches(self):
        self.assertEqual(self.cat("Zzz qqq wwww"), PHIL)

    # --- Behavioural guarantees of the scoring model ---

    def test_plural_form_matches_singular_keyword(self):
        self.assertEqual(self.cat("Comparing agents in production"), AI)

    def test_hyphenated_keyword_matches(self):
        self.assertEqual(self.cat("A micro-frontend approach"), ARCH)

    def test_description_contributes_to_the_score(self):
        self.assertEqual(
            self.cat("Untitled", "A deep dive into observability and quality gates"), TEST
        )

    def test_many_weak_matches_beat_one_incidental_match(self):
        # Three cloud terms should outrank the single "model" mention.
        self.assertEqual(
            self.cat("Cloud topology, load balancing and multi-region failover", "model"),
            CLOUD,
        )

    def test_is_deterministic(self):
        title = "Testing microservices with contract tests"
        self.assertEqual(self.cat(title), self.cat(title))

    def test_case_insensitive(self):
        self.assertEqual(self.cat("AGENTIC CODING"), self.cat("agentic coding"))


if __name__ == "__main__":
    unittest.main()
