# News Aggregator — Next Steps & Active Roadmap

This document tracks immediate active tasks, implementation status for dashboard UX improvements, and concise instructions for resuming work.

---

## 1. Dashboard UI Modernization (UI Expert Review)

Based on the recommendations in [`docs/ui-expert-review.md`](ui-expert-review.md).

| # | Feature / Recommendation | Status | Notes |
| :--- | :--- | :---: | :--- |
| **1.1** | **In-Place Row Selection (Zero Layout Shift)** | ✅ **Done** | Fixed 48px `.select-col`; row jumping eliminated; event delegation toggles `.selected-row`; native browser tooltips always provide contextual bulk guidance on header (`Select all visible articles to export...` / `Deselect all visible articles`), with row tooltips suppressed once selection is active for quiet multi-selection |
| **1.2** | **Tighten Header & Brand Wordmark** | ✅ **Done** | Removed heavy border line; recovered ~60px vertical height; integrated mechanical hook icon |
| **1.3** | **Accessible Switch Controls** | ✅ **Done** | Converted checkboxes to animated pill switches with WAI-ARIA (`role="switch"`, `aria-checked`) |
| **1.4** | **Eliminate ALL CAPS Typography** | ✅ **Done** | Title/Sentence Case with proper optical weights across headers, badges, and labels |
| **2.1** | **Modal Dialog for Sources & Categories** | ✅ **Done** | Replaced 400–700px CLS accordion with native `<dialog id="guideDialog">` (tabbed, Escape/backdrop close) |
| **2.2** | **Category & Source Label Synchronization** | ✅ **Done** | Compact labels (`AI & Agentic Eng`, etc.) synced across table badges, modal, and filter dropdowns |
| **2.3** | **Clean Source Definitions** | ✅ **Done** | Removed redundant author attributions from `definition.json` descriptions (Addy Osmani, Simon Willison, Burkov AI) |
| **2.4** | **Documentation Contract** | ✅ **Done** | Added Section 10 to [`docs/DEVELOPER-GUIDE.md`](DEVELOPER-GUIDE.md) governing cross-component label sync |
| **3.1** | **True Viewport Sticky Table Header** | ✅ **Done** | Unconstrained `.table-container` (`overflow: visible`), removed parent backdrop filter, and added inner cell radii |
| **3.2** | **Consolidated Action & Export Toolbar** | ✅ **Done** | Moved search input adjacent to table results with fixed 350px width; added inline `✕` clear button (supports click, input sync, Esc key); symmetric displayed/selected count badges with fixed minimum widths (`.pill-displayed: 116px`, `.pill-selected: 146px`), 25px right-aligned `.count-num` slots, and `tabular-nums` making both the capsules and their inner text 100% motionless; compact 34px export controls (Markdown `.md`, HTML `.html`) with 8px border radius; tightened vertical spacing between filter controls and table toolbar |
| **3.3** | **Dynamic Faceted Filter Counts & Dimming** | ✅ **Done** | Multidimensional cross-filtering: live match counts inside dropdowns reflect the intersection of all other active filters (timeframe, sources, types, categories) with zero-match dimming; fixed filter widths (`timeframe: 180px`, `sources: 200px`, `types: 180px`, `categories: 210px`) and unified `.toggles-wrapper` prevent toolbar shift and line wrapping |
| **3.4** | **Table Column Layout & Typography Stability** | ✅ **Done** | Implemented `table-layout: fixed` to completely eliminate horizontal layout shift when filtering; calibrated fixed metadata column widths (`.select-col: 44px` meeting WCAG AAA, `.date-column: 110px` pulled tight with `0.5rem` padding, `.source-column: 205px`, `.category-column: 170px` with asymmetric `0.4rem` gutters creating a cohesive metadata tag cluster, `.author-column: 170px`, article title flex `width: auto` gaining horizontal breathing room); defensive truncation (`text-overflow: ellipsis`) on badges; top-aligned select checkboxes; calibrated content-type emoji icon alignment (`vertical-align: -0.02em`) centering glyphs with text cap-height; inline article title and spotlight badge flow preventing spurious wrapping |

---

## 2. Immediate Shortlist (Active Tasks)

