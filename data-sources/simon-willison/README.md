# Simon Willison's Weblog

- **Source ID:** `simon-willison`
- **Author:** Simon Willison
- **Website:** https://simonwillison.net/
- **Feed (Highlights only):** https://simonwillison.net/atom/entries/
- **Type:** rss / atom
- **Article ID Prefix:** `sw`
- **Description:** Highlights and long-form blog entries on AI, LLMs, agents, and open-source architecture by Simon Willison.

## Highlights Policy

Simon Willison maintains two feeds:
1. `/atom/everything/`: All micro-posts, link snippets, and quotations.
2. `/atom/entries/`: Exclusively the long-form articles and essays (matching the "Highlights" section on his homepage).

Per editorial design and author respect, this scraper ingests exclusively from `/atom/entries/` and does not truncate the article body into arbitrary partial excerpts. The article `description` field is left empty so that titles, tags, and links speak for themselves.

## Data Pipeline

Run this source scraper individually:
```bash
python3 data-sources/simon-willison/scraper.py
```

Or refresh via the master orchestrator:
```bash
python3 code/build.py --refresh --source simon-willison
```
