import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.analytics_service import AnalyticsService

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

PERIOD_OPTIONS = [3, 6, 12]

COLORS = {
    "income": "#34D399",
    "expense": "#F87171",
    "savings": "#60A5FA",
    "accent": "#A78BFA",
    "muted": "#94A3B8",
    "gold": "#FBBF24",
}

CATEGORY_COLORS = [
    "#60A5FA",
    "#34D399",
    "#A78BFA",
    "#FBBF24",
    "#38BDF8",
    "#F87171",
    "#FB923C",
    "#94A3B8",
]


def _chart_config():
    return {"displayModeBar": False}


def make_income_vs_expense(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["label"],
            y=df["income"],
            name="Income",
            marker_color=COLORS["income"],
            hovertemplate="%{x}<br>Income: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=df["label"],
            y=df["expense"],
            name="Expenses",
            marker_color=COLORS["expense"],
            hovertemplate="%{x}<br>Expenses: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def make_spending_trend(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["label"],
            y=df["expense"],
            name="Spending",
            mode="lines+markers",
            line=dict(color=COLORS["expense"], width=2.5),
            fill="tozeroy",
            marker=dict(size=6),
            hovertemplate="%{x}<br>Spending: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def make_savings_trend(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["label"],
            y=df["savings"],
            name="Monthly savings",
            marker_color=COLORS["savings"],
            opacity=0.55,
            hovertemplate="%{x}<br>Monthly savings: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["label"],
            y=df["cumulative_savings"],
            name="Total saved",
            mode="lines+markers",
            line=dict(color=COLORS["accent"], width=2.5),
            marker=dict(size=6),
            hovertemplate="%{x}<br>Total saved: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def make_category_donut(categories: pd.DataFrame) -> go.Figure:
    total = float(categories["amount"].sum())
    fig = go.Figure(
        go.Pie(
            labels=categories["category"],
            values=categories["amount"],
            hole=0.6,
            marker=dict(colors=CATEGORY_COLORS),
            textinfo="percent",
            hovertemplate="%{label}<br>$%{value:,.2f} (%{percent})<extra></extra>",
        )
    )
    fig.update_layout(
        annotations=[
            dict(
                text=f"<b>${total:,.0f}</b><br>spent",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14),
            )
        ],
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def make_budget_utilization(utilization: pd.DataFrame) -> go.Figure:
    frame = utilization.sort_values("percent")
    colors = [
        COLORS["expense"] if overspent else COLORS["income"]
        for overspent in frame["overspent"]
    ]
    fig = go.Figure(
        go.Bar(
            x=frame["percent"],
            y=frame["name"],
            orientation="h",
            marker_color=colors,
            hovertemplate="%{y}<br>Used: %{x:.1f}% of $%{customdata:,.2f}<extra></extra>",
            customdata=frame["amount"],
        )
    )
    fig.update_layout(
        xaxis=dict(title="Budget used (%)", range=[0, 100]),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def make_investment_donut(allocation: pd.DataFrame) -> go.Figure:
    total = float(allocation["amount"].sum())
    fig = go.Figure(
        go.Pie(
            labels=allocation["investment_type"],
            values=allocation["amount"],
            hole=0.6,
            marker=dict(colors=CATEGORY_COLORS),
            textinfo="percent",
            hovertemplate="%{label}<br>$%{value:,.2f} (%{percent})<extra></extra>",
        )
    )
    fig.update_layout(
        annotations=[
            dict(
                text=f"<b>${total:,.0f}</b><br>invested",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14),
            )
        ],
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def make_top_expenses(top: pd.DataFrame) -> go.Figure:
    frame = top.copy()
    frame["abs_amount"] = frame["amount"].abs()
    frame = frame.sort_values("abs_amount")
    fig = go.Figure(
        go.Bar(
            x=frame["abs_amount"],
            y=frame["description"],
            orientation="h",
            marker_color=COLORS["expense"],
            customdata=frame[["date", "category"]],
            hovertemplate="%{y}<br>%{customdata[0]} • %{customdata[1]}<br>$%{x:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis=dict(title="Amount ($)"),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def _chart_container(title: str, fig: go.Figure | None, height: int = 340):
    with st.container(border=True):
        st.markdown(f"### {title}")
        if fig is None:
            st.caption("No data available for this chart yet.")
        else:
            st.plotly_chart(fig, height=height, config=_chart_config())


st.session_state.setdefault("analytics_service", AnalyticsService())

service = st.session_state.analytics_service

st.title(":material/analytics: Analytics")
st.caption("Deep-dive charts across your spending, savings, budgets, investments and top expenses.")

today = dt.date.today()
year_options = list(range(today.year - 2, today.year + 2))
with st.sidebar:
    st.markdown("### Trend period")
    period = st.selectbox(
        "Trend period",
        PERIOD_OPTIONS,
        index=PERIOD_OPTIONS.index(6),
        key="anl_period",
        format_func=lambda value: f"Last {value} months",
    )
    st.markdown("### Analyze month")
    month_name = st.selectbox(
        "Month",
        MONTH_NAMES,
        index=today.month - 1,
        key="anl_month",
    )
    year = st.selectbox(
        "Year",
        year_options,
        index=year_options.index(today.year),
        key="anl_year",
    )

month = MONTH_NAMES.index(month_name) + 1
month_label = f"{month_name} {year}"

summary = service.get_month_summary(year, month)
monthly = service.get_monthly_series(period)
categories = service.get_category_distribution(year, month)
utilization = service.get_budget_utilization(year, month)
allocation = service.get_investment_allocation()
top_expenses = service.get_top_expenses(year, month)

with st.container(horizontal=True):
    st.metric("Income", f"${summary['income']:,.2f}", border=True)
    st.metric(
        "Expenses",
        f"${summary['expense']:,.2f}",
        delta_color="inverse",
        border=True,
    )
    st.metric(
        "Savings",
        f"${summary['savings']:,.2f}",
        delta=f"{summary['savings_rate']:.1f}% of income",
        delta_color="inverse" if summary["savings"] < 0 else "normal",
        border=True,
    )
    st.metric(
        "Invested",
        f"${allocation['amount'].sum():,.2f}" if not allocation.empty else "$0.00",
        border=True,
    )

st.space("small")

if summary["income"] == 0 and summary["expense"] == 0 and allocation.empty:
    st.info(
        "No data to analyze yet. Add transactions, budgets, bills or investments — or "
        "use the Transactions page to load sample data — to populate these charts.",
        icon=":material/analytics:",
    )

trend_col1, trend_col2 = st.columns(2, gap="large")
with trend_col1:
    _chart_container(":material/account_balance: Income vs Expense", make_income_vs_expense(monthly))
with trend_col2:
    _chart_container(":material/category: Expense categories", make_category_donut(categories) if not categories.empty else None)

st.space("small")

trend_col3, trend_col4 = st.columns(2, gap="large")
with trend_col3:
    _chart_container(":material/show_chart: Monthly spending trend", make_spending_trend(monthly))
with trend_col4:
    _chart_container(":material/savings: Savings trend", make_savings_trend(monthly))

st.space("small")

util_col, inv_col = st.columns(2, gap="large")
with util_col:
    _chart_container(":material/target: Budget utilization", make_budget_utilization(utilization) if not utilization.empty else None)
with inv_col:
    _chart_container(":material/trending_up: Investment allocation", make_investment_donut(allocation) if not allocation.empty else None)

st.space("small")

with st.container(border=True):
    st.markdown(f"### :material/local_fire_department: Top expenses — {month_label}")
    if top_expenses.empty:
        st.caption("No expenses recorded for this month.")
    else:
        st.plotly_chart(
            make_top_expenses(top_expenses),
            height=360,
            config=_chart_config(),
        )

st.space("small")

st.caption("Charts are built from data stored locally in SQLite.")
