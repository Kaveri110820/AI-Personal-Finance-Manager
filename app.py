import streamlit as st

st.set_page_config(
    page_title="AI Personal Finance Manager",
    page_icon=":material/savings:",
    layout="wide",
)

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
pg.run()
