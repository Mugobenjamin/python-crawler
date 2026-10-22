from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, ListFlowable, ListItem, PageBreak

from app.config import CrawlConfig


def generate_pdf_handbook(records: list[dict[str, Any]], config: CrawlConfig) -> str:
    output_path = Path(config.pdf_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    story: list[Any] = []
    styles = getSampleStyleSheet()

    story.append(Paragraph("Google Search Central SEO Handbook", styles["Title"]))
    story.append(Spacer(1, 24))
    story.append(Paragraph("Generated from Google Search Central documentation and structured SEO guidance.", styles["BodyText"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Coverage note: this handbook summarizes official Google guidance and general implementation examples; it does not claim exhaustive coverage of every SEO topic.", styles["BodyText"]))
    story.append(PageBreak())
    story.append(Paragraph("Table of Contents", styles["Heading1"]))
    for index, record in enumerate(records[:10], start=1):
        story.append(Paragraph(f"{index}. {record.get('title', 'Untitled page')}", styles["BodyText"]))
    story.append(PageBreak())

    story.append(Paragraph("Introduction", styles["Heading1"]))
    story.append(Paragraph("This handbook explains core SEO concepts, Google Search mechanics, technical implementation guidance, and audit workflows for public documentation. It is meant to be practical and traceable to official sources.", styles["BodyText"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("References", styles["Heading2"]))
    refs = []
    for record in records[:10]:
        refs.append(record.get("canonical_url") or record.get("url") or "unknown")
    story.append(ListFlowable([ListItem(Paragraph(ref), bulletType="1") for ref in refs], bulletType="1"))

    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    doc.build(story)
    return str(output_path)
