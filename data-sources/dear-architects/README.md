# Dear Architects Source Documentation

## Source Overview
* **Author:** Luca Mezzalira
* **Official Site:** [https://deararchitects.xyz/](https://deararchitects.xyz/)
* **Archive URL:** [https://www.deararchitects.xyz/archive](https://www.deararchitects.xyz/archive)
* **Newsletter Platform:** MailerLite JSON feed and hosted email webviews
* **Archive:** Enabled with unlimited retention

---

## DOM Selectors & Extraction Rules

1. **Issue Header:**
   - Appears as `### Luca Mezzalira's Dear Architects` in markdown outputs.
   - Format: a bold `#IssueNum - Issue Title` link followed by the publication date.

2. **Quotes:**
   - Extracted from blockquotes and quote-like heading or paragraph sections.
   - Stored in `definition.json` and rendered below the issue header.

3. **Article Headings:**
   - Articles are identified inside `<h2>` or `<h3>` tags with embedded anchor links `<a href="...">`.

4. **Visual Markers:**
   - Video link domains (`youtube.com`, `youtu.be`, `gitnation.com`) automatically receive the `▶️` marker.
   - Book link domains (`amazon.com`, `amzn.to`, `oreilly.com`, `manning.com`) automatically receive the `📖` marker.

5. **Spotlight:**
   - `<h1>` articles and sections explicitly labelled "In the spotlight" are flagged
     with `is_spotlight: true`.

6. **Filtering:**
   - Excludes configured sponsor and tracking domains unless the content matches the
     shared useful-content whitelist.
