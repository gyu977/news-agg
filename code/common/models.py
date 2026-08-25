"""
Data models and validation contracts for the news-agg pipeline.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import json

@dataclass
class Quote:
    text: str
    author: str

    def to_dict(self) -> Dict[str, str]:
        return {"text": self.text, "author": self.author}

@dataclass
class Article:
    id: str
    newsletter: str
    issue_number: Optional[int]
    issue_title: str
    issue_link: str
    date: str
    date_str: str
    title: str
    link: str
    author: Optional[str] = None
    description: str = ""
    category: str = "Engineering Philosophy & Estimation"
    is_spotlight: bool = False
    type: str = "article"
    hide: bool = False
    user_overrides: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Article":
        return cls(
            id=data.get("id", ""),
            newsletter=data.get("newsletter", ""),
            issue_number=data.get("issue_number"),
            issue_title=data.get("issue_title", ""),
            issue_link=data.get("issue_link", ""),
            date=data.get("date", ""),
            date_str=data.get("date_str", ""),
            title=data.get("title", ""),
            link=data.get("link", ""),
            author=data.get("author"),
            description=data.get("description", ""),
            category=data.get("category", "Engineering Philosophy & Estimation"),
            is_spotlight=data.get("is_spotlight", False),
            type=data.get("type", "article"),
            hide=data.get("hide", False),
            user_overrides=data.get("user_overrides", []),
            metadata=data.get("metadata", {})
        )

@dataclass
class ParsedIssueInfo:
    id: str
    date: str
    date_str: str
    title: str
    url: str
    quotes: List[Quote] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["quotes"] = [q.to_dict() if isinstance(q, Quote) else q for q in self.quotes]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParsedIssueInfo":
        raw_quotes = data.get("quotes", [])
        parsed_quotes = []
        for q in raw_quotes:
            if isinstance(q, dict):
                parsed_quotes.append(Quote(text=q.get("text", ""), author=q.get("author", "")))
            elif isinstance(q, Quote):
                parsed_quotes.append(q)
        return cls(
            id=str(data.get("id", "")),
            date=data.get("date", ""),
            date_str=data.get("date_str", ""),
            title=data.get("title", ""),
            url=data.get("url", ""),
            quotes=parsed_quotes
        )

@dataclass
class ParsedIssuesTrack:
    count: int = 0
    issues: List[ParsedIssueInfo] = field(default_factory=list)
    last_parsed_issue: str = ""
    last_parsed_date: str = ""

@dataclass
class SourceDefinition:
    source_id: str
    name: str
    author: str
    official_site: str
    archive_url: str
    parsed_issues: ParsedIssuesTrack
    default_header: str
    short_name: str = ""
    sponsor_domains: List[str] = field(default_factory=list)
    archive_retention_days: Optional[int] = None
    has_archive: bool = True
    static: bool = False
    refresh_enabled: bool = True
    refresh_disabled_reason: str = ""
    selectors_spec: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["parsed_issues"]["issues"] = [
            iss.to_dict() if isinstance(iss, ParsedIssueInfo) else iss 
            for iss in self.parsed_issues.issues
        ]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceDefinition":
        parsed_track_raw = data.get("parsed_issues", {})
        raw_issues = parsed_track_raw.get("issues", [])
        parsed_issues_list = [
            ParsedIssueInfo.from_dict(iss) if isinstance(iss, dict) else iss
            for iss in raw_issues
        ]

        parsed_track = ParsedIssuesTrack(
            count=parsed_track_raw.get("count", len(parsed_issues_list)),
            issues=parsed_issues_list,
            last_parsed_issue=parsed_track_raw.get("last_parsed_issue", ""),
            last_parsed_date=parsed_track_raw.get("last_parsed_date", "")
        )
        return cls(
            source_id=data.get("source_id", ""),
            name=data.get("name", ""),
            author=data.get("author", ""),
            official_site=data.get("official_site", ""),
            archive_url=data.get("archive_url", ""),
            parsed_issues=parsed_track,
            default_header=data.get("default_header", ""),
            short_name=data.get("short_name") or data.get("name", ""),
            sponsor_domains=data.get("sponsor_domains", []),
            archive_retention_days=data.get("archive_retention_days"),
            has_archive=data.get("has_archive", True),
            static=data.get("static", False),
            refresh_enabled=data.get("refresh_enabled", True),
            refresh_disabled_reason=data.get("refresh_disabled_reason", ""),
            selectors_spec=data.get("selectors_spec", {})
        )
