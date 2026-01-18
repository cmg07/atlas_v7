from __future__ import annotations
from typing import Any, Dict
import numpy as np

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

class RiskEngine:
    @staticmethod
    def monte_carlo_ruin(win_rate: float, payoff: float, risk_per_trade: float, sims=2400, trades=220) -> float:
        win_rate = clamp(win_rate, 0.01, 0.99)
        payoff = clamp(payoff, 0.5, 10.0)
        risk_per_trade = clamp(risk_per_trade, 0.001, 0.2)

        outcomes = np.random.choice([1, 0], size=(sims, trades), p=[win_rate, 1-win_rate])
        pnl = np.where(outcomes == 1, payoff * risk_per_trade, -risk_per_trade)
        equity = pnl.cumsum(axis=1)
        ruin = (equity < -0.50).any(axis=1)
        return float(ruin.mean() * 100)

    @staticmethod
    def sizing_by_atr(price: float, atr: float, capital: float, risk_pct: float, stop_atr_mult: float) -> Dict[str, Any]:
        risk_cash = capital * (risk_pct / 100.0)
        stop_dist = atr * stop_atr_mult
        qty = int(max(0, risk_cash / (stop_dist + 1e-12)))
        return {"qty": qty, "stop_dist": stop_dist, "risk_cash": risk_cash}
