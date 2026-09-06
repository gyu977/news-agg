"""
The Pragmatic Engineer Scraper & Parser using the shared SubstackScraper implementation.
Extracts articles, podcast episodes, and Pulse digests from newsletter.pragmaticengineer.com.
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
code_dir = os.path.join(project_root, "code")

for p in [code_dir, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.substack_scraper import SubstackScraper


class PragmaticEngineerScraper(SubstackScraper):
    base_url = "https://newsletter.pragmaticengineer.com"
    newsletter_name = "The Pragmatic Engineer"
    article_id_prefix = "pe"
    log_name = "PragmaticEngineer"

    def __init__(self):
        super().__init__(source_dir=current_dir)


if __name__ == "__main__":
    scraper = PragmaticEngineerScraper()
    scraper.discover_and_ingest_posts()
