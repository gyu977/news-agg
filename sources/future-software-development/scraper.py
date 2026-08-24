"""
Future of Software Development (Thoughtworks FOSE 2026) Scraper & Ingestor.
Ingests curated reflections, podcasts, and articles from the Thoughtworks Engelberg retreat.
"""

import os
import sys
from typing import List, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
code_dir = os.path.join(project_root, "code")

for p in [code_dir, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.base_scraper import BaseScraper
from common.models import Article

class FutureSoftwareDevelopmentScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_dir=current_dir)

    def sync_data(self) -> int:
        """
        Synchronizes FOSE articles in data.json.
        """
        print(f"[FutureSoftwareDevelopment] Synced {len(self.articles)} FOSE articles.")
        self.save_data()
        return len(self.articles)

if __name__ == "__main__":
    scraper = FutureSoftwareDevelopmentScraper()
    scraper.sync_data()
