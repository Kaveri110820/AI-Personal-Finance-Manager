import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ai_service import AIService
from services.report_service import ReportService
from utils.pdf_report import generate_report_pdf

MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

CHART_COLORS = [
    "#F87171",
    "#FBBF24",
    "#38BDF8",
    "#34D399",
    "#A78BFA",
    "#FB923C",
    "#60A5FA",
    "#94A3B8",
]


def _make_category_chart(categories: pd.DataFrame) -> go.Figure:
    frame = categories.sort_values("amount", ascending=True)
    fig = go.Figure(
        go.Bar(
            x=frame["amount"],
            y=frame["category"],
            orientation="h",
            marker_color=CHART_COLORS,
            hovertemplate="%{y}: $%{x:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title="Spend ($)",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


st.session_state.setdefault("report_service", ReportService())
st.session_state.setdefault("report_ai", AIService())

service = st.session_state.report_service
ai = st.session_state.report_ai

st.title(":material/bar_chart: Financial Reports")
st.caption("A monthly snapshot of your income, expenses, savings, budgets, bills and investments.")

today = dt.date.today()
year_options = list(range(today.year - 2, today.year + 2))
with st.sidebar:
    st.markdown("### Report month")
    month_name = st.selectbox(
        "Month",
        MONTH_NAMES,
        index=today.month - 1,
        key="rpt_month",
    )
    year = st.selectbox(
        "Year",
        year_options,
        index=year_options.index(today.year),
        key="rpt_year",
    )
    st.space("small")
    st.markdown("### Export")
    st.caption("Download a polished PDF summary of this month.")

month = MONTH_NAMES.index(month_name) + 1
month_label = f"{month_name} {year}"

report_key = (year, month)
if st.session_state.get("rpt_summary_key") != report_key:
    st.session_state.rpt_summary_key = report_key
    st.session_state.pop("rpt_summary", None)

report = service.generate(year, month)

report_sig = (
    report["income"],
    report["expense"],
    report["bills_total"],
    len(report["categories"]),
    len(report["budget_overview"]),
)
if (
    st.session_state.get("rpt_summary") is None
    or st.session_state.get("rpt_summary_sig") != report_sig
):
    with st.spinner("Writing your AI report summary…"):
        st.session_state.rpt_summary = ai.generate_report_summary(report)
    st.session_state.rpt_summary_sig = report_sig
    if st.session_state.rpt_summary:
        service.update_summary(year, month, st.session_state.rpt_summary)
report_summary = st.session_state.rpt_summary

with st.container(horizontal=True):
    st.metric("Income", f"${report['income']:,.2f}", border=True)
    st.metric(
        "Expenses",
        f"${report['expense']:,.2f}",
        delta_color="inverse",
        border=True,
    )
    st.metric(
        "Savings",
        f"${report['savings']:,.2f}",
        delta=f"{report['savings_rate']:.1f}% of income",
        delta_color="inverse" if report["savings"] < 0 else "normal",
        border=True,
    )
    st.metric(
        "Investments",
        f"${report['investment_total']:,.2f}",
        border=True,
    )

st.space("small")

if report_summary:
    with st.container(border=True):
        st.markdown("### :material/summarize: Executive summary")
        st.markdown(report_summary["summary"])
        hl_col, cn_col = st.columns(2, gap="large")
        with hl_col:
            if report_summary["highlights"]:
                st.markdown("**Highlights**")
                for item in report_summary["highlights"]:
                    st.markdown(f"- {item}")
        with cn_col:
            if report_summary["concerns"]:
                st.markdown("**Concerns**")
                for item in report_summary["concerns"]:
                    st.markdown(f"- {item}")
        st.caption(
            "Written by Gemini." if report_summary["source"] == "gemini"
            else "From built-in rules (no API key configured)."
        )
    st.space("small")

if report["income"] == 0 and report["expense"] == 0:
    st.info(
        f"No transactions found for {month_label}. Import transactions, set budgets, "
        "add bills or record investments to make this report meaningful.",
        icon=":material/bar_chart:",
    )

left_col, right_col = st.columns([3, 2], gap="large")

with left_col:
    with st.container(border=True):
        st.markdown("### Expense categories")
        if report["categories"].empty:
            st.caption("No expenses recorded for this month.")
        else:
            st.plotly_chart(
                _make_category_chart(report["categories"]),
                height=320,
                config={"displayModeBar": False},
            )
            categories_display = report["categories"].copy()
            total = float(categories_display["amount"].sum())
            categories_display["Share"] = (
                categories_display["amount"] / total * 100 if total else 0.0
            )
            st.dataframe(
                categories_display,
                hide_index=True,
                width="stretch",
                column_config={
                    "category": st.column_config.TextColumn("Category"),
                    "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                    "Share": st.column_config.ProgressColumn(
                        "Share", min_value=0, max_value=100
                    ),
                },
            )

with right_col:
    with st.container(border=True):
        st.markdown("### Budget summary")
        overview = report["budget_overview"]
        if overview.empty:
            st.caption("No budgets set for this period.")
        else:
            budget_display = overview[
                ["name", "amount", "spent", "remaining", "percent"]
            ].copy()
            st.dataframe(
                budget_display,
                hide_index=True,
                width="stretch",
                column_config={
                    "name": st.column_config.TextColumn("Budget"),
                    "amount": st.column_config.NumberColumn("Limit", format="$%.2f"),
                    "spent": st.column_config.NumberColumn("Spent", format="$%.2f"),
                    "remaining": st.column_config.NumberColumn("Remaining", format="$%.2f"),
                    "percent": st.column_config.ProgressColumn(
                        "Used", min_value=0, max_value=100
                    ),
                },
            )

st.space("small")

bill_col, inv_col = st.columns(2, gap="large")

with bill_col:
    with st.container(border=True):
        st.markdown("### :material/calendar_month: Bills due")
        st.metric(
            "Total due",
            f"${report['bills_total']:,.2f}",
            delta=f"{report['bills_paid']:,.2f} paid",
            border=True,
        )
        bills = report["bills"]
        if bills.empty:
            st.caption("No bills due in this month.")
        else:
            bills_display = bills[["name", "due_date", "amount", "status"]].copy()
            bills_display["due_date"] = pd.to_datetime(bills_display["due_date"]).dt.date
            st.dataframe(
                bills_display,
                hide_index=True,
                width="stretch",
                column_config={
                    "name": st.column_config.TextColumn("Bill"),
                    "due_date": st.column_config.DateColumn("Due date", format="DD MMM YYYY"),
                    "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                    "status": st.column_config.TextColumn("Status"),
                },
            )

with inv_col:
    with st.container(border=True):
        st.markdown("### :material/trending_up: Investments")
        st.metric(
            "Total invested",
            f"${report['investment_total']:,.2f}",
            border=True,
        )
        allocation = report["allocation"]
        if allocation.empty:
            st.caption("No investments recorded.")
        else:
            allocation_display = allocation[["investment_type", "amount", "percent"]].copy()
            allocation_display.columns = ["Type", "Amount", "Share"]
            st.dataframe(
                allocation_display,
                hide_index=True,
                width="stretch",
                column_config={
                    "Type": st.column_config.TextColumn("Type"),
                    "Amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                    "Share": st.column_config.ProgressColumn(
                        "Share", min_value=0, max_value=100
                    ),
                },
            )

st.space("small")

with st.container(border=True):
    st.markdown("### :material/download: Export report")
    st.caption(
        f"Generate a polished PDF for {month_label} covering income, expenses, savings, "
        "budgets, bills, investments and expense categories."
    )
    pdf_bytes = generate_report_pdf(report, month_label)
    st.download_button(
        "Download monthly report (PDF)",
        data=pdf_bytes,
        file_name=f"financial_report_{year}_{month:02d}.pdf",
        mime="application/pdf",
        type="primary",
        icon=":material/download:",
        key="rpt_download",
        width="stretch",
    )

st.caption("Reports are generated from data stored locally in SQLite.")
