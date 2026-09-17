# News Aggregator — Next Steps & Active Roadmap

This document tracks immediate active tasks, implementation status for dashboard UX improvements, and concise instructions for resuming work.

---

## 1. Dashboard UI Modernization (UI Expert Review)

Based on the recommendations in [`docs/ui-expert-review-en.md`](docs/ui-expert-review.md).

| # | Feature / Recommendation | Status | Notes |
| :--- | :--- | :---: | :--- |
| **1.1** | **In-Place Row Selection (Zero Layout Shift)** | ✅ **Done** | Fixed 48px `.select-col`; row jumping eliminated; event delegation toggles `.selected-row` |
| **1.2** | **Tighten Header & Brand Wordmark** | ✅ **Done** | Removed heavy border line; recovered ~60px vertical height; integrated mechanical hook icon |
| **1.3** | **Accessible Switch Controls** | ✅ **Done** | Converted checkboxes to animated pill switches with WAI-ARIA (`role="switch"`, `aria-checked`) |
| **1.4** | **Eliminate ALL CAPS Typography** | ✅ **Done** | Title/Sentence Case with proper optical weights across headers, badges, and labels |
| **2.1** | **Modal Dialog for Sources & Categories** | ✅ **Done** | Replaced 400–700px CLS accordion with native `<dialog id="guideDialog">` (tabbed, Escape/backdrop close) |
| **2.2** | **Category & Source Label Synchronization** | ✅ **Done** | Compact labels (`AI & Agentic Eng`, etc.) synced across table badges, modal, and filter dropdowns |
| **2.3** | **Clean Source Definitions** | ✅ **Done** | Removed redundant author attributions from `definition.json` descriptions (Addy Osmani, Simon Willison, Burkov AI) |
| **2.4** | **Documentation Contract** | ✅ **Done** | Added Section 10 to [`docs/DEVELOPER-GUIDE.md`](docs/DEVELOPER-GUIDE.md) governing cross-component label sync |
| **3.1** | **True Viewport Sticky Table Header** | ⏳ **Postponed** | In progress: needs removal of parent `backdrop-filter` & clipping boundaries on `.table-container` to lock `<th>` to viewport |
| **3.2** | **Consolidated Action & Export Toolbar** | 📋 **To Be Implemented** | Move search input adjacent to table results and unify *Export View* and *Export Selection* into a single cohesive action bar |
| **3.3** | **Dynamic Filter Counts & Dimming** | 📋 **To Be Implemented** | Compute live match counts inside dropdown options and dim/disable items with 0 active matches (e.g. *Pulses* in 30d window) |

---

## 2. General Backlog (Future Considerations)

- **Additional Feeds**: Martin Fowler (Bliki), ByteByteGo (Systems Design), Dan Luu (Performance). Use `code/tools/scaffold_source.py`.
- **Scheduled CI/CD**: Set up `.github/workflows/refresh.yml` to automate weekly newsletter ingestion on GitHub Actions.
- **Bookmarks**: Browser `localStorage` bookmarking (`[★ Saved]`) for offline reading queues.
- **Aggregated RSS Feed**: Add `code/builders/build_feed.py` to output a unified `output/feed.xml`.

---

## 3. How to Resume in a New Session

When starting a new Antigravity session:
1. Select the project **`news-agg`**.
2. Provide this starting prompt:
   > *"We are continuing work on the news aggregator project. Please read `NEXT_STEPS.md`. Let's resume with the remaining UI tasks: Item 3.1 (Sticky Table Header fix) and Item 3.2 (Consolidated Action & Export Toolbar)."*

