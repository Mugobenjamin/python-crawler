# Google Search Central SEO Documentation Crawler and PDF Generator

This repository contains a Python application that crawls the public Google Search Central documentation, extracts SEO-related guidance, stores structured records in SQLite and JSONL, and generates a searchable PDF handbook.

## Architecture and implementation plan

1. Crawl layer
   - Normalize and scope URL discovery from the Google Search Central docs.
   - Respect robots.txt and crawl policy.
   - Persist crawl state so interrupted runs can resume.

2. Extraction and classification layer
   - Parse HTML, strip boilerplate, extract metadata and article structure.
   - Classify content into SEO topic buckets and preserve source URLs.

3. Storage and reporting layer
   - Store pages and extracted content in SQLite and JSONL.
   - Emit CSV/manifest outputs and audit coverage statistics.

4. PDF generation layer
   - Build a handbook using ReportLab with chapters, glossary, references, and bibliographic sources.
   - Keep source URLs bound to each substantive section.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --start-url https://developers.google.com/search/docs --max-pages 200 --max-depth 3
python main.py --resume
python main.py --generate-pdf
```

## CLI examples

```bash
python main.py --help
python main.py --start-url https://developers.google.com/search/docs --max-pages 500 --delay 2.0 --dry-run
python main.py --config sample_config.yaml --generate-pdf
```

## Project structure

- `app/` – crawler, fetcher, extraction, storage, classification, PDF generation modules
- `tests/` – unit tests for URL normalization, robots handling, redirects, extraction, storage, and PDF generation
- `sample_config.yaml` – sample runtime configuration
- `requirements.txt` – Python dependencies
- `main.py` – CLI entrypoint

## Notes

- The crawler intentionally avoids bypassing robots.txt, auth, or anti-bot protections.
- JavaScript-rendered content is not executed; this is noted in extracted metadata and generation flow.
- PDFs and output artifacts are generated only when the code is executed in a local environment and the crawl completes successfully.
