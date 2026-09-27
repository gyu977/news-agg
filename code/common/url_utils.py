"""
URL Utilities for news-agg.
Provides tracking redirect unshortening, URL health validation, SSRF protection,
and query parameter sanitization.
"""

import ipaddress
import time
import urllib.parse
import urllib.request
import urllib.error
from typing import Tuple, Optional, Set

# Modern browser User-Agent to avoid 403 Forbidden blocks from anti-bot click trackers
# (MailerLite clicks.mlsend.com, Beehiiv, Medium, Cloudflare)
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

# Known tracking, redirect, and URL shortener domains
TRACKING_REDIRECT_DOMAINS: Set[str] = {
    # Newsletter click tracking
    "clicks.mlsend.com",
    "click.mlsend.com",
    "link.mail.beehiiv.com",
    "email.mg2.substack.com",
    "email.substack.com",
    # Generic shorteners
    "t.co",
    "bit.ly",
    "tinyurl.com",
    "lnkd.in",
    "buff.ly",
    "ow.ly",
    "is.gd",
    "rebrand.ly",
}

# Tracking parameters that carry attribution only and do not affect content identity
TRACKING_PARAMS: Set[str] = {
    "ml_subscriber", "ml_subscriber_hash", "mc_cid", "mc_eid",
    "trk", "trkinfo", "urlhash", "li_fat_id", "originaltrk",
    "si", "fbclid", "gclid", "dclid", "msclkid", "twclid", "igshid",
    "ref", "referrer", "source", "ck_subscriber_id", "_hsenc", "_hsmi",
    "vero_id", "vero_conv", "yclid", "wickedid", "oly_enc_id", "oly_anon_id",
    # Substack, Medium, Beehiiv subscriber tokens
    "publication_id", "post_id", "isFreemail", "audience", "r",
    # Marketing automation & affiliate / campaign tokens
    "mkt_tok", "spm", "feature", "context", "cmpid", "mbid", "cid",
}

TRACKING_PREFIXES: Tuple[str, ...] = ("utm_", "mc_", "pk_", "piwik_", "matomo_", "hsa_", "sc_")


