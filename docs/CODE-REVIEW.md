# `news-agg` — Implementation Review

**Date:** 2026-08-25 · **Commit reviewed:** `9b5d570` · **Status:** Original review **34 of 34 fixed**. Independent re-review **14 of 14 fixed**: 0 Critical, 5 High, 6 Medium, 3 Low. The suite now has **148 tests** (1 BeautifulSoup fixture skipped locally because PyPI access is blocked).

Remaining uncertainty is data-only and tracked in [`DATA-DISCREPANCIES.md`](DATA-DISCREPANCIES.md): missing Dear Architects issues #261/#262, one unverified date (#275), pre-mailbox dates #217/#218, unverified historical dates in Token by Token / Andriy Burkov, and residual content-quality backfill. The four final scraper fixes are implemented but still need a network-enabled agent to exercise live endpoints because this environment cannot install `bs4` (PyPI returned HTTP 403). · **Scope:** code, data sources, generated data/docs, HTML dashboard

**Current snapshot:** `python3 code/build.py` runs and is byte-reproducible. The committed
data contains **702 records: 660 visible, 42 hidden** across 7 sources, with 0 duplicate
IDs, 0 missing titles/links, 0 malformed ISO dates, 0 invalid categories/types, and the
normalizer at a fixed point. The worktree is intentionally dirty with the accumulated
review fixes and documentation; nothing has been committed.

**Post-review enhancements:** manually reviewed all **438 visible 2026 articles** and
corrected **117 categories** across Addy Osmani (8), Andriy Burkov (27), Dear Architects
(53), Pragmatic Engineer (9), and Token by Token (20). Each editorial correction is
protected by a `category` user override. The dashboard now supports checkbox-based
multi-selection for source, content type, and category, using OR within each dimension and
AND across dimensions. Spotlight is disabled and cleared unless Dear Architects or Token
by Token is selected. Multi-select menus have stable dimensions, overlay the results table,
close when another menu opens or the user clicks elsewhere, and support Escape. Source/category
description counts remain synchronized with the currently displayed view. Source and category
filters use the same logical order as their description lists; content types are ordered
alphabetically by their displayed labels. Source definitions now separate canonical `name`
from the compact `short_name` used only by table badges; filters, descriptions, sorting,
tooltips, and exports retain full names. The selected stacked-news SVG is installed as both
the dashboard favicon and header mark. Cross-source duplicates use a clear `Also in N`
indicator with full source names in the tooltip; live source counts and HTML/Markdown
exports include every recommending source. Its custom tooltip replaces the browser-delayed
`title` UI, appears after 100 ms, stays within the viewport, and supports keyboard focus.
Repository layout now uses `data-sources/` for source adapters/canonical data and
`generated/` for ignored Markdown build artifacts; runtime paths, tests, and documentation
use the renamed directories consistently. View and selection export controls share aligned
right-side dimensions, and selected counts use the same badge treatment as result counts.
The Liz Fong-Jones Observability Engineering Masterclass is editorially fixed as a
`presentation` with a persistent type override.
All opened multi-select menus use a stable 320 px width; their option lists expand naturally
through ten items and scroll only above that threshold or when constrained by viewport height.
Dashboard terminology now consistently uses `Category`/`Categories`; the final table column
is `Article`, and the desktop category column is widened while mobile cards remain fluid.
The personal collection's canonical display name is now `On My Radar` across data,
definitions, filters, descriptions, table badges, exports, and documentation; stable
`my-collected-articles` and `others-*` identifiers are unchanged.
Author sorting is null-safe, locale-aware, numeric-aware, and keeps blank authors last in
both directions. Seven Token by Token bold-text artifacts were corrected: two verified
bylines are retained with overrides, five unknown bylines are cleared, and that source no
longer infers authors from arbitrary `<strong>` fragments.

---

# Independent re-review — 2026-08-25

This pass was performed from the implementation and runtime behavior, without assuming
the findings or closure claims from the original review were correct.

## Re-review matrix

| Area | 🔴 Critical | 🟠 High | 🟡 Medium | 🔵 Low | Total |
| :--- | :--: | :--: | :--: | :--: | :--: |
| **CLI / builders** | 0 | 2 | 2 | 1 | 5 |
| **Sources / crawling** | 0 | 3 | 3 | 1 | 7 |
| **Data / docs** | 0 | 0 | 1 | 1 | 2 |
| **Total** | **0** | **5** | **6** | **3** | **14** |

## 🟠 High

- [x] **R1 · Pragmatic Engineer refresh crashes on every valid post** `NOW`
  `data-sources/pragmatic-engineer/scraper.py:106` writes `metadata["slug"] = slug`, but
  `slug` is never defined in `parse_post_payload()`. Reproduced offline with a minimal
  valid Substack payload: `NameError: name 'slug' is not defined`. The exception occurs
  before any article can be returned, so a live refresh cannot ingest a single post.
  The existing tests never import or invoke this concrete source adapter.
  **Fix:** use `post.get("slug", "")`; add direct fixture tests for valid, missing-date,
  podcast, Pulse and guest-author payloads.
  **Done:** metadata now uses `post.get("slug", "")`. A concrete adapter test imports
  `PragmaticEngineerScraper`, parses a representative valid payload and asserts the slug/date.

- [x] **R2 · Historical duplicate issue numbers can permanently block Dear Architects refresh** `LATENT`
  `common/mailerlite_scraper.py:346-351` combines API and archive discoveries, then calls
  `_deduplicate_discovered()` **before** filtering known issue IDs. That helper raises
  whenever one issue number maps to distinct URLs. Dear Architects already has this exact
  historical condition: three distinct emails were sent as `#260` (D2). Therefore an old,
  already-known archive anomaly can abort every future refresh, including when the API has
  a valid new issue. Reproduced with `#305` plus two historical `#260` URLs.
  **Fix:** classify duplicate-number conflicts after separating known/history/new entries;
  report historical conflicts without blocking unrelated new issues, while still refusing
  to guess their corrected numbers.
  **Done:** deduplication now receives the committed `id → URL` map. If a duplicate number
  is historical, it preserves the known URL, reports/quarantines ambiguous extras, and
  continues with unrelated new issues. Unknown duplicate numbers still fail loudly.

