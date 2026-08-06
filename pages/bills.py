import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.bill_service import BillService

WINDOW_OPTIONS = [7, 14, 30, 60, 90]


def _on_bill_action():
    click = st.session_state.get("bll_actions")
    if not click:
        return
    display = st.session_state.get("bll_display")
    row = click.get("row")
    if display is None or row is None or row >= len(display):
        return
    bill_id = int(display.iloc[row]["id"])
    label = str(click.get("label") or "")
    if "Edit" in label:
        st.session_state.bll_edit_id = bill_id
        for key in ("bll_name", "bll_due_date", "bll_amount", "bll_status"):
            st.session_state.pop(key, None)
    elif "Delete" in label:
        st.session_state.bll_pending_delete = bill_id
        st.session_state.bll_pending_delete_name = str(display.iloc[row]["name"])


def _cancel_edit():
    st.session_state.pop("bll_edit_id", None)
    for key in ("bll_name", "bll_due_date", "bll_amount", "bll_status"):
        st.session_state.pop(key, None)


st.session_state.setdefault("bill_service", BillService())
st.session_state.setdefault("bll_edit_id", None)
st.session_state.setdefault("bll_pending_delete", None)
st.session_state.setdefault("bll_pending_delete_name", None)

service = st.session_state.bill_service

st.title(":material/calendar_month: Bill reminder")
st.caption("Track recurring bills, see what is due today, and never miss a payment again.")

today = dt.date.today()

with st.sidebar:
    st.markdown("### Reminder window")
    window = st.selectbox(
        "Show bills due within",
        WINDOW_OPTIONS,
        index=WINDOW_OPTIONS.index(30),
        key="bll_window",
        format_func=lambda value: f"{value} days",
    )
    st.caption(
        "The table below lists pending bills due today, overdue, or within the "
        "selected window. Mark bills as paid to clear them from reminders."
    )

stats = service.get_stats()
due_today = service.get_due_today()
overdue = service.get_overdue()
upcoming = service.get_upcoming(window)

with st.container(horizontal=True):
    st.metric("Due today", f"{len(due_today):,}", border=True)
    st.metric(
        "Overdue",
        f"{len(overdue):,}",
        delta=f"${overdue['amount'].sum():,.2f}" if not overdue.empty else "",
        delta_color="inverse",
        border=True,
    )
    st.metric(
        f"Next {window} days",
        f"{len(upcoming):,}",
        delta=f"${upcoming['amount'].sum():,.2f}" if not upcoming.empty else "",
        border=True,
    )
    st.metric("Pending bills", f"{stats['pending']:,}", border=True)

if not overdue.empty:
    total = overdue["amount"].sum()
    st.warning(
        f"**{len(overdue):,} bill{'s' if len(overdue) != 1 else ''} overdue** — "
        f"totalling **${total:,.2f}**. Catch up on payments as soon as possible.",
        icon=":material/error:",
    )

st.space("small")

if stats["total"] == 0:
    st.info(
        "No bills yet. Add your recurring bills below to start tracking due dates "
        "and amounts.",
        icon=":material/calendar_month:",
    )
else:
    reminders = service.get_reminders(window)
    if reminders.empty:
        st.success(
            "No pending bills in the reminder window. Add a bill below or widen the "
            "window from the sidebar.",
            icon=":material/check_circle:",
        )
    else:
        display = reminders[["id", "name", "due_date", "amount", "status"]].copy()
        display["due_date"] = pd.to_datetime(display["due_date"]).dt.date
        display["actions"] = [
            [":material/edit: Edit", ":material/delete: Delete"] for _ in range(len(display))
        ]
        st.session_state.bll_display = display
        st.data_editor(
            display,
            hide_index=True,
            key="bll_editor",
            on_change="rerun",
            disabled=["id", "name", "due_date", "amount"],
            column_config={
                "id": None,
                "name": st.column_config.TextColumn("Bill", width="medium"),
                "due_date": st.column_config.DateColumn("Due date", format="DD MMM YYYY"),
                "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                "status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["pending", "paid"],
                    required=True,
                    help="Mark a bill as paid to remove it from reminders.",
                ),
                "actions": st.column_config.ButtonColumn(
                    "Actions",
                    on_click=_on_bill_action,
                    key="bll_actions",
                    type="tertiary",
                    alignment="center",
                ),
            },
        )
        st.caption(
            "Tip: change a status to **paid** directly in the table. Edit or delete "
            "bills from the actions column."
        )

        editor_state = st.session_state.get("bll_editor") or {}
        edited_rows = editor_state.get("edited_rows") or {}
        if edited_rows:
            changed = 0
            for row_index, changes in edited_rows.items():
                if "status" in changes:
                    bill_id = int(display.iloc[int(row_index)]["id"])
                    if service.set_status(bill_id, str(changes["status"])):
                        changed += 1
            if changed:
                st.toast(
                    f"Updated {changed} bill{'s' if changed != 1 else ''}",
                    icon=":material/check_circle:",
                )