- **Sticky Table Header Not Covering First Column Selection Marker (UI Bug / Polish)**: 🔴 **Open**
  - *Context*: When an article is selected, its left blue selection indicator on the first column remains visible / bleeds through when passing underneath the fixed sticky table header during scroll. The previous `box-shadow: inset 3px 0 0` did not eliminate the effect.
  - *Root Cause Analysis*:
    1. **Header Translucency**: `th` uses `background: rgba(15, 23, 42, 0.95)` with `backdrop-filter: blur(12px)`. The 5% translucency allows vibrant cyan (`#38bdf8`) to glow through the header during scroll.
    2. **Curved Corner Masking**: `thead tr:first-child th:first-child` has `border-top-left-radius: 15px`. Because `.table-container` uses `overflow: visible` (to allow sticky positioning), rows scrolling past `top: 0` peek through the transparent outer curve of the corner.
  - *Planned Action*:
    1. Make `th` background 100% opaque (`#0f172a`) during scroll to prevent color bleed-through.
    2. Square off or mask the scrolling boundary so the selection marker is completely covered under the header.
- **"Show Only Selected" View Toggle (UI Feature Candidate)**: ⏳ **Planned**
  - *Context*: When reviewing or curating articles, users selecting multiple rows across a 300+ item table need a quick way to isolate only their selected articles on screen before exporting or clearing.
  - *Goal*: Add an inline `Show only` / `Show all` toggle directly inside the `.pill-selected` capsule (`[ 3 selected | 👁️ Show only | Clear ]`), keeping selection management in a single, motionless capsule that vanishes when no rows are checked.
- **Unified Export for Active Filtered Views (UI Polish Candidate)**: ⏳ **Planned**
  - *Context*: Currently, export buttons appear only when $\ge 1$ item is selected. When 0 rows are selected, users might want to export the entire currently filtered view (e.g. `Export View (322)`) directly from the table toolbar.
- **Author Column Quality Audit & Representation Review**: ⏳ **Planned**
  - *Context*: Some rows currently have missing authors or unexpected/weird values (e.g. publisher credits, scraping artifacts). This may stem from parsing errors or imprecise extraction heuristics in certain newsletter scrapers.
  - *Planned Action*:
    1. **Parsing & Root-Cause Audit**: Audit individual scrapers (MailerLite, Substack, RSS feeds) and `BaseScraper._is_plausible_author` in `normalize_data.py` to identify where authors are dropped or misparsed and tighten author extraction rules.
    2. **Layout & Byline Evaluation**: Revisit whether author deserves a standalone table column or should be consolidated into the `Article` cell as an inline byline (e.g., *Title — by Author*), which would eliminate empty cell gaps and expand horizontal space for titles and descriptions.
- **Onboard "The Week Ahead" (`the-week-ahead`) as a Dedicated Curated Source**: ✅ **Done**
  - *Context*: A high-signal weekly events and conference radar published by *Above* (Above Impacts), forecasting upcoming landmark software architecture, AI infrastructure, and engineering conferences (e.g., GOTO Copenhagen, CoreWeave Fully Connected, The AI Conference).
  - *Delivered*:
    1. Dedicated source directory `data-sources/the-week-ahead/` (`definition.json`, `data.json`, `scraper.py`, `README.md`) with Week 40 edition ingested.
    2. Filtering policy enforcing `hide: true` on non-engineering summits (film festivals, creator marketing) while retaining core architecture and AI infrastructure events.
    3. UI styling `.badge-week-ahead` and `badgeClasses` mapping in `code/builders/news_template.html`.
    4. Normalizer registration in `code/tools/normalize_data.py` (`"the-week-ahead": "twa"`).
    5. Test coverage in `tests/test_filter_matrix.py` and `tests/test_scraper_infrastructure.py`.

---

## 3. General Backlog (Future Considerations & Architectural Thresholds)

- **Conference Type Icon Readability (UI Polish)**: ✅ **Done**
  - *Resolution*: Replaced low-contrast `🎟️` with high-contrast auditorium `🏛️` across `code/common/constants.py`, `code/builders/news_template.html`, `data-sources/my-collected-articles/scraper.py`, and `docs/DEVELOPER-GUIDE.md` for crisp legibility at 14px on dark backgrounds.
- **URL Validation & Unshortener Hardening (Prevent Broken/Hallucinated Links)**: ✅ **Done**
  - *Delivered*:
    1. **`code/common/url_utils.py`**: Browser User-Agent redirect follower `unshorten_url()`, two-tier reachability probe `validate_url()` (HEAD with GET range fallback), and tracking query sanitizer `clean_tracking_params()`.
    2. **Scraper Pipeline Hardening**: `BaseScraper` class methods (`unshorten_url()`, `validate_url()`, `is_tracking_redirect()`), and `MailerLiteScraper.parse_issue_html()` auto-unshortening resolving `clicks.mlsend.com` redirect links directly into true destinations before creating `Article` records.
    3. **CLI Health & Audit Utility (`code/tools/check_links.py`)**: Multi-threaded tool supporting `--url`, `--source`, `--all`, and `--fix-tracking` to audit link health and repair tracking redirect links in place.
    4. **Unit Tests (`tests/test_url_validation.py`)**: Full test coverage across redirect following, authwalls, 405 fallbacks, and scraper integration (all 198 tests passing).