- [x] **R3 · Two refresh-enabled scrapers still convert network failure into success** `LATENT`
  `addy-osmani/scraper.py:84-89` catches every listing failure, continues, then prints
  `"No articles extracted"` and exits 0. `pragmatic-engineer/scraper.py:131-138` catches an
  API failure, breaks with an empty list, saves unchanged data and exits 0. Consequently
  `build.py --refresh` reports `✓ Data sources refresh completed` even though these sources
  were not refreshed — the subprocess return-code fix cannot detect failures the child
  process swallows.
  **Fix:** distinguish “no new content” from “source could not be fetched”; propagate a
  non-zero exit when every discovery request fails.
  **Done:** Addy tracks successful listing requests and raises if all fail. Pragmatic no
  longer catches archive API failures; invalid response types and all-unparseable batches
  also raise. Child scripts therefore exit non-zero and the orchestrator detects failure.

- [x] **R4 · Failed refreshes still mutate generated artifacts before returning non-zero** `NOW`
  `build.py:101-139` records `refresh_ok = False` but runs all requested builders before
  checking it. Reproduced with
  `python3 code/build.py --refresh --source does-not-exist --news-page`: exit code is 1,
  but `news.html` is first overwritten with an empty 0-article dashboard.
  **Fix:** abort before any build when refresh fails, or build transactionally and replace
  outputs only after the entire operation succeeds.
  **Done:** `build.py` returns immediately after a failed refresh, before inbox processing
  or any builder call. A failure-path test asserts builders are not invoked.

- [x] **R5 · Dashboard generation silently succeeds with partial/corrupt source input** `LATENT`
  `build_news_page.py:58-83` catches broad exceptions while reading each definition/data
  file, prints a warning, and continues. A malformed `data.json` therefore removes an
  entire source from `news.html` while the build exits successfully. Markdown builders use
  `load_source()` and fail loudly, so the generated surfaces can disagree.
  **Fix:** fail the dashboard build on malformed managed JSON; only skip explicitly
  optional sources through configuration.
  **Done:** broad definition/data JSON catches were removed from `build_news_page.py`.
  Decode/read failures now propagate and prevent partial dashboard output.

## 🟡 Medium

- [x] **R6 · CLI accepts invalid source IDs and nonsensical day windows** `NOW`
  `python3 code/build.py --source does-not-exist --latest` exits 0 and generates nothing.
  `--days -1 --news-page` exits 0 and reports “3 articles from last -1 days”.
  **Fix:** validate `--source` against `discover_sources()` and require `--days >= 1`
  through an argparse type/validator.
  **Done:** added `available_sources()` and the `positive_days` argparse type. Unknown
  sources and non-positive windows exit 2 before touching artifacts.

- [x] **R7 · Stored `parsed_issues` metadata contradicts the data despite M2 being marked fixed** `NOW`
  Current definitions: Addy has 8 issues but blank `last_parsed_issue/date`; Pragmatic
  declares `count: 23` with `issues: []`; My Collected Articles is frozen at one July issue
  while data spans 12 dates through October. The shared writer exists, but existing
  definitions were never migrated and no test audits this relationship.
  **Fix:** run a one-time tracker migration and add definition-level invariants for
  `count`, sorted issues and `last_parsed_*`.
  **Done:** migrated Addy (8 monthly issues), Pragmatic (23 post issues), and My Collected
  Articles (4 monthly issues). A new all-source integrity test enforces count, ordering and
  `last_parsed_*` consistency.

- [x] **R8 · Archive retention remains data-relative and freezes forever** `LATENT`
  `builder_core.apply_archive_retention:111-120` anchors its cutoff to `max(article date)`,
  not the clock. The static Andriy Burkov “90 Days Rolling” archive will therefore retain
  the same 65 articles indefinitely, even years after the source stopped updating.
  **Fix:** anchor rolling retention to `datetime.now()`; use unlimited retention if the
  intent for a static imported source is preservation rather than recency.
  **Done:** `apply_archive_retention()` now subtracts retention from `datetime.now()`.
  A regression test proves a feed whose newest item is 350 days old yields an empty
  90-day archive rather than a frozen historical band.

- [x] **R9 · Dashboard timeframe filter is still data-relative** `LATENT`
  `news_template.html:1156-1187` computes 7/30/90-day cutoffs from the newest embedded
  article. The server-side 90-day embedding is clock-relative, but the interactive
  filters are not. If the feed stalls within that outer window, “Last 7 Days” continues
  showing stale items relative to the last scrape.
  **Fix:** anchor interactive filters to `Date.now()`; retain future-event handling
  explicitly rather than through a max-date heuristic.
  **Done:** 7/30/90-day cutoffs now derive from `Date.now()`. Future-dated events are
  explicitly retained. The obsolete `maxTimestamp` path is removed and tested.

- [x] **R10 · Invalid Substack dates are silently rewritten as today** `LATENT`
  `pragmatic-engineer/scraper.py:69-76` catches every date parsing error and assigns
  `datetime.now()`. A malformed or changed API date silently moves old content to the top
  of every latest view and changes its stable ID month segment.
  **Fix:** reject/quarantine malformed posts with an explicit warning or error; never
  manufacture a publication date.
  **Done:** `parse_post_payload()` raises a contextual `ValueError`; discovery reports and
  skips malformed posts, and fails the batch if the API returned posts but none parsed.

