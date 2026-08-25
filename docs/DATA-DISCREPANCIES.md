# Data Discrepancies — Deferred Fixes

**Recorded:** 2026-08-25 · **Status:** D1, D6, D7 and D9 resolved; D2–D5 and D8 remain data work · **Owner issues:** H9, C5, M8, M9 and re-review R7 in [`CODE-REVIEW.md`](CODE-REVIEW.md)

This file records **data-level** defects — wrong values in `data-sources/*/data.json` and `definition.json` — as distinct from code defects. They are deliberately deferred so that code fixes can land first without mixing large data rewrites into the same commits.

Ground truth for Dear Architects issue dates is stored in
[`data-sources/dear-architects/issue_dates.json`](../data-sources/dear-architects/issue_dates.json), extracted from 10 mailbox screenshots covering issues #219–#304.

---

## D1 · Dear Architects — 34 issue dates are one day early — ✅ RESOLVED

**Root cause before H9 was fixed:** the old Dear Architects scraper derived dates arithmetically from a hardcoded anchor (`#300 = 2026-07-25`) at exactly 7-day intervals, rather than reading the real send date.

**Verification:** all 86 issues cross-checked against mailbox screenshots. **49 correct, 34 wrong, 1 unverifiable.** Every error is exactly **+1 day** (stored date is one day earlier than the real send date) — the newsletter slips a day some weeks, and the rigid 7-day grid cannot represent that. Errors oscillate rather than accumulate, which is why the drift went unnoticed.

**Impact before correction:** 181 surviving article records carried a wrong `date` and `date_str` after same-issue duplicate consolidation. This affected chronological sort order, 90-day window membership, and every generated Markdown digest.

| Issue | Stored | Correct | Delta | Articles |
| :-- | :-- | :-- | :-- | :-- |
| 299 | `2026-07-18` | `2026-07-19` | +1d | 6 |
| 296 | `2026-06-27` | `2026-06-28` | +1d | 7 |
| 291 | `2026-05-23` | `2026-05-24` | +1d | 6 |
| 288 | `2026-05-02` | `2026-05-03` | +1d | 7 |
| 287 | `2026-04-25` | `2026-04-26` | +1d | 7 |
| 286 | `2026-04-18` | `2026-04-19` | +1d | 6 |
| 285 | `2026-04-11` | `2026-04-12` | +1d | 6 |
| 282 | `2026-03-21` | `2026-03-22` | +1d | 6 |
| 281 | `2026-03-14` | `2026-03-15` | +1d | 6 |
| 280 | `2026-03-07` | `2026-03-08` | +1d | 8 |
| 278 | `2026-02-21` | `2026-02-22` | +1d | 7 |
| 271 | `2026-01-03` | `2026-01-04` | +1d | 5 |
| 270 | `2025-12-27` | `2025-12-28` | +1d | 4 |
| 258 | `2025-10-04` | `2025-10-05` | +1d | 6 |
| 257 | `2025-09-27` | `2025-09-28` | +1d | 6 |
| 255 | `2025-09-13` | `2025-09-14` | +1d | 5 |
| 254 | `2025-09-06` | `2025-09-07` | +1d | 5 |
| 253 | `2025-08-30` | `2025-08-31` | +1d | 5 |
| 247 | `2025-07-19` | `2025-07-20` | +1d | 6 |
| 241 | `2025-06-07` | `2025-06-08` | +1d | 5 |
| 240 | `2025-05-31` | `2025-06-01` | +1d | 5 |
| 239 | `2025-05-24` | `2025-05-25` | +1d | 5 |
| 238 | `2025-05-17` | `2025-05-18` | +1d | 4 |
| 237 | `2025-05-10` | `2025-05-11` | +1d | 6 |
| 236 | `2025-05-03` | `2025-05-04` | +1d | 4 |
| 235 | `2025-04-26` | `2025-04-27` | +1d | 4 |
| 233 | `2025-04-12` | `2025-04-13` | +1d | 5 |
| 232 | `2025-04-05` | `2025-04-06` | +1d | 5 |
| 230 | `2025-03-22` | `2025-03-23` | +1d | 6 |
| 228 | `2025-03-08` | `2025-03-09` | +1d | 6 |
| 226 | `2025-02-22` | `2025-02-23` | +1d | 6 |
| 222 | `2025-01-25` | `2025-01-26` | +1d | 6 |
| 221 | `2025-01-18` | `2025-01-19` | +1d | 6 |
| 220 | `2025-01-11` | `2025-01-12` | +1d | 6 |
**Done:** corrected all 34 known `definition.json` issue dates and propagated them to 181 article records. `test_dear_architects_dates_match_mailbox_ground_truth` now ratchets both surfaces against `issue_dates.json`. Future MailerLite ingestion reads authoritative API/page metadata and refuses to ingest if no real date is present; the arithmetic fallback is deleted.

