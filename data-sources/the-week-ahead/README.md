# The Week Ahead (Above) Source Specification

* **Source ID**: `the-week-ahead`
* **Radar Name**: The Week Ahead
* **Author / Host**: Above ([Above Impacts](https://dk.linkedin.com/company/aboveimpacts))
* **Location**: Copenhagen, Denmark
* **Official Website**: [https://dk.linkedin.com/company/aboveimpacts](https://dk.linkedin.com/company/aboveimpacts)
* **Archive URL**: [https://www.linkedin.com/company/aboveimpacts/posts/](https://www.linkedin.com/company/aboveimpacts/posts/)
* **Platform**: Curated weekly conference & summit radar
* **Article ID Prefix**: `twa`
* **Last Updated**: 28 September 2026 (Week 40)
* **Refresh Policy**: Static / semi-automated ingestion. Automated crawling is disabled to avoid automated LinkedIn rate-limiting (HTTP 999). Issues are ingested via `scraper.py:ingest_issue_data()` or manual batch additions.

---

## 🎯 Editorial Filtering Policy (Signal vs. Noise)

Because Above curates a multidisciplinary weekly forecast covering tech, media, film, and design events, issues are filtered to maintain high engineering and technical signal:

### 🚫 Filtered / Hidden (`hide: true`)
1. **Film & Media Festivals**: Film finance, production, and cinema festivals (e.g., *FilmFest Hamburg Explorer Konferenz*, *Nashville Film Festival Creators Conference*).
2. **Generic Influencer & Creator Marketing**: Creator economy marketing and monetization conferences (e.g., *VidSummit*).

### ✅ Retained / Active (`hide: false`)
1. **Software Architecture & Distributed Systems**: Engineering conferences covering architecture, distributed systems, resilient design, and craft (e.g., *GOTO Copenhagen 2026*).
2. **Cloud Infrastructure & AI Systems**: High-performance compute, GPU networking, cloud infrastructure, and AI engineering summits (e.g., *CoreWeave Fully Connected*, *The AI Conference*).
3. **Tech Industry & Engineering Culture**: Regional developer ecosystems, tech policy, AI governance, and digital futures (e.g., *Boston AI Week*, *SOFTER Digital Futures*).

---

## 🛠 Ingestion Workflow

To ingest future issues:
1. Locate the weekly forecast post on the Above Impacts LinkedIn feed.
2. Structure the events with verified official event URLs, dates, categories, and content types (`conference`).
3. Set `hide: true` and `hide_reason` on non-engineering events.
4. Run `TheWeekAheadScraper.ingest_issue_data()` in `data-sources/the-week-ahead/scraper.py`.
