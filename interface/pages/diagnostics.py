from __future__ import annotations
import streamlit as st

def render_diagnostics(ctx):
    st.subheader("DIAGNOSTICS")
    st.write({
        "app": ctx["config"]["app"],
        "cache": ctx["config"]["cache"],
        "db_path": ctx["db_path"],
        "broker": ctx["broker"].get_account_state(),
    })
