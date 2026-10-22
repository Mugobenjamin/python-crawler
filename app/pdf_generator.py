from __future__ import annotations

from collections import defaultdict

TOPICS = {
    "fundamentals": ["seo fundamentals", "how google search works", "search basics", "google search"],
    "crawling_indexing_ranking": ["crawl", "index", "ranking", "rendering", "search indexing"],
    "robots_and_indexing": ["robots.txt", "robots meta", "noindex", "nofollow", "crawl delay"],
    "sitemaps": ["sitemap", "xml sitemap", "url discovery"],
    "canonicalization": ["canonical", "duplicate content", "redirect", "301", "302", "url canonicalization"],
    "site_architecture": ["site architecture", "internal linking", "url structure", "navigation"],
    "keyword_research": ["keyword research", "search intent", "content strategy"],
    "on_page_seo": ["title link", "meta description", "heading", "on-page seo"],
    "image_video_seo": ["image seo", "video seo", "alt text"],
    "javascript_seo": ["javascript seo", "rendered content", "dynamic rendering"],
    "mobile_https": ["mobile-first", "https", "page experience"],
    "web_vitals": ["core web vitals", "lcp", "cls", "fid", "performance"],
    "structured_data": ["structured data", "schema", "rich result"],
    "multilingual": ["multilingual", "multiregional", "hreflang"],
    "migrations": ["migration", "crawl budget", "website migration"],
    "search_console": ["search console", "index coverage", "troubleshooting"],
    "spam_policies": ["spam policy", "risky seo", "heavy spam"],
    "ecommerce": ["ecommerce seo", "product schema", "shop"],
    "audit_checklists": ["audit", "checklist", "technical seo"],
}


def classify_pages(records: list[dict]) -> dict[str, int]:
    coverage: dict[str, int] = defaultdict(int)
    for record in records:
        text = " ".join([
            record.get("title", ""),
            record.get("meta_description", ""),
            record.get("main_content", ""),
            " ".join(record.get("headings_h2_h3", [])),
        ]).lower()

        matched: set[str] = set()
        for category, keywords in TOPICS.items():
            if any(keyword in text for keyword in keywords):
                matched.add(category)

        for category in matched:
            coverage[category] += 1

    return dict(sorted(coverage.items()))
