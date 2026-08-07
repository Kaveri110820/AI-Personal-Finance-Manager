import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ai_service import AIService, CATEGORIES
from services.transaction_service import TransactionService, categorize
from utils.excel_reader import extract_transactions_from_excel
from utils.pdf_reader import extract_transactions_from_pdf

COLORS = {
    "income": "#34D399",
    "expense": "#F87171",
    "muted": "#94A3B8",
}

COLUMN_ORDER = ["id", "date", "description", "category", "amount", "balance", "delete"]

SAMPLE_TRANSACTIONS = [
    ("Monthly salary deposit", "Salary", 4200.00),
    ("Rent payment", "Bills", -1850.00),
    ("Tesco supermarket", "Food", -96.20),
    ("Starbucks coffee", "Food", -4.85),
    ("Electricity bill", "Bills", -74.80),
    ("Netflix subscription", "Entertainment", -15.99),
    ("Shell fuel station", "Travel", -52.40),
    ("Gym membership", "Healthcare", -35.00),
    ("Freelance project invoice", "Salary", 850.00),
    ("Mobile phone bill", "Bills", -42.50),
    ("Restaurant dinner", "Food", -62.30),
    ("Amazon order", "Shopping", -38.75),
    ("Pharmacy prescription", "Healthcare", -18.20),
    ("Train ticket", "Travel", -28.40),
    ("Movie night", "Entertainment", -24.00),
    ("Water bill", "Bills", -31.60),
    ("Whole Foods grocery", "Food", -118.45),
    ("Uber ride", "Travel", -19.80),
    ("Dividend payout", "Investment", 12.34),
    ("Zara clothing", "Shopping", -64.90),
]

PREVIEW_COLUMNS = {
    "date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
    "description": st.column_config.TextColumn("Description"),
    "category": st.column_config.TextColumn("Category"),
    "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
    "balance": st.column_config.NumberColumn("Balance", format="$%.2f"),
}


def _style_amount(value):
    if value is None:
        return ""
    color = COLORS["income"] if value > 0 else COLORS["expense"]
    return f"color: {color}; font-weight: 600;"


def _load_sample_data():
    today = dt.date.today()
    rows = [
        {
            "date": today - dt.timedelta(days=3 * index),
            "description": description,
            "category": category,
            "amount": amount,
            "source": "Sample",
        }
        for index, (description, category, amount) in enumerate(SAMPLE_TRANSACTIONS)
    ]
    inserted, skipped = st.session_state.service.add_transactions(rows)
    st.session_state.import_done = (inserted, skipped)
    st.session_state.pop("tx_date_range", None)


def _clear_filters():
    for key in ("tx_search", "tx_categories", "tx_date_range"):
        st.session_state.pop(key, None)


def _run_ai_categorize():
    records = st.session_state.get("tx_ai_set") or []
    if not records:
        return
    result = st.session_state.ai.apply_categories(st.session_state.service, records)
    st.session_state.ai_done = result


def _ai_reset():
    st.session_state.pop("ai_done", None)


def _on_delete_click():
    click = st.session_state.get("tx_delete")
    if not click:
        return
    display_df = st.session_state.get("tx_display")
    row = click.get("row")
    if display_df is None or row is None or row >= len(display_df):
        return
    st.session_state.pending_delete = int(display_df.iloc[row]["id"])
    st.session_state.pending_delete_desc = str(display_df.iloc[row]["description"])


st.session_state.setdefault("pending_import", None)
st.session_state.setdefault("pending_import_source", None)
st.session_state.setdefault("pending_delete", None)
st.session_state.setdefault("pending_delete_desc", None)
st.session_state.setdefault("import_done", None)
st.session_state.setdefault("ai_done", None)
st.session_state.setdefault("service", TransactionService())
st.session_state.setdefault("ai", AIService())

service = st.session_state.service
ai = st.session_state.ai

st.title(":material/receipt_long: Transactions")
st.caption("Upload a bank statement, review the extracted rows, then search, filter and manage your transactions.")

done = st.session_state.get("import_done")
if done:
    inserted, skipped = done
    message = f"Imported {inserted:,} transactions."
    if skipped:
        message += f" Skipped {skipped:,} duplicates."
    st.success(message, icon=":material/check_circle:")
    st.session_state.pop("import_done", None)