---

## D2 · Dear Architects — issues #261 and #262 are missing entirely

`data.json` jumps from #260 (2025-10-18) straight to #263 (2025-11-08). The mailbox explains why — three consecutive emails were all sent with the subject line `#260`:

| Subject says | Real date | Present in `data.json`? |
| :-- | :-- | :-- |
| `#260` | 2025-10-18 | ✅ stored as #260 (title matches: *"the truth about distributed systems, Pinterest DX…"*) |
| `#260` | 2025-10-25 | ❌ **missing** — should be #261 |
| `#260` | 2025-11-02 | ❌ **missing** — should be #262 |

**Impact:** two entire issues and all their articles are absent from the dataset. The screenshots supply dates only, not contents — recovery needs the MailerLite archive entries.

**Fix plan:** locate both issues in the MailerLite archive, ingest them, and assign the corrected numbers #261/#262. The scraper guard is now implemented: distinct URLs sharing an issue number raise an explicit `ValueError` rather than one being silently skipped.

---

## D3 · Dear Architects — issue #275 date unverified

The `#275` row was hovered when its screenshot was taken, so action icons covered the date column. Recorded as `null` in `issue_dates.json` rather than guessed.

Bounded by neighbours: **after #274 (2026-01-24)** and **before #276 (2026-02-07)**. Currently stored as `2026-01-31`, which is consistent with that window but derives from the same unreliable arithmetic.

**Fix plan:** re-screenshot the row without hovering, or read the date from the MailerLite archive.

---

## D4 · Dear Architects — issues #217 and #218 unverifiable

`data.json` contains #217 (`2024-12-21`) and #218 (`2024-12-28`). Both predate the oldest mailbox screenshot (#219, 2025-01-04), so no ground truth exists for them. Given D1's pattern they are *likely* also one day early, but this is unconfirmed.

**Fix plan:** leave untouched unless the MailerLite archive confirms otherwise. Do **not** apply a blanket +1 day.

---

## D5 · Other sources use the same arithmetic — dates unverified

The identical anchor-plus-7-days pattern appears in two more scrapers, neither of which has been checked against ground truth:

| Source | Anchor | Location |
| :-- | :-- | :-- |
| `token-by-token` | `#16 = 2026-07-30` | `scraper.py:266-272` |
| `andriy-burkov-ai` | `#336 = 2026-07-25` | `scraper.py:289-295` |

Given Dear Architects showed a **40% error rate** under the same scheme, both should be presumed wrong until verified.

**Code fix complete:** no scraper derives dates from issue-number arithmetic anymore. MailerLite uses send/page metadata; the disabled LinkedIn importer requires page metadata. **Data verification remains open:** obtain equivalent mailbox/archive evidence and repeat the D1 comparison for the already-stored historical values.

---

## D6 · 58 redundant records from un-canonicalised URLs — ✅ RESOLVED

**Root cause:** H3 / C5 / M8. Canonicalising URLs (stripping `si`/`fbclid`/`gclid`/`ref`, normalising `youtu.be` → `youtube.com/watch?v=`) collapses **737 records → 679 distinct links**.

