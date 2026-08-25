"""Dear Architects scraper using the shared MailerLite implementation."""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
code_dir = os.path.join(project_root, "code")
for path in (code_dir, project_root):
    if path not in sys.path:
        sys.path.insert(0, path)

from common.mailerlite_scraper import MailerLiteScraper


class DearArchitectsScraper(MailerLiteScraper):
    api_endpoint = (
        "https://assets.mailerlite.com/jsonp/1235400/recent-emails/"
        "c6c6dffbc838e26c96033e6029092723e53f2a0f7ec2b099bd6dd294a0b33e00"
        "?limit=50&offset=0"
    )
    article_id_prefix = "da"
    newsletter_name = "Dear Architects"
    blocked_link_terms = ("deararchitects.xyz",)
    archive_pages = (
        "https://deararchitects.xyz/",
        "https://www.deararchitects.xyz/archive",
    )
    log_name = "DearArchitects"

    def __init__(self):
        super().__init__(source_dir=current_dir)


if __name__ == "__main__":
    DearArchitectsScraper().discover_and_ingest_new_issues()
