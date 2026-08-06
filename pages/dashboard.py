import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

COLORS = {
    "income": "#34D399",
    "expense": "#F87171",
    "savings": "#60A5FA",
    "accent": "#A78BFA",
    "muted": "#94A3B8",
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

PERIODS = {
    "Last 3 months": 3,
    "Last 6 months": 6,
    "Last 12 months": 12,
}


@st.cache_data(ttl="1h", show_spinner=False)
def load_financial_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    end = pd.Timestamp.today().normalize().to_period("M")
    periods = pd.period_range(end - 11, end, freq="M")
    labels = [p.strftime("%b %Y") for p in periods]
    n = len(labels)

    income = [8200 + i * 260 + ((i * 3) % 4) * 150 for i in range(n)]
    expense = [6450 + ((i * 7) % 5) * 220 + ((i * 2) % 3) * 120 for i in range(n)]
    monthly_savings = [round(i - e, 2) for i, e in zip(income, expense)]

    cumulative = []
    running = 0.0
    for value in monthly_savings:
        running += value
        cumulative.append(round(running, 2))

    budget_used = [64 + (i * 5) % 14 for i in range(n)]
    pending_bills = [7, 6, 6, 5, 5, 4, 6, 5, 4, 5, 4, 5]
    investments = [
        22100,
        22800,
        23450,
        24100,
        23900,
        24750,
        25600,
        26300,
        25900,
        27100,
        27850,
        28600,
    ]

    monthly_df = pd.DataFrame(
        {
            "Month": labels,
            "Income": income,
            "Expense": expense,
            "Savings": monthly_savings,
            "Cumulative Savings": cumulative,
            "Budget Used": budget_used,
            "Pending Bills": pending_bills,
            "Investments": investments,
        }
    )

    category_df = pd.DataFrame(
        {
            "Category": [
                "Housing",
                "Groceries",
                "Transport",
                "Dining Out",
                "Utilities",
                "Health",
                "Entertainment",
                "Other",
            ],
            "Amount": [1850, 780, 320, 415, 290, 210, 245, 150],
        }
    )

    today = pd.Timestamp.today().normalize()
    tx_rows = [
        (0, "Coffee shop", "Dining Out", -8.50),
        (1, "Salary deposit", "Income", 4200.00),
        (2, "Grocery store", "Groceries", -96.20),
        (3, "Electricity bill", "Utilities", -74.80),
        (4, "Online subscription", "Entertainment", -15.99),
        (6, "Fuel station", "Transport", -52.40),
        (8, "Gym membership", "Health", -35.00),
        (10, "Freelance project", "Income", 850.00),
        (12, "Rent payment", "Housing", -1850.00),
        (14, "Phone bill", "Utilities", -42.50),
    ]
    transactions_df = pd.DataFrame(
        [
            {
                "Date": (today - pd.Timedelta(days=days)).date(),
                "Description": description,
                "Category": category,
                "Amount": amount,
            }
            for days, description, category, amount in tx_rows
        ]
    )

    return monthly_df, category_df, transactions_df


def pct_change(series: pd.Series) -> float:
    return (series.iloc[-1] / series.iloc[-2] - 1) * 100


def style_amount(value: float) -> str:
    color = COLORS["income"] if value >= 0 else COLORS["expense"]
    return f"color: {color}; font-weight: 600;"


def make_spending_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["Month"],
            y=df["Expense"],
            name="Spending",
            marker_color=COLORS["expense"],
            hovertemplate="%{x}<br>Spending: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["Month"],
            y=df["Income"],
            name="Income",
            mode="lines+markers",
            line=dict(color=COLORS["income"], width=2.5),
            marker=dict(size=6),
            hovertemplate="%{x}<br>Income: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def make_category_chart(category_df: pd.DataFrame, total: float) -> go.Figure:
    fig = px.pie(
        category_df,
        names="Category",
        values="Amount",
        hole=0.6,
        color_discrete_sequence=CATEGORY_COLORS,
    )
    fig.update_traces(
        textinfo="percent",
        hovertemplate="%{label}<br>$%{value:,.0f} (%{percent})<extra></extra>",
    )
    fig.update_layout(
        annotations=[
            dict(
                text=f"<b>${total:,.0f}</b><br>monthly spend",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=15),
            )
        ],
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def make_savings_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["Month"],
            y=df["Savings"],
            name="Monthly savings",
            marker_color=COLORS["savings"],
            opacity=0.55,
            hovertemplate="%{x}<br>Monthly savings: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["Month"],
            y=df["Cumulative Savings"],
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


monthly_df, category_df, transactions_df = load_financial_data()

st.title(":material/savings: AI Personal Finance Manager")
st.caption("A complete overview of your income, spending, savings, bills and investments.")

with st.sidebar:
    st.markdown("**Reporting period**")
    period = st.selectbox(
        "Period",
        list(PERIODS),
        index=1,
        label_visibility="collapsed",
    )

df = monthly_df.tail(PERIODS[period])

total_income = df["Income"].sum()
total_expense = df["Expense"].sum()
savings = total_income - total_expense

income_delta = pct_change(df["Income"])
expense_delta = pct_change(df["Expense"])
savings_delta = pct_change(df["Savings"])
budget_delta = df["Budget Used"].iloc[-1] - df["Budget Used"].iloc[-2]
bills_delta = df["Pending Bills"].iloc[-1] - df["Pending Bills"].iloc[-2]
investments_delta = pct_change(df["Investments"])

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        "Total income",
        f"${total_income:,.0f}",
        f"{income_delta:+.1f}% vs previous month",
        chart_data=df["Income"].tolist(),
        chart_type="line",
        border=True,
    )
