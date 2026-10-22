from __future__ import annotations

import argparse
import os
from pathlib import Path

from app.config import CrawlConfig, load_config
from app.crawler import CrawlSession
from app.pdf_generator import generate_pdf_handbook


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl Google Search Central docs and generate an SEO handbook.")
    parser.add_argument("--config", type=str, default="sample_config.yaml", help="Path to YAML config file.")
    parser.add_argument("--start-url", type=str, default=None, help="Seed URL to crawl.")
    parser.add_argument("--max-pages", type=int, default=None, help="Maximum pages to fetch.")
    parser.add_argument("--max-depth", type=int, default=None, help="Maximum crawl depth.")
    parser.add_argument("--delay", type=float, default=None, help="Delay in seconds between requests.")
    parser.add_argument("--dry-run", action="store_true", help="Only report the planned crawl without fetching.")
    parser.add_argument("--resume", action="store_true", help="Resume from persisted crawl state.")
    parser.add_argument("--generate-pdf", action="store_true", help="Generate the PDF handbook after crawling.")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for crawl files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args)

    os.makedirs(config.output_dir, exist_ok=True)

    session = CrawlSession(config)
    session.run()

    if args.generate_pdf or config.generate_pdf:
        pdf_path = generate_pdf_handbook(session.records, config)
        print(f"PDF generated at: {pdf_path}")

    print(f"Discovered URLs: {session.stats['discovered_urls']}")
    print(f"Fetched pages: {session.stats['fetched_pages']}")
    print(f"Skipped pages: {session.stats['skipped_pages']}")
    print(f"Failed requests: {session.stats['failed_requests']}")
    print(f"Extraction failures: {session.stats['extraction_failures']}")
    print(f"Topics covered: {len(session.stats['topic_coverage'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
