from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.classifier import classify_pages
from app.config import CrawlConfig
from app.extractor import extract_page
from app.fetcher import Fetcher
from app.robots_policy import RobotsPolicy
from app.url_utils import dedupe_key, is_in_scope, normalize_url


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
        self.stats = {
            "discovered_urls": 0,
            "fetched_pages": 0,
            "skipped_pages": 0,
            "failed_requests": 0,
            "extraction_failures": 0,
            "topic_coverage": {},
        }
        self.db_path = Path(config.sqlite_path)
        self.jsonl_path = Path(config.jsonl_path)
        self.csv_path = Path(config.csv_path)
        self.manifest_path = Path(config.manifest_path)
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._init_storage()

        if config.resume:
            self._resume_from_state()
        else:
            self.queue.append((normalize_url(config.start_url), 0))
            self.seen.add(dedupe_key(config.start_url))

    def _init_storage(self) -> None:
        self.conn = sqlite3.connect(self.db_path)
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
        state_file = Path(self.config.state_path)
        if state_file.exists():
            payload = json.loads(state_file.read_text(encoding="utf-8"))
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
        Path(self.config.state_path).write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _write_outputs(self) -> None:
        with self.jsonl_path.open("w", encoding="utf-8") as handle:
            for record in self.records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

        with self.csv_path.open("w", encoding="utf-8") as handle:
            handle.write("url,title,status_code,fetch_timestamp,content_hash\n")
            for record in self.records:
                handle.write(
                    f"{record.get('url','')},{record.get('title','').replace(',',' ')}"
                    f",{record.get('status_code','')},{record.get('fetch_timestamp','')},{record.get('content_hash','')}\n"
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
            "coverage": self.stats["topic_coverage"],
            "statistics": {
                "discovered_urls": self.stats["discovered_urls"],
                "fetched_pages": self.stats["fetched_pages"],
                "skipped_pages": self.stats["skipped_pages"],
                "failed_requests": self.stats["failed_requests"],
                "extraction_failures": self.stats["extraction_failures"],
            },
        }
        self.manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    def run(self) -> None:
        if self.config.dry_run:
            self.stats["discovered_urls"] = len(self.seen)
            self._persist_state()
            return

        while self.queue and self.stats["fetched_pages"] < self.config.max_pages:
            url, depth = self.queue.pop(0)
            if url in self.visited:
                continue
            self.visited.add(url)

            normalized = normalize_url(url)
            if not is_in_scope(normalized, self.config.allowed_domains):
                self.skipped.append({"url": normalized, "reason": "out_of_scope"})
                self.stats["skipped_pages"] += 1
                continue

            result = self.fetcher.fetch(normalized)
            self.stats["discovered_urls"] = max(self.stats["discovered_urls"], len(self.seen))

            if result.status_code is None:
                self.errors.append({"url": normalized, "error": result.error})
                self.stats["failed_requests"] += 1
                continue

            if result.status_code >= 400:
                self.errors.append({"url": normalized, "status_code": result.status_code})
                self.stats["failed_requests"] += 1
                continue

            try:
                record = extract_page(normalized, result.body, result)
            except Exception as exc:  # pragma: no cover - defensive branch
                self.errors.append({"url": normalized, "error": str(exc)})
                self.stats["extraction_failures"] += 1
                continue

            self.records.append(record)
            self.stats["fetched_pages"] += 1
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
            time_sleep = getattr(self.config, "delay_seconds", 2.0)
            if time_sleep > 0:
                import time
                time.sleep(time_sleep)

        self._persist_state()
        self._write_outputs()
        self.stats["discovered_urls"] = len(self.seen)
        self.conn.close()