st.subheader("Import a statement")
import_tab, pdf_tab = st.tabs(
    [":material/table_chart: Excel", ":material/picture_as_pdf: PDF"]
)

with import_tab:
    excel_file = st.file_uploader(
        "Upload an Excel bank statement",
        type=["xlsx", "xls", "csv"],
        key="excel_uploader",
        label_visibility="collapsed",
        help="Accepted formats: .xlsx, .xls, .csv. Date, description and amount/debit/credit columns are detected automatically.",
    )
    if excel_file is not None:
        try:
            extracted = extract_transactions_from_excel(excel_file)
        except Exception as exc:
            extracted = pd.DataFrame()
            st.error(f"Could not read the Excel file: {exc}", icon=":material/error:")
        if extracted is None or extracted.empty:
            st.warning(
                "No transactions could be extracted. Check that the sheet contains date, description and amount (or debit/credit) columns.",
                icon=":material/error:",
            )
            st.session_state.pending_import = None
        else:
            st.session_state.pending_import = extracted
            st.session_state.pending_import_source = "Excel"

with pdf_tab:
    pdf_file = st.file_uploader(
        "Upload a PDF bank statement",
        type=["pdf"],
        key="pdf_uploader",
        label_visibility="collapsed",
        help="Tables are parsed with pdfplumber. Verifies typical statement layouts with Date, Description and Withdrawal/Deposit columns.",
    )
    if pdf_file is not None:
        try:
            extracted = extract_transactions_from_pdf(pdf_file)
            extracted = pd.DataFrame(extracted, columns=["date", "description", "amount", "balance"])
        except Exception as exc:
            extracted = pd.DataFrame()
            st.error(f"Could not read the PDF file: {exc}", icon=":material/error:")
        if extracted is None or extracted.empty:
            st.warning(
                "No transactions could be extracted from this PDF. The statement may use a layout that is not recognized.",
                icon=":material/error:",
            )
            st.session_state.pending_import = None
        else:
            st.session_state.pending_import = extracted
            st.session_state.pending_import_source = "PDF"

pending_import = st.session_state.get("pending_import")
if pending_import is not None and isinstance(pending_import, pd.DataFrame) and not pending_import.empty:
    with st.container(border=True):
        preview = pending_import.copy()
        preview["category"] = [
            categorize(str(description), amount)
            for description, amount in zip(preview["description"], preview["amount"])
        ]
        source_name = st.session_state.get("pending_import_source", "Statement")
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(
                f"**{len(preview):,} transactions extracted** from your {source_name} statement."
            )
        with c2:
            st.markdown(
                f"Net **${preview['amount'].sum():,.2f}**" if preview["amount"].sum() >= 0 else f"Net **-${-preview['amount'].sum():,.2f}**",
                text_alignment="right",
            )
        preview = preview[["date", "description", "category", "amount", "balance"]]
        st.dataframe(
            preview.head(10),
            hide_index=True,
            column_config=PREVIEW_COLUMNS,
            key="import_preview",
        )
        st.caption(f"Showing the first 10 of {len(preview):,} rows.")
        if st.button(
            f"Import {len(preview):,} transactions",
            type="primary",
            icon=":material/download:",
            key="import_btn",
            width="stretch",
        ):
            rows, inserted, skipped = service.import_dataframe(pending_import)
            st.session_state.import_done = (inserted, skipped)
            st.session_state.pending_import = None
            st.session_state.pending_import_source = None
            st.session_state.pop("excel_uploader", None)
            st.session_state.pop("pdf_uploader", None)
            st.session_state.pop("tx_date_range", None)
            st.rerun()