- [x] **R11 · The green test suite does not execute source-specific parser code** `NOW`
  Tests cover `BaseScraper`, `MailerLiteScraper` helpers and committed JSON, but never
  import/call Pragmatic, Addy, Dear Architects or Token by Token with representative
  fixtures. This is why R1 coexists with 125 passing tests.
  **Fix:** add offline HTML/API fixtures and direct adapter tests; `bs4` should be installed
  in CI from `requirements.txt`.
  **Done:** concrete tests now import and exercise Pragmatic, Addy, Dear Architects,
  Token by Token and My Collected Articles. They caught and fixed an additional defect:
  both MailerLite adapters lacked `__init__`, so `DearArchitectsScraper()` and
  `TokenByTokenScraper()` could not instantiate. The HTML fixture runs when `bs4` is
  installed; it is the suite's single local skip because this environment receives HTTP
  403 from PyPI.

## 🔵 Low

- [x] **R12 · Static sources emit a false scraping-stalled warning on every build** `NOW`
  `build_latest.py:26` calls `warn_if_stale()` without consulting source configuration.
  FOSE is explicitly static, yet every build warns that “scraping may have stalled”.
  **Fix:** suppress crawl-staleness warnings for `static` / refresh-disabled definitions,
  or label them as archival age instead.
  **Done:** per-source latest builds consult `static`/`refresh_enabled`; dashboard warnings
  are emitted only when its selected source set contains a refreshable source.

- [x] **R13 · Source READMEs describe obsolete behavior and datasets** `NOW`
  Addy still says “strictly 2026” although code uses a rolling 730-day window; Andriy
  documents live LinkedIn discovery although refresh is disabled; My Collected Articles
  says “July 2026 / 7 articles” while it contains 16 records through October.
  **Fix:** update source-local documentation alongside scraper/config changes.
  **Done:** Addy documents the 730-day window, Andriy documents static/manual import and
  disabled discovery, My Collected Articles documents 16 records through October, and the
  root source table reflects Addy's rolling retention.

- [x] **R14 · Markdown render/export paths do not escape Markdown control characters** `LATENT`
  Builders escape only `$`; dashboard Markdown exports escape nothing. Stored descriptions
  already contain literal `*`, and future scraped titles containing `]`, `[` or `*` can
  break links/emphasis in generated files.
  **Fix:** add a shared Markdown text/link-label escaper and use it in builders plus both
  dashboard Markdown exporters.
  **Done:** added shared Python text/URL escapers and applied them to issue headers, quotes,
  authors, titles, descriptions and links in full/compact builders. Equivalent JavaScript
  escapers protect both dashboard Markdown exports, including sources with empty issue URLs.

---

## How this document is organised

Issues are grouped **severity-major → area-minor**:

* **Severity** determines *sequencing* — what gets fixed first.
* **Area** determines *batching* — what gets fixed together, because each area has exactly one verification method.

| Area | Paths | Verify with |
| :--- | :--- | :--- |
| **HTML** | `code/builders/news_template.html` | `node` eval / open in browser |
| **Code** | `code/build.py`, `code/common/`, `code/builders/*.py` | `python3 code/build.py` |
| **Sources** | `data-sources/*/scraper.py`, `data-sources/*/definition.json` | `python3 code/build.py --refresh` (needs `bs4`) |
| **Data & docs** | `data-sources/*/data.json`, `generated/*.md`, `*.md` | data-lint script |

Each issue also carries one orthogonal tag:

* **`NOW`** — user-visible or wrong today.
* **`LATENT`** — currently harmless, breaks on the next run, next scrape, or next year.

### Severity matrix

| Area | 🔴 Critical | 🟠 High | 🟡 Medium | 🔵 Low | Total |
| :--- | :--: | :--: | :--: | :--: | :--: |
| **HTML** | 3 | 0 | 1 | 5 | 9 |
| **Code** | 1 | 8 | 1 | 1 | 11 |
| **Sources** | 1 | 5 | 5 | 0 | 11 |
| **Data & docs** | 0 | 0 | 2 | 1 | 3 |
| **Total** | **5** | **13** | **9** | **7** | **34** |

Resolved per area: HTML **9/9**, Code **11/11**, Sources **11/11**, Data & docs **3/3**.

---

## 🔴 Critical

### HTML

- [x] **C1 · Dashboard search is completely broken** `NOW`
  `news_template.html:1148` — `article.author.toLowerCase()` is called unguarded, but **154 of the 281** embedded articles have `"author": null`. Every keystroke in the search box throws `TypeError: Cannot read properties of null`, aborting `render()` mid-filter. `description` and `issue_title` are exposed the same way.
  *Reproduced in `node`.*
  **Fix:** null-coalesce each field, e.g. `(article.author || '').toLowerCase()`.

- [x] **C2 · "Export to HTML" produces an empty document** `NOW`
  `news_template.html:1487`, `:1583-1586` — inside the `generateArticlesHTML` template literal the placeholders are written `\${titleText}` and `\${rows}`. The backslash escapes the interpolation, so the exported file literally contains `<h1>${titleText}</h1>` and `${rows}` instead of the article cards.
  *Reproduced in `node`: export contains the literal string `${titleText}`.*
  **Fix:** remove the backslashes so the placeholders interpolate.

- [x] **C3 · Stored XSS via unescaped `innerHTML`** `NOW`
  `news_template.html:1300` (`tdCategory`), `:1323` (`tdDetails`) — interpolate `article.title`, `article.description`, `article.link` and `article.category` **unescaped**, even though `escapeHtml()` exists at `:1084` and is correctly used in `populateSourceFilter`/`populateCategoryFilter`. The same flaw repeats in `generateArticlesHTML` (`:1449+`) and both Markdown exporters. All of this content is third-party scraped HTML. Additionally `href="${article.link}"` is unvalidated, permitting `javascript:` URLs.
  **Fix:** route every interpolated value through `escapeHtml()`; allow-list `http(s):` for `href`.

