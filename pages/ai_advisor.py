import calendar
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
from services.transaction_service import TransactionService

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

COLORS = {
    "income": "#34D399",
    "expense": "#F87171",
    "savings": "#60A5FA",
    "accent": "#A78BFA",
    "muted": "#94A3B8",
}

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


def _make_category_chart(category_spending: dict) -> go.Figure:
    frame = pd.DataFrame(
        list(category_spending.items()), columns=["category", "amount"]
    ).sort_values("amount", ascending=True)
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


st.session_state.setdefault("advisor_service", TransactionService())
st.session_state.setdefault("advisor_ai", AIService())

service = st.session_state.advisor_service
ai = st.session_state.advisor_ai

st.title(":material/psychology: AI Savings Advisor")
st.caption("An AI reads your monthly transactions to spot top spending, unnecessary expenses and realistic savings.")

today = dt.date.today()
year_options = list(range(today.year - 2, today.year + 2))
with st.sidebar:
    st.markdown("### Analyze month")
    month_name = st.selectbox(
        "Month",
        MONTH_NAMES,
        index=today.month - 1,
        key="adv_month",
    )
    year = st.selectbox(
        "Year",
        year_options,
        index=year_options.index(today.year),
        key="adv_year",
    )
    st.caption(
        "Powered by Gemini; falls back to built-in rules when no API key is configured."
    )

month = MONTH_NAMES.index(month_name) + 1
month_label = f"{month_name} {year}"
first = dt.date(year, month, 1)
last = dt.date(year, month, calendar.monthrange(year, month)[1])

analysis_key = (year, month)
if st.session_state.get("adv_analysis_key") != analysis_key:
    st.session_state.adv_analysis_key = analysis_key
    st.session_state.pop("adv_analysis", None)
    st.session_state.pop("adv_insights", None)

transactions = service.get_transactions(start=first, end=last)
transaction_count = int(len(transactions))

if (
    st.session_state.get("adv_analysis") is None
    or st.session_state.get("adv_analysis_n") != transaction_count
):
    with st.spinner("Analyzing your month with AI…"):
        st.session_state.adv_analysis = ai.analyze_savings(transactions)
    st.session_state.adv_analysis_n = transaction_count
analysis = st.session_state.adv_analysis

st.space("small")

if analysis is None:
    st.info(
        f"No expense transactions found for {month_label}. Add transactions for that "
        "month or pick a different month to get savings advice.",
        icon=":material/psychology:",
    )
    st.stop()

if (
    st.session_state.get("adv_insights") is None
    or st.session_state.get("adv_insights_n") != transaction_count
):
    with st.spinner("Generating financial insights…"):
        st.session_state.adv_insights = ai.generate_insights(transactions)
    st.session_state.adv_insights_n = transaction_count
insights = st.session_state.adv_insights

with st.container(horizontal=True):
    st.metric("Total income", f"${analysis['income']:,.2f}", border=True)
    st.metric(
        "Total expense",
        f"${analysis['expense']:,.2f}",
        delta_color="inverse",
        border=True,
    )
    st.metric(
        "Savings",
        f"${analysis['savings']:,.2f}",
        delta=f"{analysis['savings_rate']:.1f}% of income",
        delta_color="inverse" if analysis["savings"] < 0 else "normal",
        border=True,
    )
    st.metric(
        "Potential extra",
        f"${analysis['additional_savings']:,.2f}/mo",
        border=True,
    )

st.space("small")

with st.container(border=True):
    st.markdown("### :material/summarize: AI savings summary")
    st.markdown(analysis["summary"])
    st.caption(
        "Summary written by Gemini." if analysis["source"] == "gemini"
        else "Summary from built-in rules (no API key configured)."
    )

st.space("small")

left_col, right_col = st.columns([3, 2], gap="large")

with left_col:
    with st.container(border=True):
        st.markdown("### :material/local_fire_department: Top spending category")
        top_share = (
            analysis["top_amount"] / analysis["expense"] * 100
            if analysis["expense"]
            else 0.0
        )
        st.markdown(
            f"**{analysis['top_category']}** is your biggest expense at "
            f"**${analysis['top_amount']:,.2f}** — {top_share:.0f}% of your "
            f"spending in {month_label}."
        )
        st.progress(min(top_share / 100.0, 1.0))

    st.space("small")

    with st.container(border=True):
        st.markdown("### Category spending")
        st.plotly_chart(
            _make_category_chart(analysis["category_spending"]),
            height=320,
            config={"displayModeBar": False},
        )

with right_col:
    with st.container(border=True):
        st.markdown("### :material/savings: Monthly savings estimate")
        st.metric(
            "Current savings",
            f"${analysis['savings']:,.2f}",
            border=True,
        )
        st.metric(
            "Potential additional savings",
            f"${analysis['additional_savings']:,.2f}",
            border=True,
        )
        st.metric(
            "Estimated savings potential",
            f"${analysis['estimated_savings']:,.2f}",
            delta=f"+{analysis['additional_savings']:,.2f} from advice",
            border=True,
        )
        st.caption(
            "Applying all suggestions could take you from "
            f"**${analysis['savings']:,.2f}** to **${analysis['estimated_savings']:,.2f}** "
            "saved per month."
        )

    st.space("small")

    with st.container(border=True):
        st.markdown("### :material/lightbulb: Savings suggestions")
        if not analysis["suggestions"]:
            st.caption("No suggestions for this month's categories.")
        for item in analysis["suggestions"]:
            with st.expander(f"{item['title']} — potential ${item['potential']:,.2f}"):
                st.markdown(item["message"])
                st.caption(f"{item['category']} spend: ${item['spent']:,.2f}")

st.space("small")

if analysis["unnecessary"]:
    with st.container(border=True):
        st.markdown("### :material/remove_shopping_cart: Unnecessary expenses")
        st.caption(
            "Optional, discretionary spending that can safely be reduced. Amounts are "
            "your actual spend; the potential shows what a sensible trim could save."
        )
        unnecessary_df = pd.DataFrame(analysis["unnecessary"])
        unnecessary_df.columns = ["Category", "Spend", "Potential saving"]
        st.dataframe(
            unnecessary_df,
            hide_index=True,
            width="stretch",
            column_config={
                "Category": st.column_config.TextColumn("Category"),
                "Spend": st.column_config.NumberColumn("Spend", format="$%.2f"),
                "Potential saving": st.column_config.NumberColumn(
                    "Potential saving", format="$%.2f"
                ),
            },
        )

if insights:
    st.space("small")
    with st.container(border=True):
        st.markdown("### :material/insights: Financial insights")
        st.markdown(insights["summary"])
        for insight in insights["insights"]:
            st.markdown(f"- {insight}")
        st.caption(
            "Insights generated by Gemini." if insights["source"] == "gemini"
            else "Insights from built-in rules (no API key configured)."
        )

st.space("small")

st.caption(
    f"Analysis for {month_label} from transactions stored in SQLite. "
    "Advice is illustrative, not financial guidance."
)
