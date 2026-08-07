from pathlib import Path

import streamlit as st

APP_VERSION = "1.0.0"

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "finance.db"

CURRENCIES = {
    "INR": {"symbol": "₹", "name": "Indian Rupee"},
    "USD": {"symbol": "$", "name": "US Dollar"},
    "EUR": {"symbol": "€", "name": "Euro"},
}

THEMES = ["Light", "Dark"]


def format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    return f"{size_bytes / 1024:.0f} KB"


def get_db_size() -> str:
    if DB_PATH.exists():
        return format_size(DB_PATH.stat().st_size)
    return "Not available"


st.title(":material/settings: Settings")
st.caption("Customize your preferences. Settings are saved locally and applied app-wide.")

st.space("small")

pref_col, sys_col = st.columns([3, 2], gap="large")

with pref_col:
    with st.container(border=True):
        st.markdown("### :material/palette: Appearance")
        theme_col, currency_col = st.columns(2)
        with theme_col:
            theme = st.segmented_control(
                "Theme",
                options=THEMES,
                default="Dark",
                key="settings_theme",
                help="Placeholder — theme switching is not wired up yet. The app currently uses the dark theme.",
            )
        with currency_col:
            currency = st.segmented_control(
                "Default currency",
                options=list(CURRENCIES),
                default="INR",
                format_func=lambda code: f"{CURRENCIES[code]['symbol']} {code}",
                key="settings_currency",
                help="Used as the default display currency for the app.",
            )
        if theme == "Light":
            st.caption("Light theme is selected, but is not implemented yet.")

    with st.container(border=True):
        st.markdown("### :material/tune: Budget & notifications")
        budget_col, notif_col = st.columns(2)
        with budget_col:
            st.number_input(
                f"Monthly budget default ({CURRENCIES[currency]['symbol']})",
                min_value=0,
                value=50000,
                step=1000,
                key="settings_budget",
                help="Default monthly budget used when creating a new budget.",
            )
        with notif_col:
            st.toggle(
                "Bill reminder notifications",
                value=True,
                key="settings_notifications",
                help="Placeholder — notifications are not implemented yet.",
            )

with sys_col:
    with st.container(border=True):
        st.markdown("### :material/auto_awesome: Google AI Studio")
        st.badge("Not configured", icon=":material/schedule:", color="orange")
        st.space("small")
        st.caption(
            "Connect a Gemini API key to enable AI categorization and smart advice. "
            "Placeholder — no API checks are performed yet."
        )

    with st.container(border=True):
        st.markdown("### :material/database: Database")
        st.metric("Engine", "SQLite", border=True)
        st.metric("File size", get_db_size(), border=True)
        st.caption(str(DB_PATH))
        st.caption("All transactions are stored locally. This is informational only.")

    with st.container(border=True):
        st.markdown("### :material/info: About")
        st.metric("App version", APP_VERSION, border=True)

st.space("small")

save_col, _ = st.columns([1, 2])
with save_col:
    if st.button(
        "Save settings",
        type="primary",
        icon=":material/save:",
        key="settings_save_btn",
        width="stretch",
    ):
        st.success(
            "Settings saved.",
            icon=":material/check_circle:",
        )
        st.caption("This is a placeholder — nothing is persisted to the database yet.")
