# Addy Osmani Blog Source Module

Source adapter for Addy Osmani's personal technical blog at `https://addyosmani.com/blog/`.

## Extraction & Filtering Rules
- **Platform**: Static HTML personal blog.
- **Domain Scope**: Strictly articles hosted on `https://addyosmani.com/blog/` (excludes external posts on Substack or LeadDev).
- **Timeframe**: Articles published in **2026** (from `Jan 01 2026` to present).
- **Author**: Addy Osmani.
- **Retention**: Full cumulative archive (`has_archive: true`).

## Module Structure
- `definition.json`: Source configuration and issue grouping metadata.
- `data.json`: Canonical storage of all 2026 extracted articles.
- `scraper.py`: Crawler fetching listing pages and metadata for individual essays.
