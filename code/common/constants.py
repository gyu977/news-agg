"""
Canonical categories, content types, and visual markers for the news-agg ETL pipeline.
"""

CATEGORIES = [
    "AI-Native & Agentic Software Engineering",
    "Large Language Models & Evaluation Infrastructure",
    "Software Architecture & Distributed Systems",
    "Software Testing, Quality & Observability",
    "Cloud Infrastructure & System Reliability",
    "Tech Industry, Jobs & Careers",
    "Engineering Philosophy & Estimation"
]

CONTENT_TYPES = ["article", "video", "book", "pulse", "presentation", "conference"]

VISUAL_MARKERS = {
    "book": "📖",
    "video": "▶️",
    "pulse": "⚡",
    "presentation": "🎤",
    "conference": "🎟️",
    "article": ""
}

# Domain-based marker rules
DOMAIN_MARKER_RULES = [
    (["youtube.com", "youtu.be", "gitnation.com"], "video"),
    (["manning.com", "oreilly.com", "amazon.com", "amzn.to", "link.amazon"], "book")
]

# Excluded sponsors / tracking domains unless explicitly whitelisted.
# Newsletter sponsor slots are almost always routed through an ad network or a link
# shortener, so the domain is the reliable signal — the ad copy itself varies weekly.
SPONSOR_DOMAINS = [
    "fandf.co",          # F&F ad network
    "fnf.dev",           # F&F ad network (the domain actually used by Dear Architects)
    "go.rbrk.co",        # Rubrik campaign links
    "theaiplatform.app",
    # Link shorteners: used exclusively for paid slots in the tracked newsletters, and
    # they hide the destination from every other heuristic here.
    "bit.ly",
    "tinyurl.com",
    "t.co/",
    "lnkd.in",
]

# Sponsored links that are kept anyway, matched against the article title/description.
# These are paid placements whose content is still genuinely useful to readers.
SPONSOR_WHITELIST_TERMS = [
    "qconferences.com",
    "honeycomb",
    "observability engineering",
    "observability day",
]

# --- Content-quality guards (M9) -------------------------------------------------
# Newsletter templates surround real articles with subscribe prompts, social CTAs and
# footer chrome. When a heading loop picks up one of these it becomes an "article"
# whose title is a UI string. Matched case-insensitively against the *whole* title,
# after whitespace collapsing.
BOILERPLATE_TITLES = [
    "subscribe to receive an email when this happens",
    "subscribe",
    "subscribe now",
    "unsubscribe",
    "read more",
    "read online",
    "view in browser",
    "view this email in your browser",
    "click here",
    "learn more",
    "sign up",
    "share this",
    "forward to a friend",
    "update your preferences",
    "manage your subscription",
    "privacy policy",
    "terms of service",
    "follow me on linkedin",
    "follow us",
    "sponsored",
    "advertisement",
    "in the spotlight",
    "until next week",
    "see you next week",
    "thanks for reading",
]

# Titles shorter than this are *probably* truncation artefacts ("Flint", "Archi").
# This is only a reporting signal, never an auto-hide: plenty of real headlines are
# short ("GLM-5.2", "Kimi K3", "Reddit"), and a truncated title still points at a real
# article, so discarding it would lose content that a human can instead repair.
MIN_TITLE_LENGTH = 12

# Link schemes that can never be an article destination.
NON_ARTICLE_SCHEMES = ("mailto:", "tel:", "javascript:", "sms:")
