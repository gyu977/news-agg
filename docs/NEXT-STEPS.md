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
| **3.4** | **Table Column Layout & Typography Stability** | ✅ **Done** | Implemented `table-layout: fixed` to completely eliminate horizontal layout shift when filtering; calibrated fixed metadata column widths (`.select-col: 48px`, `.source-column: 165px`, `.date-column: 115px` with concise `20 Oct 2026` format, `.author-column: 170px`, `.category-column: 180px`, article title `width: auto` flex gaining 95px total); defensive truncation (`text-overflow: ellipsis`) on badges; top-aligned select checkboxes and content-type icons; inline article title and spotlight badge flow preventing spurious wrapping |

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

---

## 3. General Backlog (Future Considerations & Architectural Thresholds)

- **Conference Type Icon Readability (UI Polish)**: ✅ **Done**
  - *Resolution*: Replaced low-contrast `🎟️` with high-contrast auditorium `🏛️` across `code/common/constants.py`, `code/builders/news_template.html`, `data-sources/my-collected-articles/scraper.py`, and `docs/DEVELOPER-GUIDE.md` for crisp legibility at 14px on dark backgrounds.
- **URL Validation & Unshortener Hardening (Prevent Broken/Hallucinated Links)**:
  - *Context*: When unshortening newsletter tracking links (e.g. MailerLite `clicks.mlsend.com`), standard `urllib` requests can fail with `HTTP Error 403: Forbidden` due to default script User-Agents. If an assistant or fallback process resorts to web search or manual lookup, reconstructed slugs (like Medium's 12-hex post ID) risk hallucinating broken URLs.
  - *Planned Action*:
    1. **Automated Scraper Unshortener (Option A)**: Ensure `MailerLiteScraper` (and shared unshortening routines) pass a standard browser `User-Agent` to resolve tracking redirects directly (`302 Found`) without triggering 403s.
    2. **Automated Link Verification Tool (Option A)**: Add a lightweight `validate_url` check in `code/tools/normalize_data.py` (or a dedicated `code/tools/check_links.py`) that performs a `HEAD`/`GET` probe to ensure newly ingested links resolve to `200 OK` (not `404` or `410`).
    3. **Assistant Operational Rule (Option B)**: If an HTTP error (e.g. 403, 429, 999) requires manual/search resolution, the final destination URL must be actively tested for HTTP validity (via `curl -ILs` or Python probe) before being saved to any `data.json`.
- **Next Week Priority — Migrate Andriy Burkov Source to Substack (`aiweekly.substack.com`)**:
  - *Context*: Andriy Burkov cross-publishes the exact same weekly content under *True Positive Weekly* on Substack (`https://aiweekly.substack.com/api/v1/posts`).
  - *Benefits*: Eliminates LinkedIn authwalls, HTTP 999 blocks, and manual imports; enables automated weekly refreshes (`--refresh --source andriy-burkov-ai`); guarantees 100% direct, un-gated destination URLs.
  - *Implementation Notes*: Filter for posts starting with `True Positive Weekly` (ignoring occasional book chapter promos), parse `<ul><li><a href="...">` from `body_html`, keep `source_id: andriy-burkov-ai` and `short_name: Burkov AI`, and maintain existing signal-to-noise editorial rules (`hide: true` for consumer op-eds / detector controversies).
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


