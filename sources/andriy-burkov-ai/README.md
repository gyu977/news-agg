# Artificial Intelligence (Andriy Burkov) Source Specification

* **Source ID**: `andriy-burkov-ai`
* **Newsletter Name**: Artificial Intelligence (Andriy Burkov)
* **Author**: Andriy Burkov
* **Official Website**: [https://www.linkedin.com/newsletters/artificial-intelligence-6598352935271358464/](https://www.linkedin.com/newsletters/artificial-intelligence-6598352935271358464/)
* **Platform**: LinkedIn Newsletters & LinkedIn Pulse
* **Archive Retention**: `90` days (3 months archive limit property)
* **Publication Cadence**: Weekly on Saturdays

---

## 🎯 Extraction Selectors

| Element | DOM Selector / Detection Rule |
| :--- | :--- |
| **Issue Discovery** | `a[href*="/pulse/artificial-intelligence-"]` on newsletter homepage |
| **Articles** | `<p>`, `<li>` tags with external links inside `<article>` container |
| **LinkedIn Redirect Unwrapping** | Extracts `url` parameter from `/redir/redirect?url=...` |
| **Author Name** | Leading tag `[Author]` or leading `**Author**` prefix |
| **Sponsor Filter** | URLs matching `fandf.co`, `[Sponsored]` markers |
| **Visual Markers** | `▶️` (YouTube), `📖` (Books/Arxiv), `⚡` (Pulse) |
