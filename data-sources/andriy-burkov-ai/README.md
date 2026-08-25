# Artificial Intelligence (Andriy Burkov) Source Specification

* **Source ID**: `andriy-burkov-ai`
* **Newsletter Name**: Artificial Intelligence (Andriy Burkov)
* **Author**: Andriy Burkov
* **Official Website**: [https://www.linkedin.com/newsletters/artificial-intelligence-6598352935271358464/](https://www.linkedin.com/newsletters/artificial-intelligence-6598352935271358464/)
* **Platform**: Static import from LinkedIn Newsletters / Pulse
* **Archive Retention**: `90` days (3 months archive limit property)
* **Publication Cadence**: Weekly on Saturdays
* **Refresh Policy**: Automated LinkedIn crawling is disabled because the site blocks
  unauthenticated automation and does not permit this scraper approach. Existing imported
  data remains available; future updates require an authorised/manual export.

---

## Historical Import Parser

| Element | DOM Selector / Detection Rule |
| :--- | :--- |
| **Issue Discovery** | Disabled; no automated discovery is performed |
| **Articles** | `<p>`, `<li>` tags with external links inside `<article>` container |
| **LinkedIn Redirect Unwrapping** | Extracts `url` parameter from `/redir/redirect?url=...` |
| **Author Name** | Leading tag `[Author]` or leading `**Author**` prefix |
| **Sponsor Filter** | URLs matching `fandf.co`, `[Sponsored]` markers |
| **Visual Markers** | `▶️` (YouTube), `📖` (Books/Arxiv), `⚡` (Pulse) |
