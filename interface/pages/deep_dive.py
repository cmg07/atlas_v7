from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import pytz

from core.logic.indicators import IndicatorEngine
from core.logic.costs import CostEngine
from core.logic.regimes import RegimeEngine
from core.logic.scores import ScoreEngine
from core.logic.risk import RiskEngine
from core.logic.verdict import VerdictEngine
from core.execution.models import OrderIntent

def _plot_candles(d: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=d.index,
        open=d["open"], high=d["high"], low=d["low"], close=d["close_final"],
        name="PX",
    ))
    fig.add_trace(go.Scatter(x=d.index, y=d["SMA20"], name="SMA20", opacity=0.85))
    fig.add_trace(go.Scatter(x=d.index, y=d["SMA50"], name="SMA50", opacity=0.65))
    fig.update_layout(template="plotly_dark", height=560, xaxis_rangeslider_visible=False, margin=dict(l=8,r=8,t=8,b=8))
    return fig

def _to_local_ui(ts_utc_index: pd.DatetimeIndex, tz_ui: str) -> pd.DatetimeIndex:
    tz = pytz.timezone(tz_ui)
    return ts_utc_index.tz_convert(tz)

def render_deep_dive(ctx: Dict[str, Any]):
    st.subheader("DEEP DIVE — 1 ASSET MODE")

    ticker = ctx["ticker"]
    priority_source = ctx.get("priority_source", "")
    bridge_key = ctx.get("bridge_key", "")

    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.caption("COST (bps)")
        spread = st.number_input("SPREAD (bps)", 0, 200, 5, help="Spread = custo implícito entre bid/ask. Quanto maior, mais edge você precisa.")
