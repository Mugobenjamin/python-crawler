from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "gclid",
    "fbclid",
    "dclid",
    "mc_cid",
    "mc_eid",
    "igshid",
    "hsa_",
}


def normalize_url(url: str) -> str:
    """Normalize the URL by removing fragments, filtering tracking params, normalizing host casing, and deduplicating."""
    if not url:
        return ""
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    query_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if any(key.lower().startswith(prefix) for prefix in TRACKING_PARAMS):
            continue
        query_items.append((key, value))
    query = urlencode(query_items)

    normalized = urlunsplit((scheme, netloc, parsed.path or "/", query, ""))
    if normalized.endswith("/") is False and parsed.path.endswith("/"):
        normalized = normalized.rstrip("/") + "/"
    return normalized


def is_in_scope(url: str, allowed_domains: Iterable[str]) -> bool:
    try:
        host = urlsplit(url).netloc.lower()
    except Exception:
        return False
    allowed = [domain.lower().lstrip(".") for domain in allowed_domains]
    return any(host == domain or host.endswith(f".{domain}") for domain in allowed)


def dedupe_key(url: str) -> str:
    return normalize_url(url)


def iter_links_from_html(html: str, base_url: str) -> list[str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if href and not href.startswith("mailto:") and not href.startswith("javascript:"):
            links.append(href)
    return links
