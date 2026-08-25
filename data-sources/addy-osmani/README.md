# Addy Osmani Blog Source Module

Source adapter for Addy Osmani's personal technical blog at `https://addyosmani.com/blog/`.

## Extraction & Filtering Rules
- **Platform**: Static HTML personal blog.
- **Domain Scope**: Strictly articles hosted on `https://addyosmani.com/blog/` (excludes external posts on Substack or LeadDev).
- **Timeframe**: Rolling **730-day** publication window.
- **Author**: Addy Osmani.
- **Retention**: Full cumulative archive (`has_archive: true`).

## Module Structure
- `definition.json`: Source configuration and issue grouping metadata.
- `data.json`: Canonical storage of extracted articles inside the rolling window.
- `scraper.py`: Crawler fetching listing pages and metadata for individual essays.