class _BoundedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom HTTP redirect handler enforcing a strict max_hops limit."""

    def __init__(self, max_hops: int = 5):
        super().__init__()
        self.max_redirections = max_hops


def is_safe_public_url(url: str) -> bool:
    """
    Validates that a URL uses http/https and does not target internal, private,
    loopback, or cloud-metadata IP addresses (SSRF protection).
    """
    if not url:
        return False
    try:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme.lower() not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        hostname = hostname.lower()
        if (
            hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0")
            or hostname.endswith(".local")
            or hostname.endswith(".internal")
        ):
            return False
        # Check if the hostname is a private/loopback/link-local IP address
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        except ValueError:
            # Valid domain name string, not an IP literal
            pass
        return True
    except Exception:
        return False


def is_tracking_param(name: str) -> bool:
    """Returns True if the query parameter is an attribution/tracking parameter."""
    lowered = name.lower()
    return lowered in TRACKING_PARAMS or lowered.startswith(TRACKING_PREFIXES)


def clean_tracking_params(url: str) -> str:
    """
    Strips UTM and click-tracking parameters from a URL while preserving legitimate query keys.
    """
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    filtered_params = {
        k: v for k, v in query_params.items()
        if not is_tracking_param(k)
    }
    clean_query = urllib.parse.urlencode(filtered_params, doseq=True)
    return urllib.parse.urlunparse((
        parsed.scheme, parsed.netloc, parsed.path, parsed.params, clean_query, parsed.fragment
    ))


def is_tracking_redirect_domain(url: str) -> bool:
    """Checks whether the URL host matches a known tracking or shortener domain."""
    if not url:
        return False
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
        if ":" in netloc:
            netloc = netloc.split(":", 1)[0]
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return any(
            netloc == domain or netloc.endswith("." + domain)
            for domain in TRACKING_REDIRECT_DOMAINS
        )
    except Exception:
        return False


def unshorten_url(url: str, timeout: int = 10, max_hops: int = 5, force: bool = False) -> str:
    """
    Resolves tracking redirect links (e.g. clicks.mlsend.com, bit.ly, t.co) to their
    true destination URL using a browser User-Agent to avoid 403 blocks.
    
    Enforces `max_hops` to guard against redirect loops. Rejects non-public/private addresses.
    
    If `force` is True, attempts redirect resolution even if the host is not in
    TRACKING_REDIRECT_DOMAINS.
    
    Returns the cleaned, unshortened destination URL. On timeout, error, or SSRF rejection,
    returns the cleaned original URL.
    """
    if not url:
        return ""
    
    clean_original = clean_tracking_params(url.strip())
    if not is_safe_public_url(clean_original):
        return clean_original

    if not force and not is_tracking_redirect_domain(clean_original):
        return clean_original

    req = urllib.request.Request(
        clean_original,
        headers={
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    )

    opener = urllib.request.build_opener(_BoundedRedirectHandler(max_hops=max_hops))

    try:
        with opener.open(req, timeout=timeout) as response:
            destination = response.geturl()
            if destination:
                return clean_tracking_params(destination)
    except urllib.error.HTTPError as exc:
        # Some servers redirect but reject subsequent content requests with 403 or 401.
        # If headers contain Location, extract it using the failing request's URL as base.
        location = exc.headers.get("Location") if hasattr(exc, "headers") else None
        if location:
            base = getattr(exc, "url", clean_original) or clean_original
            resolved = urllib.parse.urljoin(base, location)
            return clean_tracking_params(resolved)
        # Log and return original if resolution failed
        print(f"[url_utils] Unshorten warning for {clean_original}: HTTP {exc.code}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        print(f"[url_utils] Unshorten failed for {clean_original}: {exc}")

    return clean_original


def validate_url(url: str, timeout: int = 10) -> Tuple[bool, int, str]:
    """
    Validates whether a URL resolves successfully (HTTP 200..399 or acceptable anti-bot status).
    
    Method:
      1. Performs SSRF check to reject private/loopback/cloud-metadata targets.
      2. Tries an HTTP HEAD request with a browser User-Agent.
      3. If HEAD returns 405 Method Not Allowed or 403, falls back to a streaming GET
         with Range: bytes=0-1024 to inspect headers (expecting 200 OK or 206 Partial Content)
         without downloading large response bodies.
         
    Returns:
      (is_valid: bool, status_code: int, message_or_destination: str)
      
    Classification:
      - 200..399 (including 206 Partial Content): Valid (True, code, final_url)
      - 401, 403, 429, 999: Considered alive/valid domain, but flagged as restricted (True, code, message)
      - 404, 410: Broken link (False, code, "Not Found / Gone")
      - Connection/DNS failure, timeout, malformed URL, or SSRF block: Broken (False, 0, error_message)
    """
    if not url:
        return False, 0, "Empty URL"

    if not is_safe_public_url(url):
        return False, 0, "Blocked unsafe or non-public URL (SSRF protection)"

    req_headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "*/*",
    }

    # 1. Attempt HEAD probe
    try:
        head_req = urllib.request.Request(url, headers=req_headers, method="HEAD")
        with urllib.request.urlopen(head_req, timeout=timeout) as response:
            code = response.getcode()
            destination = response.geturl()
            return True, code, destination
    except urllib.error.HTTPError as exc:
        code = exc.code
        # If HEAD is disallowed (405) or forbidden (403), fall back to streaming GET
        if code in (403, 405):
            try:
                get_req = urllib.request.Request(
                    url,
                    headers={**req_headers, "Range": "bytes=0-1024"},
                    method="GET"
                )
                with urllib.request.urlopen(get_req, timeout=timeout) as get_resp:
                    get_code = get_resp.getcode()
                    get_dest = get_resp.geturl()
                    return True, get_code, get_dest
            except urllib.error.HTTPError as get_exc:
                if get_exc.code in (401, 403, 429, 999):
                    return True, get_exc.code, f"Restricted/Authwall (HTTP {get_exc.code})"
                if get_exc.code in (404, 410):
                    return False, get_exc.code, f"Dead link (HTTP {get_exc.code})"
                return False, get_exc.code, f"HTTP Error {get_exc.code}"
            except Exception:
                pass
        
        if code in (401, 403, 429, 999):
            return True, code, f"Restricted/Authwall (HTTP {code})"
        if code in (404, 410):
            return False, code, f"Dead link (HTTP {code})"
        return False, code, f"HTTP Error {code}"

    except (urllib.error.URLError, ValueError) as exc:
        return False, 0, f"Connection/DNS or URL Error: {exc}"
    except (TimeoutError, OSError) as exc:
        return False, 0, f"Timeout or Network Error: {exc}"
