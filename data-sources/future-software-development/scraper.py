"""Static source marker for the curated Thoughtworks FOSE 2026 dataset."""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
code_dir = os.path.join(project_root, "code")
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

from common.base_scraper import BaseScraper


class FutureSoftwareDevelopmentScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_dir=current_dir)

    def sync_data(self) -> int:
        raise RuntimeError(
            "future-software-development is a curated static source; "
            "edit data.json directly and run the normalizer/build."
        )


if __name__ == "__main__":
    print(
        "[FutureSoftwareDevelopment] Static curated source; "
        "there is no network refresh operation."
    )
