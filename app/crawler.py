import json

from app.config import CrawlConfig
from app.crawler import CrawlSession


def test_resume_queue_is_loaded(tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"queue": [["https://developers.google.com/search/docs", 0]], "seen": ["https://developers.google.com/search/docs"], "visited": [], "records": [], "skipped": [], "errors": [], "stats": {}}), encoding="utf-8")
    config = CrawlConfig(
        start_url="https://developers.google.com/search/docs",
        allowed_domains=["developers.google.com"],
        output_dir=str(tmp_path),
        sqlite_path=str(tmp_path / "test.db"),
        jsonl_path=str(tmp_path / "content.jsonl"),
        csv_path=str(tmp_path / "pages.csv"),
        manifest_path=str(tmp_path / "manifest.json"),
        state_path=str(state_file),
        resume=True,
    )
    session = CrawlSession(config)
    assert session.queue[0][0] == "https://developers.google.com/search/docs"

