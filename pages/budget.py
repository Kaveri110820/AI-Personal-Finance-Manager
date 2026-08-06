import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ai_service import CATEGORIES
from services.budget_service import BudgetService

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


def _on_budget_action():
    click = st.session_state.get("bdg_actions")
    if not click:
        return
    display = st.session_state.get("bdg_display")
    row = click.get("row")
    if display is None or row is None or row >= len(display):
        return
    budget_id = int(display.iloc[row]["id"])
    label = str(click.get("label") or "")
    if "Edit" in label:
        st.session_state.bdg_edit_id = budget_id
        for key in ("bdg_scope", "bdg_category", "bdg_amount"):
            st.session_state.pop(key, None)
    elif "Delete" in label:
        st.session_state.bdg_pending_delete = budget_id
        st.session_state.bdg_pending_delete_name = str(display.iloc[row]["name"])


def _cancel_edit():
    st.session_state.pop("bdg_edit_id", None)
    for key in ("bdg_scope", "bdg_category", "bdg_amount"):
        st.session_state.pop(key, None)


st.session_state.setdefault("budget_service", BudgetService())
st.session_state.setdefault("bdg_edit_id", None)
st.session_state.setdefault("bdg_pending_delete", None)
st.session_state.setdefault("bdg_pending_delete_name", None)

service = st.session_state.budget_service

st.title(":material/target: Budget Planner")
st.caption("Set monthly and category budgets, track spending against them and catch overspending before it happens.")

today = dt.date.today()
year_options = list(range(today.year - 2, today.year + 2))
with st.sidebar:
    st.markdown("### Budget month")
    month_name = st.selectbox(
        "Month",
        MONTH_NAMES,
        index=today.month - 1,
        key="bdg_month",
    )
    year = st.selectbox(
        "Year",
        year_options,
        index=year_options.index(today.year),
        key="bdg_year",
    )
month = MONTH_NAMES.index(month_name) + 1
month_label = f"{month_name} {year}"

monthly_budget = service.get_monthly_budget()
total_spent = service.get_total_spent(year, month)
overview = service.get_overview(year, month)
category_count = int((overview["scope"] == "category").sum()) if not overview.empty else 0

warnings = []
if monthly_budget and total_spent > monthly_budget["amount"]:
    warnings.append(
        f"The monthly budget of **${monthly_budget['amount']:,.2f}** has been exceeded "
        f"by **${total_spent - monthly_budget['amount']:,.2f}**."
    )
if not overview.empty:
    for _, row in overview[overview["overspent"]].iterrows():
        if row["scope"] == "category":
            warnings.append(
                f"**{row['name']}** is over budget by **${-row['remaining']:,.2f}** "
                f"(spent ${row['spent']:,.2f} of ${row['amount']:,.2f})."
            )
if warnings:
    st.warning("\n\n".join(f"- {w}" for w in warnings), icon=":material/warning:")

with st.container(horizontal=True):
    st.metric(
        "Monthly budget",
        f"${monthly_budget['amount']:,.2f}" if monthly_budget else "Not set",
        border=True,
    )
    st.metric(f"Spent in {month_label}", f"${total_spent:,.2f}", border=True)
    if monthly_budget:
        remaining = monthly_budget["amount"] - total_spent
        st.metric(
            "Remaining",
            f"${remaining:,.2f}",
            delta=f"{remaining / monthly_budget['amount']:.0%} of budget",
            delta_color="inverse" if remaining < 0 else "normal",
            border=True,
        )
    st.metric("Category budgets", f"{category_count}", border=True)

st.space("small")

if overview.empty:
    st.info(
        "No budgets set yet. Add a monthly total or a per-category budget below to start tracking.",
        icon=":material/target:",
    )
