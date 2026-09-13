# Artificial Intelligence (Andriy Burkov) Source Specification

* **Source ID**: `andriy-burkov-ai`
* **Newsletter Name**: Artificial Intelligence (Andriy Burkov)
* **Author**: Andriy Burkov
* **Official Website**: [https://www.linkedin.com/newsletters/artificial-intelligence-6598352935271358464/](https://www.linkedin.com/newsletters/artificial-intelligence-6598352935271358464/)
* **Platform**: Static import from LinkedIn Newsletters / Pulse
* **Archive Retention**: `90` days (3 months archive limit property)
* **Last Updated:** 12 September 2026 (Issue #343)
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
| **Content Types** | Derived from canonical domain and title rules shared by `BaseScraper` |

---

## 🎯 Editorial Filtering Policy (Signal vs. Noise)

Because Andriy Burkov curates a broad weekly "Artificial Intelligence" feed (~8 items per week) rather than a pure software engineering newsletter, future imports and manual additions must follow this filtering policy:

### 🚫 Filtered / Hidden (`hide: true`)
1. **General Consumer & Societal News**:
   - Mainstream media opinion pieces and op-eds (e.g. book scanning copyright disputes, general web traffic discussions).
   - Non-technical consumer/student topics (e.g. AI impact on high school homework, consumer chatbot psychology).
   - General social media bot and content moderation commentary.
2. **Academic Conference & Detector Drama**:
   - Administrative and reviewer controversies (e.g. conference desk rejections over detector false positives).
   - Benchmark disputes around generic AI text detectors (e.g. Pangram, GPTZero, Turnitin).

### ✅ Retained / Active (`hide: false`)
1. **Core Technical & Software Engineering**:
   - Machine learning systems, inference engines, and runtimes (e.g. vLLM, speculative decoding, KV cache compression).
   - Coding agents, execution harnesses, tool calling, and sandboxing.
   - LLM architectures, open weights, evaluation frameworks, and watermarking internals.
2. **Pure Academic Mathematics & Natural Science**:
   - Foundational computer science and mathematical logic (e.g. Quanta Magazine coverage of Reverse Mathematics, Erdős problems, Lean formal verification).
   - Deep learning breakthroughs applied to natural sciences (e.g. weather physics, genomics, molecular/food design).

