from __future__ import annotations
from typing import Any, Dict
import pandas as pd

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

class RegimeEngine:
    @staticmethod
    def analyze(d: pd.DataFrame, cost_bps: int) -> Dict[str, Any]:
        last = d.iloc[-1]
        close = float(last["close_final"])
        sma20 = float(last["SMA20"])
        sma50 = float(last["SMA50"])
        z = float(last["ZScore"])
        vol = float(last["VolAnn"])
        dd = float(last["Drawdown"])
        slope = float((d["SMA20"].iloc[-1] - d["SMA20"].iloc[-6]) / (abs(d["SMA20"].iloc[-6]) + 1e-9))

        up = sma20 > sma50 and close > sma20 and slope > 0
        dn = sma20 < sma50 and close < sma20 and slope < 0

        vol_hostil = vol > 45.0
        stress = dd < -0.20

        label = "TRANSITION"
        if stress:
            label = "STRESS"
        elif vol_hostil:
            label = "VOL"
        elif up:
            label = "UPTREND"
        elif dn:
            label = "DOWNTREND"

        if abs(z) >= 2 and not stress:
            label += " EXT" if z > 0 else " DISC"

        score = 75
        score -= int(abs(z) * 7)
        score -= int(max(0, vol - 25))
        score -= int(abs(dd) * 120)
        score -= int(cost_bps * 0.8)
        score = int(clamp(score, 0, 100))

        return {"label": label, "z": z, "vol": vol, "dd": dd, "slope": slope, "score": score}