else:
    display = overview[["id", "name", "amount", "spent", "remaining", "percent"]].copy()
    display["actions"] = [
        [":material/edit: Edit", ":material/delete: Delete"] for _ in range(len(display))
    ]
    st.session_state.bdg_display = display
    st.dataframe(
        display,
        hide_index=True,
        key="bdg_table",
        column_config={
            "id": None,
            "name": st.column_config.TextColumn("Budget", width="medium"),
            "amount": st.column_config.NumberColumn("Limit", format="$%.2f"),
            "spent": st.column_config.NumberColumn("Spent", format="$%.2f"),
            "remaining": st.column_config.NumberColumn("Remaining", format="$%.2f"),
            "percent": st.column_config.ProgressColumn("Used", min_value=0, max_value=100),
            "actions": st.column_config.ButtonColumn(
                "Actions",
                on_click=_on_budget_action,
                key="bdg_actions",
                type="tertiary",
                alignment="center",
            ),
        },
    )

st.space("small")

with st.container(border=True):
    editing = None
    if st.session_state.get("bdg_edit_id"):
        editing = service.get_budget(st.session_state.get("bdg_edit_id"))
    if editing:
        editing_name = editing["category"] or "Monthly total"
        st.markdown(f"**Edit budget** — {editing_name}")
    else:
        st.markdown("**Add a budget**")
    with st.form("budget_form"):
        col1, col2, col3 = st.columns([1, 1, 1])
        scope_index = 0 if (editing and editing["scope"] == "category") else 1
        scope = col1.selectbox(
            "Scope",
            ["Category", "Monthly total"],
            index=scope_index,
            key="bdg_scope",
        )
        amount_default = editing["amount"] if editing else 0.0
        if scope == "Category":
            cat_index = 0
            if editing and editing["category"] in CATEGORIES:
                cat_index = CATEGORIES.index(editing["category"])
            category = col2.selectbox(
                "Category",
                CATEGORIES,
                index=cat_index,
                key="bdg_category",
            )
        else:
            category = None
        amount = col3.number_input(
            "Amount ($)",
            min_value=0.0,
            max_value=1_000_000_000.0,
            step=10.0,
            value=amount_default,
            key="bdg_amount",
        )
        submitted = st.form_submit_button(
            "Save budget",
            type="primary",
            icon=":material/save:",
            key="bdg_submit",
            width="stretch",
        )

    if editing and st.button(
        "Cancel editing",
        icon=":material/close:",
        on_click=_cancel_edit,
        key="bdg_cancel_edit",
    ):
        st.rerun()

    if submitted:
        if amount <= 0:
            st.error("Enter a budget amount greater than zero.", icon=":material/error:")
        elif editing:
            if service.update_budget(editing["id"], amount):
                st.toast(f"Budget updated to ${amount:,.2f}", icon=":material/check_circle:")
            st.session_state.pop("bdg_edit_id", None)
            for key in ("bdg_scope", "bdg_category", "bdg_amount"):
                st.session_state.pop(key, None)
            st.rerun()
        elif scope == "Monthly total":
            service.add_monthly_budget(amount)
            st.toast(f"Monthly budget set to ${amount:,.2f}", icon=":material/check_circle:")
            st.rerun()
        else:
            service.add_category_budget(category, amount)
            st.toast(f"{category} budget set to ${amount:,.2f}", icon=":material/check_circle:")
            st.rerun()

st.space("small")

pending_delete = st.session_state.get("bdg_pending_delete")
if pending_delete:
    name = st.session_state.get("bdg_pending_delete_name", "this budget")
    st.warning(
        f"**Delete budget** — “{name}”? This cannot be undone.",
        icon=":material/delete:",
    )
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Delete", type="primary", icon=":material/delete:", key="bdg_confirm_delete"):
            if service.delete_budget(int(pending_delete)):
                st.toast("Budget deleted", icon=":material/check_circle:")
            st.session_state.bdg_pending_delete = None
            st.session_state.bdg_pending_delete_name = None
            st.rerun()
        if st.button("Cancel", key="bdg_cancel_delete"):
            st.session_state.bdg_pending_delete = None
            st.session_state.bdg_pending_delete_name = None
            st.rerun()

st.caption(
    "Budgets are monthly and stored in SQLite. Spending is calculated from transactions with "
    "negative amounts in the selected month."
)
