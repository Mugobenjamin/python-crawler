from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

from app.config import CrawlConfig
from app.extractor import extract_page
from app.robots_policy import RobotsPolicy
from app.url_utils import dedupe_key, is_in_scope, normalize_url


@dataclass
class FetchResult:
    url: str
    status_code: int | None = None
    final_url: str | None = None
    canonical_url: str | None = None
    redirect_url: str | None = None
    error: str | None = None
    body: str = ""
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    headers: dict[str, str] = field(default_factory=dict)


class Fetcher:
    def __init__(self, config: CrawlConfig, robots_policy: RobotsPolicy) -> None:
        self.config = config
        self.robots_policy = robots_policy
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent, "Accept-Language": "en-US,en;q=0.9"})

    def fetch(self, url: str, *, allow_redirects: bool = True) -> FetchResult:
        normalized = normalize_url(url)
        if not self.robots_policy.can_fetch(normalized):
            return FetchResult(url=normalized, status_code=403, error="blocked by robots.txt")

        last_error: str | None = None
        for attempt in range(1, 5):
            try:
                response = self.session.get(
                    normalized,
                    timeout=self.config.timeout_seconds,
                    allow_redirects=allow_redirects,
                    headers={"User-Agent": self.config.user_agent},
                )

                if response.status_code in {429, 503}:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            sleep_for = max(float(retry_after), 0)
                        except ValueError:
                            sleep_for = 2.0
                        time.sleep(sleep_for)
                    else:
                        time.sleep(2 ** attempt)
                    continue

                if response.status_code >= 500:
                    if attempt < 4:
                        time.sleep(2 ** attempt)
                        continue

                return FetchResult(
                    url=normalized,
                    status_code=response.status_code,
                    final_url=normalize_url(response.url),
                    redirect_url=response.history[0].headers.get("Location") if response.history else None,
                    body=response.text,
                    headers=dict(response.headers),
                )
            except requests.RequestException as exc:
                last_error = str(exc)
                if attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                return FetchResult(url=normalized, status_code=None, error=last_error)

        return FetchResult(url=normalized, status_code=None, error=last_error or "Request failed")
