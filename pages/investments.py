import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.investment_service import INVESTMENT_TYPES, InvestmentService

ALLOCATION_COLORS = [
    "#60A5FA",
    "#34D399",
    "#A78BFA",
    "#FBBF24",
    "#F87171",
]


def _on_investment_action():
    click = st.session_state.get("inv_actions")
    if not click:
        return
    display = st.session_state.get("inv_display")
    row = click.get("row")
    if display is None or row is None or row >= len(display):
        return
    investment_id = int(display.iloc[row]["id"])
    label = str(click.get("label") or "")
    if "Edit" in label:
        st.session_state.inv_edit_id = investment_id
        for key in ("inv_name", "inv_type", "inv_amount"):
            st.session_state.pop(key, None)
    elif "Delete" in label:
        st.session_state.inv_pending_delete = investment_id
        st.session_state.inv_pending_delete_name = str(display.iloc[row]["name"])


def _cancel_edit():
    st.session_state.pop("inv_edit_id", None)
    for key in ("inv_name", "inv_type", "inv_amount"):
        st.session_state.pop(key, None)


def _make_allocation_chart(allocation: pd.DataFrame, total: float) -> object:
    if allocation.empty:
        return None
    fig = px.pie(
        allocation,
        names="investment_type",
        values="amount",
        hole=0.6,
        color_discrete_sequence=ALLOCATION_COLORS,
    )
    fig.update_traces(
        textinfo="percent",
        hovertemplate="%{label}<br>$%{value:,.2f} (%{percent})<extra></extra>",
    )
    fig.update_layout(
        annotations=[
            dict(
                text=f"<b>${total:,.2f}</b><br>total invested",
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


st.session_state.setdefault("investment_service", InvestmentService())
st.session_state.setdefault("inv_edit_id", None)
st.session_state.setdefault("inv_pending_delete", None)
st.session_state.setdefault("inv_pending_delete_name", None)

service = st.session_state.investment_service

st.title(":material/trending_up: Investment Tracker")
st.caption("Track your holdings across stocks, mutual funds, gold, fixed deposits and crypto.")

investments = service.get_investments()
total = service.get_total()
stats = service.get_stats()
allocation = service.get_allocation()

with st.container(horizontal=True):
    st.metric("Total invested", f"${total:,.2f}", border=True)
    st.metric("Investments", f"{stats['count']:,}", border=True)
    if not allocation.empty:
        st.metric(
            "Top allocation",
            allocation.iloc[0]["investment_type"],
            delta=f"{allocation.iloc[0]['percent']:.0f}% of portfolio",
            border=True,
        )

st.space("small")

if investments.empty:
    st.info(
        "No investments yet. Add a stock, mutual fund, gold holding, fixed deposit "
        "or crypto position below to start tracking your portfolio.",
        icon=":material/trending_up:",
    )
else:
    chart_col, table_col = st.columns([2, 1], gap="large")
    with chart_col:
        with st.container(border=True):
            st.subheader("Portfolio allocation")
            st.plotly_chart(
                _make_allocation_chart(allocation, total),
                height=360,
                config={"displayModeBar": False},
            )
    with table_col:
        with st.container(border=True):
            st.subheader("By type")
            breakdown = allocation[["investment_type", "amount", "percent"]].copy()
            breakdown.columns = ["Type", "Amount", "Share"]
            st.dataframe(
                breakdown,
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

    display = investments[["id", "name", "investment_type", "amount"]].copy()
    display["actions"] = [
        [":material/edit: Edit", ":material/delete: Delete"] for _ in range(len(display))
    ]
    st.session_state.inv_display = display
    st.dataframe(
        display,
        hide_index=True,
        key="inv_table",
        column_config={
            "id": None,
            "name": st.column_config.TextColumn("Name", width="medium"),
            "investment_type": st.column_config.TextColumn("Type"),
            "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
            "actions": st.column_config.ButtonColumn(
                "Actions",
                on_click=_on_investment_action,
                key="inv_actions",
                type="tertiary",
                alignment="center",
            ),
        },
    )

st.space("small")

with st.container(border=True):
    editing = None
    if st.session_state.get("inv_edit_id"):
        editing = service.get_investment(st.session_state.get("inv_edit_id"))
    if editing:
        st.markdown(f"**Edit investment** — {editing['name']}")
    else:
        st.markdown("**Add an investment**")
    with st.form("investment_form"):
        col1, col2, col3 = st.columns([2, 1, 1])
        name_default = editing["name"] if editing else ""
        name = col1.text_input("Investment name", value=name_default, key="inv_name")
        type_index = 0
        if editing and editing["investment_type"] in INVESTMENT_TYPES:
            type_index = INVESTMENT_TYPES.index(editing["investment_type"])
        investment_type = col2.selectbox(
            "Type",
            INVESTMENT_TYPES,
            index=type_index,
            key="inv_type",
        )
        amount_default = editing["amount"] if editing else 0.0
        amount = col3.number_input(
            "Amount ($)",
            min_value=0.0,
            max_value=1_000_000_000.0,
            step=100.0,
            value=amount_default,
            key="inv_amount",
        )
        submitted = st.form_submit_button(
            "Save investment",
            type="primary",
            icon=":material/save:",
            key="inv_submit",
            width="stretch",
        )

    if editing and st.button(
        "Cancel editing",
        icon=":material/close:",
        on_click=_cancel_edit,
        key="inv_cancel_edit",
    ):
        st.rerun()

    if submitted:
        if not name.strip():
            st.error("Enter an investment name.", icon=":material/error:")
        elif amount <= 0:
            st.error("Enter an amount greater than zero.", icon=":material/error:")
        elif editing:
            if service.update_investment(
                editing["id"], name, investment_type, amount
            ):
                st.toast(
                    f"Investment “{name.strip()}” updated", icon=":material/check_circle:"
                )
            st.session_state.pop("inv_edit_id", None)
            for key in ("inv_name", "inv_type", "inv_amount"):
                st.session_state.pop(key, None)
            st.rerun()
        else:
            service.add_investment(name, investment_type, amount)
            st.toast(
                f"Investment “{name.strip()}” added", icon=":material/check_circle:"
            )
            st.rerun()

st.space("small")

pending_delete = st.session_state.get("inv_pending_delete")
if pending_delete:
    name = st.session_state.get("inv_pending_delete_name", "this investment")
    st.warning(
        f"**Delete investment** — “{name}”? This cannot be undone.",
        icon=":material/delete:",
    )
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button(
            "Delete",
            type="primary",
            icon=":material/delete:",
            key="inv_confirm_delete",
        ):
            if service.delete_investment(int(pending_delete)):
                st.toast("Investment deleted", icon=":material/check_circle:")
            st.session_state.inv_pending_delete = None
            st.session_state.inv_pending_delete_name = None
            st.rerun()
        if st.button("Cancel", key="inv_cancel_delete"):
            st.session_state.inv_pending_delete = None
            st.session_state.inv_pending_delete_name = None
            st.rerun()

st.caption(
    "Investments are stored locally in SQLite. The allocation chart groups your "
    "holdings by type and shows the share of your total portfolio."
)
