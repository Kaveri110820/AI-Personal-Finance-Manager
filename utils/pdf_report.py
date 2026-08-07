from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ACCENT = colors.HexColor("#7C3AED")
HEADER_BG = colors.HexColor("#7C3AED")
ALT_ROW = colors.HexColor("#F3F0FB")
BORDER = colors.HexColor("#DDD6FE")
MUTED = colors.HexColor("#64748B")
GREEN = colors.HexColor("#059669")
RED = colors.HexColor("#DC2626")
WHITE = colors.HexColor("#FFFFFF")

PAGE = A4
MARGIN = 18 * mm


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _build_table(headers: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    data = [headers, *rows]
    table = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, ALT_ROW]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    table.setStyle(TableStyle(style))
    return table


def _empty_note(text: str) -> Paragraph:
    style = ParagraphStyle(
        "EmptyNote", fontSize=9, textColor=MUTED, spaceBefore=4, spaceAfter=4
    )
    return Paragraph(f"<i>{text}</i>", style)


def generate_report_pdf(report: dict, month_label: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=PAGE,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=f"Financial Report — {month_label}",
        author="AI Personal Finance Manager",
    )

    base = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=base["Title"],
        fontSize=22,
        textColor=ACCENT,
        spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle", parent=base["Normal"], fontSize=10, textColor=MUTED, spaceAfter=8
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=base["Heading2"],
        fontSize=13,
        textColor=ACCENT,
        spaceBefore=12,
        spaceAfter=4,
    )

    card_label_style = ParagraphStyle(
        "CardLabel", parent=base["Normal"], fontSize=8, textColor=WHITE, alignment=TA_CENTER
    )
    card_value_style = ParagraphStyle(
        "CardValue",
        parent=base["Normal"],
        fontSize=13,
        textColor=WHITE,
        alignment=TA_CENTER,
        spaceBefore=2,
    )

    story = []
    story.append(Paragraph("Financial Report", title_style))
    story.append(Paragraph(f"{month_label} &nbsp;•&nbsp; AI Personal Finance Manager", subtitle_style))

    income = report["income"]
    expense = report["expense"]
    savings = report["savings"]
    rate = report["savings_rate"]

    summary_cards = [
        (
            "INCOME",
            _money(income),
            GREEN,
        ),
        (
            "EXPENSES",
            _money(expense),
            RED,
        ),
        (
            "SAVINGS",
            _money(savings),
            ACCENT,
        ),
    ]
    card_cells = []
    for label, value, bg in summary_cards:
        card_cells.append(
            [
                Paragraph(label, card_label_style),
                Paragraph(value, card_value_style),
            ]
        )
    cards = Table(
        [card_cells],
        colWidths=[(PAGE[0] - 2 * MARGIN) / 3] * 3,
    )
    cards.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), GREEN),
                ("BACKGROUND", (1, 0), (1, 0), RED),
                ("BACKGROUND", (2, 0), (2, 0), ACCENT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ]
        )
    )
    story.append(cards)
    story.append(
        Paragraph(
            f"Savings rate: <b>{rate:.1f}%</b> of income. Period "
            f"{report['start'].isoformat()} to {report['end'].isoformat()}.",
            subtitle_style,
        )
    )

    story.append(Paragraph("Expense Categories", heading_style))
    categories = report["categories"]
    if categories.empty:
        story.append(_empty_note("No expenses recorded for this month."))
    else:
        total = float(categories["amount"].sum())
        rows = [
            [
                str(row["category"]),
                _money(row["amount"]),
                f"{row['amount'] / total * 100:.1f}%",
            ]
            for _, row in categories.iterrows()
        ]
        rows.append(
            ["Total", _money(total), "100.0%"]
        )
        table = _build_table(
            ["Category", "Amount", "Share"],
            rows,
            [(PAGE[0] - 2 * MARGIN) * 0.5, (PAGE[0] - 2 * MARGIN) * 0.25, (PAGE[0] - 2 * MARGIN) * 0.25],
        )
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("BACKGROUND", (0, -1), (-1, -1), ALT_ROW),
                ]
            )
        )
        story.append(table)

    story.append(Paragraph("Budget Summary", heading_style))
    overview = report["budget_overview"]
    if overview.empty:
        story.append(_empty_note("No budgets set for this period."))
    else:
        rows = []
        for _, row in overview.iterrows():
            used = f"{row['percent']:.0f}%"
            if row["overspent"]:
                used = f'<font color="#DC2626"><b>{used}</b></font>'
            rows.append(
                [
                    str(row["name"]),
                    _money(row["amount"]),
                    _money(row["spent"]),
                    _money(row["remaining"]),
                    used,
                ]
            )
        table = _build_table(
            ["Budget", "Limit", "Spent", "Remaining", "Used"],
            rows,
            [(PAGE[0] - 2 * MARGIN) * 0.22] * 5,
        )
        story.append(table)

    story.append(Paragraph("Bills", heading_style))
    bills = report["bills"]
    if bills.empty:
        story.append(_empty_note("No bills due in this period."))
    else:
        rows = [
            [
                str(row["name"]),
                str(row["due_date"]),
                _money(row["amount"]),
                str(row["status"]).capitalize(),
            ]
            for _, row in bills.iterrows()
        ]
        table = _build_table(
            ["Bill", "Due date", "Amount", "Status"],
            rows,
            [(PAGE[0] - 2 * MARGIN) * 0.40, (PAGE[0] - 2 * MARGIN) * 0.20, (PAGE[0] - 2 * MARGIN) * 0.20, (PAGE[0] - 2 * MARGIN) * 0.20],
        )
        story.append(table)
    story.append(
        Paragraph(
            f"Total due: <b>{_money(report['bills_total'])}</b> — paid "
            f"{_money(report['bills_paid'])}, outstanding {_money(report['bills_pending'])}.",
            subtitle_style,
        )
    )

    story.append(Paragraph("Investments", heading_style))
    allocation = report["allocation"]
    if allocation.empty:
        story.append(_empty_note("No investments recorded."))
    else:
        rows = [
            [
                str(row["investment_type"]),
                _money(row["amount"]),
                f"{row['percent']:.1f}%",
            ]
            for _, row in allocation.iterrows()
        ]
        table = _build_table(
            ["Type", "Amount", "Share"],
            rows,
            [(PAGE[0] - 2 * MARGIN) * 0.5, (PAGE[0] - 2 * MARGIN) * 0.25, (PAGE[0] - 2 * MARGIN) * 0.25],
        )
        story.append(table)
    story.append(
        Paragraph(
            f"Total invested: <b>{_money(report['investment_total'])}</b>.",
            subtitle_style,
        )
    )

    story.append(Spacer(1, 14))
    story.append(
        Paragraph(
            "Generated by AI Personal Finance Manager. Figures come from locally stored "
            "SQLite data.",
            ParagraphStyle("Footer", parent=base["Normal"], fontSize=8, textColor=MUTED),
        )
    )

    doc.build(story)
    return buffer.getvalue()
