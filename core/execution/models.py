from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class OrderIntent:
    ticker: str
    side: str
    order_type: str
    tif: str
    qty: int
    notional: float
    price_ref: float
    limit_price: Optional[float]
    stop: Optional[float]
    target: Optional[float]
    risk_pct: float
    regime: str
    score: float
    cost_bps: int
    status: str
    tags: str
