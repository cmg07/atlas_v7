from __future__ import annotations
import pandas as pd
import streamlit as st

def render_ledger(store):
    st.subheader("LEDGER (SQLite)")
    rows = store.read_ledger(limit=300)
    if not rows:
        st.info("EMPTY")
        return
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, height=520)
