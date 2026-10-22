from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
from typing import Any

import yaml


@dataclass
class CrawlConfig:
    start_url: str = "https://developers.google.com/search/docs"
    allowed_domains: list[str] = field(default_factory=lambda: ["developers.google.com"])
    max_pages: int = 200
    max_depth: int = 3
    delay_seconds: float = 2.0
    concurrency: int = 1
    timeout_seconds: int = 20
    user_agent: str = "GoogleSearchCentralDocCrawler/1.0 (+https://github.com/Mugobenjamin/python-crawler)"
    output_dir: str = "./outputs"
    state_path: str = "./outputs/crawl_state.json"
    sqlite_path: str = "./outputs/seo_knowledge_base.db"
    jsonl_path: str = "./outputs/seo_content.jsonl"
    csv_path: str = "./outputs/seo_pages.csv"
    manifest_path: str = "./outputs/crawl_manifest.json"
    pdf_path: str = "./outputs/google_search_seo_handbook.pdf"
    dry_run: bool = False
    resume: bool = False
    generate_pdf: bool = False

    def __post_init__(self) -> None:
        self.output_dir = str(Path(self.output_dir))
        self.state_path = str(Path(self.output_dir) / "crawl_state.json") if self.state_path == "./outputs/crawl_state.json" else self.state_path
        self.sqlite_path = str(Path(self.output_dir) / "seo_knowledge_base.db") if self.sqlite_path == "./outputs/seo_knowledge_base.db" else self.sqlite_path
        self.jsonl_path = str(Path(self.output_dir) / "seo_content.jsonl") if self.jsonl_path == "./outputs/seo_content.jsonl" else self.jsonl_path
        self.csv_path = str(Path(self.output_dir) / "seo_pages.csv") if self.csv_path == "./outputs/seo_pages.csv" else self.csv_path
        self.manifest_path = str(Path(self.output_dir) / "crawl_manifest.json") if self.manifest_path == "./outputs/crawl_manifest.json" else self.manifest_path
        self.pdf_path = str(Path(self.output_dir) / "google_search_seo_handbook.pdf") if self.pdf_path == "./outputs/google_search_seo_handbook.pdf" else self.pdf_path


def load_config(args: Any | None = None) -> CrawlConfig:
    config_path = getattr(args, "config", "sample_config.yaml") if args else "sample_config.yaml"
    config_dict: dict[str, Any] = {}

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as handle:
            config_dict = yaml.safe_load(handle) or {}

    config = CrawlConfig(**config_dict)

    if args is not None:
        if getattr(args, "start_url", None):
            config.start_url = args.start_url
        if getattr(args, "max_pages", None) is not None:
            config.max_pages = args.max_pages
        if getattr(args, "max_depth", None) is not None:
            config.max_depth = args.max_depth
        if getattr(args, "delay", None) is not None:
            config.delay_seconds = args.delay
        if getattr(args, "dry_run", False):
            config.dry_run = True
        if getattr(args, "resume", False):
            config.resume = True
        if getattr(args, "generate_pdf", False):
            config.generate_pdf = True
        if getattr(args, "output_dir", None):
            config.output_dir = args.output_dir

    os.makedirs(config.output_dir, exist_ok=True)
    return config