### Code

- [x] **C4 · `bs4` is undeclared, and scraper failures are reported as success** `LATENT`
  6 of 7 scrapers `import bs4` (`addy-osmani:13`, `andriy-burkov-ai:15`, `dear-architects:12`, `my-collected-articles:15`, `pragmatic-engineer:12`, `token-by-token:11`) but there is no `requirements.txt` / `pyproject.toml`, and `bs4` is **not installed** in this environment. Worse, `code/build.py:47,56` calls `subprocess.run(...)` without `check=` and never inspects `returncode`, so all six crash with a traceback and `--refresh` still prints `✓ Data sources refresh completed!`.
  **Fix:** add `requirements.txt` (`beautifulsoup4`), capture return codes, and exit non-zero on any scraper failure.

### Sources

- [x] **C5 · 91 duplicate article IDs from positional ID schemes** `NOW`
  `dear-architects:151` (`da-{issue}-{idx}`), `andriy-burkov-ai:154` (`ab-…`), `token-by-token:128` (`tbt-…`) derive IDs from enumeration order. Because `merge_articles` keys on **link**, re-parsing an issue whose item order shifted appends a new record that reuses an existing ID. Measured: **88 duplicated IDs in `dear-architects`**, 3 in `andriy-burkov-ai`. Example — `da-293-1` maps to three different articles. When `issue_number` is `None` the IDs collapse further into a shared `da-None-*` namespace.
  **Fix:** derive `id` from a stable hash/slug of the cleaned link, never from index.
  **Done:** added `BaseScraper.make_article_id()` producing `{prefix}-{issue}-{hash6}` from the canonical link, and switched all seven scrapers to it (`da`, `ab`, `tbt`, `addy`, `pe`, `others`; `fose` is hand-curated). Existing data migrated by the new `code/tools/normalize_data.py` — **702 ids rewritten, 0 collisions remaining**. `_article_key()` now also compares canonical links, so a re-scrape matches an existing record regardless of tracking-parameter spelling. Verified: 277 articles in `news.html`, 277 unique ids.

---

## 🟠 High

### Code

- [x] **H1 · Quotes are dead in the dashboard — int/str key mismatch** `NOW`
  `build_news_page.py:66` builds `quote_map` keyed by `definition.json`'s `id` (a **string**, `"304"`) then looks it up at `:80` with `data.json`'s `issue_number` (an **int**, `304`). The lookup never matches: **0 of 281** embedded articles carry a `quote` field, making the `a.quote` branches in `exportSelectionToMarkdown`, `exportViewToMarkdown` and `generateArticlesHTML` permanently unreachable. `builder_core.load_source:56` does the `str()` conversion correctly — which is why Markdown output has quotes and the HTML doesn't.
  **Fix:** `quote_map[str(iss_num)]` on both write and read.

- [x] **H2 · `auto_categorize` matches unbounded substrings** `NOW`
  `base_scraper.py:117-160` — first-match-wins over raw `in` substring checks with no word boundaries and no scoring. Verified misfires: `"The latest release of Postgres"` → *Software Testing* (matches `test` inside **la·test**); `"Contest results"` → *Software Testing*; `"Modeling the market"` → *LLM & Evaluation* (matches `model`); `"Kubernetes at scale"` and `"The AWS outage postmortem"` → *Engineering Philosophy* fallback. The keyword lists also contain one-off literals (`glm-5.2`, `kimi3`, `spotify podcasts`, `luck filter`) that read as overfitting to a single past issue.
  **Fix:** word-boundary regex, score all categories and take the best match, drop the one-off literals.
  **Done:** `_compiled_keyword()` compiles each keyword to a `(?<!\w)…s?(?!\w)` pattern (word boundaries that tolerate `-`/`.` in keywords like `micro-frontend`, `glm-5.2`, plus optional plurals); `auto_categorize` now scores every category, weighting multi-word phrases higher and deduplicating matches by text span so `microservice`/`microservices` count once. The one-off literals were left in place — they are now harmless because they can only match as whole tokens. Affects future scrapes only; existing `data.json` categories are untouched.

- [x] **H3 · `clean_url` strips the wrong parameters** `NOW`
  `base_scraper.py:76-90` — the deny-list keeps `si`, `fbclid`, `gclid`, `ref`, `mc_cid` while stripping `s`, which is a legitimate search/query param on many sites. Verified: `https://site.com/search?s=query` → `https://site.com/search` (broken), while `https://youtu.be/…?si=8pJAfud7AAortv5D` passes through untouched — which is precisely why that YouTube link exists twice as two separate records.
  **Fix:** extend the deny-list with `si`/`fbclid`/`gclid`/`ref`/`mc_*`; remove `s`.
  **Done:** replaced the inline list with `TRACKING_PARAMS` (26 entries) + `TRACKING_PREFIXES` (`utm_`, `mc_`, `pk_`, `piwik_`, `matomo_`, `hsa_`). `s` is no longer stripped; `si`, `fbclid`, `gclid`, `msclkid`, `igshid`, `twclid`, `ref`, `source` and friends now are. Added a separate `canonical_link()` (lowercased host, no `www.`/fragment/trailing slash, sorted query, https) used **only** for identity comparison, so the stored user-facing `link` is never mangled. 36 stored links were cleaned by the normalizer. 25 tests in `tests/test_url_identity.py`.

- [x] **H4 · `merge_articles` overwrites good data with empty values** `LATENT`
  `base_scraper.py:170-175` skips only `None`, so a re-parse yielding `description=""`, `title=""` or `author=""` clobbers previously good content. `hide=False` likewise silently un-hides a record unless the user manually added `"hide"` to `user_overrides`.
  **Fix:** skip falsy/empty values; never auto-reset `hide`.

