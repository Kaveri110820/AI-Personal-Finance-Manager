import sys
from pathlib import Path

import pandas as pd
import pdfplumber
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FILE_TYPES = {
    ".xlsx": {
        "label": "Excel workbook",
        "icon": ":material/table_chart:",
        "color": "green",
    },
    ".xls": {
        "label": "Excel workbook (legacy)",
        "icon": ":material/table_chart:",
        "color": "green",
    },
    ".pdf": {
        "label": "PDF document",
        "icon": ":material/picture_as_pdf:",
        "color": "red",
    },
}

PREVIEW_ROWS = 10
MAX_SIZE_MB = 50


def format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    return f"{size_bytes / 1024:.0f} KB"


def detect_file_type(filename: str) -> str:
    return Path(filename).suffix.lower()


def extract_excel_preview(uploaded_file) -> pd.DataFrame:
    return pd.read_excel(uploaded_file, nrows=PREVIEW_ROWS)


def extract_pdf_first_page(uploaded_file) -> str:
    with pdfplumber.open(uploaded_file) as pdf:
        if not pdf.pages:
            return ""
        return pdf.pages[0].extract_text() or ""


def render_excel_preview(uploaded_file):
    try:
        preview = extract_excel_preview(uploaded_file)
    except Exception as exc:
        st.error(
            f"Could not read this Excel file: {exc}",
            icon=":material/error:",
        )
        return
    if preview.empty:
        st.warning(
            "This workbook appears to be empty. No rows were found.",
            icon=":material/inbox:",
        )
        return
    st.dataframe(
        preview.head(PREVIEW_ROWS),
        hide_index=True,
        key=f"excel_preview_{uploaded_file.file_id}",
    )
    st.caption(f"Showing the first {min(PREVIEW_ROWS, len(preview)):,} rows.")


def render_pdf_preview(uploaded_file):
    try:
        page_text = extract_pdf_first_page(uploaded_file)
    except Exception as exc:
        st.error(
            f"Could not read this PDF file: {exc}",
            icon=":material/error:",
        )
        return
    if not page_text.strip():
        st.warning(
            "No text could be extracted from the first page. "
            "The statement may be image-based or scanned.",
            icon=":material/error:",
        )
        return
    st.markdown("**First page**")
    with st.container(border=True):
        st.text(page_text)


def render_file_card(uploaded_file):
    ext = detect_file_type(uploaded_file.name)
    file_info = FILE_TYPES.get(ext)
    if file_info is None:
        st.error(
            f"Unsupported file type “{ext or 'unknown'}”. "
            "Accepted formats: .xlsx, .xls and .pdf.",
            icon=":material/error:",
        )
        return

    with st.container(border=True):
        st.markdown(f"### {file_info['icon']} {uploaded_file.name}")
        st.badge(file_info["label"], color=file_info["color"])

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Size", format_size(uploaded_file.size), border=True)
        with c2:
            st.metric(
                "Detected type",
                ext.upper().lstrip("."),
                border=True,
            )
        with c3:
            mime = uploaded_file.type or "not provided"
            st.metric("MIME type", mime, border=True)

        if uploaded_file.size > MAX_SIZE_MB * 1024 * 1024:
            st.warning(
                f"This file exceeds the {MAX_SIZE_MB} MB size limit. "
                "Processing may be slow or fail.",
                icon=":material/warning:",
            )

        st.space("small")
        if ext in (".xlsx", ".xls"):
            render_excel_preview(uploaded_file)
        else:
            render_pdf_preview(uploaded_file)


st.title(":material/upload_file: Upload Bank Statement")
st.caption(
    "Upload an Excel or PDF bank statement to inspect its contents before it is "
    "imported. Files are previewed only — nothing is saved to the database yet."
)

uploaded_files = st.file_uploader(
    "Bank statement",
    type=["xlsx", "xls", "pdf"],
    accept_multiple_files=True,
    key="upload_uploader",
    help="Accepted formats: .xlsx, .xls and .pdf. The file type is detected "
    "automatically and the first rows or first page are shown for preview.",
)

if not uploaded_files:
    with st.container(border=True):
        st.markdown(
            "**No file uploaded.**\n\n"
            "Drop an Excel (.xlsx, .xls) or PDF (.pdf) bank statement above to "
            "see a preview of its contents."
        )
        st.caption("The preview shows the first 10 rows for Excel files and the text of the first page for PDF files.")
    st.stop()

for uploaded_file in uploaded_files:
    render_file_card(uploaded_file)

st.space("small")
st.caption("Ready to import? The next step will parse and save the transactions.")
