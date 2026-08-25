# News Aggregator Architecture & Developer Guide (`INSTRUCTIONS.md`)

This document defines the architectural patterns, data schemas, scraper design principles, and guidelines for maintaining and expanding the `news-agg` system.

---

## 1. System Architecture

The codebase follows a modular 3-tier architecture:

```text
┌─────────────────────────────────────────────────────────────┐
│                       Data Sources                          │
│ data-sources/<id>/ (definition, data, scraper)              │
└──────────────────────────────┬──────────────────────────────┘
                               │ Ingests / Merges
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Core Engine & Models                     │
│    code/common/ (models.py, constants.py, base_scraper.py)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ Feeds into
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Publishing & Builders                    │
│   code/builders/ (build_latest, build_archive, build_news)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ Emits
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     Output Deliverables                     │
│ generated/*.md (Digests & Archives) | news.html (App)       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Standardized Source Module Structure

Every newsletter source resides in its own self-contained directory inside `data-sources/`:

```text
data-sources/<source-id>/
├── definition.json    # Source configuration, archive settings, and issue quote tracker
├── data.json          # Canonical database of all extracted articles
├── scraper.py         # Source-specific crawler/extractor inheriting from BaseScraper
└── README.md          # Source overview and scraping notes
```

---

## 3. Data Schemas & JSON Specifications

### A. `definition.json` Schema
```json
{
  "source_id": "andriy-burkov-ai",
  "name": "Artificial Intelligence (Andriy Burkov)",
  "author": "Andriy Burkov",
  "official_site": "https://www.linkedin.com/in/andriyburkov/",
  "archive_url": "https://www.linkedin.com/newsletters/artificial-intelligence-6862271403061649408/",
  "has_archive": true,
  "archive_retention_days": 90,
  "static": false,
  "refresh_enabled": true,
  "refresh_disabled_reason": "",
  "default_header": "### Andriy Burkov's Artificial Intelligence",
  "sponsor_domains": ["fandf.co"],
  "parsed_issues": {
    "count": 8,
    "issues": [
      {
        "id": 340,
        "date": "2026-08-22",
        "date_str": "22 August 2026",
        "title": "Artificial Intelligence #340",
        "url": "https://www.linkedin.com/pulse/artificial-intelligence-340-andriy-burkov-xlmpc/",
        "quotes": [
          {
            "text": "Models don't fail because they are small; they fail because their context is polluted.",
            "author": "Andriy Burkov"
          }
        ]
      }
    ],
    "last_parsed_issue": 340,
    "last_parsed_date": "2026-08-22"
  }
}
```

#### Key Properties:
* `has_archive` (`bool`): Set to `false` for one-off collections or event series (e.g. `future-software-development`, `my-collected-articles`) to skip generating cumulative archive files while still building 90-day views.
* `archive_retention_days` (`int`, optional): Set to `90` for newsletters where historical issues are pruned from the cumulative archive (e.g. LinkedIn Pulse). Leave `null` or omit for unlimited cumulative archives.
* `sponsor_domains` (`string[]`): Domains automatically filtered by `BaseScraper` (e.g. `fandf.co` affiliate links).
* `static` (`bool`): Marks curated/imported data that has no supported network refresh.
* `refresh_enabled` (`bool`): Allows `build.py --refresh` to run the source scraper. Static or policy-blocked sources set this to `false`.
* `refresh_disabled_reason` (`string`): Human-readable explanation printed when refresh skips a source.

---

### B. `data.json` Schema (Article Contract)
```json
[
  {
    "id": "da-304-26f3ca",
    "newsletter": "Dear Architects",
    "issue_number": 304,
    "issue_title": "2026: What's hype vs. reality?",
    "issue_link": "https://preview.mailerlite.io/preview/1235400/emails/196533603141682314",
    "date": "2026-08-22",
    "date_str": "22 August 2026",
    "title": "Decoupling AI Logic from Core Workflows",
    "link": "https://example.com/ai-logic",
    "author": "Luca Mezzalira",
    "description": "Examines architectural patterns for isolating fast-moving LLM integrations from stable domain business logic.",
    "category": "AI-Native & Agentic Software Engineering",
    "is_spotlight": true,
    "type": "article",
    "hide": false,
    "user_overrides": ["category"],
    "metadata": {}
  }
]
```

#### Field Rules:
* `id`: Stable article identifier in the form **`{prefix}-{issue}-{hash6}`**, where `hash6` is the
  first 6 hex digits of the SHA-1 of the *canonical* link (see below). Mint it with
  `BaseScraper.make_article_id(prefix, issue, link, title)` — never with a positional index, which
  produces collisions whenever the index restarts per issue. `{issue}` is the issue number, or the
  article's `YYYY-MM` for sources without issue numbers. Current prefixes: `da`, `tbt`, `ab`,
  `addy`, `pe`, `fose`, `others`.
* `link`: Cleaned by `BaseScraper.clean_url()`, which strips tracking parameters (`utm_*`, `si`,
  `fbclid`, `gclid`, `ref`, `mc_*`, …) while preserving meaningful ones such as `s`, `v` and `id`.
  `BaseScraper.canonical_link()` goes further (lowercased host, no `www.`, no fragment, sorted
  query) and is used **only** for identity comparison — the stored `link` stays user-facing.
* `date`: ISO 8601 string (`YYYY-MM-DD`) required for reliable chronological sorting across sources.
* `category`: Must match one of the **7 Canonical Categories** (see below).
* `type`: Content type identifier (`article`, `book`, `video`, `pulse`, `presentation`, `conference`).
* `hide` (`bool`): When `true`, the article is excluded from all Markdown digests and HTML dashboards without deleting the record.
* `user_overrides` (`string[]`): Tracks fields manually edited by the user (e.g. `["category", "description"]`). The scraper's `merge_articles()` will **never overwrite** fields listed in `user_overrides` during subsequent crawler runs.

---

## 4. Visual Markers & Content Types

The system applies visual markers across Markdown outputs and the HTML dashboard:

| Type Identifier | Visual Icon | Used For | Detection Rules |
| :--- | :---: | :--- | :--- |
| `conference` | **🎟️** | Conferences, Summits, Codecamps | `conference`, `summit`, `codecon`, `codecamp` |
| `presentation` | **🎤** | Talks, Webinars, Masterclasses, Keynotes | `talk`, `webinar`, `presentation`, `masterclass` |
| `book` | **📖** | Books & Early Release Manuscripts | `manning.com`, `oreilly.com`, `amazon.com` |
| `video` | **▶️** | Recorded Talks, Podcasts, YouTube | `youtube.com`, `youtu.be`, `podcast` |
| `pulse` | **⚡** | Weekly Pulse Summaries | `The Pulse:` title prefix |
| `article` | *(none)* | Standard technical articles & essays | Default fallback |

---

## 5. Canonical Subject Categories

All articles are classified into one of these 7 canonical categories:

1. **AI-Native & Agentic Software Engineering** — Building software with agents: loops, orchestration, context engineering, and the day-to-day craft of AI-assisted development.
2. **Large Language Models & Evaluation Infrastructure** — The models themselves: architectures, training, open weights, local inference, model specs, evals, and coding benchmarks.
3. **Software Architecture & Distributed Systems** — Boundaries and modularity: architectural decision-making, ADRs, micro frontends, microservices, DSLs, and distributed systems design.
4. **Software Testing, Quality & Observability** — Verifying software: automated repair, code-review agents, test strategy, evals-as-tests, non-functional requirements, and observability.
5. **Cloud Infrastructure & System Reliability** — Running systems at scale: databases, service topology, load balancing, sidecars, cloud security, resilience, and SRE practice.
6. **Tech Industry, Jobs & Careers** — The business around the code: AI spend and economics, industry news and incidents, hiring, and developer careers.
7. **Engineering Philosophy & Estimation** — Where the craft is heading: enduring fundamentals, mental models, napkin math estimation, and engineering culture.

> [!IMPORTANT]
> **Adding or Changing Categories**:
> If a category is added, renamed, or modified, you must update:
> 1. [`code/common/constants.py`](../code/common/constants.py) (`CATEGORIES` array).
> 2. [`code/builders/news_template.html`](../code/builders/news_template.html) (the `<ul class="source-list category-list">` inside `#categoryDesc`).
> 3. [`code/common/base_scraper.py`](../code/common/base_scraper.py) (`auto_categorize()` keyword mapping).
> 4. Rebuild deliverables with `python3 code/build.py`.

