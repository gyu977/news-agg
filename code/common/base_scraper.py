"""
BaseScraper class providing in-memory HTTP fetching with retry, redirect resolving,
sponsor filtering, auto-categorization, and field-level merge logic for all news sources.
"""

import os
import re
import json
import time
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional

try:
    from common.models import Article, SourceDefinition, Quote, ParsedIssueInfo
    from common.constants import CATEGORIES, DOMAIN_MARKER_RULES, SPONSOR_DOMAINS
except ImportError:
    from code.common.models import Article, SourceDefinition, Quote, ParsedIssueInfo
    from code.common.constants import CATEGORIES, DOMAIN_MARKER_RULES, SPONSOR_DOMAINS

class BaseScraper:
    def __init__(self, source_dir: str):
        self.source_dir = source_dir
        self.definition_path = os.path.join(source_dir, "definition.json")
        self.data_path = os.path.join(source_dir, "data.json")
        
        self.definition: Optional[SourceDefinition] = None
        self.articles: List[Article] = []
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

    def fetch_html(self, url: str, max_retries: int = 3) -> str:
        """Fetch URL content in-memory via HTTP request with retry backoff."""
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        )
        last_err = None
        for attempt in range(1, max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=15) as response:
                    return response.read().decode("utf-8", errors="replace")
            except Exception as e:
                last_err = e
                print(f"[BaseScraper] Attempt {attempt}/{max_retries} failed for URL {url}: {e}")
                if attempt < max_retries:
                    time.sleep(attempt * 1.5)
        raise last_err

    def clean_url(self, url: str) -> str:
        """
        Removes UTM tracking tags and tracking query parameters while preserving the main link.
        """
        if not url:
            return ""
        parsed = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        # Drop UTM tags, MailerLite tracking, LinkedIn tracking
        filtered_params = {
            k: v for k, v in query_params.items() 
            if not k.lower().startswith("utm_") and k.lower() not in ["ml_subscriber", "ml_subscriber_hash", "trk", "urlhash", "li_fat_id", "s"]
        }
        clean_query = urllib.parse.urlencode(filtered_params, doseq=True)
        return urllib.parse.urlunparse((
            parsed.scheme, parsed.netloc, parsed.path, parsed.params, clean_query, parsed.fragment
        ))

    def is_sponsor_link(self, url: str, title: str = "", whitelist_terms: Optional[List[str]] = None) -> bool:
        """
        Detects sponsored/affiliate links based on domain patterns and whitelist rules.
        """
        whitelist = whitelist_terms or ["observability engineering", "honeycomb"]
        lower_title = title.lower()
        if any(term in lower_title for term in whitelist):
            return False

        lower_url = url.lower()
        source_sponsors = self.definition.sponsor_domains if self.definition and self.definition.sponsor_domains else SPONSOR_DOMAINS
        for sp_domain in source_sponsors:
            if sp_domain in lower_url:
                return True
        return False

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
        
        for category, keywords in keywords_map:
            if any(kw in text for kw in keywords):
                return category
                
        return "Engineering Philosophy & Estimation"

    def _article_key(self, art: Article) -> str:
        """
        Generate a robust unique composite identifier for article matching during merges.
        Prioritizes canonical link, then explicit ID, then normalized title.
        """
        link = (art.link or "").strip()
        if link:
            return f"link:{link}"
        art_id = (art.id or "").strip()
        if art_id:
            return f"id:{art_id}"
        title = (art.title or "").strip().lower()
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
                    if field_name not in match.user_overrides:
                        new_val = getattr(new_art, field_name)
                        if new_val is not None:
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
