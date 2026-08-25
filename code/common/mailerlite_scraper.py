"""Shared MailerLite newsletter discovery and parsing."""

import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

from common.base_scraper import BaseScraper
from common.models import Article, ParsedIssueInfo, Quote


class _PublicationMetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values: List[str] = []
        self._json_ld = False
        self.json_ld: List[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "meta":
            marker = (
                attributes.get("property")
                or attributes.get("name")
                or attributes.get("itemprop")
            )
            if marker in {
                "article:published_time",
                "date",
                "publish-date",
                "publication_date",
                "datePublished",
            }:
                self.values.append(attributes.get("content", ""))
        elif tag == "time":
            self.values.append(attributes.get("datetime", ""))
        elif tag == "script" and attributes.get("type") == "application/ld+json":
            self._json_ld = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._json_ld = False

    def handle_data(self, data):
        if self._json_ld:
            self.json_ld.append(data)


class MailerLiteScraper(BaseScraper):
    """Common implementation for newsletters published through MailerLite."""

    api_endpoint = ""
    article_id_prefix = ""
    newsletter_name = ""
    blocked_link_terms: Tuple[str, ...] = ()
    archive_pages: Tuple[str, ...] = ()
    log_name = "MailerLite"
    extract_article_authors = True

    @staticmethod
    def parse_publication_date(value: Any) -> Optional[datetime]:
        """Parse MailerLite/API/page dates without assuming a weekly cadence."""
        if value in (None, ""):
            return None
        if isinstance(value, (int, float)):
            timestamp = float(value)
            if timestamp > 10_000_000_000:
                timestamp /= 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)

        text = str(value).strip()
        if not text:
            return None
        if text.isdigit():
            return MailerLiteScraper.parse_publication_date(int(text))

        iso_text = text.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(iso_text)
        except ValueError:
            pass
        try:
            return parsedate_to_datetime(text)
        except (TypeError, ValueError):
            pass
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d %B %Y",
            "%B %d, %Y",
        ):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    @classmethod
    def publication_date_from_mail(cls, mail: Dict[str, Any]) -> Optional[datetime]:
        for key in ("date", "sent_at", "sentAt", "send_at", "published_at", "created_at"):
            parsed = cls.parse_publication_date(mail.get(key))
            if parsed:
                return parsed
        return None

    @classmethod
    def publication_date_from_html(cls, html: str) -> Optional[datetime]:
        parser = _PublicationMetadataParser()
        parser.feed(html)
        for value in parser.values:
            parsed = cls.parse_publication_date(value)
            if parsed:
                return parsed
        for raw_json in parser.json_ld:
            try:
                payload = json.loads(raw_json)
            except json.JSONDecodeError:
                continue
            objects = payload if isinstance(payload, list) else [payload]
            for obj in objects:
                if isinstance(obj, dict):
                    parsed = cls.parse_publication_date(
                        obj.get("datePublished") or obj.get("dateCreated")
                    )
                    if parsed:
                        return parsed
        return None

    @staticmethod
    def format_publication_date(dt: datetime) -> Tuple[str, str]:
        date_iso = dt.date().isoformat()
        date_str = dt.strftime("%d %B %Y").lstrip("0")
        return date_iso, date_str

    def parse_subject(self, subject: str) -> Optional[Tuple[int, str]]:
        match = re.search(r"#(\d+)\s*[-—–]?\s*(.*)", subject)
        if match:
            return int(match.group(1)), match.group(2).strip()
        reverse = re.search(r"(.*?)\s*[-—–]?\s*#(\d+)", subject)
        if reverse:
            return int(reverse.group(2)), reverse.group(1).strip()
        return None

    def issue_title(self, number: int, parsed_title: str) -> str:
        return parsed_title or f"{self.newsletter_name} #{number}"

    def _decode_jsonp(self, raw_text: str) -> Dict[str, Any]:
        text = raw_text.strip()
        if not text.startswith(("{", "[")):
            match = re.fullmatch(r"[A-Za-z0-9_$]+\((.*)\);?", text, flags=re.DOTALL)
            if not match:
                raise ValueError(f"{self.log_name}: malformed MailerLite JSONP response")
            text = match.group(1)
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError(f"{self.log_name}: expected an object from MailerLite")
        return payload

    def fetch_mailerlite_payload(self) -> Dict[str, Any]:
        raw = self.fetch_url(
            self.api_endpoint,
            accept="application/json,text/javascript,*/*;q=0.1",
        ).decode("utf-8", errors="replace")
        return self._decode_jsonp(raw)

    def discover_from_api(self) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        for mail in self.fetch_mailerlite_payload().get("mails", []):
            subject = mail.get("subject", "")
            parsed = self.parse_subject(subject)
            preview_path = mail.get("preview_path")
            if not parsed or not preview_path:
                continue
            number, parsed_title = parsed
            url = f"https://preview.mailerlite.io/{preview_path.lstrip('/')}"
            issues.append({
                "num": number,
                "title": self.issue_title(number, parsed_title),
                "url": url,
                "published_at": self.publication_date_from_mail(mail),
            })
        return issues

    def discover_from_archive_pages(self) -> List[Dict[str, Any]]:
        from bs4 import BeautifulSoup

        issues: List[Dict[str, Any]] = []
        for page_url in self.archive_pages:
            html = self.fetch_html(page_url)
            soup = BeautifulSoup(html, "html.parser")
            for anchor in soup.find_all("a"):
                href = anchor.get("href", "").strip()
                if "preview.mailerlite.io" not in href:
                    continue
                parsed = self.parse_subject(anchor.get_text(" ", strip=True))
                if not parsed:
                    continue
                number, parsed_title = parsed
                issues.append({
                    "num": number,
                    "title": self.issue_title(number, parsed_title),
                    "url": href,
                    "published_at": None,
                })
        return issues

    @staticmethod
    def _deduplicate_discovered(
        issues: List[Dict[str, Any]],
        known_issue_urls: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        by_url: Dict[str, Dict[str, Any]] = {}
        for issue in issues:
            by_url.setdefault(issue["url"], issue)

        by_number: Dict[int, List[Dict[str, Any]]] = {}
        for issue in by_url.values():
            by_number.setdefault(issue["num"], []).append(issue)

        known_issue_urls = known_issue_urls or {}
        result = []
        conflicts = {}
        for number, numbered_issues in by_number.items():
            if len(numbered_issues) == 1:
                result.append(numbered_issues[0])
                continue

            known_url = known_issue_urls.get(str(number))
            if known_url:
                canonical_known = BaseScraper.canonical_link(known_url)
                matching = [
                    issue for issue in numbered_issues
                    if BaseScraper.canonical_link(issue["url"]) == canonical_known
                ]
                # Preserve the already-tracked issue if it is present; quarantine the
                # ambiguous historical extras without blocking unrelated new issues.
                if matching:
                    result.append(matching[0])
                print(
                    f"[MailerLite] Historical issue #{number} maps to "
                    f"{len(numbered_issues)} URLs; ambiguous extras were skipped."
                )
                continue

            conflicts[number] = {issue["url"] for issue in numbered_issues}

        if conflicts:
            details = ", ".join(
                f"#{num}: {len(urls)} URLs" for num, urls in sorted(conflicts.items())
            )
            raise ValueError(
                "Duplicate issue numbers discovered; refusing to guess corrected numbering: "
                + details
            )
        return result

    def extract_quotes(self, soup) -> List[Quote]:
        quotes = []
        for blockquote in soup.find_all("blockquote"):
            text = blockquote.get_text(separator=" ", strip=True)
            if "—" not in text and "-" not in text:
                continue
            parts = re.split(r"[-—–]\s*", text, maxsplit=1)
            quotes.append(Quote(
                text=parts[0].strip('“"” '),
                author=parts[1].strip() if len(parts) > 1 else "Unknown",
            ))
        if quotes:
            return quotes

        for tag in soup.find_all(["h2", "p"]):
            text = tag.get_text(separator=" ", strip=True)
            if not text.startswith(('"', "“")) or len(text) <= 25 or tag.find("a"):
                continue
            parent = tag.find_parent("table") or tag.find_parent("div")
            if not parent:
                continue
            siblings = [
                node.get_text(" ", strip=True)
                for node in parent.find_all(["p", "div", "h2", "h3"])
                if node.get_text(strip=True)
            ]
            author = "Unknown"
            for index, sibling in enumerate(siblings):
                if text in sibling and index + 1 < len(siblings):
                    candidate = siblings[index + 1]
                    if len(candidate.split()) <= 5 and not candidate.startswith(('"', "“")):
                        author = candidate.strip("—–- ")
                    break
            return [Quote(text=text.strip('“"” '), author=author)]
        return []

    def parse_issue_html(
        self,
        html: str,
        issue_number: Optional[int],
        issue_title: str,
        issue_link: str,
        date_iso: str,
        date_str: str,
    ) -> List[Article]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        self._last_quotes = self.extract_quotes(soup)
        articles: List[Article] = []
        seen_links = set()

        for header in soup.find_all(["h1", "h2", "h3"]):
            anchor = header.find("a")
            if not anchor or not anchor.get("href"):
                continue
            clean_link = self.clean_url(anchor["href"].strip())
            lower_link = clean_link.lower()
            if (
                not clean_link
                or "unsubscribe" in lower_link
                or "mailerlite.com" in lower_link
                or any(term in lower_link for term in self.blocked_link_terms)
                or clean_link in seen_links
            ):
                continue

            title = anchor.get_text(" ", strip=True).replace("&amp;", "and").replace("&", "and")
            if not title or title.lower() == "in the spotlight":
                continue
            if self.is_sponsor_link(clean_link, title) or self.is_boilerplate(title, clean_link):
                continue

            is_spotlight = header.name == "h1" or "in the spotlight" in title.lower()
            title = re.sub(
                r"\s*-\s*in the spotlight",
                "",
                title,
                flags=re.IGNORECASE,
            ).strip()
            parent = header.find_parent("table") or header.find_parent("div")
            description = ""
            author = None
            if parent:
                if "spotlight" in parent.get_text(" ", strip=True).lower():
                    is_spotlight = True
                if self.extract_article_authors:
                    for strong in parent.find_all("strong"):
                        candidate = strong.get_text(" ", strip=True)
                        if (
                            0 < len(candidate.split()) <= 4
                            and candidate.lower() not in title.lower()
                            and "spotlight" not in candidate.lower()
                        ):
                            author = candidate
                            break
                parts = []
                for paragraph in parent.find_all("p"):
                    text = paragraph.get_text(" ", strip=True).replace("&amp;", "and")
                    if (
                        len(text) > 20
                        and title.lower() not in text.lower()
                        and "mailerlite" not in text.lower()
                    ):
                        parts.append(text)
                description = " ".join(parts)

            articles.append(Article(
                id=self.make_article_id(
                    self.article_id_prefix, issue_number, clean_link, title
                ),
                newsletter=self.newsletter_name,
                issue_number=issue_number,
                issue_title=issue_title,
                issue_link=issue_link,
                date=date_iso,
                date_str=date_str,
                title=title,
                link=clean_link,
                author=author,
                description=description,
                category=self.auto_categorize(title, description),
                is_spotlight=is_spotlight,
                type=self.detect_content_type(clean_link),
                hide=False,
                user_overrides=[],
                metadata={},
            ))
            seen_links.add(clean_link)
        return articles

    def ingest_issue(
        self,
        issue_number: Optional[int],
        issue_title: str,
        issue_url: str,
        published_at: Optional[datetime] = None,
    ) -> int:
        html = self.fetch_html(issue_url)
        actual_date = published_at or self.publication_date_from_html(html)
        if not actual_date:
            raise ValueError(
                f"{self.log_name} issue #{issue_number} has no authoritative publication date "
                "in MailerLite metadata or page metadata; refusing arithmetic fallback."
            )
        date_iso, date_str = self.format_publication_date(actual_date)
        parsed_articles = self.parse_issue_html(
            html, issue_number, issue_title, issue_url, date_iso, date_str
        )
        if not parsed_articles:
            print(f"[{self.log_name}] Warning: no articles extracted for issue #{issue_number}.")
            return 0

        merged_count = self.merge_articles(parsed_articles)
        issue_id = str(issue_number) if issue_number is not None else date_iso
        existing = list(self.definition.parsed_issues.issues) if self.definition else []
        existing_by_id = {issue.id: issue for issue in existing}
        existing_by_id[issue_id] = ParsedIssueInfo(
            id=issue_id,
            date=date_iso,
            date_str=date_str,
            title=issue_title,
            url=issue_url,
            quotes=list(getattr(self, "_last_quotes", [])),
        )
        self.sync_parsed_issues(list(existing_by_id.values()))
        self.save_data()
        return merged_count

    def discover_and_ingest_new_issues(self, reparse_all: bool = False) -> int:
        known_ids = set()
        known_issue_urls = {}
        if self.definition and not reparse_all:
            known_ids = {str(issue.id) for issue in self.definition.parsed_issues.issues}
            known_issue_urls = {
                str(issue.id): issue.url for issue in self.definition.parsed_issues.issues
            }

        discovered = self.discover_from_api()
        if self.archive_pages:
            discovered.extend(self.discover_from_archive_pages())
        discovered = self._deduplicate_discovered(discovered, known_issue_urls)
        discovered = [
            issue for issue in discovered
            if reparse_all or str(issue["num"]) not in known_ids
        ]
        discovered.sort(key=lambda issue: issue["num"])
        if not discovered:
            print(f"[{self.log_name}] No new unparsed issues found.")
            return 0

        total = 0
        for issue in discovered:
            total += self.ingest_issue(
                issue_number=issue["num"],
                issue_title=issue["title"],
                issue_url=issue["url"],
                published_at=issue["published_at"],
            )
        return total