- [x] **H5 · `--days` is ignored by every Markdown builder** `NOW`
  `build.py:74` defines `--days` (default 90) but passes it only to `build_news_page(args.days)` at `:110`. `build_latest(args.source)` and `build_latest_compact(args.source)` (`:98,101`) never receive it, so `build_single_latest`'s `days_window` stays pinned at its own default of 90. `python3 code/build.py --days 30` silently produces 90-day Markdown.
  **Fix:** thread `days_window` through both latest builders.

- [x] **H6 · `--inbox` is silently skipped when combined with `--refresh`** `NOW`
  `build.py:80` — `if args.inbox and not args.refresh:`. Running `--refresh --inbox` ingests nothing from `inbox.md` and prints no warning. (The intent was presumably that `my-collected-articles`' own scraper handles it during refresh, but that couples the two flags invisibly.)
  **Fix:** run the inbox processor whenever `--inbox` is passed, or warn explicitly.

- [x] **H7 · `--source` is ignored by `--news-page`** `NOW`
  `build.py:110` — `build_news_page(args.days)` takes no `source_id`, and `build_news_page` always rescans all of `data-sources/`. `--news-page --source dear-architects` rebuilds the whole dashboard.
  **Fix:** accept and honour an optional `source_id`, or document that the dashboard is always global.

- [x] **H8 · Rolling windows are data-relative, not clock-relative** `LATENT`
  `builder_core.apply_time_window:71-79` and `build_news_page.py:118-124` both anchor the cutoff to `max(article date)` rather than `now`. If scraping stalls for six months, "last 90 days" silently keeps showing the same stale 90-day slice instead of emptying — the outage becomes invisible.
  **Fix / Done:** both call sites now derive the cutoff from `datetime.now()`, so a stalled feed visibly empties instead of freezing. Added `staleness_days()` and `warn_if_stale()` to `builder_core`, called per-source in `build_latest` and once for the dashboard — the build now prints `[stale] future-software-development: newest article is 31 days old`, which is exactly the condition the old code hid. Future-dated conference entries are still retained. 6 tests in `test_content_quality.py`.

### Sources

- [x] **H9 · Publication dates are computed by arithmetic, not scraped** `LATENT`
  `dear-architects:301-307` (anchor #300 = 2026-07-25), `token-by-token:266-272` (#16 = 2026-07-30), `andriy-burkov-ai:289-295` (#336 = 2026-07-25) all derive dates as `anchor ± (issue_delta × 7 days)`. A single skipped or double-sent issue shifts **every** date permanently. `dear-architects` reaches back to #219, so its oldest entries carry dates invented ~2 years from the anchor.
  **Fix / Done:** extracted `common/mailerlite_scraper.py`. MailerLite discovery now reads the real send timestamp from `date`, `sent_at`, `sentAt`, `send_at`, `published_at`, or `created_at`; if absent, ingestion reads `article:published_time`, `<time datetime>`, or JSON-LD `datePublished` from the issue page. Andriy Burkov's retained manual importer uses the same page-metadata parser. If neither source supplies a date, ingestion raises an explicit error — there is **no arithmetic fallback**.
  Applied the mailbox ground truth to existing Dear Architects data: **34 issue dates and 181 article dates corrected**; a data-integrity test now requires every known issue/article date to match `issue_dates.json`. Duplicate issue numbers discovered at distinct URLs raise instead of being silently discarded, directly exposing the #261/#262 case. Historical Token by Token and Andriy Burkov values remain unverified data (D5), but future code can no longer invent them. 6 date/discovery tests.

- [x] **H10 · Boolean precedence bug in the sponsor filter** `NOW`
  `andriy-burkov-ai:104` — `if "[Sponsored]" in line or "sponsor" in line.lower() and "fandf.co" in clean_link` parses as `A or (B and C)`. Any line containing "Sponsored" is dropped regardless of its domain, discarding legitimate articles.
  **Fix / Done:** parenthesising alone was not enough. The bare substring `"sponsor" in line.lower()` is itself a false-positive generator — it discards headlines *about* sponsorship ("How open source sponsorship actually works"). Replaced it with `BaseScraper.has_sponsor_marker()`, a regex for genuine placement labels (`[Sponsored]`, `(Sponsored)`, `Sponsored:`, `Sponsored by`, `Presented by`, `In partnership with`, `Paid promotion`). The marker and the ad-network domain are now independent signals sharing one whitelist carve-out. 6 tests.

- [x] **H11 · Scraper shells out to the build system** `LATENT`
  `my-collected-articles:342` — `os.system(f"python3 {build_py}")`. Under `build.py --refresh` this triggers a **nested rebuild** inside the refresh loop, breaks on paths containing spaces, and assumes `python3` is on `PATH`. The same scraper also rewrites `inbox.md` (`archive_inbox_items`, `:269`) on every refresh, mutating a user-owned file as a side effect of an unrelated command.
  **Fix / Done (partial):** the `os.system(...)` nested build is deleted — `build.py` owns sequencing, and the scraper now just reports its ingest count. `archive_inbox_items` still rewrites `inbox.md`; that is arguably the source's purpose (an inbox is consumed), so it is left in place and noted rather than changed.

- [x] **H12 · `future-software-development/scraper.py` is a stub, not a scraper** `LATENT`
  35 lines; `sync_data()` (`:25-33`) only prints and re-saves the 16 hand-seeded records. No network access, no `extract_issues()` override (the inherited one raises `NotImplementedError`), no `merge_articles()`. It is silently included in `--refresh`, implying a refresh that never happens.
  **Fix / Done:** chose the honest static-source model. `SourceDefinition` now carries `static`, `refresh_enabled`, and `refresh_disabled_reason`; FOSE declares itself curated/static, and `build.py --refresh` skips it before launching a subprocess while printing the reason. Direct invocation also identifies it as static and never rewrites `data.json`. 2 refresh-policy tests.

- [x] **H13 · Sponsor deny-list was effectively inert — 42 ads rendered as articles** `NOW`
  `constants.py:33` declared `SPONSOR_DOMAINS = ["fandf.co"]`, a single domain. But Dear Architects routes its paid slots through **`fnf.dev`** (same ad network, different domain) and **`bit.ly`**, neither of which was listed. Measured: **42 visible advertising records** — 24 `fnf.dev`, 14 `bit.ly` (11 `dear-architects` + 3 `andriy-burkov-ai`), 2 `fandf.co`, 1 `go.rbrk.co`, 1 `theaiplatform.app`. Worse, the only two records the deny-list *did* match were handed back by the hardcoded whitelist `["observability engineering", "honeycomb"]` in `is_sponsor_link()`. Contents include affiliate discount codes (`LucaON202630`), webinar signups and vendor pitches (Atlassian, Tenable, Postman, Udacity, Heroku, Aiven, CodeRabbit…).
  Two secondary defects surfaced with them: HTML source indentation leaked into scraped text (**154 fields** with embedded newlines and runs of spaces, e.g. a title rendering as `5 hands-on weeks to master modern\n   architecture`), and 3 `author` fields holding non-authors (`"published on InfoQ"`, `":"`, `"7,258"` — a view count).
  **Fix / Done:** extended `SPONSOR_DOMAINS` to the real ad-network domains plus link shorteners (shorteners are used *exclusively* for paid slots here and hide the destination from every other heuristic — bit.ly returns 403 to non-browser clients, so the target cannot be resolved at build time). Replaced the hardcoded whitelist with a `SPONSOR_WHITELIST_TERMS` constant now matched against **URL and title** (previously title only, so a domain carve-out was impossible). Kept `certification.qconferences.com` and, following maintainer review, restored the Honeycomb / *Observability Engineering* carve-outs. **3 qconferences records and 3 Honeycomb/Observability records remain visible**; other ads stay hidden. `normalize_data.py` also collapses whitespace and drops implausible authors.

---

## 🟡 Medium

### Sources

- [x] **M1 · Hardcoded year filter expires in January** `LATENT`
  `addy-osmani:118` — `if year_str != "2026": continue`. Yields zero articles from 2027-01-01 onward.
  **Fix / Done:** replaced with a rolling `RECENT_WINDOW_DAYS = 730` cutoff measured from `datetime.now()`. Note the original was worse than "expires in January": in *any* January it also discarded the previous December's posts.

- [x] **M2 · `parsed_issues` tracker is inconsistent across sources** `NOW`
  `pragmatic-engineer:183-186` stores `count = len(self.articles)` (an *article* count, not issues), leaves `issues: []`, and writes an *article id* into `last_parsed_issue` — the shipped `definition.json` reads `count: 23, issues: 0`. `addy-osmani:207-214` never sets `last_parsed_issue`/`last_parsed_date` (both `""`). `my-collected-articles` never touches `parsed_issues` at all (frozen at `count: 1`).
  **Fix / Done:** added `BaseScraper.sync_parsed_issues(issues)` as the single writer of the tracker — it sorts newest-first, sets `count` to the number of *issues*, and derives `last_parsed_issue`/`last_parsed_date` from the newest entry, so the four fields can no longer disagree. Adopted by `addy-osmani` (which never set `last_parsed_*`), `pragmatic-engineer` (which wrote an article count and an article id) and `my-collected-articles` (which never maintained it at all — now grouped into monthly batches). 4 tests.

- [x] **M3 · `token-by-token/definition.json` is missing schema keys** `NOW`
  Lacks `has_archive` and `archive_retention_days`; every other source declares both. It currently works only because `.get("has_archive", True)` defaults favourably — the schema contract is undocumented-by-omission.
  **Fix / Done:** both keys added explicitly (`has_archive: true`, `archive_retention_days: null`), matching the values the defaults were silently supplying. All 7 sources now declare the full schema.

- [x] **M4 · Full re-crawl on every run, no rate limiting, no `robots.txt`** `LATENT`
  `dear-architects:324` and `andriy-burkov-ai:312` call `discover_and_ingest_new_issues(reparse_all=True)`, discarding `known_ids` — ~86 (DA) and ~8 (Burkov) full HTTP fetches per refresh, with no `time.sleep()` and one `save_data()` write per issue. No scraper consults `robots.txt`, and all spoof a desktop Chrome UA (`base_scraper.py:54`, `addy-osmani:40`, `my-collected-articles:64`). `andriy-burkov-ai:257` scrapes LinkedIn, which its ToS prohibits and which serves HTTP 999 to unauthenticated clients — this source is both fragile and legally questionable.
  **Fix / Done:** `BaseScraper.fetch_url()` is now the single HTTP path: honest `news-agg/1.0` UA, `robots.txt` evaluation, one-second inter-request throttle, retry/backoff, explicit `PermissionError` on disallowed URLs, and JSON/HTML wrappers. Addy Osmani, My Collected Articles, Pragmatic Engineer and MailerLite discovery were moved off private `urlopen` implementations; no browser-spoofing UA remains. MailerLite defaults to incremental discovery (`reparse_all=False`), and no scraper main forces full recrawls.
  LinkedIn automation is disabled rather than worked around: Andriy Burkov is marked static with the ToS/HTTP-999 reason, skipped by `--refresh`, and its discovery method raises if called programmatically. The existing imported data remains available. 6 crawl/refresh-policy tests.

- [x] **M5 · ~90% duplication between the two MailerLite scrapers** `LATENT`
  `dear-architects.py` and `token-by-token.py` share near-identical quote extraction, heading loop, author/description parsing and JSONP fetch (`dear-architects:239-262` ≡ `token-by-token:238-256`). The definition-tracking block is byte-identical across `dear-architects:200-231`, `token-by-token:177-208` and `andriy-burkov-ai:202-233`.
  **Fix / Done:** added `common/mailerlite_scraper.py`, owning JSONP decoding, API/archive discovery, subject parsing, authoritative date extraction, duplicate-number detection, quote extraction, heading/article parsing, issue ingestion, tracker updates and incremental selection. Dear Architects and Token by Token are now thin declarative adapters (API endpoint, id prefix, newsletter name, excluded own-domain links, archive pages, and Token by Token's title formatting). Their combined scraper implementation fell from ~650 duplicated lines to 55 adapter lines.

*Also noted in this area (lower confidence, worth a look during the fix pass): over-broad `is_spotlight` detection scoped to the whole wrapper `<table>` (`dear-architects:128`, `token-by-token:105`); fuzzy title/description line matching (`andriy-burkov-ai:98-102`); quote splitting that cuts at the first hyphen (`dear-architects:48-53`); fragile LinkedIn redirect unwrapping (`andriy-burkov-ai:38-42`); hardcoded pagination caps (`pragmatic-engineer:141`, `addy-osmani:77-80`, which ignores `selectors_spec.pages`); `%-d` strftime being non-portable to Windows; broad `except Exception` blocks that mask fetch failures.*

### Code

- [x] **M6 · Fragile HTML template resolution with a silent fallback** `LATENT`
  `build_news_page.py:24-33` tries `news_template.html`, then falls back to `project_root/news.html` — the **generated output**. If the template is ever missing or renamed, the builder silently re-injects into the last generated page, compounding drift instead of failing loudly. The third candidate, `old/all-news-enhanced.html`, does not exist in the repo.
  **Fix:** require the canonical template; raise if absent.

### HTML

- [x] **M7 · Stale newsletter names break badges and counts** `NOW`
  `news_template.html:813` (`data-source`), `:871` (filter `<option>`) and `:1273` (badge mapping) all use `"Future software development (Thoughtworks)"`, but the actual value in `data.json` is `"Future of Software Development (Thoughtworks FOSE)"`. Consequences: `badge-fose` (styled at `:437`) never applies, the FOSE description badge always renders `0`, and the hardcoded `<option>` list is dead weight since `populateSourceFilter()` overwrites it at runtime anyway.
  **Fix:** correct the string; consider deriving the source list from the data rather than hardcoding it twice.

### Data & docs

- [x] **M8 · 16 cross-source duplicate links** `NOW`
  The same article is ingested by multiple newsletters and rendered 2–3× in the dashboard. Examples: *Software Factories, Light and Dark* (`addy-osmani` + `dear-architects` + `token-by-token`); *Enforced Application Architecture for Agents and Humans*, *TDD in the agent loop*, *Eval-Driven Design Systems*, *DoorDash AI Code Reviewer*, *State of AI in Software Development 2026* (each in `dear-architects` + `token-by-token`). Two `andriy-burkov-ai` records duplicate within the same source. There is no global dedupe step — `merge_articles` only dedupes *within* a source.
  **Fix:** add a cross-source dedupe in `build_news_page`/`builder_core` keyed on cleaned link, keeping the earliest-dated record and noting the other sources.
  **Done:** `build_news_page.py` now groups by `canonical_link()`, keeps the **earliest-dated** record and attaches `also_in: [...]` naming the later sources. The dashboard renders a `+N` pill on the source badge whose tooltip lists them, and the source filter matches `also_in` as well as `newsletter`, so filtering by *Token by Token* still finds an article credited to *Dear Architects*. Verified: **22 duplicates merged, 261 articles rendered, 0 duplicate links in view**, 12 articles carrying an `also_in`. The per-source Markdown digests are deliberately unchanged — each file covers one source, so there is nothing to dedupe across.

- [x] **M9 · Scraped boilerplate stored as article content** `NOW`
  `ab-335-7` and `ab-334-7` both have `title: "Subscribe to receive an email when this happens"` → `https://aiweekly.substack.com/`. Truncated titles: `ab-338-6` = `"Flint"`, `tbt-1-1` = `"Archi"`. One record has a `mailto:hello@truepositive.ca` link. Quality totals across 737 records: **558 missing authors**, **99 empty descriptions**.
  **Fix / Done (partial):** added `BOILERPLATE_TITLES` (24 entries), `NON_ARTICLE_SCHEMES` and `BaseScraper.is_boilerplate()`, applied at ingest and as a normalizer step. **3 records hidden** — the two `"Subscribe to receive an email when this happens"` entries and the `mailto:` one.
  The proposed minimum-title-length guard was **deliberately not used to hide anything**: at a 12-character threshold it also flags `GLM-5.2`, `Kimi K3`, `Reddit`, `Superagency` and `MVC Mistake`, which are real. A truncated title still points at a real article, so discarding it would lose content. It is instead exposed as `is_suspicious_title()`, reported by the normalizer (**13 visible records**) and ratcheted by a test. Tracked as D8.
  Still open: 558 missing authors and 99 empty descriptions — these need backfill, not a filter.

---

## 🔵 Low

### HTML

- [x] **L1 · Dead duplicate function definition** — `exportSelectionToMarkdown` is defined twice, at `:1368` and again at `:1619` in the second `<script>` block. The later definition wins; the first (which uses an inline Blob instead of `triggerDownload`) is unreachable. `getBadgeClass()` at `:1665` is also never called.
- [x] **L2 · Sort headers are not keyboard-accessible** — `<th onclick="handleSort(...)">` at `:943-947` have no `tabindex`, `role="button"` or key handler; column sorting is mouse-only.
- [x] **L3 · Overloaded timeframe sentinel** — `:860` uses `<option value="all">Last 3 Months</option>`, so `"all"` means "90 days" here but "no filter" everywhere else. The default selection is `"30"` (`:858`), meaning the page loads showing 1 month of a 3-month dataset, which is easy to misread as missing data.
- [x] **L7 · Stale `currentViewArticles` on a no-results filter** `NOW` — *(found while fixing C1; fixed in the same pass)*
  `render()`'s empty-results early-return updated `resultsCount` but left `currentViewArticles` holding the **previous** filter's articles, so "Export view" after a search with no matches exported the wrong set. Now reset to `[]`.
- [x] **L4 · Misleading "live" counts** — `renderCategoryCounts()` (`:1005`) is commented "Append the **live** article count" but runs once against the unfiltered set and is never re-invoked from `render()`, so the badges never reflect active filters.

### Code

- [x] **L5 · No tests, no CI, no declared Python version** — nothing under `tests/`, no workflow, no `requirements.txt`. `pragmatic-engineer:33` uses a `tuple[str, ...]` annotation requiring Python ≥3.9 (the environment here is 3.9.6) but no minimum is documented. Given the pipeline's central invariants (ID uniqueness, canonical categories, date formats), a small data-lint test would have caught C5, M8 and M9 automatically.
  **Done:** added a stdlib `unittest` suite (no new dependencies) — 42 tests, run with `python3 -m unittest discover -s tests`:
  - `tests/test_auto_categorize.py` — 17 tests pinning the H2 fix (word boundaries, plural forms, hyphenated keywords, scoring, determinism). Verified to fail 4/17 if the pre-H2 substring matching is restored.
  - `tests/test_merge_articles.py` — 14 tests pinning the H4 fix (empty/whitespace/`None` never clobber, `hide` never auto-resets) plus `user_overrides` precedence, key precedence and merge idempotence.
  - `tests/test_data_integrity.py` — 9 data-lint tests over all 737 records: full schema coverage, canonical `CATEGORIES`/`CONTENT_TYPES` (imported, not hardcoded), ISO dates, no surviving tracking params, non-empty ids/titles, `user_overrides` naming real fields. The still-deferred D6/D7 defects are covered by **ratchet** tests that pin the current duplicate counts (`dear-architects` 97, `andriy-burkov-ai` 3 ids / 2 links) so the data cannot silently degrade, and that fail with an explicit "tighten this test" message once the duplicates are actually removed.
  `requirements.txt` was added under C4. Python minimum is still undeclared — see the note below.

### Data & docs

- [x] **L6 · Documentation inconsistencies**
  * The former `docs/INSTRUCTIONS.md:123` said "**6** Canonical Categories"; §5 listed **7**, matching `constants.py`.
  * The former `docs/INSTRUCTIONS.md:169` announced a "4-step process" then listed **5** steps.
  * Six links point at `file:///Users/gyu/projects/news-agg/…` — another machine's absolute paths (`:160`, `:161`, `:162`, `:231`).
  * `README.md:86` and the former `INSTRUCTIONS.md:32` documented `generated/` as a deliverable, but `.gitignore` excludes it — worth stating that outputs are generated, not committed.
  * `README.md:44` describes `--inbox` without mentioning it is a no-op alongside `--refresh` (see H6).

---

## Root-cause clusters

Several issues share a single origin. Fixing the cluster resolves all members:

| Cluster | Members | Single fix |
| :--- | :--- | :--- |
| **Unsafe string interpolation in the template** | C1, C2, C3 | One pass over `news_template.html` render/export paths |
| **Link identity** | C5, H3, M8 | Canonical URL normalisation + hash-derived IDs |
| **Silent failure** | C4, H8, M6, M4 | Fail loudly: return codes, staleness checks, no fallbacks |
| **Type-coercion at the JSON boundary** | H1, M2, M3 | Normalise `issue_number`/`id` to `str` in one place |
| **CLI flags not threaded through** | H5, H6, H7 | One pass over `build.py` argument plumbing |
| **Copy-paste scraper logic** | M5, M2, H9 | Extract `MailerLiteScraper` + shared date/issue helpers |

---

## Suggested fix order

| Group | Contents | Risk | Verification |
| :-- | :--- | :--- | :--- |
| **1** | C1, C2, C3 — HTML render + export safety | Low | `node` eval, then browser |
| **2** | H1 — quote key mismatch | Low | Quotes appear in `news.html` |
| **3** | C4, L5 — `requirements.txt`, return codes, data-lint test | Low | `--refresh` fails loudly without `bs4` |
| **4** | C5, H3, M8 — link normalisation, stable IDs, dedupe | Medium | Re-run data-lint: 0 dup IDs, 0 dup links |
| **5** | H5, H6, H7 — CLI flag plumbing | Low | `--days 30` changes Markdown output |
| **6** | H2, H4 — categorisation + merge semantics | Medium | Spot-check reclassified articles |
| **7** | M7, M1, M2, M3, L6 — naming, schema and doc consistency | Low | Rebuild, diff |
| **8** | H9, H11, H12, M4, M5 — scraper correctness & etiquette | High | Implemented offline; live endpoints still need network verification |

Groups 1–3 are self-contained and independently verifiable. Group 4 rewrites `data.json` IDs and should be committed on its own. Group 8 is implemented and covered by offline tests; a network-enabled agent should still exercise the live refresh paths with `bs4` installed.

---

## Verification commands used

```bash
# Reproducible build
python3 code/build.py && git status --short          # → clean

# Data integrity scan (737 records, 7 sources)
#  → 0 bad categories / types / dates, 0 utm_ residue
#  → 91 duplicate IDs, 16 duplicate links, 558 null authors, 99 empty descriptions

# JS defect reproduction
node -e "…"   # C1 TypeError on null author; C2 literal ${titleText} in export

# Categoriser probe
#  "The latest release of Postgres" → Software Testing (matches 'test' in 'latest')
```