| Kind | Groups | Disposition |
| :-- | :-- | :-- |
| Same-source duplicates | 38 | Merge in `data.json` — 36 auto-mergeable (titles agree), 2 need review |
| Cross-source duplicates | 18 | **Keep** — two newsletters recommending the same article is real signal. Dedupe at render time only. |

The 2 needing review are recurring promo links whose ad copy changes between issues, so they are arguably sponsor content to drop rather than merge:

* `tokenbytoken.ai/` — *"Master AI one Token at a time"* (da-292-3) vs *"One email a week…"* (da-286-2)
* `certification.qconferences.com/` — two different QCon ads (da-282-2, da-280-3)

**Resolved** by `code/tools/normalize_data.py` (run once; idempotent and re-runnable):
`dear-architects` went **479 → 444 records**, merging **35 same-issue duplicates** and cleaning
**36 links**. Verified lossless against `git show HEAD:…` — 0 titles lost, 0 fields degraded,
`hide` flags and `user_overrides` preserved. Cross-issue repeats were deliberately kept.

Four cross-issue repeats remain and are covered by a ratchet test rather than deleted, because
removing them is an editorial judgement rather than a data defect:

| Link | Issues | Assessment |
| :-- | :-- | :-- |
| `tokenbytoken.ai/` | da #292, #286 | Promo blast — candidate for `hide: true` |
| `certification.qconferences.com/` | da #282, #280 | QCon advert — candidate for `hide: true` |
| `aiweekly.substack.com/` | ab #335, #334 | Subscribe CTA scraped as an article — candidate for `hide: true` |
| `blog.bytebytego.com/p/a-guide-to-ai-inference-engineering` | ab #334, #333 | **Genuine** repeat recommendation — keep both |

---

## D7 · 91 duplicate article IDs — ✅ RESOLVED

**Root cause:** C5. Positional `{prefix}-{issue}-{idx}` IDs, where a second parse pass restarts the counter at 1. 88 duplicates in `dear-architects`, 3 in `andriy-burkov-ai`. Indices are not even contiguous, because filtered sponsor links consume numbers.

**Agreed fix:** re-key as `{prefix}-{issue}-{hash6}`, where `hash6` is derived from the canonical URL. Must land **after** D6, since the hash depends on the canonical URL.

**Resolved.** `BaseScraper.make_article_id()` now mints `{prefix}-{issue}-{hash6}` from the
canonical link (SHA-1, first 6 hex digits), and all seven scrapers were switched to it. All
**702 existing ids were rewritten** by the normalizer. The prefix is a constant in
`code/tools/normalize_data.py` rather than a `definition.json` field — one fewer place for the
two to drift apart. Guarded by `tests/test_data_integrity.py` (global uniqueness, id format,
no duplicate link within an issue) and `tests/test_url_identity.py` (id stability across
tracking-parameter variants, position independence).


---

## D8 · Content-quality defects — ⚠️ PARTLY RESOLVED

| Defect | Count | Status |
| :-- | :-- | :-- |
| Boilerplate stored as articles | 2 | ✅ hidden — `ab-335-af1153`, `ab-334-af1153` (*"Subscribe to receive an email when this happens"* → `aiweekly.substack.com`) |
| Non-article link | 1 | ✅ hidden — `ab-333-2541d0`, `mailto:hello@truepositive.ca` |
| Suspiciously short titles | 13 | ⬜ **open — 3 confirmed incomplete, 10 valid or requiring judgement** (see below) |
| Longer partial titles | 2 | ⬜ **open — confirmed from destination-page titles** (see below) |
| Missing author | 558 | ⬜ open — 76% of records |
| Empty description | 99 | ⬜ open — 13% of records |

**Resolved:** `BOILERPLATE_TITLES` + `NON_ARTICLE_SCHEMES` in `constants.py`, applied by
`BaseScraper.is_boilerplate()` at ingest and as a `normalize_data.py` step. 3 records hidden.

### Truncated titles are reported, not hidden

The original fix plan proposed a minimum-title-length guard that would also `hide` short
titles. **That was rejected after measuring it.** At a 12-character threshold the guard
flags 13 records, but most are legitimate:

