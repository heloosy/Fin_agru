"""
AgriSpark 2.0 — PDF Farm Plan Generator
Builds a professional, branded PDF using ReportLab.
"""

import os
import uuid
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

import config

# ─── Brand Colours ────────────────────────────────────────────────────────────
GREEN_DARK  = colors.HexColor("#1B4332")
GREEN_MID   = colors.HexColor("#40916C")
GREEN_LIGHT = colors.HexColor("#D8F3DC")
GOLD        = colors.HexColor("#F4A261")
WHITE       = colors.white
GREY_TEXT   = colors.HexColor("#4A4A4A")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold",
                                fontSize=24, textColor=WHITE,
                                spaceAfter=8, alignment=TA_CENTER),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica-Bold",
                                   fontSize=14, textColor=GOLD,
                                   spaceAfter=6, alignment=TA_CENTER),
        "section": ParagraphStyle("section", fontName="Helvetica-Bold",
                                  fontSize=15, textColor=colors.HexColor("#0D3B16"),
                                  spaceBefore=16, spaceAfter=6),
        "body": ParagraphStyle("body", fontName="Helvetica",
                               fontSize=11, textColor=GREY_TEXT,
                               spaceAfter=6, leading=16),
        "small": ParagraphStyle("small", fontName="Helvetica",
                                fontSize=9, textColor=GREY_TEXT,
                                alignment=TA_CENTER),
    }