with col2:
    st.metric(
        "Total expense",
        f"${total_expense:,.0f}",
        f"{expense_delta:+.1f}% vs previous month",
        delta_color="inverse",
        chart_data=df["Expense"].tolist(),
        chart_type="line",
        border=True,
    )
with col3:
    st.metric(
        "Savings",
        f"${savings:,.0f}",
        f"{savings_delta:+.1f}% vs previous month",
        chart_data=df["Savings"].tolist(),
        chart_type="line",
        border=True,
    )

col4, col5, col6 = st.columns(3)
with col4:
    st.metric(
        "Budget used",
        f"{df['Budget Used'].iloc[-1]:.0f}%",
        f"{budget_delta:+.0f} pts vs last month",
        delta_color="inverse",
        chart_data=df["Budget Used"].tolist(),
        chart_type="bar",
        border=True,
    )
with col5:
    st.metric(
        "Pending bills",
        str(df["Pending Bills"].iloc[-1]),
        f"{bills_delta:+d} vs last month",
        delta_color="inverse",
        chart_data=df["Pending Bills"].tolist(),
        chart_type="bar",
        border=True,
    )
with col6:
    st.metric(
        "Investments",
        f"${df['Investments'].iloc[-1]:,.0f}",
        f"{investments_delta:+.1f}% vs last month",
        chart_data=df["Investments"].tolist(),
        chart_type="line",
        border=True,
    )

st.space("small")

chart_col1, chart_col2 = st.columns(2, gap="large")
with chart_col1:
    with st.container(border=True):
        st.subheader("Monthly spending")
        st.plotly_chart(
            make_spending_chart(df),
            height=320,
            config={"displayModeBar": False},
        )
with chart_col2:
    with st.container(border=True):
        st.subheader("Expense categories")
        st.plotly_chart(
            make_category_chart(category_df, df["Expense"].iloc[-1]),
            height=320,
            config={"displayModeBar": False},
        )

chart_col3, chart_col4 = st.columns(2, gap="large")
with chart_col3:
    with st.container(border=True):
        st.subheader("Savings trend")
        st.plotly_chart(
            make_savings_chart(df),
            height=320,
            config={"displayModeBar": False},
        )
with chart_col4:
    with st.container(border=True):
        st.subheader("Recent transactions")
        styled_tx = transactions_df.style.map(style_amount, subset=["Amount"])
        st.dataframe(
            styled_tx,
            hide_index=True,
            column_config={
                "Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                "Amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
            },
        )

st.caption("Sample data for demonstration purposes.")