---

## 6. How to Add a New Newsletter Source

Follow this 5-step process to add a new newsletter:

### Step 1: Create Module Directory
Create `data-sources/<new-source-id>/`.

### Step 2: Create `definition.json`
Define the source metadata, archive rules, and header title.

### Step 3: Implement `scraper.py`
Subclass `BaseScraper` from `code/common/base_scraper.py`:

```python
import os
import sys
from bs4 import BeautifulSoup

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
code_dir = os.path.join(project_root, "code")

for p in [code_dir, project_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from common.base_scraper import BaseScraper
from common.models import Article

class MyNewsletterScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_dir=current_dir)

    def fetch_latest_issues(self):
        # 1. Fetch web/API content
        # 2. Extract articles into Article objects
        # 3. Use self.merge_articles(new_articles) to protect user overrides
        # 4. Use self.save_data() to commit changes
        pass

if __name__ == "__main__":
    scraper = MyNewsletterScraper()
    scraper.fetch_latest_issues()
```

### Step 4: Update Template Descriptions (`code/builders/news_template.html`)
Add the new source entry with its `data-source` identifier and description inside the `#sourceDesc` panel:
```html
<li data-source="My New Newsletter"><strong>My New Newsletter</strong> — Concise description of this source.</li>
```

### Step 5: Build & Verify
Run the master builder:
```bash
python3 code/build.py
```
The builders automatically auto-discover all directories in `data-sources/` containing a `definition.json`, generate the corresponding Markdown files in `generated/`, and compile the updated `news.html`.

