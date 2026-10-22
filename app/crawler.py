from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.classifier import classify_pages
from app.config import CrawlConfig
from app.fetcher import Fetcher
from app.robots_policy import RobotsPolicy
from app.url_utils import is_in_scope, normalize_url


class CrawlSession:
    def __init__(self, config: CrawlConfig) -> None:
        self.config = config
        self.robots_policy = RobotsPolicy(config.user_agent)
        self.fetcher = Fetcher(config, self.robots_policy)
        self.queue: list[tuple[str, int]] = []
        self.seen: set[str] = set()
        self.visited: set[str] = set()
        self.records: list[dict[str, Any]] = []
        self.skipped: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self.stats: dict[str, Any] = {
            "discovered_urls": 0,
            "fetched_pages": 0,
            "skipped_pages": 0,
            "failed_requests": 0,
            "extraction_failures": 0,
            "topic_coverage": {},
        }
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(config.sqlite_path)
        self.jsonl_path = Path(config.jsonl_path)
        self.csv_path = Path(config.csv_path)
        self.manifest_path = Path(config.manifest_path)
        self.state_path = Path(config.state_path)

        self._init_storage()

        if config.resume:
            self._resume_from_state()
        else:
            self.queue.append((normalize_url(config.start_url), 0))
            self.seen.add(normalize_url(config.start_url))

    def _init_storage(self) -> None:
        self.conn = __import__("sqlite3").connect(self.db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pages (
                url TEXT PRIMARY KEY,
                canonical_url TEXT,
                title TEXT,
                meta_description TEXT,
                page_type TEXT,
                status_code INTEGER,
                fetch_timestamp TEXT,
                content_hash TEXT,
                classification TEXT,
                source_urls TEXT,
                html_excerpt TEXT
            )
            """
        )
        self.conn.commit()

    def _resume_from_state(self) -> None:
        if not self.state_path.exists():
            self.queue.append((normalize_url(self.config.start_url), 0))
            self.seen.add(normalize_url(self.config.start_url))
            return

        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.queue = [(url, int(depth)) for url, depth in payload.get("queue", [])]
        self.seen = set(payload.get("seen", []))
        self.visited = set(payload.get("visited", []))
        self.records = payload.get("records", [])
        self.skipped = payload.get("skipped", [])
        self.errors = payload.get("errors", [])
        self.stats = payload.get("stats", self.stats)

    def _persist_state(self) -> None:
        state = {
            "queue": self.queue,
            "seen": sorted(self.seen),
            "visited": sorted(self.visited),
            "records": self.records,
            "skipped": self.skipped,
            "errors": self.errors,
            "stats": self.stats,
        }
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _write_outputs(self) -> None:
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with self.jsonl_path.open("w", encoding="utf-8") as handle:
            for record in self.records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

        with self.csv_path.open("w", encoding="utf-8") as handle:
            handle.write("url,title,status_code,fetch_timestamp,content_hash\n")
            for record in self.records:
                title = (record.get("title") or "").replace(",", " ")
                handle.write(
                    f"{record.get('url', '')},{title},{record.get('status_code', '')},"
                    f"{record.get('fetch_timestamp', '')},{record.get('content_hash', '')}\n"
                )

        manifest = {
            "config": {
                "start_url": self.config.start_url,
                "max_pages": self.config.max_pages,
                "max_depth": self.config.max_depth,
                "delay_seconds": self.config.delay_seconds,
                "resume": self.config.resume,
                "dry_run": self.config.dry_run,
            },
            "discovered_pages": sorted(self.seen),
            "completed_requests": [r.get("url") for r in self.records],
            "skipped_pages": self.skipped,
            "errors": self.errors,
            "coverage": self.stats.get("topic_coverage", {}),
            "statistics": {
                "discovered_urls": self.stats.get("discovered_urls", 0),
                "fetched_pages": self.stats.get("fetched_pages", 0),
                "skipped_pages": self.stats.get("skipped_pages", 0),
                "failed_requests": self.stats.get("failed_requests", 0),
                "extraction_failures": self.stats.get("extraction_failures", 0),
            },
        }
        self.manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    def run(self) -> None:
        if self.config.dry_run:
            self.stats["discovered_urls"] = len(self.seen)
            self._persist_state()
            return

        while self.queue and self.stats.get("fetched_pages", 0) < self.config.max_pages:
            url, depth = self.queue.pop(0)
            if url in self.visited:
                continue
            self.visited.add(url)

            normalized = normalize_url(url)
            if not is_in_scope(normalized, self.config.allowed_domains):
                self.skipped.append({"url": normalized, "reason": "out_of_scope"})
                self.stats["skipped_pages"] = self.stats.get("skipped_pages", 0) + 1
                continue

            result = self.fetcher.fetch(normalized)
            self.stats["discovered_urls"] = max(self.stats.get("discovered_urls", 0), len(self.seen))

            if result.status_code is None:
                self.errors.append({"url": normalized, "error": result.error})
                self.stats["failed_requests"] = self.stats.get("failed_requests", 0) + 1
                continue

            if result.status_code >= 400:
                self.errors.append({"url": normalized, "status_code": result.status_code})
                self.stats["failed_requests"] = self.stats.get("failed_requests", 0) + 1
                continue

            try:
                from app.extractor import extract_page
                record = extract_page(normalized, result.body, result)
            except Exception as exc:  # pragma: no cover - defensive branch
                self.errors.append({"url": normalized, "error": str(exc)})
                self.stats["extraction_failures"] = self.stats.get("extraction_failures", 0) + 1
                continue

            self.records.append(record)
            self.stats["fetched_pages"] = self.stats.get("fetched_pages", 0) + 1
            self.stats["topic_coverage"] = classify_pages(self.records)

            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO pages (url, canonical_url, title, meta_description, page_type, status_code, fetch_timestamp, content_hash, classification, source_urls, html_excerpt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        record.get("url"),
                        record.get("canonical_url"),
                        record.get("title"),
                        record.get("meta_description"),
                        record.get("page_type"),
                        record.get("status_code"),
                        record.get("fetch_timestamp"),
                        record.get("content_hash"),
                        "; ".join(record.get("topics", [])),
                        "; ".join(record.get("references", [])),
                        (record.get("main_content") or "")[:2000],
                    ),
                )

            if depth >= self.config.max_depth:
                continue

            for link in record.get("internal_links", []):
                child = normalize_url(link)
                if not child:
                    continue
                if not is_in_scope(child, self.config.allowed_domains):
                    continue
                if child not in self.seen:
                    self.seen.add(child)
                    self.queue.append((child, depth + 1))

            self._persist_state()
            self._write_outputs()
            if self.config.delay_seconds > 0:
                time.sleep(self.config.delay_seconds)

        self._persist_state()
        self._write_outputs()
        self.stats["discovered_urls"] = len(self.seen)
        self.conn.close()