slippage = st.number_input("SLIPPAGE (bps)", 0, 200, 5, help="Slippage = pior execução real vs preço teórico. Aumenta em baixa liquidez/volatilidade.")
fee = st.number_input("FEE (bps)", 0, 200, 2, help="Fee = comissão da corretora + emolumentos. Some no custo total do trade.")


    with col2:
        st.caption("RISK INPUTS")
        win = st.slider("WIN %", 30, 70, 45) / 100.0
        payoff = st.slider("PAYOFF (R)", 1.0, 5.0, 2.0)
        risk_pct = st.slider("RISK/TRD %", 0.5, 5.0, 2.0)
        capital = st.number_input("CAPITAL", min_value=100.0, value=float(ctx["config"]["risk"]["default_capital"]), step=500.0)

    if st.button("ANALYZE", type="primary"):
        prof = ctx["profile_cfg"]
        max_cost_block = int(prof["max_cost_block_bps"])
        cost = CostEngine.compute(spread, slippage, fee, max_cost_block)

        df, dbg = ctx["data_router"].fetch_prices(
            ticker=ticker,
            priority_source=priority_source,
            bridge_key=bridge_key,
        )
        if df is None or df.empty:
            st.error("NO DATA")
            with st.expander("DEBUG"):
                st.json(dbg)
            return

        d = IndicatorEngine.calculate(df)
        if d is None or d.empty:
            st.error("INDICATORS_FAIL")
            with st.expander("DEBUG"):
                st.json(dbg)
            return

        last = d.iloc[-1]
        prev = d.iloc[-2]
        px = float(last["close_final"])
        chg_pct = float((px / (float(prev["close_final"]) + 1e-9) - 1.0) * 100)

        reg = RegimeEngine.analyze(d, cost["total_bps"])
        weights = {"trend": 0.50, "meanrev": 0.15, "risk": 0.35}
        mf = ScoreEngine.multi(d, last, cost["total_bps"], reg["label"], weights)

        risk_eff = min(float(risk_pct), float(prof["risk_cap_pct"]))
        ruin = RiskEngine.monte_carlo_ruin(win, payoff, risk_eff / 100.0)

        verdict = VerdictEngine.decide(
            regime=reg,
            cost=cost,
            ruin_pct=ruin,
            score=mf["final_score"],
            strict_vol=float(prof["strict_vol"]),
            strict_dd_pct=float(prof["strict_dd_pct"]),
            ruin_threshold=float(ctx["config"]["risk"]["ruin_threshold_pct"]),
        )

        d_ui = d.copy()
        d_ui.index = _to_local_ui(d.index, ctx["config"]["app"]["timezone_ui"])

        st.plotly_chart(_plot_candles(d_ui.tail(280)), use_container_width=True)

        st.markdown(f"**PX_LAST:** `{px:.2f}`  |  **CHG%:** `{chg_pct:+.2f}%`  |  **REGIME:** `{reg['label']}`  |  **SCORE:** `{mf['final_score']}`")
        st.markdown(f"**COST:** `{cost['total_bps']} bps`  |  **RUIN:** `{ruin:.2f}%`  |  **COMMAND:** `{verdict['command']}`")

        technical_json = {
            "ticker": ticker,
            "price": px,
            "chg_pct": chg_pct,
            "regime": reg,
            "score": mf,
            "cost": cost,
            "ruin": ruin,
            "verdict": verdict,
            "last_metrics": {
                "ATR14": float(last["ATR14"]),
                "ZScore": float(last["ZScore"]),
                "RSI14": float(last["RSI14"]),
                "VolAnn": float(last["VolAnn"]),
                "Drawdown": float(last["Drawdown"]),
            },
        }

        ai_out = ctx["ai"].generate(technical_json)
        st.markdown("### AI (OpenAI)")
        st.code(ai_out["analysis"])

        st.markdown("---")
        st.markdown("### ORDER TICKET (SIM + SafetyGuard)")

        side = st.selectbox("SIDE", ["BUY", "SELL"])
        order_type = st.selectbox("TYPE", ["MARKET", "LIMIT"])
        tif = st.selectbox("TIF", ["DAY", "GTC"])
        stop_atr = st.slider("STOP xATR", 1.0, 4.0, float(prof["stop_atr"]), 0.1)
        target_r = st.slider("TARGET (R)", 1.0, 5.0, float(prof["target_r"]), 0.1)

        atr = float(last["ATR14"])
        stop = px - stop_atr * atr if side == "BUY" else px + stop_atr * atr
        target = px + target_r * (px - stop) if side == "BUY" else px - target_r * (stop - px)

        sizing = RiskEngine.sizing_by_atr(px, atr, capital, risk_eff, stop_atr)
        qty = int(sizing["qty"])
        notional = float(qty * px)

        limit_price = None
        if order_type == "LIMIT":
            limit_price = st.number_input("LIMIT PRICE", min_value=0.01, value=float(px), step=0.10)

        tags = st.text_input("TAGS", value=f"{ctx['profile_name']}|{reg['label']}")

        st.write({"qty": qty, "notional": notional, "stop": stop, "target": target, "risk_pct": risk_eff})

        if st.button("LOG ORDER (SQLite)"):
            order = OrderIntent(
                ticker=ticker,
                side=side,
                order_type=order_type,
                tif=tif,
                qty=qty,
                notional=notional,
                price_ref=px,
                limit_price=limit_price,
                stop=stop,
                target=target,
                risk_pct=risk_eff,
                regime=reg["label"],
                score=mf["final_score"],
                cost_bps=cost["total_bps"],
                status=verdict["status"],
                tags=tags,
            )

            verdict_safety = ctx["safety_guard"].validate(order, capital)
            if not verdict_safety["ok"]:
                st.error(f"SAFETY BLOCK: {verdict_safety['reason']}")
                return

            ts_utc = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            ctx["store"].log_order({
                "timestamp_utc": ts_utc,
                "ticker": ticker,
                "side": side,
                "order_type": order_type,
                "tif": tif,
                "qty": qty,
                "notional": notional,
                "price_ref": px,
                "limit_price": limit_price,
                "stop": stop,
                "target": target,
                "risk_pct": risk_eff,
                "regime": reg["label"],
                "score": mf["final_score"],
                "cost_bps": cost["total_bps"],
                "status": verdict["status"],
                "tags": tags,
                "realized_pnl": 0.0,
            })
            st.success("ORDER LOGGED ✅")
