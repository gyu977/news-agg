# Token by Token Source Specification

* **Source ID**: `token-by-token`
* **Newsletter Name**: Token by Token
* **Author**: Luca Mezzalira
* **Official Website**: [https://www.tokenbytoken.ai/](https://www.tokenbytoken.ai/)
* **Platform**: MailerLite
* **Account ID**: `2096144`
* **Dynamic API Endpoint**: `https://assets.mailerlite.com/jsonp/2096144/recent-emails/0371fada216137b32c04343dc4ad33a6140353a621bb0d8111810301386e7619`
* **Archive:** Enabled with unlimited retention

---

## 🎯 Extraction Selectors

| Element | DOM Selector / Detection Rule |
| :--- | :--- |
| **Spotlight Article** | `<h1><a href="...">` |
| **Standard Articles** | `<h2><a href="...">`, `<h3><a href="...">` |
| **Article Descriptions** | Sibling `<p>` paragraphs with length > 20 characters |
| **Author Name** | Not inferred from `<strong>` tags because newsletter emphasis was producing false bylines; verified authors are maintained through overrides |
| **Sponsor Filter** | URLs matching `fandf.co` |
| **Visual Markers** | `▶️` (YouTube/GitNation), `📖` (Amazon/Manning/O'Reilly), `⚡` (Pulse) |
