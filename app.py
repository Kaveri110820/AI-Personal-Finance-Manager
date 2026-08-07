import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pages.login import render_login
from services.auth_service import AuthService

st.set_page_config(
    page_title="AI Personal Finance Manager",
    page_icon=":material/savings:",
    layout="wide",
)

st.session_state.setdefault("auth_service", AuthService())
st.session_state.setdefault("authenticated", False)
st.session_state.setdefault("username", None)

auth = st.session_state.auth_service

if not st.session_state.authenticated:
    render_login(auth)
    st.stop()

PAGES = {
    "Overview": [
        st.Page(
            "pages/dashboard.py",
            title="Dashboard",
            icon=":material/dashboard:",
            default=True,
        ),
        st.Page("pages/analytics.py", title="Analytics", icon=":material/analytics:"),
    ],
    "Manage": [
        st.Page("pages/transactions.py", title="Transactions", icon=":material/receipt_long:"),
        st.Page("pages/budget.py", title="Budget", icon=":material/target:"),
        st.Page("pages/bills.py", title="Bills", icon=":material/calendar_month:"),
    ],
    "Invest & Track": [
        st.Page("pages/investments.py", title="Investments", icon=":material/trending_up:"),
        st.Page("pages/reports.py", title="Reports", icon=":material/bar_chart:"),
        st.Page("pages/ai_advisor.py", title="AI Advisor", icon=":material/psychology:"),
    ],
    "Data & Settings": [
        st.Page("pages/upload.py", title="Upload", icon=":material/upload_file:"),
        st.Page("pages/settings.py", title="Settings", icon=":material/settings:"),
    ],
}

pg = st.navigation(PAGES, expanded=True)

with st.sidebar:
    st.caption(f"Signed in as **{st.session_state.username}**")
    if st.button(
        "Logout",
        icon=":material/logout:",
        key="logout_btn",
        width="stretch",
    ):
        st.session_state.pop("authenticated", None)
        st.session_state.pop("username", None)
        st.rerun()
    st.divider()

pg.run()
