#!/usr/bin/env python3
"""
InfoQ Java News RSS Scraper.
Fetches and syncs Java news roundups, JEP milestones, and enterprise JVM ecosystem updates from InfoQ.
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
code_root = os.path.abspath(os.path.join(current_dir, "..", "..", "code"))
project_root = os.path.abspath(os.path.join(code_root, ".."))

for p in [code_root, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.rss_feed_scraper import RSSFeedScraper


class InfoQJavaScraper(RSSFeedScraper):
    feed_url = "https://feed.infoq.com/java/news/"
    newsletter_name = "InfoQ Java"
    article_id_prefix = "java"
    log_name = "InfoQJava"
    default_author = "Michael Redlich"

    def __init__(self):
        super().__init__(source_dir=current_dir)


if __name__ == "__main__":
    scraper = InfoQJavaScraper()
    scraper.discover_and_ingest_feed()
