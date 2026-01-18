from __future__ import annotations

import streamlit as st
import toml
import yfinance as yf


from core.data.ticker_resolver import TickerResolver
from database.sqlite_store import SQLiteStore, DBConfig
from core.data.universe_loader import UniverseLoader
from core.data.data_router import DataRouter, DataConfig
from core.execution.mock_broker import MockBroker
from core.execution.safety_guard import SafetyGuard, SafetyConfig
from core.ai.narrative_ai import NarrativeAI, OpenAIConfig

from interface.theme import apply_theme
from interface.components import tape_render
from interface.pages.deep_dive import render_deep_dive
from interface.pages.screener import render_screener
from interface.pages.ledger import render_ledger
from interface.pages.diagnostics import render_diagnostics
from interface.pages.glossary import render_glossary


def load_config(path: str = "config/config.toml"):
    return toml.load(path)

def main():
    st.set_page_config(page_title="ATLAS v6.0", page_icon="📟", layout="wide")
    apply_theme()

    cfg = load_config()

    store = SQLiteStore(DBConfig(path="atlas.db"))
    universe_loader = UniverseLoader(store)
    universe_df = universe_loader.load()

    broker = MockBroker()
    data_router = DataRouter(DataConfig(min_rows=int(cfg["data"]["min_rows"])))

    sh = cfg["market_hours"]
    safety_cfg = SafetyConfig(
        tz_market=str(sh["timezone"]),
        open_hhmm=str(sh["open"]),
        close_hhmm=str(sh["close"]),
        auction_pre_open_start=str(sh["auction_pre_open_start"]),
        auction_pre_open_end=str(sh["auction_pre_open_end"]),
        auction_close_start=str(sh["auction_close_start"]),
        auction_close_end=str(sh["auction_close_end"]),
        max_daily_loss_pct=float(cfg["risk"]["max_daily_loss_pct"]),
    )
    safety_guard = SafetyGuard(store, broker, safety_cfg)

    ocfg = cfg["openai"]
    ai = NarrativeAI(OpenAIConfig(
        enabled=bool(ocfg["enabled"]),
        model=str(ocfg["model"]),
        timeout_sec=int(ocfg["timeout_sec"]),
        max_output_tokens=int(ocfg["max_output_tokens"]),
    ))

    st.sidebar.subheader("CONTROL")
    profile_name = st.sidebar.selectbox("PROFILE", ["Trend", "MeanReversion", "Defensive"], index=0)
    profile_cfg = cfg["profiles"][profile_name]

    categories = sorted(universe_df["category"].unique().tolist())
    sel_cat = st.sidebar.selectbox("CLASS", categories, index=0)

    sub = universe_df[universe_df["category"] == sel_cat].copy()
    asset = st.sidebar.selectbox("ASSET", sub["name"].tolist(), index=0)

    row = sub[sub["name"] == asset].iloc[0].to_dict()
    ticker_raw = str(row["ticker_yahoo"]).strip()
    ticker = TickerResolver.resolve(ticker_raw, sel_cat) or ticker_raw

    priority_source = str(row.get("priority_source","")).strip()
    bridge_key = str(row.get("bridge_key","")).strip()

    if "tape_items" not in st.session_state:
        st.session_state["tape_items"] = []

    colA, colB = st.columns([3, 1])
    with colA:
        st.markdown("# ATLAS v6.0")
        st.markdown(f"<span class='small'>TICKER: <b style='color:var(--amber2)'>{ticker}</b> | CLASS: <b>{sel_cat}</b> | PROFILE: <b>{profile_name}</b></span>", unsafe_allow_html=True)
with colB:
    if st.button("F2 REFRESH TAPE"):
        items = []
        for t in list({ticker, "^BVSP", "BRL=X", "BTC-USD", "^GSPC"})[:6]:
            try:
                df = yf.download(
                    t,
                    period="10d",
                    interval="1d",
                    progress=False,
                    threads=False,
                    auto_adjust=False,
                )
                if df is None or df.empty:
                    continue

                col = "Adj Close" if "Adj Close" in df.columns else "Close"
                s = df[col].dropna()
                if len(s) < 2:
                    continue

                last = float(s.iloc[-1])
                prev = float(s.iloc[-2])
                chg = (last / (prev + 1e-9) - 1.0) * 100
                items.append({"ticker": t, "price": last, "chg_pct": chg})

            except Exception:
                continue

        st.session_state["tape_items"] = items


auto = st.toggle("AUTO TAPE", value=True)
refresh_sec = st.slider("REFRESH (s)", 5, 60, 15)

force = st.button("REFRESH NOW")

if auto or force:
    if "last_tape_refresh" not in st.session_state:
        st.session_state["last_tape_refresh"] = 0

    if force or (time.time() - st.session_state["last_tape_refresh"] >= refresh_sec):
        from yfinance import download
        items = []
        for t in list({ticker, "^BVSP", "BRL=X", "BTC-USD", "^GSPC"})[:6]:
            try:
                df = download(t, period="10d", interval="1d", progress=False, threads=False, auto_adjust=False)
                if df is None or df.empty:
                    continue
                col = "Adj Close" if "Adj Close" in df.columns else "Close"
                s = df[col].dropna()
                if len(s) < 2:
                    continue
                last = float(s.iloc[-1])
                prev = float(s.iloc[-2])
                chg = (last / (prev + 1e-9) - 1.0) * 100
                items.append({"ticker": t, "price": last, "chg_pct": chg})
            except Exception:
                continue

        st.session_state["tape_items"] = items
        st.session_state["last_tape_refresh"] = time.time()

            from yfinance import download
            items = []
            for t in list({ticker, "^BVSP", "BRL=X", "BTC-USD", "^GSPC"})[:6]:
                try:
                    df = download(t, period="10d", interval="1d", progress=False, threads=False, auto_adjust=False)
                    if df is None or df.empty:
                        continue
                    col = "Adj Close" if "Adj Close" in df.columns else "Close"
                    s = df[col].dropna()
                    if len(s) < 2:
                        continue
                    last = float(s.iloc[-1])
                    prev = float(s.iloc[-2])
                    chg = (last / (prev + 1e-9) - 1.0) * 100
                    items.append({"ticker": t, "price": last, "chg_pct": chg})
                except Exception:
                    continue
            st.session_state["tape_items"] = items

    tape_render(st.session_state["tape_items"])
    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["DEEP DIVE", "SCREENER", "LEDGER", "DIAGNOSTICS", "HELP"])


    ctx = {
        "config": cfg,
        "profile_name": profile_name,
        "profile_cfg": profile_cfg,
        "ticker": ticker,
        "priority_source": priority_source,
        "bridge_key": bridge_key,
        "data_router": data_router,
        "store": store,
        "broker": broker,
        "safety_guard": safety_guard,
        "ai": ai,
        "db_path": "atlas.db",
    }

    with tab1:
        render_deep_dive(ctx)
    with tab2:
        render_screener(ctx, universe_df)
    with tab3:
        render_ledger(store)
    with tab4:
        render_diagnostics(ctx)
    with tab5:
        render_glossary()


if __name__ == "__main__":
    main()
