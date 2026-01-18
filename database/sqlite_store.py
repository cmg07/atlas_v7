from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


DB_PATH_DEFAULT = "atlas.db"


@dataclass(frozen=True)
class DBConfig:
    path: str = DB_PATH_DEFAULT


class SQLiteStore:
    """
    SQLite + WAL para ambiente Streamlit (multi-thread).
    Resolve corrupção/lock comum de CSV em ledger.
    """
    def __init__(self, cfg: DBConfig):
        self.cfg = cfg
        self._ensure_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.cfg.path, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _ensure_db(self) -> None:
        os.makedirs(os.path.dirname(self.cfg.path) or ".", exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS universe (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              category TEXT NOT NULL,
              ticker_yahoo TEXT NOT NULL,
              currency_code TEXT DEFAULT "",
              base TEXT DEFAULT "spot",
              country TEXT DEFAULT "",
              exchange TEXT DEFAULT "",
              priority_source TEXT DEFAULT "",
              bridge_key TEXT DEFAULT "",
              is_active INTEGER DEFAULT 1,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_universe_cat ON universe(category);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_universe_ticker ON universe(ticker_yahoo);")

            conn.execute("""
            CREATE TABLE IF NOT EXISTS ledger (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              timestamp_utc TEXT NOT NULL,
              ticker TEXT NOT NULL,
              side TEXT NOT NULL,
              order_type TEXT NOT NULL,
              tif TEXT NOT NULL,
              qty INTEGER NOT NULL,
              notional REAL NOT NULL,
              price_ref REAL NOT NULL,
              limit_price REAL,
              stop REAL,
              target REAL,
              risk_pct REAL NOT NULL,
              regime TEXT,
              score REAL,
              cost_bps INTEGER,
              status TEXT,
              tags TEXT,
              realized_pnl REAL DEFAULT 0.0
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_ts ON ledger(timestamp_utc);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_ticker ON ledger(ticker);")

    # ---------------- Universe
    def upsert_universe_rows(self, rows: Iterable[Dict[str, Any]]) -> int:
        ins = 0
        with self._connect() as conn:
            for r in rows:
                ticker = str(r.get("ticker_yahoo", "")).strip()
                if not ticker:
                    continue

                exists = conn.execute(
                    "SELECT 1 FROM universe WHERE ticker_yahoo = ? LIMIT 1;",
                    (ticker,),
                ).fetchone()

                if exists:
                    continue

                conn.execute("""
                    INSERT INTO universe
                    (name, category, ticker_yahoo, currency_code, base, country, exchange, priority_source, bridge_key, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    r.get("name", ""),
                    r.get("category", ""),
                    ticker,
                    r.get("currency_code", ""),
                    r.get("base", "spot"),
                    r.get("country", ""),
                    r.get("exchange", ""),
                    r.get("priority_source", ""),
                    r.get("bridge_key", ""),
                ))
                ins += 1
        return ins

    def get_universe(self, only_active: bool = True) -> List[Dict[str, Any]]:
        q = "SELECT * FROM universe"
        if only_active:
            q += " WHERE is_active = 1"
        q += " ORDER BY category, name;"

        with self._connect() as conn:
            rows = conn.execute(q).fetchall()
            return [dict(r) for r in rows]

    # ---------------- Ledger
    def log_order(self, row: Dict[str, Any]) -> int:
        with self._connect() as conn:
            cur = conn.execute("""
                INSERT INTO ledger
                (timestamp_utc, ticker, side, order_type, tif, qty, notional, price_ref, limit_price,
                 stop, target, risk_pct, regime, score, cost_bps, status, tags, realized_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["timestamp_utc"],
                row["ticker"],
                row["side"],
                row["order_type"],
                row["tif"],
                int(row["qty"]),
                float(row["notional"]),
                float(row["price_ref"]),
                row.get("limit_price", None),
                row.get("stop", None),
                row.get("target", None),
                float(row["risk_pct"]),
                row.get("regime", ""),
                row.get("score", None),
                row.get("cost_bps", None),
                row.get("status", ""),
                row.get("tags", ""),
                float(row.get("realized_pnl", 0.0)),
            ))
            return int(cur.lastrowid)

    def read_ledger(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ledger ORDER BY id DESC LIMIT ?;",
                (int(limit),)
            ).fetchall()
            return [dict(r) for r in rows]

    def daily_realized_pnl(self, date_utc: str) -> float:
        with self._connect() as conn:
            row = conn.execute("""
                SELECT COALESCE(SUM(realized_pnl), 0.0) AS pnl
                FROM ledger
                WHERE substr(timestamp_utc, 1, 10) = ?;
            """, (date_utc,)).fetchone()
            return float(row["pnl"]) if row else 0.0
