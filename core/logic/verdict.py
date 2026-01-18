from __future__ import annotations
from typing import Any, Dict

class VerdictEngine:
    @staticmethod
    def decide(regime: Dict[str, Any], cost: Dict[str, Any], ruin_pct: float, score: float,
               strict_vol: float, strict_dd_pct: float, ruin_threshold: float) -> Dict[str, Any]:
        status = "AUTORIZADO"
        reasons = []

        if cost["blocked"]:
            status = "BLOQUEIO"
            reasons.append("COST_BLOCK")

        if "STRESS" in regime["label"]:
            if status != "BLOQUEIO":
                status = "DEFENSIVO"
            reasons.append("REGIME_STRESS")

        if "VOL" in regime["label"]:
            if status != "BLOQUEIO":
                status = "DEFENSIVO"
            reasons.append("REGIME_VOL")

        if float(regime["vol"]) > float(strict_vol):
            if status != "BLOQUEIO":
                status = "DEFENSIVO"
            reasons.append("VOL_LIMIT")

        if float(regime["dd"]) * 100 < float(strict_dd_pct):
            if status != "BLOQUEIO":
                status = "DEFENSIVO"
            reasons.append("DD_LIMIT")

        if ruin_pct > float(ruin_threshold):
            if status != "BLOQUEIO":
                status = "DEFENSIVO"
            reasons.append("RUIN_HIGH")

        if regime["score"] < 35 and status != "BLOQUEIO":
            status = "DEFENSIVO"
            reasons.append("OPERABILITY_LOW")

        if score < 40 and status != "BLOQUEIO":
            status = "DEFENSIVO"
            reasons.append("SCORE_LOW")

        command = {"AUTORIZADO": "READY", "DEFENSIVO": "DEFENSIVE", "BLOQUEIO": "BLOCKED"}[status]
        return {"status": status, "command": command, "reasons": reasons or ["OK"]}
