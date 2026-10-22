import json
from pathlib import Path

from app.config import CrawlConfig
from app.crawler import CrawlSession


def test_crawl_state_persistence(tmp_path):
    config = CrawlConfig(
        start_url="https://developers.google.com/search/docs",
        allowed_domains=["developers.google.com"],
        output_dir=str(tmp_path),
        sqlite_path=str(tmp_path / "test.db"),
        jsonl_path=str(tmp_path / "content.jsonl"),
        csv_path=str(tmp_path / "pages.csv"),
        manifest_path=str(tmp_path / "manifest.json"),
        state_path=str(tmp_path / "state.json"),
        max_pages=10,
        max_depth=1,
        dry_run=True,
    )
    session = CrawlSession(config)
    session._persist_state()
    payload = json.loads(Path(config.state_path).read_text(encoding="utf-8"))
    assert "queue" in payload
    assert "seen" in payload
