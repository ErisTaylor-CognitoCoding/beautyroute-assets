"""Render an Athena AI Audit Report to PDF using reportlab.

A4 layout, Cognito Coding orange brand accent -- matches invoice_pdf.py style.
Destination: /home/coolzerohacks/projects/Pantheon/athena_pdf.py
"""
import io
import re
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
from reportlab.lib.enums import TA_RIGHT, TA_CENTER


ORANGE = colors.HexColor("#FF6600")
INK = colors.HexColor("#1A1A1A")
MUTED = colors.HexColor("#5F6570")
LINE = colors.HexColor("#E6E3DC")
CREAM = colors.HexColor("#FDFCF8")


def render(submission) -> bytes:
    """Render the Athena audit report to a PDF bytes blob."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"Athena AI Audit -- {submission.business_name}",
        author="Cognito Coding",
    )
    ss = getSampleStyleSheet()

    h1 = ParagraphStyle("ah1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                         fontSize=22, textColor=INK, spaceAfter=4)
    tagline = ParagraphStyle("atagline", parent=ss["Normal"], fontName="Helvetica",
                              fontSize=10, textColor=MUTED, spaceAfter=4)
    meta = ParagraphStyle("ameta", parent=ss["Normal"], fontName="Helvetica",
                           fontSize=10, textColor=MUTED, alignment=TA_RIGHT, spaceAfter=2)
    meta_o = ParagraphStyle("amoto", parent=ss["Normal"], fontName="Helvetica-Bold",
                             fontSize=14, textColor=ORANGE, alignment=TA_RIGHT)
    sec = ParagraphStyle("asec", parent=ss["Heading2"], fontName="Helvetica-Bold",
                          fontSize=14, textColor=ORANGE, spaceBefore=12, spaceAfter=4)
    sub_h = ParagraphStyle("asubh", parent=ss["Heading3"], fontName="Helvetica-Bold",
                            fontSize=11, textColor=INK, spaceBefore=8, spaceAfter=3)
    body = ParagraphStyle("abody", parent=ss["Normal"], fontName="Helvetica",
                           fontSize=10, textColor=INK, leading=15, spaceAfter=6)
    bullet = ParagraphStyle("abullet", parent=ss["Normal"], fontName="Helvetica",
                             fontSize=10, textColor=INK, leading=15,
                             leftIndent=12, firstLineIndent=-12, spaceAfter=3)
    foot = ParagraphStyle("afoot", parent=ss["Normal"], fontName="Helvetica",
                           fontSize=9, textColor=MUTED, alignment=TA_CENTER)

    story = []

    # ---- Header ----
    hdr = Table(
        [[
            [
                Paragraph("Cognito Coding", h1),
                Paragraph("Automate the Boring. Focus on What Matters.", tagline),
                Paragraph("info@cognitocoding.com . cognitocoding.com", tagline),
            ],
            [
                Paragraph("ATHENA AI AUDIT", meta_o),
                Paragraph(f"Prepared for: <b>{_esc(submission.business_name)}</b>", meta),
                Paragraph(f"Date: {datetime.utcnow().strftime('%d %B %Y')}", meta),
            ],
        ]],
        colWidths=[100 * mm, 70 * mm],
    )
    hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 2.4, ORANGE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 8 * mm))

    # ---- Business summary strip ----
    sdata = [
        [Paragraph("Business", tagline), Paragraph("Industry", tagline), Paragraph("Team Size", tagline)],
        [
            Paragraph(f"<b>{_esc(submission.business_name)}</b>", body),
            Paragraph(_esc(submission.industry or "—"), body),
            Paragraph(_esc(submission.team_size or "—"), body),
        ],
    ]
    stbl = Table(sdata, colWidths=[65 * mm, 55 * mm, 50 * mm])
    stbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F4EC")),
        ("BACKGROUND", (0, 1), (-1, 1), CREAM),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("LINEBEFORE", (0, 0), (0, -1), 3, ORANGE),
    ]))
    story.append(stbl)
    story.append(Spacer(1, 8 * mm))

    # ---- Report body (markdown -> flowables) ----
    _render_md(submission.report_markdown or "", story, sec, sub_h, body, bullet)

    # ---- Footer ----
    story.append(Spacer(1, 12 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=LINE))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Cognito Coding . info@cognitocoding.com . cognitocoding.com . "
        "Automate the Boring. Focus on What Matters.",
        foot,
    ))

    doc.build(story)
    return buf.getvalue()


def _render_md(text, story, sec, sub_h, body, bullet):
    """Convert simple markdown to reportlab flowables."""
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            story.append(Spacer(1, 2 * mm))
        elif s.startswith("## "):
            story.append(Paragraph(_clean(s[3:]), sec))
        elif s.startswith("### "):
            story.append(Paragraph(_clean(s[4:]), sub_h))
        elif s.startswith("# "):
            story.append(Paragraph(_clean(s[2:]), sec))
        elif s.startswith("- ") or s.startswith("* "):
            story.append(Paragraph("&bull; " + _clean(s[2:]), bullet))
        else:
            story.append(Paragraph(_clean(s), body))


def _esc(text: str) -> str:
    """Escape for reportlab XML -- no bold/italic processing."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _clean(text: str) -> str:
    """Escape + convert markdown bold/italic to reportlab XML tags."""
    text = _esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    return text
