from pathlib import Path

from app.config import CrawlConfig
from app.pdf_generator import generate_pdf_handbook


def test_pdf_generation_creates_file(tmp_path):
    config = CrawlConfig(output_dir=str(tmp_path), pdf_path=str(tmp_path / "test.pdf"))
    records = [{"title": "Intro", "canonical_url": "https://developers.google.com/search/docs"}]
    pdf_path = generate_pdf_handbook(records, config)
    assert Path(pdf_path).exists()
    assert pdf_path.endswith("test.pdf")
