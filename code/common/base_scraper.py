"""
BaseScraper class providing in-memory HTTP fetching with retry, redirect resolving,
sponsor filtering, auto-categorization, and field-level merge logic for all news sources.
"""

import os
import re
import json
import time
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import urllib.robotparser
from typing import List, Dict, Any, Optional

try:
    from common.models import Article, SourceDefinition, Quote, ParsedIssueInfo
    from common.constants import CATEGORIES, DOMAIN_MARKER_RULES, SPONSOR_DOMAINS, SPONSOR_WHITELIST_TERMS, BOILERPLATE_TITLES, MIN_TITLE_LENGTH, NON_ARTICLE_SCHEMES
except ImportError:
    from code.common.models import Article, SourceDefinition, Quote, ParsedIssueInfo
    from code.common.constants import CATEGORIES, DOMAIN_MARKER_RULES, SPONSOR_DOMAINS, SPONSOR_WHITELIST_TERMS, BOILERPLATE_TITLES, MIN_TITLE_LENGTH, NON_ARTICLE_SCHEMES

class BaseScraper:
    USER_AGENT = "news-agg/1.0 (+https://github.com/gyu977/news-agg; contact via GitHub issues)"
    REQUEST_DELAY_SECONDS = 1.0

    def __init__(self, source_dir: str):
        self.source_dir = source_dir
        self.definition_path = os.path.join(source_dir, "definition.json")
        self.data_path = os.path.join(source_dir, "data.json")
        
        self.definition: Optional[SourceDefinition] = None
        self.articles: List[Article] = []
        self._last_request_at = 0.0
        self._robots = {}
        self.load_data()

    def load_data(self):
        if os.path.exists(self.definition_path):
            with open(self.definition_path, "r", encoding="utf-8") as f:
                self.definition = SourceDefinition.from_dict(json.load(f))
        
        if os.path.exists(self.data_path):
            with open(self.data_path, "r", encoding="utf-8") as f:
                raw_articles = json.load(f)
                self.articles = [Article.from_dict(a) for a in raw_articles]

    def save_data(self):
        if self.definition:
            with open(self.definition_path, "w", encoding="utf-8") as f:
                json.dump(self.definition.to_dict(), f, indent=2, ensure_ascii=False)
                
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump([a.to_dict() for a in self.articles], f, indent=2, ensure_ascii=False)

    def _robots_allowed(self, url: str) -> bool:
        """Return whether this scraper may fetch URL according to the site's robots.txt."""
        parsed = urllib.parse.urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots:
            robots_url = urllib.parse.urljoin(origin, "/robots.txt")
            parser = urllib.robotparser.RobotFileParser(robots_url)
            try:
                self._throttle()
                request = urllib.request.Request(
                    robots_url,
                    headers={"User-Agent": self.USER_AGENT, "Accept": "text/plain"},
                )
                with urllib.request.urlopen(request, timeout=10) as response:
                    self._last_request_at = time.monotonic()
                    lines = response.read().decode("utf-8", errors="replace").splitlines()
                parser.parse(lines)
            except urllib.error.HTTPError as exc:
                self._last_request_at = time.monotonic()
                if exc.code != 404:
                    print(f"[BaseScraper] Could not read {robots_url} (HTTP {exc.code}); allowing request.")
                parser.parse([])
            except (urllib.error.URLError, OSError) as exc:
                self._last_request_at = time.monotonic()
                print(f"[BaseScraper] Could not read {robots_url} ({exc}); allowing request.")
                parser.parse([])
            self._robots[origin] = parser
        return self._robots[origin].can_fetch(self.USER_AGENT, url)

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.REQUEST_DELAY_SECONDS - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def fetch_url(
        self,
        url: str,
        max_retries: int = 3,
        timeout: int = 15,
        accept: str = "text/html,application/xhtml+xml",
    ) -> bytes:
        """Fetch a URL with robots checks, an honest UA, throttling, and retry backoff."""
        if not self._robots_allowed(url):
            raise PermissionError(f"robots.txt disallows fetching {url}")

        req = urllib.request.Request(
            url,
            headers={"User-Agent": self.USER_AGENT, "Accept": accept},
        )
        last_err = None
        for attempt in range(1, max_retries + 1):
            try:
                self._throttle()
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    self._last_request_at = time.monotonic()
                    return response.read()
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                self._last_request_at = time.monotonic()
                last_err = exc
                print(f"[BaseScraper] Attempt {attempt}/{max_retries} failed for URL {url}: {exc}")
                if attempt < max_retries:
                    time.sleep(attempt * 1.5)
        raise last_err

    def fetch_html(self, url: str, max_retries: int = 3) -> str:
        """Fetch HTML in-memory through the shared crawl policy."""
        return self.fetch_url(url, max_retries=max_retries).decode("utf-8", errors="replace")

    def fetch_json(self, url: str, max_retries: int = 3) -> Any:
        """Fetch and decode a JSON response through the shared crawl policy."""
        raw = self.fetch_url(
            url,
            max_retries=max_retries,
            accept="application/json,text/javascript,*/*;q=0.1",
        ).decode("utf-8", errors="replace").strip()
        return json.loads(raw)

    # Query parameters that carry tracking/attribution only and never affect the
    # resource identity. `s` is deliberately NOT here: it is a legitimate search
    # parameter on many sites (WordPress `?s=query`), unlike YouTube's `si`.
    TRACKING_PARAMS = frozenset({
        "ml_subscriber", "ml_subscriber_hash", "mc_cid", "mc_eid",
        "trk", "trkinfo", "urlhash", "li_fat_id", "originaltrk",
        "si", "fbclid", "gclid", "dclid", "msclkid", "twclid", "igshid",
        "ref", "referrer", "source", "ck_subscriber_id", "_hsenc", "_hsmi",
        "vero_id", "vero_conv", "yclid", "wickedid", "oly_enc_id", "oly_anon_id",
    })

    # Prefixes matched case-insensitively against the start of a parameter name.
    TRACKING_PREFIXES = ("utm_", "mc_", "pk_", "piwik_", "matomo_", "hsa_")

    def clean_url(self, url: str) -> str:
        """
        Removes UTM tracking tags and tracking query parameters while preserving the main link.
        """
        if not url:
            return ""
        parsed = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        filtered_params = {
            k: v for k, v in query_params.items()
            if not self._is_tracking_param(k)
        }
        clean_query = urllib.parse.urlencode(filtered_params, doseq=True)
        return urllib.parse.urlunparse((
            parsed.scheme, parsed.netloc, parsed.path, parsed.params, clean_query, parsed.fragment
        ))

    @classmethod
    def _is_tracking_param(cls, name: str) -> bool:
        lowered = name.lower()
        return (
            lowered in cls.TRACKING_PARAMS
            or lowered.startswith(cls.TRACKING_PREFIXES)
        )

    @classmethod
    def canonical_link(cls, url: str) -> str:
        """
        Reduce a URL to a stable identity for deduplication and ID generation.

        Beyond `clean_url`, this lowercases the host, drops `www.`, strips the
        fragment and any trailing slash, normalises the scheme to https and sorts
        the surviving query parameters, so that two spellings of the same article
        produce one key. The result is used for comparison only — the original
        `link` remains what the dashboard opens.
        """
        if not url:
            return ""
        parsed = urllib.parse.urlparse(url.strip())
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        # Drop a default port so :443/:80 spellings collapse together.
        for scheme_port in (":80", ":443"):
            if netloc.endswith(scheme_port):
                netloc = netloc[: -len(scheme_port)]
        path = parsed.path.rstrip("/") or "/"
        params = sorted(
            (k.lower(), v)
            for k, v in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            if not cls._is_tracking_param(k)
        )
        query = urllib.parse.urlencode(params, doseq=False)
        scheme = "https" if parsed.scheme in ("http", "https", "") else parsed.scheme
        return urllib.parse.urlunparse((scheme, netloc, path, "", query, ""))

    @classmethod
    def make_article_id(cls, prefix: str, issue: Any, link: str, title: str = "") -> str:
        """
        Build a stable, collision-resistant article id: `{prefix}-{issue}-{hash6}`.

        The hash is derived from the canonical link (falling back to the normalised
        title), so the id survives re-scrapes, renumbering and reordering — unlike
        the positional `{prefix}-{issue}-{index}` scheme it replaces, where a
        restarting index produced the same id for unrelated articles.
        """
        basis = cls.canonical_link(link) or " ".join((title or "").lower().split())
        digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:6]
        segment = str(issue).strip() if issue not in (None, "") else "x"
        return f"{prefix}-{segment}-{digest}"

    def is_sponsor_link(self, url: str, title: str = "", whitelist_terms: Optional[List[str]] = None) -> bool:
        """
        Detects sponsored/affiliate links based on domain patterns and whitelist rules.

        Whitelist terms are matched against the URL *and* the title, so a carve-out can
        be expressed either as a domain to keep or as a phrase to keep.
        """
        whitelist = whitelist_terms if whitelist_terms is not None else SPONSOR_WHITELIST_TERMS
        haystack = f"{url} {title}".lower()
        if any(term.lower() in haystack for term in whitelist):
            return False

        lower_url = url.lower()
        # A source's own list *extends* the global one; it must never shadow it, or a
        # stale per-source entry silently disables every globally-known ad domain.
        source_sponsors = list(SPONSOR_DOMAINS)
        if self.definition and self.definition.sponsor_domains:
            source_sponsors += [d for d in self.definition.sponsor_domains if d not in source_sponsors]
        for sp_domain in source_sponsors:
            if sp_domain in lower_url:
                return True
        return False

    def is_boilerplate(self, title: str, url: str = "") -> bool:
        """
        True when a scraped heading is newsletter chrome rather than an article (M9).

        Deliberately high-confidence only — an exact deny-list match or a link scheme
        that cannot be an article. Short/truncated titles are *not* included: see
        `is_suspicious_title`, which reports rather than discards.
        """
        collapsed = " ".join((title or "").split())
        if not collapsed:
            return True
        if collapsed.lower().strip(" .:!?-–—") in BOILERPLATE_TITLES:
            return True
        if (url or "").strip().lower().startswith(NON_ARTICLE_SCHEMES):
            return True
        return False

    def is_suspicious_title(self, title: str) -> bool:
        """True when a title looks truncated. Reporting signal only — never hides."""
        collapsed = " ".join((title or "").split())
        return 0 < len(collapsed) < MIN_TITLE_LENGTH

    # Explicit sponsorship markers only. A bare `"sponsor" in line` substring also
    # matches headlines *about* sponsorship ("How open source sponsorship works") and
    # silently discarded them, so the marker must be a recognisable label.
    _SPONSOR_MARKER_RE = re.compile(
        r"(\[\s*sponsor(ed|)\s*\]"
        r"|\(\s*sponsor(ed|)\s*\)"
        r"|^\s*sponsor(ed|)\s*[:\-–—]"
        r"|\bsponsored\s+(by|content|post|link)\b"
        r"|\bpresented\s+by\b"
        r"|\bin\s+partnership\s+with\b"
        r"|\bpaid\s+(partnership|promotion)\b)",
        re.IGNORECASE,
    )

    @classmethod
    def has_sponsor_marker(cls, line: str) -> bool:
        """True when a newsletter line carries an explicit paid-placement label."""
        return bool(cls._SPONSOR_MARKER_RE.search(line or ""))

    def sync_parsed_issues(self, issues: List[Dict], sort_desc: bool = True) -> None:
        """
        Single source of truth for `definition.parsed_issues` (M2).

        `count` counts *issues*, `last_parsed_*` always describe the newest issue, and
        `issues` is kept sorted newest-first. Callers pass plain dicts or
        ParsedIssueInfo; previously each scraper maintained these four fields by hand
        and each got a different subset wrong.
        """
        if not self.definition:
            return

        infos = [i if isinstance(i, ParsedIssueInfo) else ParsedIssueInfo.from_dict(i) for i in issues]
        if sort_desc:
            infos.sort(key=lambda i: (i.date or "", i.id or ""), reverse=True)

        track = self.definition.parsed_issues
        track.issues = infos
        track.count = len(infos)
        track.last_parsed_issue = infos[0].id if infos else ""
        track.last_parsed_date = infos[0].date if infos else ""

    def detect_content_type(self, url: str) -> str:
        """Detect content type based on URL domain patterns."""
        for domains, content_type in DOMAIN_MARKER_RULES:
            for d in domains:
                if d in url.lower():
                    return content_type
        return "article"

    def auto_categorize(self, title: str, description: str = "") -> str:
        """Classify article into one of the 7 subject categories."""
        text = f"{title} {description}".lower()
        
        keywords_map = [
            ("AI-Native & Agentic Software Engineering", [
                "claude code", "loop", "agent", "vibe coding", "ai writes the code", 
                "ai-native", "ai reviewer", "ai-generated code", "ai product", "ai tools", 
                "agentic", "slow ai", "coder", "prompting", "spec-driven", "codex"
            ]),
            ("Large Language Models & Evaluation Infrastructure", [
                "evaluation", "model", "parameter", "quantization", "benchmarks", 
                "glm-5.2", "kimi", "open-weight", "small language model", "evals", 
                "gpt2", "kimi3", "gpt-4", "how models learn"
            ]),
            ("Software Architecture & Distributed Systems", [
                "architecture", "microservices", "microservice", "micro-frontend", 
                "modular", "systems design", "structural", "skeleton architecture", 
                "architects", "architecting", "adr", "service topology"
            ]),
            ("Software Testing, Quality & Observability", [
                "test", "testing", "observability", "qa", "repair at scale", "quality", 
                "sapfix", "observability engineering", "reproducible environments"
            ]),
            ("Cloud Infrastructure & System Reliability", [
                "cloud", "security", "dsql", "balancing", "sidecar", "topology", 
                "multi-region", "oltp", "aurora dsql", "load balancing", "spotify podcasts"
            ]),
            ("Tech Industry, Jobs & Careers", [
                "job", "hiring", "hiring managers", "career", "senior dev", "economy", 
                "market", "salary", "luck filter", "developers", "employment"
            ]),
            ("Engineering Philosophy & Estimation", [
                "math", "philosophy", "factories", "factory", "fundamental", "unconference", 
                "reflections", "retreat", "worthy of the judgment", "fose", "napkin math", "human"
            ])
        ]
        
        # Score every category instead of returning the first substring hit, so that a
        # single incidental keyword cannot outrank a category with several real matches.
        # Matches are deduplicated by text span, so overlapping keywords that describe
        # the same word (e.g. "microservice" and "microservices") only count once.
        best_category, best_score = None, 0.0
        for category, keywords in keywords_map:
            spans = {}
            for kw in keywords:
                for m in self._compiled_keyword(kw).finditer(text):
                    # Multi-word phrases are far more specific than single tokens.
                    weight = 1.0 + 0.5 * kw.count(" ")
                    span = m.span()
                    if weight > spans.get(span, 0.0):
                        spans[span] = weight
            score = sum(spans.values())
            if score > best_score:
                best_category, best_score = category, score

        return best_category or "Engineering Philosophy & Estimation"

    # Cache of compiled keyword patterns, built lazily on first categorisation.
    _KEYWORD_PATTERNS: Dict[str, Any] = {}

    @classmethod
    def _compiled_keyword(cls, keyword: str):
        """
        Compile a keyword into a word-boundary pattern, tolerating a plural 's'.
        Custom boundaries (rather than \\b) are used so keywords containing '-' or '.'
        such as 'micro-frontend' or 'glm-5.2' still match correctly.
        """
        pattern = cls._KEYWORD_PATTERNS.get(keyword)
        if pattern is None:
            pattern = re.compile(r"(?<!\w)" + re.escape(keyword) + r"s?(?!\w)")
            cls._KEYWORD_PATTERNS[keyword] = pattern
        return pattern

    def _article_key(self, art: Article) -> str:
        """
        Generate a robust unique composite identifier for article matching during merges.
        Prioritizes canonical link, then explicit ID, then normalized title.
        """
        link = self.canonical_link(art.link or "")
        if link:
            return f"link:{link}"
        art_id = (art.id or "").strip()
        if art_id:
            return f"id:{art_id}"
        title = " ".join((art.title or "").strip().lower().split())
        return f"title:{title}"

    def merge_articles(self, incoming_articles: List[Article]) -> int:
        """
        Merge new scraped articles into existing storage, strictly preserving
        fields specified in 'user_overrides' for existing articles.
        Matches articles by robust composite key (link, ID, or title).
        """
        existing_by_key = {self._article_key(a): a for a in self.articles}
        
        updated_count = 0
        for new_art in incoming_articles:
            key = self._article_key(new_art)
            match = existing_by_key.get(key)
            if match:
                for field_name in ["category", "hide", "title", "description", "author", "type", "is_spotlight"]:
                    if field_name in match.user_overrides:
                        continue
                    new_val = getattr(new_art, field_name)
                    if new_val is None:
                        continue
                    # An empty scrape result must never clobber good existing content.
                    if isinstance(new_val, str) and not new_val.strip():
                        continue
                    # Never silently un-hide a record the user has hidden.
                    if field_name == "hide" and match.hide and not new_val:
                        continue
                    setattr(match, field_name, new_val)
                updated_count += 1
            else:
                self.articles.append(new_art)
                existing_by_key[key] = new_art
                updated_count += 1

        self.articles.sort(key=lambda x: x.date, reverse=True)
        return updated_count

    def extract_issues(self) -> List[Article]:
        raise NotImplementedError("Subclasses must implement extract_issues()")
