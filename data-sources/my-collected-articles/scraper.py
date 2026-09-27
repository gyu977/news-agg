"""
Smart Inbox Processor & Ingestor for Collected Articles (Mihai V.).
Reads raw links and markdown notes from inbox files, enriches metadata from the web,
auto-categorizes, assigns visual markers (📖 Book, ▶️ Video, ⚡ Pulse, 🎤 Presentation, 🏛️ Conference),
merges into data.json, and rebuilds presentations.
"""

import os
import re
import sys
import json
import urllib.parse
from datetime import datetime
from html.parser import HTMLParser
from typing import List, Optional, Dict, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
code_dir = os.path.join(project_root, "code")

for p in [code_dir, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.base_scraper import BaseScraper
from common.models import Article


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.title_parts = []
        self.in_title = False
        self.first_time = None

    def handle_starttag(self, tag, attrs):
        attrs = {key.lower(): value for key, value in attrs if value is not None}
        if tag.lower() == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            content = attrs.get("content")
            if key and content and key not in self.meta:
                self.meta[key] = content.strip()
        elif tag.lower() == "title":
            self.in_title = True
        elif tag.lower() == "time" and not self.first_time:
            self.first_time = attrs.get("datetime")

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self):
        return " ".join("".join(self.title_parts).split())


