"""
Shared test helpers: puts `code/` on sys.path and exposes a BaseScraper subclass
that can be constructed without touching the filesystem.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE_DIR = os.path.join(REPO_ROOT, "code")
SOURCES_DIR = os.path.join(REPO_ROOT, "data-sources")

if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from common.base_scraper import BaseScraper  # noqa: E402
from common.models import Article, SourceDefinition  # noqa: E402


class StubScraper(BaseScraper):
    """BaseScraper with the filesystem-loading __init__ bypassed."""

    def __init__(self, articles=None, definition=None):
        self.source_dir = ""
        self.definition_path = ""
        self.data_path = ""
        self.definition = definition
        self.articles = list(articles or [])


def make_article(**overrides) -> Article:
    """Build an Article with sensible defaults, overriding only what a test cares about."""
    defaults = dict(
        id="src-1-abc123",
        newsletter="Test Source",
        issue_number=1,
        issue_title="Issue 1",
        issue_link="https://example.com/issue/1",
        date="2026-01-01",
        date_str="January 1, 2026",
        title="A title",
        link="https://example.com/article",
    )
    defaults.update(overrides)
    return Article(**defaults)


def iter_source_dirs():
    """Yield (source_id, absolute_path) for every source that has a data.json."""
    for name in sorted(os.listdir(SOURCES_DIR)):
        path = os.path.join(SOURCES_DIR, name)
        if os.path.isfile(os.path.join(path, "data.json")):
            yield name, path