def generate_pdf(profile: dict, plan_text: str, lang: str = "EN") -> str:
    """
    Generate a PDF farm plan and return the absolute file path.
    profile: dict with farmer fields
    plan_text: full AI-generated advisory text
    lang: 'EN' or 'TH'
    """
    os.makedirs(config.PDF_DIR, exist_ok=True)
    farmer_id = str(uuid.uuid4())[:8]
    filename  = f"agrispark_plan_{farmer_id}.pdf"
    filepath  = os.path.join(config.PDF_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    st  = _styles()
    story = []

    # ── Header Banner ────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("🌾 AGRISPARK MASTER ADVISORY", st["title"]),
    ]]
    header_table = Table(header_data, colWidths=[17*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0D361F")), # High-Authority Dark Green
        ("TOPPADDING",    (0, 0), (-1, -1), 22),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [8]),
    ]))
    story.append(header_table)

    subtitle = ("MISSION-CRITICAL FARM COMMANDS" if lang == "EN"
                else "คำสั่งการทำฟาร์มที่สำคัญยิ่ง")
    story.append(Paragraph(subtitle, st["subtitle"]))
    story.append(Spacer(1, 0.4*cm))

    # ── Date & ID ────────────────────────────────────────────────────────────
    date_str = datetime.now().strftime("%d %B %Y")
    story.append(Paragraph(f"GENRATED: {date_str}  |  ARCHIVE ID: {farmer_id}", st["small"]))
    story.append(HRFlowable(width="100%", thickness=2.5, color=GREEN_DARK, spaceAfter=12))

    # ── Farmer Profile Table ──────────────────────────────────────────────────
    heading = "FARMER PROFILE" if lang == "EN" else "ข้อมูลเกษตรกร"
    story.append(Paragraph(heading, st["section"]))

    labels_en = ["Name", "Location", "Past Crop", "Planned Crop", "Soil Type", "Terrain"]
    labels_th = ["ชื่อ", "ที่ตั้ง", "พืชที่ผ่านมา", "พืชที่วางแผน", "ประเภทดิน", "สภาพพื้นที่"]
    labels = labels_th if lang == "TH" else labels_en
    fields = ["name", "location", "past_crop", "current_crop", "soil_type", "terrain"]

    table_data = [[
        Paragraph(f"<b>{lbl}</b>", st["body"]),
        Paragraph(str(profile.get(f, "—")), st["body"])
    ] for lbl, f in zip(labels, fields)]

    profile_table = Table(table_data, colWidths=[5*cm, 12*cm])
    profile_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (0, -1), GREEN_LIGHT),
        ("GRID",         (0, 0), (-1, -1), 0.5, GREEN_MID),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(profile_table)
    story.append(Spacer(1, 0.4*cm))

    # ── AI Plan Content ───────────────────────────────────────────────────────
    plan_heading = "YOUR FARM ADVISORY PLAN" if lang == "EN" else "แผนการเกษตรของคุณ"
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN_MID, spaceAfter=6))

    import re

    def _clean(text):
        """Escape HTML and convert markdown bold."""
        text = (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;"))
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        return text

    def _make_table(rows):
        """Render a markdown table as a ReportLab table, auto-sizing columns."""
        if not rows:
            return None
        num_cols = max(len(r) for r in rows)
        page_width = 17 * cm

        # Fixed widths for known table shapes
        if num_cols == 6:
            col_widths = [2.2*cm, 2.5*cm, 3.5*cm, 3.2*cm, 2.5*cm, 3.1*cm]
        elif num_cols == 3:
            col_widths = [3.5*cm, 4.5*cm, 9*cm]
        elif num_cols == 2:
            col_widths = [5*cm, 12*cm]
        else:
            col_widths = [page_width / num_cols] * num_cols

        # Pad all rows to same column count
        padded = []
        for row in rows:
            while len(row) < num_cols:
                row.append(Paragraph("", st["body"]))
            padded.append(row[:num_cols])

        tbl = Table(padded, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            # Header row
            ("BACKGROUND",    (0, 0), (-1, 0), GREEN_DARK),
            ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 9),
            # Alternating body rows
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREEN_LIGHT]),
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("GRID",          (0, 0), (-1, -1), 0.4, GREEN_MID),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("WORDWRAP",      (0, 0), (-1, -1), 1),
        ]))
        return tbl

    lines = plan_text.split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        if not line:
            story.append(Spacer(1, 0.15*cm))
            i += 1
            continue

        # ── TABLE DETECTOR ─────────────────────────────────────────────────
        next_line = lines[i+1].strip() if i + 1 < len(lines) else ""
        is_separator = next_line.replace(" ", "").replace("|", "").replace("-", "") == ""
        if line.startswith("|") and is_separator:
            table_rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells_raw = lines[i].strip().strip("|").split("|")
                # Skip pure separator rows (|---|---| etc.)
                if all(re.fullmatch(r'[\s\-:]+', c) for c in cells_raw):
                    i += 1
                    continue
                cells = [
                    Paragraph(_clean(c.strip()), st["body"])
                    for c in cells_raw
                ]
                table_rows.append(cells)
                i += 1
            tbl = _make_table(table_rows)
            if tbl:
                story.append(Spacer(1, 0.2*cm))
                story.append(tbl)
                story.append(Spacer(1, 0.3*cm))
            continue

        # ── HEADINGS ───────────────────────────────────────────────────────
        if line.startswith("#"):
            hashes = len(line) - len(line.lstrip("#"))
            text = _clean(line.lstrip("#").strip())
            if hashes <= 2:
                # Big section banner
                banner_data = [[Paragraph(f"<b>{text}</b>",
                    ParagraphStyle("banner", fontName="Helvetica-Bold", fontSize=13,
                                   textColor=WHITE, alignment=TA_LEFT))]]
                banner = Table(banner_data, colWidths=[17*cm])
                banner.setStyle(TableStyle([
                    ("BACKGROUND",    (0, 0), (-1, -1), GREEN_DARK),
                    ("TOPPADDING",    (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
                ]))
                story.append(Spacer(1, 0.4*cm))
                story.append(banner)
                story.append(Spacer(1, 0.2*cm))
            else:
                story.append(Paragraph(f"<b>{text}</b>", st["section"]))
            i += 1
            continue

        # ── HORIZONTAL RULE ────────────────────────────────────────────────
        if line.startswith("---"):
            story.append(HRFlowable(width="100%", thickness=1,
                                    color=GREEN_MID, spaceAfter=6, spaceBefore=6))
            i += 1
            continue

        # ── BULLET / LIST ITEMS ────────────────────────────────────────────
        if line.startswith(("- ", "* ", "+ ")):
            clean = _clean(line[2:])
            bullet_style = ParagraphStyle("bullet", fontName="Helvetica",
                                          fontSize=10, textColor=GREY_TEXT,
                                          leftIndent=14, spaceAfter=3, leading=15,
                                          bulletText="•")
            story.append(Paragraph(clean, bullet_style))
            i += 1
            continue

        # ── INDENTED BULLET (sub-point) ────────────────────────────────────
        if line.startswith(("  - ", "  * ")):
            clean = _clean(line.strip()[2:])
            sub_style = ParagraphStyle("sub_bullet", fontName="Helvetica",
                                       fontSize=9, textColor=GREY_TEXT,
                                       leftIndent=28, spaceAfter=2, leading=13,
                                       bulletText="◦")
            story.append(Paragraph(clean, sub_style))
            i += 1
            continue

        # ── PLAIN PARAGRAPH ────────────────────────────────────────────────
        clean = _clean(line)
        story.append(Paragraph(clean, st["body"]))
        i += 1

    # ── Footer ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN_MID, spaceAfter=6))
    footer_text = ("AgriSpark 2.0 — AI Agricultural Advisory for Southeast Asia | "
                   "WhatsApp your questions anytime for ongoing support.")
    story.append(Paragraph(footer_text, st["small"]))

    doc.build(story)
    return filepath


def get_pdf_url(filepath: str) -> str:
    """Convert local path to public URL for WhatsApp delivery."""
    filename = os.path.basename(filepath)
    base = config.BASE_URL.strip("/")
    
    # 🕵️‍♂️ SMART PROTOCOL: Ensure the URL has http/https
    if base and not (base.startswith("http://") or base.startswith("https://")):
        # Default to https for security unless it's localhost
        if "localhost" in base or "127.0.0.1" in base:
            base = f"http://{base}"
        else:
            base = f"https://{base}"
            
    return f"{base}/static/pdf/{filename}"
