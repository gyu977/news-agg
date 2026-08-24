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

# Excluded sponsors / tracking domains unless explicitly whitelisted
SPONSOR_DOMAINS = ["fandf.co"]
