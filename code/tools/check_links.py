#!/usr/bin/env python3
"""
CLI Link Health & Unshortener Tool for news-agg.

Audits link health across data-sources/*/data.json, discovers broken/dead links,
identifies tracking redirects, and optionally fixes tracking redirect URLs in place.

Usage:
  python3 code/tools/check_links.py --url "https://clicks.mlsend.com/link/c/..."
  python3 code/tools/check_links.py --source dear-architects
  python3 code/tools/check_links.py --source dear-architects --fix-tracking
  python3 code/tools/check_links.py --all --only-tracking --fix-tracking
  python3 code/tools/check_links.py --all --concurrency 8
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(CODE_DIR)
for _p in (CODE_DIR, PROJECT_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common.url_utils import (  # noqa: E402
    clean_tracking_params,
    is_tracking_redirect_domain,
    unshorten_url,
    validate_url,
)

SOURCES_DIR = os.path.join(PROJECT_ROOT, "data-sources")


def check_single_url(url: str, timeout: int = 10, verbose: bool = True) -> Dict:
    """Checks and unshortens a single URL interactively."""
    cleaned = clean_tracking_params(url.strip())
    is_redirect = is_tracking_redirect_domain(cleaned) or "mlsend.com" in cleaned
    destination = unshorten_url(cleaned, timeout=timeout) if is_redirect else cleaned
    
    is_valid, status_code, message = validate_url(destination, timeout=timeout)
    
    result = {
        "original_url": url,
        "clean_url": cleaned,
        "is_tracking_redirect": is_redirect,
        "unshortened_url": destination,
        "is_valid": is_valid,
        "status_code": status_code,
        "message": message,
    }
    
    if verbose:
        print(f"\n--- URL Health Check ---")
        print(f"Original:    {url}")
        if is_redirect:
            print(f"Tracking:    YES -> Unshortened: {destination}")
        print(f"Status:      {'VALID' if is_valid else 'DEAD/BROKEN'} (HTTP {status_code})")
        print(f"Details:     {message}\n")
        
    return result


def audit_source_links(
    source_id: str,
    fix_tracking: bool = False,
    only_tracking: bool = False,
    concurrency: int = 6,
    timeout: int = 10,
    verbose: bool = False,
) -> Dict:
    """
    Audits all article links for a single source.
    If fix_tracking is True, rewrites tracking redirect links with resolved destinations.
    """
    source_path = os.path.join(SOURCES_DIR, source_id)
    data_file = os.path.join(source_path, "data.json")
    if not os.path.isfile(data_file):
        print(f"[{source_id}] No data.json found at {data_file}")
        return {}

    with open(data_file, "r", encoding="utf-8") as f:
        articles = json.load(f)

    if not articles:
        print(f"[{source_id}] Empty data.json")
        return {}

    print(f"\n[{source_id}] Auditing {len(articles)} articles (concurrency={concurrency})...")

    # Filter articles to check
    targets = []
    for idx, art in enumerate(articles):
        link = (art.get("link") or "").strip()
        if not link:
            continue
        is_redirect = is_tracking_redirect_domain(link) or "mlsend.com" in link
        if only_tracking and not is_redirect:
            continue
        targets.append((idx, art, link, is_redirect))

    stats = {
        "total": len(targets),
        "valid": 0,
        "restricted": 0,
        "dead": 0,
        "tracking_found": 0,
        "tracking_fixed": 0,
        "errors": [],
    }

    modified = False

    def probe_worker(item):
        idx, art, link, is_redirect = item
        resolved_link = link
        unshortened = False
        if is_redirect:
            unshortened_url = unshorten_url(link, timeout=timeout)
            if unshortened_url and unshortened_url != link:
                resolved_link = unshortened_url
                unshortened = True

        if only_tracking:
            return idx, link, resolved_link, unshortened, True, 200, "Skipped probe (only-tracking)"

        is_valid, status_code, msg = validate_url(resolved_link, timeout=timeout)
        return idx, link, resolved_link, unshortened, is_valid, status_code, msg

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(probe_worker, item): item for item in targets}
        for future in as_completed(futures):
            try:
                idx, link, resolved, unshortened, is_valid, code, msg = future.result()
                
                if unshortened or is_tracking_redirect_domain(link) or "mlsend.com" in link:
                    stats["tracking_found"] += 1
                    if fix_tracking and resolved != link:
                        articles[idx]["link"] = resolved
                        modified = True
                        stats["tracking_fixed"] += 1
                        if verbose:
                            print(f"  [FIXED TRACKING] {link[:40]}... -> {resolved[:50]}...")

                if is_valid:
                    if code in (401, 403, 429, 999):
                        stats["restricted"] += 1
                        if verbose:
                            print(f"  [RESTRICTED] HTTP {code}: {resolved[:60]}")
                    else:
                        stats["valid"] += 1
                        if verbose:
                            print(f"  [OK] HTTP {code}: {resolved[:60]}")
                else:
                    stats["dead"] += 1
                    title = articles[idx].get("title", "")[:35]
                    stats["errors"].append((title, resolved, code, msg))
                    print(f"  [DEAD] HTTP {code} ({msg}): {title} -> {resolved}")

            except Exception as exc:
                stats["dead"] += 1
                stats["errors"].append(("", "", 0, str(exc)))

    # Save changes if fix_tracking modified any records
    if fix_tracking and modified:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=source_path, prefix="data_", suffix=".tmp")
        with open(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, data_file)
        print(f"[{source_id}] Successfully updated {stats['tracking_fixed']} links in data.json")

    print(
        f"[{source_id}] Summary: {stats['valid']} valid, {stats['restricted']} restricted, "
        f"{stats['dead']} dead, {stats['tracking_found']} tracking redirects "
        f"({stats['tracking_fixed']} fixed)."
    )

    return stats


def get_all_source_ids() -> List[str]:
    """Returns sorted list of source directory names."""
    if not os.path.isdir(SOURCES_DIR):
        return []
    return sorted([
        d for d in os.listdir(SOURCES_DIR)
        if os.path.isdir(os.path.join(SOURCES_DIR, d))
        and os.path.isfile(os.path.join(SOURCES_DIR, d, "data.json"))
    ])


def main():
    parser = argparse.ArgumentParser(description="Link Health Checker & Unshortener for news-agg")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Check/unshorten a single URL interactively")
    group.add_argument("--source", help="Check links for a specific source directory")
    group.add_argument("--all", action="store_true", help="Check links across all registered sources")

    parser.add_argument(
        "--fix-tracking",
        action="store_true",
        help="Resolve tracking redirects and update data.json in place",
    )
    parser.add_argument(
        "--only-tracking",
        action="store_true",
        help="Only check and fix tracking redirects, skipping full reachability probe",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=6,
        help="Number of concurrent worker threads (default: 6)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="HTTP request timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print verbose status for each link checked",
    )

    args = parser.parse_args()

    if args.url:
        check_single_url(args.url, timeout=args.timeout, verbose=True)
        return

    sources = get_all_source_ids() if args.all else [args.source]
    total_stats = {
        "valid": 0,
        "restricted": 0,
        "dead": 0,
        "tracking_found": 0,
        "tracking_fixed": 0,
    }

    for source_id in sources:
        stats = audit_source_links(
            source_id=source_id,
            fix_tracking=args.fix_tracking,
            only_tracking=args.only_tracking,
            concurrency=args.concurrency,
            timeout=args.timeout,
            verbose=args.verbose,
        )
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)

    print("\n===============================")
    print("TOTAL AUDIT RESULTS:")
    print(f"  Valid URLs:         {total_stats['valid']}")
    print(f"  Restricted/Botwall: {total_stats['restricted']}")
    print(f"  Dead/Broken URLs:   {total_stats['dead']}")
    print(f"  Tracking Redirects: {total_stats['tracking_found']}")
    if args.fix_tracking:
        print(f"  Tracking Fixed:     {total_stats['tracking_fixed']}")
    print("===============================\n")


if __name__ == "__main__":
    main()