---

## 7. Inbox Workflow (`inbox.md`)

To add ad-hoc articles, books, or event links:

1. Paste lines into [`inbox.md`](../inbox.md) at the project root:
   ```markdown
   ## 📥 Articles to Process

   - https://dananthony.net/blog/ai-engineering-critical-systems.html
   - **Barry O'Reilly** - [Modern Solution Architecture](https://example.com/talk)
     *Interactive masterclass session on solution architecture.*
   ```
2. Run the ingestor:
   ```bash
   python3 code/build.py --inbox
   ```
3. The scraper fetches missing OpenGraph metadata, classifies the category and content type, appends to `data-sources/my-collected-articles/data.json`, moves processed links to `## ✅ Processed Articles`, and immediately rebuilds all outputs.

---

## 8. CLI Build Options

```bash
# Build all presentation outputs from local data (default, fast/offline)
python3 code/build.py

# Crawl refresh-enabled sources for new issues and rebuild.
# Static/disabled sources (including LinkedIn) are skipped with a reason.
python3 code/build.py --refresh

# Crawl and rebuild a specific source only
python3 code/build.py --refresh --source pragmatic-engineer

# Process inbox items first, then build
python3 code/build.py --inbox

# Build only 90-day detailed Markdown files
python3 code/build.py --latest

# Build only 90-day compact Markdown bullet lists
python3 code/build.py --compact

# Build only cumulative archives
python3 code/build.py --archive

# Build only cumulative compact archives
python3 code/build.py --archive-compact

# Build only the interactive HTML dashboard
python3 code/build.py --news-page

# Build a specific source only
python3 code/build.py --source dear-architects
```
