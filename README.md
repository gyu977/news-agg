# News Aggregator & Dashboard (`news-agg`)

An automated newsletter aggregator, markdown archive builder, and interactive web dashboard for software engineering and AI newsletters.

---

## 🌟 Overview

`news-agg` consolidates articles across multiple engineering newsletters and curated reading lists into a unified dataset, generating clean Markdown digests, historical archives, and a high-performance interactive web dashboard.

---

## 🚀 Quick Start

### 1. Launch the Web Dashboard
Double-click [`news.html`](news.html) in your browser, or serve locally:
```bash
python3 -m http.server 8000
# open http://localhost:8000/news.html
```

### 2. Build / Rebuild Deliverables
To rebuild all 90-day Markdown digests, cumulative archives, and the dashboard from local data:
```bash
python3 code/build.py
```

### 3. Refresh Newsletters from the Web
To crawl online sources (MailerLite, Substack, LinkedIn) for new issues and rebuild:
```bash
# Refresh all online sources and rebuild:
python3 code/build.py --refresh

# Or refresh a single source only:
python3 code/build.py --refresh --source pragmatic-engineer
```

### 4. Add Personal Articles via Inbox
Drop new links or notes into [`inbox.md`](inbox.md) right at the project root, then run:
```bash
python3 code/build.py --inbox
```
The ingestor automatically extracts OpenGraph metadata (title, author, description, date), assigns categories and content types, merges into the dataset, and rebuilds the outputs.

---

## 📂 Active Sources

| # | Source | Author / Curator | Platform | Archive Retention |
| :- | :--- | :--- | :--- | :--- |
| **1** | **Dear Architects** | Luca Mezzalira | MailerLite JSON API | Unlimited |
| **2** | **Token by Token** | Luca Mezzalira | MailerLite JSON API | Unlimited |
| **3** | **Artificial Intelligence** | Andriy Burkov | LinkedIn Pulse | 90 Days Rolling |
| **4** | **The Pragmatic Engineer** | Gergely Orosz | Substack JSON API | Unlimited |
| **5** | **Addy Osmani** | Addy Osmani | Personal Technical Blog | 2026 Essays |
| **6** | **Future of Software Development** | Thoughtworks FOSE | Curated Retreat Series | No Archive (Event View) |
| **7** | **Others (Collected Articles)** | Mihai V. | Personal Inbox & Web Sync | Curated Collection |

---

## 📁 Repository Structure

```text
news-agg/
├── inbox.md                    # 📥 Top-level personal reading inbox
├── news.html                   # 🌟 Flagship Interactive Web Dashboard
├── README.md                   # User guide & quick start
│
├── docs/                       # 📚 Dedicated documentation
│   └── INSTRUCTIONS.md         # Architecture specifications, schemas, developer guide
│
├── code/                       # ⚙️ Core engine and generators
│   ├── build.py                # ⚡ Master CLI build runner
│   ├── common/                 # models.py, constants.py, base_scraper.py
│   └── builders/               # build_latest.py, build_archive.py, build_news_page.py
│
├── sources/                    # Standardized source modules
│   ├── dear-architects/        # definition.json, data.json, scraper.py
│   ├── token-by-token/
│   ├── andriy-burkov-ai/
│   ├── pragmatic-engineer/
│   ├── addy-osmani/
│   ├── future-software-development/
│   └── my-collected-articles/  # definition.json, data.json, scraper.py
│
└── output/                     # Generated Markdown deliverables
    ├── dear-architects.md              # 90-day detailed digest
    ├── dear-architects-compact.md      # 90-day compact bullet list
    ├── dear-architects-archive.md      # Full cumulative archive
    ├── dear-architects-archive-compact.md
    └── ...
```

---

## 📖 Developer Guide

For detailed technical specifications on data schemas, scraper design, visual markers, and adding new newsletter sources, see **[docs/INSTRUCTIONS.md](docs/INSTRUCTIONS.md)**.