with st.sidebar:
    st.markdown("### Filters")
    query = st.text_input(
        "Search transactions",
        placeholder="Merchant, description, category…",
        key="tx_search",
        label_visibility="collapsed",
        icon=":material/search:",
    )
    all_categories = service.get_categories()
    category_options = list(dict.fromkeys([*CATEGORIES, *all_categories]))
    selected_categories = st.multiselect(
        "Category",
        all_categories,
        key="tx_categories",
        placeholder="All categories",
    )
    min_date, max_date = service.get_date_range()
    today = dt.date.today()
    if min_date is None or max_date is None:
        default_range = (today - dt.timedelta(days=90), today)
    else:
        default_range = (min_date, max_date)
    date_range = st.date_input(
        "Date range",
        value=default_range,
        key="tx_date_range",
        format="DD/MM/YYYY",
    )
    limit = st.selectbox(
        "Rows shown",
        [50, 100, 250, 500, 1000, 0],
        index=3,
        key="tx_limit",
        format_func=lambda value: "All" if value == 0 else f"{value:,}",
    )
    st.button("Clear filters", icon=":material/filter_alt_off:", on_click=_clear_filters, width="stretch", key="clear_filters_btn")
    st.space("small")
    st.button(
        "Load sample transactions",
        help="Inserts a set of demo transactions so you can explore the page.",
        icon=":material/play_arrow:",
        on_click=_load_sample_data,
        width="stretch",
        key="load_sample_btn",
    )

if isinstance(date_range, tuple):
    start_date, end_date = date_range[0], date_range[1]
else:
    start_date = end_date = date_range

total_stats = service.get_stats()
total_count = total_stats["count"]

if total_count == 0:
    st.space("small")
    with st.container(border=True):
        st.markdown(
            "**No transactions yet.** Upload an Excel or PDF bank statement above to get started, "
            "or load sample transactions from the sidebar to explore."
        )
        st.caption("All transactions are stored locally in an SQLite database.")
    st.stop()

filtered_df = service.get_transactions(
    search=query.strip() or None,
    start=start_date,
    end=end_date,
    categories=selected_categories or None,
)

income = filtered_df[filtered_df["amount"] > 0]["amount"].sum()
expense = filtered_df[filtered_df["amount"] < 0]["amount"].abs().sum()
net = income - expense

filters_active = (
    bool(query.strip())
    or bool(selected_categories)
    or date_range != default_range
)
with st.container(horizontal=True):
    st.metric(
        "Transactions",
        f"{len(filtered_df):,}",
        delta=f"of {total_count:,} total" if len(filtered_df) != total_count else "",
        border=True,
    )
    st.metric("Total income", f"${income:,.2f}", border=True, delta_color="normal")
    st.metric(
        "Total expense",
        f"${expense:,.2f}",
        delta_color="inverse",
        border=True,
    )
    st.metric("Net", f"${net:,.2f}", delta_color="normal", border=True)

if filters_active:
    st.caption(
        f"Filtered view. Showing {len(filtered_df):,} of {total_count:,} transactions."
    )
else:
    st.caption(f"Showing all {len(filtered_df):,} transactions.")

ai_done = st.session_state.get("ai_done")
if ai_done:
    st.success(
        f"AI categorizer processed **{ai_done['processed']:,}** transactions "
        f"and updated **{ai_done['changed']:,}** categories.",
        icon=":material/auto_awesome:",
    )
    if ai_done.get("source") == "gemini":
        st.caption("Categorized with Gemini AI.")
    else:
        st.caption("Categorized with built-in rules (no API key configured).")
    st.session_state.pop("ai_done", None)

st.space("small")

with st.container(border=True):
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown("### :material/auto_awesome: AI Expense Categorizer")
        st.caption(
            "Automatically assigns every transaction to one of 10 categories — "
            f"{', '.join(CATEGORIES)}. Powered by Gemini; falls back to built-in "
            "rules when no API key is configured."
        )
    with c2:
        n_uncategorized = int(
            filtered_df["category"].isin(["Uncategorized", "Others"]).sum()
        )
        st.metric("Uncategorized", f"{n_uncategorized:,}", border=True)
    suggestions = []
    batch_input = [
        {
            "id": int(row["id"]),
            "description": str(row["description"]),
            "amount": float(row["amount"]),
            "current_category": str(row["category"]),
        }
        for _, row in filtered_df.iterrows()
    ]
    batch_output = ai.categorize_batch(batch_input)
    for rec in batch_output:
        suggestions.append(
            {
                "id": int(rec["id"]),
                "description": str(rec["description"]),
                "category": str(rec.get("current_category") or "Others"),
                "suggested": str(rec.get("category") or "Others"),
            }
        )
    st.session_state.tx_ai_set = suggestions
    proposed = pd.DataFrame(suggestions)
    n_suggested = int((proposed["suggested"] != proposed["category"]).sum())
    if n_suggested == 0:
        st.success(
            "All transactions already match the AI's suggestion. Nothing to update.",
            icon=":material/check_circle:",
        )
    else:
        st.markdown(
            f"The AI suggests a **different category for {n_suggested:,}** of the "
            f"{len(filtered_df):,} transactions currently in view."
        )
        preview = proposed.loc[proposed["suggested"] != proposed["category"], ["description", "category", "suggested"]]
        preview.columns = ["Description", "Current category", "AI suggestion"]
        st.dataframe(preview.head(10), hide_index=True, key="ai_preview")
        st.caption(f"Sample of the first {min(10, len(preview)):,} proposed changes. Applying updates the SQLite database.")
        left_col, right_col = st.columns([1, 1])
        with left_col:
            st.button(
                f"Apply {n_suggested:,} suggested categories",
                type="primary",
                icon=":material/auto_awesome:",
                on_click=_run_ai_categorize,
                key="ai_apply_btn",
                width="stretch",
            )
        with right_col:
            st.button(
                "Reset banner",
                icon=":material/restart_alt:",
                help="Dismiss the result banner (does not change the database).",
                on_click=_ai_reset,
                key="ai_reset_btn",
            )

