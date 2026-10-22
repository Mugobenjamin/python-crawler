from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def extract_page(url: str, html: str, response: Any) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    title = _clean_text(soup.title.string) if soup.title and soup.title.string else "Untitled"
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if meta_tag:
        meta_desc = _clean_text(meta_tag.get("content"))

    canonical = ""
    canonical_tag = soup.find("link", rel="canonical")
    if canonical_tag and canonical_tag.get("href"):
        canonical = canonical_tag.get("href")

    main_content = soup.find("main") or soup.find("article") or soup.find(id=re.compile(r"(main|content|article)"))
    if not main_content:
        main_content = soup.body or soup

    for selector in ["nav", "header", "footer", "aside", "script", "style"]:
        for element in main_content.select(selector):
            element.decompose()

    headings_h2 = [ _clean_text(h.get_text()) for h in main_content.find_all(["h2", "h3"]) ]
    paragraphs = [ _clean_text(p.get_text()) for p in main_content.find_all("p") if _clean_text(p.get_text()) ]
    lists_ = [ _clean_text(li.get_text()) for li in main_content.find_all("li") if _clean_text(li.get_text()) ]
    tables = [ _clean_text(table.get_text("\n")) for table in main_content.find_all("table") ]
    code_blocks = [ _clean_text(code.get_text()) for code in main_content.find_all("code") ]

    internal_links: list[str] = []
    references: list[str] = []
    for anchor in main_content.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        if not href or href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        if href.startswith("http"):
            references.append(href)
        else:
            internal_links.append(href)

    content_text = "\n".join(paragraphs + lists_ + tables + code_blocks)
    content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()

    page_type = "SEO documentation"
    if "robots" in (title + " " + meta_desc + " " + content_text).lower():
        page_type = "robots and indexing"
    elif "sitemap" in (title + " " + meta_desc + " " + content_text).lower():
        page_type = "sitemap"
    elif "structured data" in (title + " " + meta_desc + " " + content_text).lower():
        page_type = "structured data"

    return {
        "url": url,
        "canonical_url": canonical or url,
        "title": title,
        "meta_description": meta_desc,
        "page_type": page_type,
        "main_heading": _clean_text(main_content.find("h1").get_text()) if main_content.find("h1") else title,
        "headings_h2_h3": headings_h2,
        "main_content": content_text,
        "paragraphs": paragraphs,
        "lists": lists_,
        "tables": tables,
        "code_examples": code_blocks,
        "internal_links": internal_links,
        "references": references,
        "status_code": 200,
        "content_hash": content_hash,
        "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
        "topics": [],
    }
