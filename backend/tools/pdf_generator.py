"""
pdf_generator.py – Generates a professional stock analysis PDF report using ReportLab.
"""

from __future__ import annotations

import os
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ── Colour palette ─────────────────────────────────────────────────────────────

DARK_NAVY = colors.HexColor("#0d1117")
NAVY = colors.HexColor("#1a1f35")
PURPLE = colors.HexColor("#6c63ff")
TEAL = colors.HexColor("#00c9a7")
GOLD = colors.HexColor("#ffd166")
RED = colors.HexColor("#ef476f")
LIGHT_GREY = colors.HexColor("#e8e8f0")
MID_GREY = colors.HexColor("#8892b0")
WHITE = colors.white
SECTION_BG = colors.HexColor("#f0f4ff")


# ── Style helpers ──────────────────────────────────────────────────────────────

def _build_styles():
    base = getSampleStyleSheet()

    styles = {
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontSize=32,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=8,
            fontName="Helvetica-Bold",
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            parent=base["Normal"],
            fontSize=14,
            textColor=LIGHT_GREY,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "section_heading": ParagraphStyle(
            "section_heading",
            parent=base["Heading1"],
            fontSize=14,
            textColor=WHITE,
            fontName="Helvetica-Bold",
            spaceBefore=16,
            spaceAfter=6,
            leftIndent=0,
        ),
        "sub_heading": ParagraphStyle(
            "sub_heading",
            parent=base["Heading2"],
            fontSize=11,
            textColor=PURPLE,
            fontName="Helvetica-Bold",
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#2d2d2d"),
            leading=15,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#2d2d2d"),
            leading=14,
            spaceAfter=3,
            leftIndent=16,
            bulletIndent=0,
        ),
        "tag_buy": ParagraphStyle(
            "tag_buy",
            parent=base["Normal"],
            fontSize=18,
            textColor=TEAL,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "tag_sell": ParagraphStyle(
            "tag_sell",
            parent=base["Normal"],
            fontSize=18,
            textColor=RED,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "tag_hold": ParagraphStyle(
            "tag_hold",
            parent=base["Normal"],
            fontSize=18,
            textColor=GOLD,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "disclaimer": ParagraphStyle(
            "disclaimer",
            parent=base["Normal"],
            fontSize=7,
            textColor=MID_GREY,
            leading=10,
            alignment=TA_CENTER,
        ),
    }
    return styles


# ── Section builder helpers ────────────────────────────────────────────────────

def _section_header(title: str, styles) -> list:
    """Returns a coloured section header band."""
    table_data = [[Paragraph(f"  {title}", styles["section_heading"])]]
    tbl = Table(table_data, colWidths=[6.5 * inch])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("ROUNDEDCORNERS", [6]),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return [tbl, Spacer(1, 6)]


def _parse_report_sections(text: str) -> dict[str, str]:
    """Extract labelled sections from the LLM-generated report text."""
    # Normalise section markers
    sections = {
        "executive_summary": "",
        "company_overview": "",
        "fundamental": "",
        "technical": "",
        "news": "",
        "recommendation": "",
        "risks": "",
        "conclusion": "",
        "full_text": text,
    }

    section_patterns = [
        ("executive_summary", r"EXECUTIVE SUMMARY"),
        ("company_overview", r"COMPANY OVERVIEW"),
        ("fundamental", r"FUNDAMENTAL ANALYSIS"),
        ("technical", r"TECHNICAL ANALYSIS"),
        ("news", r"NEWS.*?SENTIMENT"),
        ("recommendation", r"INVESTMENT RECOMMENDATION|RECOMMENDATION"),
        ("risks", r"RISK FACTORS|RISKS"),
        ("conclusion", r"CONCLUSION"),
    ]

    lines = text.split("\n")
    current_key = "executive_summary"
    buffer: list[str] = []

    for line in lines:
        matched = False
        for key, pattern in section_patterns:
            if re.search(pattern, line, re.IGNORECASE) and (
                line.strip().startswith("#") or line.isupper() or re.match(r"^\d+\.", line.strip())
            ):
                if buffer:
                    sections[current_key] = "\n".join(buffer).strip()
                current_key = key
                buffer = []
                matched = True
                break
        if not matched:
            buffer.append(line)

    if buffer:
        sections[current_key] = "\n".join(buffer).strip()

    return sections


def _mk_safe(text: str) -> str:
    """Escape XML special characters and convert Markdown bold/italic to ReportLab tags."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*\n]+?)\*", r"<i>\1</i>", text)
    return text


def _render_md_table(
    header_row: list,
    data_rows: list,
    styles,
    w: float,
) -> list:
    """
    Render a parsed Markdown table as a styled ReportLab Table flowable.

    Parameters
    ----------
    header_row : list[str]        – Column header labels
    data_rows  : list[list[str]]  – Table body rows
    styles     : dict             – Style dict from _build_styles()
    w          : float            – Usable page width in points
    """
    n_cols = max(len(header_row), max((len(r) for r in data_rows), default=1))
    if n_cols == 0:
        return []

    # First column slightly wider — usually the metric/label column
    if n_cols >= 2:
        first_w    = w * 0.38
        rest_w     = (w - first_w) / (n_cols - 1)
        col_widths = [first_w] + [rest_w] * (n_cols - 1)
    else:
        col_widths = [w]

    hdr_para_style = ParagraphStyle(
        "md_tbl_hdr",
        parent=styles["body"],
        fontSize=8.5,
        textColor=WHITE,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        spaceAfter=0,
    )
    cell_para_style = ParagraphStyle(
        "md_tbl_cell",
        parent=styles["body"],
        fontSize=8.5,
        textColor=colors.HexColor("#2d2d2d"),
        leading=12,
        alignment=TA_LEFT,
        spaceAfter=0,
    )

    def _pad(row: list, n: int) -> list:
        return (list(row) + [""] * n)[:n]

    table_data = [
        [Paragraph(_mk_safe(h), hdr_para_style) for h in _pad(header_row, n_cols)]
    ]
    for row in data_rows:
        table_data.append(
            [Paragraph(_mk_safe(c), cell_para_style) for c in _pad(row, n_cols)]
        )

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(
        TableStyle([
            # Header row
            ("BACKGROUND",     (0, 0), (-1, 0),  NAVY),
            ("TEXTCOLOR",      (0, 0), (-1, 0),  WHITE),
            ("FONTNAME",       (0, 0), (-1, 0),  "Helvetica-Bold"),
            # Data rows — zebra striping
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SECTION_BG, WHITE]),
            # Borders
            ("GRID",           (0, 0), (-1, -1), 0.4, colors.HexColor("#c0c8e0")),
            ("LINEABOVE",      (0, 0), (-1, 0),  1.5, PURPLE),
            # Cell padding
            ("TOPPADDING",     (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
            ("LEFTPADDING",    (0, 0), (-1, -1), 7),
            ("RIGHTPADDING",   (0, 0), (-1, -1), 7),
            ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    return [tbl, Spacer(1, 8)]


def _text_to_paragraphs(
    text: str,
    styles,
    style_key: str = "body",
    w: float = 6.5 * inch,
) -> list:
    """
    Convert LLM-produced report text into ReportLab flowables.

    Handles:
      • Markdown tables  — pipe-delimited rows rendered as styled ReportLab Tables
      • Markdown headings — ## / ### rendered as sub_heading paragraphs
      • Bullet / numbered lists
      • **Bold** and *italic* inline markup
      • Plain paragraphs
    """
    elements: list = []
    lines = text.split("\n")
    i = 0
    # Matches table separator rows like |---|---| or |:--|:--:|
    _sep_re = re.compile(r"^[-:\s]+$")

    while i < len(lines):
        line     = lines[i]
        stripped = line.strip()

        # ── Blank line ────────────────────────────────────────────────────────
        if not stripped:
            elements.append(Spacer(1, 4))
            i += 1
            continue

        # ── Markdown heading (##, ###, #) ─────────────────────────────────────
        if stripped.startswith("#"):
            heading = re.sub(r"^#+\s*", "", stripped)
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(_mk_safe(heading), styles["sub_heading"]))
            i += 1
            continue

        # ── Markdown table block ──────────────────────────────────────────────
        if stripped.startswith("|"):
            table_lines: list = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            header_row = None
            data_rows: list = []
            for tl in table_lines:
                cells = [c.strip() for c in tl.strip("|").split("|")]
                # Skip separator rows like |---|---| — all cells are dashes/colons/spaces
                if all(_sep_re.match(c) for c in cells if c):
                    continue
                if header_row is None:
                    header_row = cells
                else:
                    data_rows.append(cells)

            if header_row:
                elements.extend(_render_md_table(header_row, data_rows, styles, w))
            continue

        # ── Bullet / numbered list ────────────────────────────────────────────
        is_bullet = (
            stripped.startswith(("•", "·"))
            or (stripped.startswith("-") and not stripped.startswith("---"))
            or (stripped.startswith("*") and not stripped.startswith("**"))
            or re.match(r"^\d+[\.\)]\s", stripped)
        )
        if is_bullet:
            clean = re.sub(r"^[-•·*]\s*", "• ", stripped)
            clean = re.sub(r"^\d+[\.\)]\s+", lambda m: m.group(), clean)
            elements.append(Paragraph(_mk_safe(clean), styles["bullet"]))
            i += 1
            continue

        # ── Plain paragraph ───────────────────────────────────────────────────
        elements.append(Paragraph(_mk_safe(stripped), styles[style_key]))
        i += 1

    return elements


def _key_metrics_table(stock_data: dict, styles, w: float) -> list:
    """
    Build a 6-cell metrics banner from raw yfinance info dict.
    Shows: Current Price | Day Change | Market Cap | P/E TTM | 52W High | 52W Low
    """
    def _f(key, pct: bool = False, bil: bool = True, dp: int = 2) -> str:
        val = stock_data.get(key)
        if val is None:
            return "—"
        try:
            v = float(val)
            if pct:
                return f"{v * 100:.{dp}f}%"
            if bil and abs(v) >= 1e9:
                return f"${v / 1e9:.2f}B"
            if bil and abs(v) >= 1e6:
                return f"${v / 1e6:.2f}M"
            return f"{v:.{dp}f}"
        except Exception:
            return str(val)

    currency = stock_data.get("currency", "")
    cur_price = stock_data.get("currentPrice") or stock_data.get("regularMarketPrice")
    prev_close = stock_data.get("previousClose")

    # Current price string
    if cur_price is not None:
        try:
            price_str = f"{currency} {float(cur_price):,.2f}"
        except Exception:
            price_str = str(cur_price)
    else:
        price_str = "—"

    # Daily change string
    change_str = "—"
    change_color = MID_GREY
    if cur_price is not None and prev_close is not None:
        try:
            chg = float(cur_price) - float(prev_close)
            chg_pct = chg / float(prev_close) * 100
            sign = "+" if chg >= 0 else ""
            change_str = f"{sign}{chg:.2f} ({sign}{chg_pct:.2f}%)"
            change_color = TEAL if chg >= 0 else RED
        except Exception:
            pass

    metrics = [
        ("CURRENT PRICE",  price_str),
        ("DAY CHANGE",      change_str),
        ("MARKET CAP",      _f("marketCap")),
        ("P/E  (TTM)",      _f("trailingPE", bil=False)),
        ("52W HIGH",        _f("fiftyTwoWeekHigh", bil=False)),
        ("52W LOW",         _f("fiftyTwoWeekLow",  bil=False)),
    ]

    lbl_style = ParagraphStyle(
        "metric_lbl",
        parent=styles["body"],
        fontSize=7,
        textColor=MID_GREY,
        alignment=TA_CENTER,
        fontName="Helvetica",
    )
    val_style = ParagraphStyle(
        "metric_val",
        parent=styles["body"],
        fontSize=11,
        fontName="Helvetica-Bold",
        textColor=DARK_NAVY,
        alignment=TA_CENTER,
        spaceAfter=0,
    )
    # First metric (current price) gets a larger font
    price_val_style = ParagraphStyle(
        "price_val",
        parent=val_style,
        fontSize=13,
        textColor=PURPLE,
    )
    change_val_style = ParagraphStyle(
        "change_val",
        parent=val_style,
        fontSize=11,
        textColor=change_color,
    )

    val_styles_list = [
        price_val_style,
        change_val_style,
        val_style, val_style, val_style, val_style,
    ]

    col_w = w / len(metrics)
    labels_row = [Paragraph(m[0], lbl_style) for m in metrics]
    values_row  = [Paragraph(metrics[i][1], val_styles_list[i]) for i in range(len(metrics))]

    tbl = Table(
        [labels_row, values_row],
        colWidths=[col_w] * len(metrics),
    )
    tbl.setStyle(
        TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), SECTION_BG),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#c8d0e8")),
            ("LINEABOVE",     (0, 0), (-1, 0),  1.5, PURPLE),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    return [tbl, Spacer(1, 8)]


def _extract_recommendation(text: str) -> str:
    """Extract BUY / HOLD / SELL from report text."""
    text_upper = text.upper()
    for keyword in ["STRONG BUY", "BUY", "STRONG SELL", "SELL", "HOLD"]:
        if keyword in text_upper:
            return keyword
    return "HOLD"


# ── Page layout helpers ────────────────────────────────────────────────────────

def _on_page(canvas, doc):
    """Header / footer on every page."""
    canvas.saveState()
    width, height = A4

    # Top accent bar
    canvas.setFillColor(PURPLE)
    canvas.rect(0, height - 4, width, 4, fill=True, stroke=False)

    # Footer
    canvas.setFillColor(MID_GREY)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(
        width / 2,
        20,
        f"Stock Analysis Report  |  Generated by CrewAI Multi-Agent System  |  "
        f"Page {doc.page}  |  {datetime.now().strftime('%B %d, %Y')}",
    )

    # Footer line
    canvas.setStrokeColor(PURPLE)
    canvas.setLineWidth(0.5)
    canvas.line(40, 30, width - 40, 30)

    canvas.restoreState()


# ── Main function ──────────────────────────────────────────────────────────────

def generate_pdf_report(
    report_text: str,
    symbol: str,
    session_id: str,
    output_dir: str = "reports",
    stock_data: dict | None = None,
) -> str:
    """
    Generate a professional PDF report from the LLM-produced report text.

    Parameters
    ----------
    report_text : str   – Raw text output from Agent 3 (Investment Strategist)
    symbol      : str   – Stock ticker symbol
    session_id  : str   – Unique session identifier (used in filename)
    output_dir  : str   – Directory where the PDF will be saved

    Returns
    -------
    str  – Absolute path to the generated PDF
    """
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, f"{session_id}_report.pdf")

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.65 * inch,
        title=f"{symbol} Stock Analysis Report",
        author="CrewAI Multi-Agent Stock Analyser",
    )

    styles = _build_styles()
    story = []
    w = 6.5 * inch  # usable width

    # ── COVER PAGE ─────────────────────────────────────────────────────────────
    cover_table = Table(
        [
            [Paragraph(f"STOCK ANALYSIS REPORT", styles["cover_title"])],
            [Paragraph(symbol.upper(), ParagraphStyle(
                "ticker", parent=styles["cover_title"], fontSize=48, textColor=PURPLE, spaceAfter=12
            ))],
            [Paragraph(
                f"Comprehensive Fundamental · Technical · News Analysis",
                styles["cover_subtitle"],
            )],
            [Paragraph(
                f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}",
                styles["cover_subtitle"],
            )],
            [Paragraph(
                "Powered by CrewAI Multi-Agent System with Local LLMs via Ollama",
                ParagraphStyle("cover_note", parent=styles["cover_subtitle"], fontSize=9, textColor=MID_GREY),
            )],
        ],
        colWidths=[w],
    )
    cover_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), DARK_NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROUNDEDCORNERS", [12]),
            ]
        )
    )
    story.append(Spacer(1, 0.3 * inch))
    story.append(cover_table)

    # Recommendation badge on cover
    recommendation = _extract_recommendation(report_text)
    rec_style_key = (
        "tag_buy"
        if "BUY" in recommendation
        else "tag_sell"
        if "SELL" in recommendation
        else "tag_hold"
    )
    rec_color = TEAL if "BUY" in recommendation else RED if "SELL" in recommendation else GOLD
    rec_table = Table(
        [[Paragraph(f"⬤  {recommendation}", styles[rec_style_key])]],
        colWidths=[w],
    )
    rec_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ROUNDEDCORNERS", [8]),
            ]
        )
    )
    # Key metrics banner (current price, change, market cap, P/E, 52W range)
    if stock_data:
        story.append(Spacer(1, 0.15 * inch))
        story.extend(_key_metrics_table(stock_data, styles, w))

    story.append(Spacer(1, 0.15 * inch))
    story.append(rec_table)
    story.append(PageBreak())

    # ── REPORT CONTENT ─────────────────────────────────────────────────────────
    sections = _parse_report_sections(report_text)

    # Agent pipeline summary table
    story.extend(_section_header("📊 Analysis Pipeline", styles))
    agent_data = [
        ["Agent", "Role", "Status"],
        ["1  ·  Stock Analyst", "Fundamental & Technical Analysis", "✅ Complete"],
        ["2  ·  News Researcher", "News Research & Sentiment", "✅ Complete"],
        ["3  ·  Investment Strategist", "Report Writing & Recommendations", "✅ Complete"],
    ]
    agent_tbl = Table(agent_data, colWidths=[2.0 * inch, 2.8 * inch, 1.5 * inch])
    agent_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PURPLE),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 1), (-1, -1), SECTION_BG),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SECTION_BG, WHITE]),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c0c8e0")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(agent_tbl)
    story.append(Spacer(1, 14))

    # ── Full report text – sectioned ──────────────────────────────────────────
    section_order = [
        ("1. Executive Summary", "executive_summary"),
        ("2. Company Overview", "company_overview"),
        ("3. Fundamental Analysis", "fundamental"),
        ("4. Technical Analysis", "technical"),
        ("5. News & Sentiment", "news"),
        ("6. Investment Recommendation", "recommendation"),
        ("7. Risk Factors", "risks"),
        ("8. Conclusion", "conclusion"),
    ]

    full_text_used = False
    for display_name, key in section_order:
        section_text = sections.get(key, "").strip()
        if section_text:
            story.extend(_section_header(f"{'📈' if key == 'fundamental' else '📰' if key == 'news' else '🎯' if key == 'recommendation' else '⚠️' if key == 'risks' else '📋'}  {display_name}", styles))
            story.extend(_text_to_paragraphs(section_text, styles))
            story.append(Spacer(1, 8))
            full_text_used = True

    # Fallback: dump entire report if section parsing yielded nothing
    if not full_text_used or sum(len(v) for k, v in sections.items() if k != "full_text") < 200:
        story.extend(_section_header("📋  Investment Report", styles))
        story.extend(_text_to_paragraphs(report_text, styles))

    # ── DISCLAIMER ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width=w, thickness=0.5, color=PURPLE))
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "DISCLAIMER: This report is generated by an AI multi-agent system for informational "
            "purposes only and does not constitute financial advice. Past performance is not "
            "indicative of future results. Always conduct your own research and consult a "
            "qualified financial advisor before making any investment decisions.",
            styles["disclaimer"],
        )
    )

    # ── Build ──────────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return pdf_path
