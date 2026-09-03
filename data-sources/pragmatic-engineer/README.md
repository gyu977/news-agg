# The Pragmatic Engineer Source Specification

* **Source ID**: `pragmatic-engineer`
* **Newsletter Name**: The Pragmatic Engineer
* **Author**: Gergely Orosz
* **Official Website**: [https://newsletter.pragmaticengineer.com/](https://newsletter.pragmaticengineer.com/)
* **Platform**: Substack
* **API Endpoint**: Paginated `https://newsletter.pragmaticengineer.com/api/v1/archive?sort=new`
* **Archive:** Enabled with unlimited retention
* **Last Updated:** 1 September 2026

---

## 🎯 Extraction Selectors

| Element | DOM Selector / Extraction Rule |
| :--- | :--- |
| **API Feed** | Substack JSON endpoint `/api/v1/archive?sort=new` |
| **Article Title** | Post `title` field |
| **Description** | Post `subtitle` field |
| **Guest Author** | Extracted from titles ending in `, with [Guest]` or `with [Guest]` |
| **Pulse Digests** | `⚡` marker if title contains `The Pulse:` |
| **Podcasts / AMA** | `▶️` marker if post is a podcast or video episode |
| **Pagination** | Requests batches of 50 posts, up to the current 200-post safety cap |
