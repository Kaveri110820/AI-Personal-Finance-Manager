import streamlit as st

from services.auth_service import AuthService


def render_login(auth: AuthService) -> None:
    _, center, _ = st.columns([1, 2.2, 1])
    with center:
        st.space("large")
        with st.container(border=True):
            st.markdown(
                "<div style='text-align:center;font-size:52px;line-height:1.1;'>"
                ":material/savings:</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<h1 style='text-align:center;margin:0;'>AI Personal Finance Manager</h1>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p style='text-align:center;'>Sign in to manage your income, spending, "
                "budgets, bills and investments.</p>",
                unsafe_allow_html=True,
            )

            if not auth.has_users():
                st.info(
                    "No account yet — create the first account below to get started.",
                    icon=":material/info:",
                )

            sign_in_tab, register_tab = st.tabs(
                [":material/login: Sign in", ":material/person_add: Create account"]
            )

            with sign_in_tab:
                with st.form("login_form"):
                    username = st.text_input(
                        "Username", key="login_user", autocomplete="username"
                    )
                    password = st.text_input(
                        "Password",
                        type="password",
                        key="login_pw",
                        autocomplete="current-password",
                    )
                    submitted = st.form_submit_button(
                        "Sign in",
                        type="primary",
                        icon=":material/login:",
                        width="stretch",
                        key="login_submit",
                    )
                if submitted:
                    if auth.authenticate(username, password):
                        st.session_state.authenticated = True
                        st.session_state.username = str(username).strip()
                        st.toast(
                            f"Welcome back, {str(username).strip()}!",
                            icon=":material/check_circle:",
                        )
                        st.rerun()
                    else:
                        st.error(
                            "Invalid username or password.",
                            icon=":material/error:",
                        )

            with register_tab:
                with st.form("register_form"):
                    reg_username = st.text_input(
                        "Username",
                        key="reg_user",
                        autocomplete="username",
                        help="3–32 characters using letters, numbers, . _ or -.",
                    )
                    reg_password = st.text_input(
                        "Password",
                        type="password",
                        key="reg_pw",
                        autocomplete="new-password",
                        help="At least 4 characters.",
                    )
                    reg_confirm = st.text_input(
                        "Confirm password",
                        type="password",
                        key="reg_pw2",
                        autocomplete="new-password",
                    )
                    submitted_reg = st.form_submit_button(
                        "Create account",
                        type="primary",
                        icon=":material/person_add:",
                        width="stretch",
                        key="register_submit",
                    )
                if submitted_reg:
                    if reg_password != reg_confirm:
                        st.error(
                            "Passwords do not match.", icon=":material/error:"
                        )
                    else:
                        ok, message = auth.register(reg_username, reg_password)
                        if ok:
                            st.session_state.authenticated = True
                            st.session_state.username = str(reg_username).strip()
                            st.toast(
                                f"Account created — welcome, {str(reg_username).strip()}!",
                                icon=":material/check_circle:",
                            )
                            st.rerun()
                        else:
                            st.error(message, icon=":material/error:")

        st.space("large")
        st.caption("Passwords are hashed with PBKDF2-SHA256 and stored locally in SQLite.")