| ID | Title | Verdict |
| :-- | :-- | :-- |
| `ab-338-254757` | *Flint* | ❌ truncated (`flint-chart`) |
| `ab-339-2db3cd` | *So who is* | ❌ truncated mid-sentence |
| `tbt-1-b606b0` | *Archi* | ❌ truncated |
| `ab-333-2ea3cc` | *GLM-5.2* | ✅ real product name |
| `ab-337-e1a7b6` | *Kimi K3* | ✅ real product name |
| `ab-339-f1afe2` | *Qwen3.8-Max* | ✅ real product name |
| `da-227-382650` | *Reddit* | ✅ real |
| `da-233-d7f799` | *Vibe coding* | ✅ real |
| `da-277-0808cd` | *EDA Visuals* | ✅ real (site name) |
| `da-280-ed96eb` | *Superagency* | ✅ real (book title) |
| `da-289-809e7a` | *MVC Mistake* | ✅ real |
| `da-301-47e394` | *Slow AI* | ✅ real (book title) |
| `tbt-16-e60c4f` | *Slow AI* | ✅ real (book title) |

Only 3 of 13 are genuine defects — a 77% false-positive rate. And a truncated title still
points at a **real article**, so hiding it would lose content rather than clean it up.

Two additional incomplete titles are long enough to evade the short-title heuristic:

| ID | Stored title | Confirmed destination title |
| :-- | :-- | :-- |
| `ab-339-343894` | *weapon against AI scrapers is a font* | *The web’s newest weapon against AI scrapers is a font* |
| `ab-338-f5f908` | *breakthrough in forecasting cyclones* | *WeatherNext: AI model achieves breakthrough in forecasting cyclones* |

Both records came from the static Andriy Burkov import. Their destination URLs and page/search
metadata confirm that the leading title text was lost during historical extraction. They are
recorded here rather than changed pending a dedicated data-cleanup pass.

**Current handling:** exposed as `BaseScraper.is_suspicious_title()`, counted by
`normalize_data.py` as a report-only statistic (it does not mark data as changed), and
ratcheted by `tests/test_data_integrity.py::test_truncated_titles_do_not_increase`
(`KNOWN_TRUNCATED_TITLES = 13`).

**Fix plan:** repair the 5 confirmed incomplete titles by hand from their link targets, then
tighten the short-title ratchet from 13 to 10. The remaining 10 short titles need a per-title
judgement, not a rule.

---

## D9 · Source definition trackers are inconsistent with committed data — ✅ RESOLVED

Found by the independent re-review (R7):

| Source | Stored tracker defect |
| :-- | :-- |
| `addy-osmani` | 8 issue entries, but `last_parsed_issue` and `last_parsed_date` are blank |
| `pragmatic-engineer` | `count: 23` and a last issue, but `issues: []` |
| `my-collected-articles` | Frozen at one July issue while data spans 12 dates through October |

The shared `sync_parsed_issues()` implementation is correct, but the committed definition
files were not migrated after it was introduced. No current integrity test checks
definition-to-data tracker consistency.

**Done:** rebuilt Addy as 8 monthly issues, Pragmatic as 23 post issues, and My Collected
Articles as 4 monthly issues. `test_definition_trackers_are_self_consistent` now requires
`count == len(issues)`, newest-first ordering, and `last_parsed_*` equal to the first issue
for all 7 sources.

---

## Correctly-excluded content — do not "fix"

The scrapers rightly skip these, and any future change must keep skipping them:

* **Unnumbered promo blasts** — *"Last chance for early access"* (2025-10-02), *"Turn what you know into real architectural impact"* (2025-09-17)
* **`#230.1 Errata Corrige`** (2025-03-23) — a correction resend of #230, not a distinct issue

## Do not import titles from the screenshots

Rendered subject lines truncate at `·`, so they are **poorer** than what is already stored:

```
screenshot: "2026: What's hype vs. reality"
data.json:  "Dear Architects - 2026: What's hype vs. reality?"
```

Screenshots are authoritative for **dates only**. Issue numbers are the join key; titles serve solely as a cross-check against row misreads.
