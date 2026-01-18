from __future__ import annotations
import pandas as pd
import streamlit as st
from core.logic.indicators import IndicatorEngine

def render_screener(ctx, universe_df: pd.DataFrame):
    st.subheader("SCREENER (CONTROLLED)")
    st.caption("Rode apenas por amostra. Nunca no boot.")

    sample_n = st.slider("Sample size", 5, 50, 10)
    cat = st.selectbox("Categoria", sorted(universe_df["category"].unique().tolist()))

    sub = universe_df[universe_df["category"] == cat].head(sample_n).copy()
    if sub.empty:
        st.warning("EMPTY CATEGORY")
        return

    if st.button("RUN SCREENER"):
        out = []
        prog = st.progress(0)
        for i, (_, r) in enumerate(sub.iterrows()):
            t = str(r["ticker_yahoo"]).strip()
            df, _ = ctx["data_router"].fetch_prices(
                ticker=t,
                priority_source=str(r.get("priority_source","")),
                bridge_key=str(r.get("bridge_key",""))
            )
            if df is None or df.empty:
                prog.progress((i+1)/len(sub))
                continue
            d = IndicatorEngine.calculate(df)
            if d is None or d.empty:
                prog.progress((i+1)/len(sub))
                continue
            last = d.iloc[-1]
            out.append({
                "ticker": t,
                "px": float(last["close_final"]),
                "z": float(last["ZScore"]),
                "rsi": float(last["RSI14"]),
                "vol": float(last["VolAnn"]),
            })
            prog.progress((i+1)/len(sub))

        if not out:
            st.warning("NO RESULTS")
            return

        sdf = pd.DataFrame(out).sort_values("z")
        st.dataframe(sdf, use_container_width=True, height=520)
