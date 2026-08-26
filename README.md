# News Aggregator & Dashboard (`news-agg`)

An automated newsletter aggregator, markdown archive builder, and interactive web dashboard for software engineering and AI newsletters.

---

## 🌟 Overview

`news-agg` consolidates articles across multiple engineering newsletters and curated reading lists into a unified dataset, generating clean Markdown digests, historical archives, and a high-performance interactive web dashboard.

---

## 🚀 Quick Start

**Requires Python 3.9 or newer.** The builders are pure standard library; only the
web scrapers need third-party packages (see step 3).

### 1. Launch the Web Dashboard
Double-click [`news.html`](news.html) in your browser, or serve locally:
```bash
python3 -m http.server 8000
# open http://localhost:8000/news.html
```

The dashboard supports multi-selection for newsletter sources, content types, and subject
categories. Selections are combined with OR inside each filter and AND across filters.
The Spotlight-only option is available when Dear Architects or Token by Token is selected.

### 2. Build / Rebuild Deliverables
To rebuild all 90-day Markdown digests, cumulative archives, and the dashboard from local data:
```bash
python3 code/build.py
```

### 3. Refresh Newsletters from the Web
To crawl refresh-enabled online sources (MailerLite, Substack, blogs) and rebuild:
```bash
# Install scraper dependencies first (one-off):
pip install -r requirements.txt

# Refresh all online sources and rebuild:
python3 code/build.py --refresh

# Or refresh a single source only:
python3 code/build.py --refresh --source pragmatic-engineer
```

Curated/static sources are skipped with an explicit reason. LinkedIn automation is
disabled because the site blocks unauthenticated crawlers and does not permit this
scraping approach; its existing imported dataset remains available.

### 4. Add Personal Articles via Inbox
Drop new links or notes into [`inbox.md`](inbox.md) right at the project root, then run:
```bash
python3 code/build.py --inbox
```
The ingestor automatically extracts OpenGraph metadata (title, author, description, date), assigns categories and content types, merges into the dataset, and rebuilds the outputs.

### 5. Normalize the Data (maintenance)
Re-cleans tracking parameters from links, merges same-issue duplicate records, re-mints article
IDs as `{prefix}-{issue}-{hash6}`, collapses leaked HTML whitespace, and hides sponsor/ad links.
Idempotent, so it is safe to re-run after any scrape:
```bash
python3 code/tools/normalize_data.py --check   # report only
python3 code/tools/normalize_data.py           # apply
```

### 6. Run the Tests
The test suite is standard-library `unittest` and needs no extra packages. It covers
article categorisation, merge semantics, and data integrity across every source:
```bash
python3 -m unittest discover -s tests
```

---

## 📂 Active Sources

| # | Source | Author / Curator | Platform | Archive Retention |
| :- | :--- | :--- | :--- | :--- |
| **1** | **Dear Architects** | Luca Mezzalira | MailerLite JSON API | Unlimited |
| **2** | **Token by Token** | Luca Mezzalira | MailerLite JSON API | Unlimited |
| **3** | **Artificial Intelligence** | Andriy Burkov | LinkedIn Pulse | 90 Days Rolling |
| **4** | **The Pragmatic Engineer** | Gergely Orosz | Substack JSON API | Unlimited |
| **5** | **Addy Osmani** | Addy Osmani | Personal Technical Blog | Unlimited (730-day discovery window) |
| **6** | **Future of Software Development** | Thoughtworks FOSE | Curated Retreat Series | No Archive (Event View) |
| **7** | **On My Radar** | Mihai V. | Personal Inbox & Web Sync | Curated Collection |

---

## 📁 Repository Structure

```text
news-agg/
├── inbox.md                    # 📥 Top-level personal reading inbox
├── news.html                   # 🌟 Flagship Interactive Web Dashboard
├── README.md                   # User guide & quick start
│
├── docs/                       # 📚 Dedicated documentation
│   ├── DEVELOPER-GUIDE.md      # Architecture, schemas, and extension guide
│   ├── CODE-REVIEW.md          # Implementation review & issue tracker
│   └── DATA-DISCREPANCIES.md   # Known data-level defects, deferred
│
├── code/                       # ⚙️ Core engine and generators
│   ├── build.py                # ⚡ Master CLI build runner
│   ├── common/                 # models, crawl policy, shared MailerLite scraper
│   └── builders/               # build_latest.py, build_archive.py, build_news_page.py
│
├── code/tools/                 # 🔧 normalize_data.py — link/ID maintenance
│
├── tests/                      # ✅ stdlib unittest suite (no dependencies)
│   ├── test_auto_categorize.py
│   ├── test_merge_articles.py
│   ├── test_url_identity.py
│   ├── test_sponsor_detection.py
│   ├── test_content_quality.py
│   ├── test_scraper_infrastructure.py
│   └── test_data_integrity.py
│
├── data-sources/               # Standardized source modules and canonical data
│   ├── dear-architects/        # definition.json, data.json, scraper.py
│   ├── token-by-token/
│   ├── andriy-burkov-ai/
│   ├── pragmatic-engineer/
│   ├── addy-osmani/
│   ├── future-software-development/
│   └── my-collected-articles/  # definition.json, data.json, scraper.py
│
└── generated/                  # Generated Markdown deliverables (local, git-ignored)
    ├── dear-architects.md              # 90-day detailed digest
    ├── dear-architects-compact.md      # 90-day compact bullet list
    ├── dear-architects-archive.md      # Full cumulative archive
    ├── dear-architects-archive-compact.md
    └── ...
```

---

## 📖 Developer Guide

For detailed technical specifications on data schemas, scraper design, visual markers, and adding new newsletter sources, see **[docs/DEVELOPER-GUIDE.md](docs/DEVELOPER-GUIDE.md)**.