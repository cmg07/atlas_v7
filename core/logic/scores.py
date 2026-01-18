from __future__ import annotations
from typing import Any, Dict
import pandas as pd

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

class ScoreEngine:
    @staticmethod
    def trend_score(last: pd.Series, d: pd.DataFrame) -> float:
        close = float(last["close_final"])
        sma20 = float(last["SMA20"])
        sma50 = float(last["SMA50"])
        slope = float((d["SMA20"].iloc[-1] - d["SMA20"].iloc[-6]) / (abs(d["SMA20"].iloc[-6]) + 1e-9))

        base = 50
        if sma20 > sma50 and close > sma20:
            base += 25
        if sma20 < sma50 and close < sma20:
            base -= 20

        slope_score = clamp(50 + clamp(slope * 450, -3, 3) * 15, 0, 100)
        return float(clamp(base * 0.55 + slope_score * 0.45, 0, 100))

    @staticmethod
    def meanrev_score(last: pd.Series) -> float:
        z = float(last["ZScore"])
        return float(clamp(50 + (-z * 18) - max(0, z - 1.0) * 12, 0, 100))

    @staticmethod
    def risk_score(last: pd.Series) -> float:
        vol = float(last["VolAnn"])
        dd = float(last["Drawdown"])
        var95 = float(last.get("VaR95", 0.0))
        cvar95 = float(last.get("CVaR95", 0.0))

        v_pen = clamp((vol - 20) * 1.9, 0, 80)
        dd_pen = clamp(abs(dd) * 180, 0, 80)
        tail_pen = clamp(abs(cvar95) * 650, 0, 80) + clamp(abs(var95) * 500, 0, 60)

        return float(clamp(100 - (v_pen * 0.45 + dd_pen * 0.35 + tail_pen * 0.20), 0, 100))

    @staticmethod
    def multi(d: pd.DataFrame, last: pd.Series, cost_bps: int, regime_label: str, weights: Dict[str, float]) -> Dict[str, Any]:
        ts = ScoreEngine.trend_score(last, d)
        mr = ScoreEngine.meanrev_score(last)
        rk = ScoreEngine.risk_score(last)

        wsum = float(weights["trend"] + weights["meanrev"] + weights["risk"])
        raw = ts * (weights["trend"]/wsum) + mr * (weights["meanrev"]/wsum) + rk * (weights["risk"]/wsum)

        p_cost = clamp(cost_bps * 2.8, 0, 80)
        p_reg = 45.0 if "STRESS" in regime_label else (25.0 if "VOL" in regime_label else 0.0)

        final = clamp(raw - (p_cost * 0.55 + p_reg * 0.45), 0, 100)

        return {
            "final_score": round(float(final), 1),
            "trend_score": round(float(ts), 1),
            "meanrev_score": round(float(mr), 1),
            "risk_score": round(float(rk), 1),
        }