- **Andriy Burkov Source Authoritative Channel**:
  - *Resolution*: Substack migration dropped. Andriy Burkov updates Substack with significant delays, whereas LinkedIn is published promptly and remains the authoritative source. Retain LinkedIn issue import workflow with active editorial curation (`hide: true` on non-engineering fluff, preserving math/deep technical articles).
- **Additional Feeds**: ByteByteGo (Systems Design), Dan Luu (Performance). Use `code/tools/scaffold_source.py` (Martin Fowler Bliki/feed added and active).
- **Scheduled CI/CD**: Set up `.github/workflows/refresh.yml` to automate weekly newsletter ingestion on GitHub Actions.
- **Bookmarks**: Browser `localStorage` bookmarking (`[★ Saved]`) for offline reading queues.
- **Aggregated RSS Feed**: Add `code/builders/build_feed.py` to output a unified `output/feed.xml`.
- **Modern CSS Modernization ("CSS Reacts, JS Just Listens" Architecture)**:
  - *Context*: Based on Adam Argyle's reactive CSS architectural patterns (`prop-for-that`) and vetted by Claude Opus for browser standards, shifting UI state management from JavaScript DOM mutation to native CSS primitives:
  - **Phase 1: Immediate Quick Wins (Zero Risk, Baseline Universal)**: ✅ **Done**
    - *Pure CSS Search Clear Button*: Search clear button visibility is now reactive via `.search-toolbar:has(#searchInput:not(:placeholder-shown)) .search-clear-btn` with smooth opacity/pointer-events transitions.
    - *Ambient UI & Battery/Performance Optimization*: Added `@media (prefers-reduced-transparency: reduce)` stripping heavy `backdrop-filter: blur(...)` to solid backgrounds and `@media (prefers-reduced-motion: reduce)` for instant, battery-efficient rendering.
  - **Phase 2: Modernization & JS DOM Decoupling**: ✅ **Done**
    - *Compositor-Thread Reading Progress*: ✅ **Done** Added a hardware-accelerated 2px gradient horizon bar (`#tableProgressBar`) under the sticky table header driven by CSS Scroll-Driven Animations (`animation-timeline: scroll()`) wrapped in `@supports (animation-timeline: scroll())` with zero main-thread JS scroll listeners.
    - *Declarative CSS Counter for Selected Rows*: ✅ **Done** Decoupled DOM mutations from numerical display using `:root { --selected-count: 0; }`, `counter-reset: selected-articles var(--selected-count);`, and `.pill-selected .count-num::after { content: counter(selected-articles); }`. JavaScript broadcasts state via CSS custom property with zero innerHTML churn, preserving fixed tabular layout.
  - **Phase 3: Progressive Enhancement**:
    - *Faceted Filter Dimming via Style Queries*: Transition zero-match option dimming to `@container style(--matches: 0)` wrapped in `@supports (container: style(...))`, keeping class-based dimming as a graceful fallback.
- **Architectural Triggers (Milestone Thresholds)**:
  - *DOM Virtualization*: Keep vanilla DOM rendering as long as active articles stay under 1,000–1,500. Only consider implementing chunked rendering / `IntersectionObserver` virtualization if the archive exceeds 1,500–2,000 items and layout latency is detected on mobile devices.
  - *URL Normalization Audit*: Periodically check `BaseScraper.TRACKING_PARAMS` whenever onboarding new feed formats (Substack, Beehiiv, LinkedIn) to preserve clean cross-source deduplication (`also_in`).
  - *E2E Browser Smoke Testing*: If table structure or client-side filtering undergoes radical architectural rewrites, consider running a one-off headless browser check to re-verify parity with `tests/test_filter_matrix.py`.

---

## 3. How to Resume in a New Session

When starting a new Antigravity session:
1. Select the project **`news-agg`**.
2. All items from the UI Modernization Plan (1.1 through 3.4), Phase 1-2 Modern CSS (progress bar, reactive clear button, declarative counter), and Conference icon readability (`🏛️`) are complete and verified. Provide this starting prompt:
   > *"We are continuing work on the news aggregator project. All UI Modernization items (1.1–3.4), Phase 1-2 Modern CSS, and Conference icon readability (`🏛️`) are completed. Please check `git status` and `NEXT-STEPS.md` for active backlog items (e.g. 'Show Only Selected' toggle, Burkov AI Substack migration, new feeds, or CI/CD)."*


