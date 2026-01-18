from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Tuple
import pytz

from database.sqlite_store import SQLiteStore
from .broker_base import BrokerBase
from .models import OrderIntent

@dataclass(frozen=True)
class SafetyConfig:
    tz_market: str
    open_hhmm: str
    close_hhmm: str
    auction_pre_open_start: str
    auction_pre_open_end: str
    auction_close_start: str
    auction_close_end: str
    max_daily_loss_pct: float

class SafetyGuard:
    def __init__(self, store: SQLiteStore, broker: BrokerBase, cfg: SafetyConfig):
        self.store = store
        self.broker = broker
        self.cfg = cfg

    def _parse_hhmm(self, hhmm: str) -> Tuple[int, int]:
        h, m = hhmm.split(":")
        return int(h), int(m)

    def _now_market(self) -> datetime:
        tz = pytz.timezone(self.cfg.tz_market)
        return datetime.now(tz)

    def _in_range(self, now: datetime, start: str, end: str) -> bool:
        sh, sm = self._parse_hhmm(start)
        eh, em = self._parse_hhmm(end)
        st = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
        en = now.replace(hour=eh, minute=em, second=0, microsecond=0)
        return st <= now <= en

    def _is_trading_time(self) -> Tuple[bool, str]:
        now = self._now_market()
        if self._in_range(now, self.cfg.auction_pre_open_start, self.cfg.auction_pre_open_end):
            return False, "AUCTION_PRE_OPEN"
        if self._in_range(now, self.cfg.auction_close_start, self.cfg.auction_close_end):
            return False, "AUCTION_CLOSE"
        if not self._in_range(now, self.cfg.open_hhmm, self.cfg.close_hhmm):
            return False, "OUTSIDE_MARKET_HOURS"
        return True, "OK"

    def _kill_switch(self, capital: float) -> Tuple[bool, str]:
        now_utc = datetime.utcnow().strftime("%Y-%m-%d")
        pnl = self.store.daily_realized_pnl(now_utc)
        limit = -(capital * (self.cfg.max_daily_loss_pct / 100.0))
        if pnl <= limit:
            return False, f"KILL_SWITCH_DAILY_LOSS pnl={pnl:.2f} limit={limit:.2f}"
        return True, "OK"

    def _position_check(self, ticker: str) -> Tuple[bool, str]:
        positions = self.broker.get_open_positions()
        for p in positions:
            if str(p.get("ticker", "")).upper() == ticker.upper():
                return False, "POSITION_ALREADY_OPEN"
        return True, "OK"

    def validate(self, order: OrderIntent, capital: float) -> Dict:
        if not self.broker.ping():
            return {"ok": False, "reason": "BROKER_OFFLINE"}

        ok_time, r_time = self._is_trading_time()
        if not ok_time:
            return {"ok": False, "reason": r_time}

        ok_pos, r_pos = self._position_check(order.ticker)
        if not ok_pos:
            return {"ok": False, "reason": r_pos}

        ok_kill, r_kill = self._kill_switch(capital)
        if not ok_kill:
            return {"ok": False, "reason": r_kill}

        return {"ok": True, "reason": "OK"}
