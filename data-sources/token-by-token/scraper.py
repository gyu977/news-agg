"""Token by Token scraper using the shared MailerLite implementation."""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
code_dir = os.path.join(project_root, "code")
for path in (code_dir, project_root):
    if path not in sys.path:
        sys.path.insert(0, path)

from common.mailerlite_scraper import MailerLiteScraper


class TokenByTokenScraper(MailerLiteScraper):
    api_endpoint = (
        "https://assets.mailerlite.com/jsonp/2096144/recent-emails/"
        "0371fada216137b32c04343dc4ad33a6140353a621bb0d8111810301386e7619"
        "?limit=50&offset=0"
    )
    article_id_prefix = "tbt"
    newsletter_name = "Token by Token"
    blocked_link_terms = ("tokenbytoken.ai",)
    log_name = "TokenByToken"
    extract_article_authors = False

    def __init__(self):
        super().__init__(source_dir=current_dir)

    def issue_title(self, number, parsed_title):
        title = parsed_title or f"Token by Token #{number}"
        return title if "token" in title.lower() else f"Token by Token #{number} - {title}"


if __name__ == "__main__":
    TokenByTokenScraper().discover_and_ingest_new_issues()