st.space("small")

with st.container(border=True):
    editing = None
    if st.session_state.get("bll_edit_id"):
        editing = service.get_bill(st.session_state.get("bll_edit_id"))
    if editing:
        st.markdown(f"**Edit bill** — {editing['name']}")
    else:
        st.markdown("**Add a bill**")
    with st.form("bill_form"):
        col1, col2, col3 = st.columns([2, 1, 1])
        name_default = editing["name"] if editing else ""
        name = col1.text_input("Bill name", value=name_default, key="bll_name")
        due_default = dt.date.fromisoformat(editing["due_date"]) if editing else today
        due_date = col2.date_input("Due date", value=due_default, key="bll_due_date")
        amount_default = editing["amount"] if editing else 0.0
        amount = col3.number_input(
            "Amount ($)",
            min_value=0.0,
            max_value=1_000_000_000.0,
            step=10.0,
            value=amount_default,
            key="bll_amount",
        )
        status_index = 1 if (editing and editing["status"] == "paid") else 0
        status = st.selectbox(
            "Status",
            ["pending", "paid"],
            index=status_index,
            key="bll_status",
        )
        submitted = st.form_submit_button(
            "Save bill",
            type="primary",
            icon=":material/save:",
            key="bll_submit",
            width="stretch",
        )

    if editing and st.button(
        "Cancel editing",
        icon=":material/close:",
        on_click=_cancel_edit,
        key="bll_cancel_edit",
    ):
        st.rerun()

    if submitted:
        if not name.strip():
            st.error("Enter a bill name.", icon=":material/error:")
        elif amount <= 0:
            st.error("Enter an amount greater than zero.", icon=":material/error:")
        elif editing:
            if service.update_bill(
                editing["id"], name, due_date.isoformat(), amount, status
            ):
                st.toast(f"Bill “{name.strip()}” updated", icon=":material/check_circle:")
            st.session_state.pop("bll_edit_id", None)
            for key in ("bll_name", "bll_due_date", "bll_amount", "bll_status"):
                st.session_state.pop(key, None)
            st.rerun()
        else:
            service.add_bill(name, due_date.isoformat(), amount, status)
            st.toast(f"Bill “{name.strip()}” added", icon=":material/check_circle:")
            st.rerun()

st.space("small")

pending_delete = st.session_state.get("bll_pending_delete")
if pending_delete:
    name = st.session_state.get("bll_pending_delete_name", "this bill")
    st.warning(
        f"**Delete bill** — “{name}”? This cannot be undone.",
        icon=":material/delete:",
    )
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Delete", type="primary", icon=":material/delete:", key="bll_confirm_delete"):
            if service.delete_bill(int(pending_delete)):
                st.toast("Bill deleted", icon=":material/check_circle:")
            st.session_state.bll_pending_delete = None
            st.session_state.bll_pending_delete_name = None
            st.rerun()
        if st.button("Cancel", key="bll_cancel_delete"):
            st.session_state.bll_pending_delete = None
            st.session_state.bll_pending_delete_name = None
            st.rerun()

st.caption(
    "Bills are stored locally in SQLite. Reminders cover bills due today, overdue "
    "bills, and bills due within the selected window."
)
