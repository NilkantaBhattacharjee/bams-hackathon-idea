"""CSV and PDF exports for the list views and the single case card.

CSV needs no extra library. PDF uses reportlab, and only the card text is written (ASCII-safe),
so the file does not depend on symbol fonts.
"""

from io import BytesIO

import pandas as pd

CSV_MIME = "text/csv"
PDF_MIME = "application/pdf"


def table_csv(df: pd.DataFrame) -> bytes:
    """UTF-8 CSV with a BOM so Excel opens accented text correctly."""
    return ("\ufeff" + df.to_csv(index=False)).encode("utf-8")


def _ascii(text: str) -> str:
    return text.encode("ascii", "replace").decode("ascii").replace("?", "-")


def card_pdf(card_text: str, title: str) -> bytes:
    """One-page PDF of a case card, one line per card line."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 20 * mm
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(20 * mm, y, _ascii(title))
    y -= 10 * mm
    pdf.setFont("Helvetica", 10)
    for line in card_text.splitlines():
        if y < 20 * mm:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = height - 20 * mm
        pdf.drawString(20 * mm, y, _ascii(line)[:110])
        y -= 6 * mm
    pdf.save()
    return buf.getvalue()
