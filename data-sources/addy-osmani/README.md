# Addy Osmani Blog Source Module

Source adapter for Addy Osmani's personal technical blog at `https://addyosmani.com/blog/`.

## Extraction & Filtering Rules
- **Platform**: Static HTML personal blog.
- **Domain Scope**: Strictly articles hosted on `https://addyosmani.com/blog/` (excludes external posts on Substack or LeadDev).
- **Discovery Window**: The crawler reads the first two blog listing pages and imports posts
  published within the latest **730 days**.
- **Author**: Addy Osmani.
- **Archive**: Enabled with no builder-level retention limit. Existing canonical records
  remain available even after they leave the crawler's discovery window.

## Module Structure
- `definition.json`: Source configuration and issue grouping metadata.
- `data.json`: Canonical storage of extracted articles inside the rolling window.
- `scraper.py`: Crawler fetching the blog index and page 2, then reading metadata from
  individual essays.
