from __future__ import annotations
from typing import Any, Dict

class CostEngine:
    @staticmethod
    def compute(spread_bps: int, slippage_bps: int, fee_bps: int, max_block_bps: int) -> Dict[str, Any]:
        total = int(spread_bps + slippage_bps + fee_bps)
        blocked = total >= int(max_block_bps)
        return {
            "total_bps": total,
            "blocked": blocked,
            "max_block": int(max_block_bps),
            "break_even_pct": total / 10000.0
        }
