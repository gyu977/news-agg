# Dear Architects Source Documentation

## Source Overview
* **Author:** Luca Mezzalira
* **Official Site:** [https://deararchitects.xyz/](https://deararchitects.xyz/)
* **Archive URL:** [https://www.deararchitects.xyz/archive](https://www.deararchitects.xyz/archive)
* **Newsletter Platform:** MailerLite Webview

---

## DOM Selectors & Extraction Rules

1. **Issue Header:**
   - Appears as `### Luca Mezzalira's Dear Architects` in markdown outputs.
   - Format: `**[#IssueNum - Issue Title](Issue Link)** - Date`

2. **Quotes:**
   - Extracted from `<blockquote>` or Gregor Hohpe quote segments.
   - Formatted directly under the issue header. Issue #300 features two quotes.

3. **Article Headings:**
   - Articles are identified inside `<h2>` or `<h3>` tags with embedded anchor links `<a href="...">`.

4. **Visual Markers:**
   - Video link domains (`youtube.com`, `youtu.be`, `gitnation.com`) automatically receive the `▶️` marker.
   - Book link domains (`amazon.com`, `amzn.to`, `oreilly.com`, `manning.com`) automatically receive the `📖` marker.

5. **Spotlight:**
   - Articles featuring "In the spotlight" are flagged with `is_spotlight: true`.

6. **Filtering:**
   - Exclude sponsored affiliate links (`fandf.co`) unless specifically whitelisted (e.g. Honeycomb Observability AMA).