st.space("small")

if filtered_df.empty:
    st.warning(
        "No transactions match the current filters. Adjust the search, date range or categories.",
        icon=":material/filter_alt:",
    )
    st.stop()

display = filtered_df[["id", "date", "description", "category", "amount", "balance"]].copy()
if limit:
    display = display.head(int(limit))
display["delete"] = ":material/delete:"

display_key = tuple(display["id"].tolist()) + tuple(display["category"].tolist())
if st.session_state.get("tx_display_key") != display_key:
    st.session_state.pop("tx_editor", None)
    st.session_state.pop("tx_delete", None)
    st.session_state.tx_display_key = display_key

st.session_state.tx_display = display

styled_display = display.style.map(_style_amount, subset=["amount"])

editor_height = min(620, max(220, len(display) * 38 + 48))

st.data_editor(
    styled_display,
    key="tx_editor",
    hide_index=True,
    on_change="rerun",
    disabled=["id", "date", "description", "amount", "balance"],
    height=editor_height,
    column_config={
        "id": None,
        "date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
        "description": st.column_config.TextColumn("Description"),
        "category": st.column_config.SelectboxColumn(
            "Category",
            options=category_options or CATEGORIES,
            required=True,
            help="Change the category directly in this cell.",
        ),
        "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
        "balance": st.column_config.NumberColumn("Balance", format="$%.2f"),
        "delete": st.column_config.ButtonColumn(
            "Delete",
            help="Remove this transaction.",
            on_click=_on_delete_click,
            key="tx_delete",
            type="tertiary",
            alignment="center",
        ),
    },
    column_order=COLUMN_ORDER,
)

editor_state = st.session_state.get("tx_editor") or {}
edited_rows = editor_state.get("edited_rows") or {}
if edited_rows:
    current_display = st.session_state.get("tx_display")
    if current_display is not None:
        changed = 0
        for row_index, changes in edited_rows.items():
            if "category" in changes:
                transaction_id = int(current_display.iloc[int(row_index)]["id"])
                if service.update_category(transaction_id, str(changes["category"])):
                    changed += 1
        if changed:
            st.toast(
                f"Updated {changed} categor{'y' if changed == 1 else 'ies'}",
                icon=":material/label:",
            )

pending_delete = st.session_state.get("pending_delete")
if pending_delete:
    description = st.session_state.get("pending_delete_desc", "this transaction")
    st.warning(
        f"**Delete transaction** — “{description}”? This cannot be undone.",
        icon=":material/delete:",
    )
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Delete", type="primary", icon=":material/delete:", key="confirm_delete"):
            if service.delete(int(pending_delete)):
                st.toast("Transaction deleted", icon=":material/check_circle:")
            st.session_state.pending_delete = None
            st.session_state.pending_delete_desc = None
            st.rerun()
        if st.button("Cancel", key="cancel_delete"):
            st.session_state.pending_delete = None
            st.session_state.pending_delete_desc = None
            st.rerun()

st.caption("Transactions are stored locally in SQLite. Duplicate rows are skipped on import.")