class MyCollectedArticlesScraper(BaseScraper):
    INBOX_PLACEHOLDER = "*(Drop new articles here)*"

    KNOWN_DOMAIN_AUTHORS = {
        "dananthony.net": "Dan Anthony",
        "incident.io": "incident.io",
        "adamtornhill.substack.com": "Adam Tornhill",
        "linkedin.com/pulse/100-most-watched": "Tech Talks Weekly",
        "lucumr.pocoo.org": "Armin Ronacher",
        "nick-tune.me": "Nick Tune",
    }

    def __init__(self):
        super().__init__(source_dir=current_dir)

    def load_all_existing_links(self) -> Dict[str, str]:
        """Maps canonical link to source name across all data sources."""
        links = {}
        sources_dir = os.path.join(project_root, "data-sources")
        if not os.path.isdir(sources_dir):
            return links
        for entry in os.listdir(sources_dir):
            data_file = os.path.join(sources_dir, entry, "data.json")
            if os.path.isfile(data_file):
                try:
                    with open(data_file, "r", encoding="utf-8") as f:
                        arts = json.load(f)
                    for a in arts:
                        c_link = self.clean_url(a.get("link") or "")
                        if c_link:
                            links[c_link] = a.get("newsletter") or entry
                except Exception:
                    pass
        return links

    def extract_web_metadata(self, url: str) -> Dict[str, Optional[str]]:
        """
        Fetches a web page to extract OpenGraph metadata (title, description, author, date).
        """
        meta = {
            "title": None,
            "description": "",
            "author": None,
            "date": None,
            "date_str": None
        }

        # Known manual fallbacks for sites that block web scraping (e.g. O'Reilly library, PDFs)
        if "building-resilient-distributed" in url:
            meta["title"] = "Building Resilient Distributed Systems"
            meta["author"] = "O'Reilly"
            meta["description"] = "Patterns and practices for building and operating resilient distributed systems."
            meta["date"] = "2026-08-15"
            meta["date_str"] = "15 August 2026"
            return meta

        if "regenerative-software" in url:
            meta["title"] = "Regenerative Software"
            meta["author"] = "O'Reilly"
            meta["description"] = "A guide to building software architectures that adapt, heal, and evolve over time."
            meta["date"] = "2026-08-15"
            meta["date_str"] = "15 August 2026"
            return meta

        if "agentic-engineering" in url:
            meta["title"] = "Agentic Engineering"
            meta["author"] = "Addy Osmani"
            meta["description"] = "Code generation has become cheap. Verification has not. As AI agents take on more of the development process, the bottleneck has moved from writing code to deciding what to build, directing agents to build it, and being able to answer for what ships."
            meta["date"] = "2026-08-28"
            meta["date_str"] = "28 August 2026"
            return meta

        if "java_at_30_essay.pdf" in url:
            meta["title"] = "Java at 30: An Essay"
            meta["author"] = "Gilad Bracha"
            meta["description"] = "Published March 2025 — An essay by Gilad Bracha reflecting on the 30th anniversary of Java, its evolution, language design trade-offs between C++ and Smalltalk, cultural artifacts in programming, and generics."
            meta["date"] = "2026-09-13"
            meta["date_str"] = "13 September 2026"
            return meta

        try:
            html = self.fetch_html(url)
            parser = MetadataParser()
            parser.feed(html)

            # Title
            meta["title"] = (
                parser.meta.get("og:title")
                or parser.meta.get("twitter:title")
                or parser.title
                or None
            )

            # Description
            meta["description"] = (
                parser.meta.get("og:description")
                or parser.meta.get("description")
                or ""
            )

            # Author
            cand_auth = (
                parser.meta.get("article:author")
                or parser.meta.get("author")
                or parser.meta.get("twitter:creator")
            )
            if cand_auth:
                if not cand_auth.startswith("@") and len(cand_auth) < 40:
                    meta["author"] = cand_auth

            # Date
            raw_dt = (
                parser.meta.get("article:published_time")
                or parser.meta.get("publication_date")
                or parser.meta.get("date")
                or parser.first_time
            )
            if raw_dt:
                try:
                    dt = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
                    meta["date"] = dt.strftime("%Y-%m-%d")
                    meta["date_str"] = dt.strftime("%d %B %Y").lstrip("0")
                except ValueError:
                    pass
        except (OSError, PermissionError, ValueError) as exc:
            print(f"[MyCollectedArticles] Warning: Could not fetch web metadata for {url}: {exc}")

        # Fallback date
        if not meta["date"]:
            now = datetime.now()
            meta["date"] = now.strftime("%Y-%m-%d")
            meta["date_str"] = now.strftime("%-d %B %Y")

        return meta

    def parse_inbox_file(self, filepath: str) -> List[Article]:
        """
        Parses articles and blocks from an inbox markdown file.
        """
        if not os.path.exists(filepath):
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Strip HTML comments
        content_no_comments = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        # Stop at Processed section
        if "## ✅ Processed Articles" in content_no_comments:
            content_no_comments = content_no_comments.split("## ✅ Processed Articles")[0]

        # Split content into paragraphs/blocks separated by blank lines or numbers
        blocks = re.split(r'\n\s*\n|\n(?=\d+\.\s+)', content_no_comments)
        parsed_articles = []
        seen_links = {a.link for a in self.articles if a.link}
        all_existing_links = self.load_all_existing_links()

        for block in blocks:
            block = block.strip()
            if not block or block.startswith("#") or block.startswith("---") or block.startswith("//"):
                continue

            # Find URLs in block
            urls = re.findall(r'https?://[^\s\)\>\]]+', block)
            if not urls:
                continue

            lines = [l.strip() for l in block.split("\n") if l.strip()]

            for raw_url in urls:
                clean_url = self.clean_url(raw_url.rstrip(".,;"))
                if not clean_url or clean_url in seen_links:
                    continue

                if clean_url in all_existing_links:
                    source_name = all_existing_links[clean_url]
                    print(f"[MyCollectedArticles] Skipping '{clean_url}': already tracked in {source_name}")
                    continue

                custom_title = None
                custom_author = None
                custom_desc = ""
                custom_date = None
                custom_date_str = None
                custom_category = None

                # Extract context from block lines
                non_url_lines = [l for l in lines if not re.search(r'https?://', l)]
                cleaned_non_url = []
                for l in non_url_lines:
                    # Clean number prefixes like "5. ", "6. "
                    l_clean = re.sub(r'^\d+\.\s*', '', l)
                    if l_clean and l_clean != self.INBOX_PLACEHOLDER:
                        cleaned_non_url.append(l_clean)

                if "barry-talk" in clean_url:
                    custom_title = "Modern Solution Architecture with Barry O'Reilly"
                    custom_author = "Barry O'Reilly"
                    custom_date = "2026-09-14"
                    custom_date_str = "14 September 2026"
                    custom_desc = "Monday, 14 September 2026, from 18.30 until 20.00 hrs (CEST). An interactive talk and masterclass session on modern solution architecture."
                elif "AI-Codecon" in clean_url:
                    custom_title = "AI Codecon: Building with Open Source AI"
                    custom_author = "O'Reilly"
                    custom_date = "2026-08-31"
                    custom_date_str = "31 August 2026"
                    custom_desc = "Join leading developers and technical experts at our virtual conference series to learn how AI is shaping new workflows, tools, and ways of building software. August 31, 2026."
                elif "codecamp.ro" in clean_url:
                    custom_title = "Codecamp Cluj-Napoca 2026"
                    custom_author = "Codecamp"
                    custom_date = "2026-10-20"
                    custom_date_str = "20 October 2026"
                    custom_desc = "20 October 2026. Conference and masterclasses covering modern software architecture, AI engineering, and craftsmanship."
                elif "frontier-engineering" in clean_url:
                    custom_title = "Frontier engineering"
                    custom_author = "Clare Liguori"
                    custom_date = "2025-09-03"
                    custom_date_str = "3 September 2025"
                    custom_desc = "A practitioner’s guide to frontier engineering. Ten principles for working with AI agents and shipping dramatically faster."
                    custom_category = "AI-Native & Agentic Software Engineering"
                elif "agentic-engineering" in clean_url:
                    custom_title = "Agentic Engineering"
                    custom_author = "Addy Osmani"
                    custom_date = "2026-08-28"
                    custom_date_str = "28 August 2026"
                    custom_desc = "Code generation has become cheap. Verification has not. As AI agents take on more of the development process, the bottleneck has moved from writing code to deciding what to build, directing agents to build it, and being able to answer for what ships."
                    custom_category = "AI-Native & Agentic Software Engineering"
                elif "threat-intelligence-report-september-2026" in clean_url:
                    custom_title = "Detecting and countering misuse of AI: September 2026"
                    custom_author = "Anthropic"
                    custom_date = "2026-09-10"
                    custom_date_str = "10 September 2026"
                    custom_desc = "Case studies from threat actors disrupted between December 2025 and August 2026 across seven areas of harm, from cyber operations and multi-agent kill chains to biological misuse."
                    custom_category = "AI-Native & Agentic Software Engineering"
                elif "we-must-pace-the-frontier" in clean_url:
                    custom_title = "We Must Pace the Frontier"
                    custom_author = "Dario Amodei"
                    custom_date = "2026-09-12"
                    custom_date_str = "12 September 2026"
                    custom_desc = "An essay by Anthropic CEO Dario Amodei on why frontier AI scaling demands deliberate pacing, third-party evaluations, and responsible capability management."
                    custom_category = "Tech Industry, Jobs & Careers"
                elif "lie-detectors" in clean_url:
                    custom_title = "Fine-Tuned Lie Detectors Failed to Generalize"
                    custom_author = "Jack Hopkins, Dipika Khullar, Rowan Wang, Fabien Roger"
                    custom_date = "2026-08-21"
                    custom_date_str = "21 August 2026"
                    custom_desc = "We trained lie detectors on on-policy lies from open-source models, but fine-tuning them didn’t generalize well to out-of-distribution cases. In these cases, fine-tuned detectors barely beat prompted baselines, and larger prompted models often beat them outright."
                    custom_category = "Large Language Models & Evaluation Infrastructure"
                elif "i-cant-keep-track-of-the-ai-stack" in clean_url:
                    custom_title = "I can’t keep track of the AI stack anymore"
                    custom_author = "Sharon Goldman"
                    custom_date = "2026-09-09"
                    custom_date_str = "9 September 2026"
                    custom_desc = "Nvidia is buying Hugging Face. OpenAI is building chips. Databricks, Salesforce and ServiceNow are sprawling across the AI technology stack. Good luck putting any of them in a box."
                    custom_category = "Tech Industry, Jobs & Careers"
                elif "java_at_30_essay.pdf" in clean_url:
                    custom_title = "Java at 30: An Essay"
                    custom_author = "Gilad Bracha"
                    custom_date = "2026-09-13"
                    custom_date_str = "13 September 2026"
                    custom_desc = "Published March 2025 — An essay by Gilad Bracha reflecting on the 30th anniversary of Java, its evolution, language design trade-offs between C++ and Smalltalk, cultural artifacts in programming, and generics."
                    custom_category = "Engineering Philosophy & Estimation"
                else:
                    if cleaned_non_url:
                        # Check first line for title/author
                        first_line = cleaned_non_url[0]
                        auth_m = re.search(r'\*\*([^*]+)\*\*', first_line)
                        if auth_m:
                            custom_author = auth_m.group(1).strip()
                        title_m = re.search(r'\[([^\]]+)\]', first_line)
                        if title_m:
                            custom_title = title_m.group(1).strip()
                        elif " - " in first_line and not first_line.lower().startswith("book"):
                            parts = first_line.split(" - ", 1)
                            custom_title = parts[1].strip()
                        elif len(first_line.split()) > 2 and not first_line.lower().startswith("book"):
                            custom_title = first_line

                        if len(cleaned_non_url) > 1:
                            custom_desc = " ".join(cleaned_non_url[1:]).strip('* ')

                # Fetch web metadata fallback
                web_meta = self.extract_web_metadata(clean_url)
                final_title = custom_title or web_meta["title"] or clean_url
                if final_title.lower().startswith("home | "):
                    final_title = final_title.split("|", 1)[1].strip()
                # Clean title suffixes like " | Dan Anthony" or " | Blog | incident.io" or " - Nick Tune"
                final_title = re.sub(r'\s*\|\s*(Blog\s*\|\s*)?[A-Za-z0-9\.\-\s]+$', '', final_title)
                final_title = re.sub(r'\s*-\s*Nick Tune$', '', final_title)
                final_title = final_title.strip()

                final_author = custom_author or web_meta["author"]
                for domain_pattern, author_name in self.KNOWN_DOMAIN_AUTHORS.items():
                    if domain_pattern in clean_url:
                        final_author = author_name
                        break

                final_desc = custom_desc or web_meta["description"] or ""
                final_date = custom_date or web_meta["date"]
                final_date_str = custom_date_str or web_meta["date_str"]

                # Detect Content Type (article, book, video, presentation, conference)
                content_type = "article"
                lower_context = (block + " " + final_title + " " + clean_url).lower()
                if "codecon" in lower_context or "codecamp" in lower_context or "conference" in lower_context or "summit" in lower_context:
                    content_type = "conference"
                elif "talk" in lower_context or "webinar" in lower_context or "presentation" in lower_context or "masterclass" in lower_context or "lecture" in lower_context:
                    content_type = "presentation"
                elif "book" in lower_context or "oreilly.com/library" in clean_url or "📖" in block:
                    content_type = "book"
                elif "youtube.com" in clean_url or "podcast" in lower_context:
                    content_type = "video"

                category = custom_category or self.auto_categorize(final_title, final_desc)
                art_id = self.make_article_id(
                    "others", (final_date or "")[:7], clean_url, final_title
                )

                # Derive clean issue title by month/year
                date_parts = final_date_str.split()
                issue_mon_year = f"{date_parts[-2]} {date_parts[-1]}" if len(date_parts) >= 2 else "Collected"

                art = Article(
                    id=art_id,
                    newsletter="Editor's Radar",
                    issue_number=None,
                    issue_title=f"{issue_mon_year} Collected Articles",
                    issue_link="",
                    date=final_date,
                    date_str=final_date_str,
                    title=final_title,
                    link=clean_url,
                    author=final_author,
                    description=final_desc,
                    category=category,
                    is_spotlight=False,
                    type=content_type,
                    hide=False,
                    user_overrides=[],
                    metadata={}
                )
                parsed_articles.append(art)
                seen_links.add(clean_url)
                print(f"[MyCollectedArticles] Ingested ({content_type}): {final_title} ({clean_url})")

        return parsed_articles

    def archive_inbox_items(self, filepath: str, ingested_articles: List[Article]):
        """
        Moves processed items into an archive section in the inbox file.
        """
        if not os.path.exists(filepath) or not ingested_articles:
            return

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        archive_block = f"\n\n### Processed on {timestamp}:\n"
        for a in ingested_articles:
            auth_str = f"**{a.author}** - " if a.author else ""
            archive_block += f"- {auth_str}[{a.title}]({a.link})\n"

        if "## ✅ Processed Articles" in content:
            parts = content.split("## ✅ Processed Articles")
            header_part = parts[0]
            if "## 📥 Articles to Process" in header_part:
                header_base = header_part.split("## 📥 Articles to Process")[0] + "## 📥 Articles to Process\n\n*(Drop new articles here)*\n\n"
            else:
                header_base = header_part
            new_content = header_base + "## ✅ Processed Articles" + archive_block + parts[1]
        else:
            if "## 📥 Articles to Process" in content:
                header_base = content.split("## 📥 Articles to Process")[0] + "## 📥 Articles to Process\n\n*(Drop new articles here)*\n\n"
            else:
                header_base = content + "\n\n"
            new_content = header_base + "## ✅ Processed Articles" + archive_block

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

    def process_all_inboxes(self) -> int:
        """
        Checks all candidate inbox files and processes any new articles.
        """
        inbox_paths = [
            os.path.join(project_root, "inbox.md")
        ]

        total_new = 0
        for path in inbox_paths:
            if os.path.exists(path):
                print(f"[MyCollectedArticles] Checking inbox at: {path}...")
                new_articles = self.parse_inbox_file(path)
                if new_articles:
                    count = self.merge_articles(new_articles)
                    self.save_data()
                    self.archive_inbox_items(path, new_articles)
                    total_new += count
                    print(f"[MyCollectedArticles] Successfully processed {len(new_articles)} items from {path}.")

        if total_new > 0:
            print(f"[MyCollectedArticles] Ingested {total_new} new articles in total.")

        # This source has no issue numbering; its natural batch is the month an item was
        # collected. The tracker was never maintained here at all, so it stayed frozen at
        # the hand-written seed value.
        if self.definition and self.articles:
            months = {}
            for a in self.articles:
                if not a.date:
                    continue
                key = a.date[:7]
                bucket = months.setdefault(key, {
                    "id": f"collected-{datetime.strptime(key, '%Y-%m').strftime('%B-%Y').lower()}",
                    "date": a.date,
                    "date_str": datetime.strptime(key, "%Y-%m").strftime("%B %Y"),
                    "title": f"Collected articles — {datetime.strptime(key, '%Y-%m').strftime('%B %Y')}",
                    "url": "",
                    "quotes": [],
                })
                if a.date > bucket["date"]:
                    bucket["date"] = a.date
            self.sync_parsed_issues(list(months.values()))
            self.save_data()

        return total_new

if __name__ == "__main__":
    scraper = MyCollectedArticlesScraper()
    scraper.process_all_inboxes()
