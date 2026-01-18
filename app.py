# ============================================================
# ATLAS v7.0 — "Global Universe + Council AI + Risk Heatmap"
# Single-file institutional trading terminal (Streamlit).
# Focus: Universe coverage + IA text reports + charts + tooltips.
#
# PowerShell:
#   cd C:\Users\caiom\atlas_v7
#   .\venv\Scripts\Activate.ps1
#   streamlit run app.py
# ============================================================

from __future__ import annotations

import os
import re
import io
import json
import math
import time
import sqlite3
import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pytz
import requests
from bs4 import BeautifulSoup

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

import yfinance as yf
from scipy.stats import skew, kurtosis

# OpenAI optional
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# ============================================================
# GLOBAL CONFIG
# ============================================================

APP_TITLE = "ATLAS v7.0 — Global Universe + Council AI"
DB_PATH = "atlas.db"
UTC = pytz.UTC
TRADING_DAYS = 252

DEFAULT_UI_TZ = "America/Sao_Paulo"
DEFAULT_MARKET_TZ = "America/Sao_Paulo"

# Wikipedia sources (robust for constituents)
WIKI_IBOV_URL = "https://pt.wikipedia.org/wiki/Lista_de_companhias_citadas_no_Ibovespa"
WIKI_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKI_NDX_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"
WIKI_DOW_URL = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
WIKI_FTSE_URL = "https://en.wikipedia.org/wiki/FTSE_100_Index"
WIKI_DAX_URL = "https://en.wikipedia.org/wiki/DAX"
WIKI_CAC_URL = "https://en.wikipedia.org/wiki/CAC_40"
WIKI_STOXX50_URL = "https://en.wikipedia.org/wiki/EURO_STOXX_50"
WIKI_NIKKEI_URL = "https://en.wikipedia.org/wiki/Nikkei_225"
WIKI_HSI_URL = "https://en.wikipedia.org/wiki/Hang_Seng_Index"

# CoinGecko (no key) for crypto top list
COINGECKO_TOP_URL = "https://api.coingecko.com/api/v3/coins/markets"

# RSS sources (lightweight)
RSS_FEEDS = {
    "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Markets (SPX)": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC&region=US&lang=en-US",
    "FX (USDBRL)": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=USDBRL%3DX&region=US&lang=en-US",
    "Crypto (BTC)": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=BTC-USD&region=US&lang=en-US",
}

# Tooltips (didactic)
TOOLTIPS = {
    "PX_LAST": "Último preço (close_final).",
    "CHG%": "Variação % vs fechamento anterior.",
    "SMA20": "Média móvel simples 20 períodos (tendência curta).",
    "SMA50": "Média móvel simples 50 períodos (tendência média).",
    "RSI14": "RSI 14: >70 sobrecomprado, <30 sobrevendido.",
    "ZScore": "ZScore vs SMA20/STD20: intensidade do desvio do preço.",
    "ATR14": "ATR 14: range médio (volatilidade absoluta).",
    "VolAnn": "Vol anualizada (rolling 20) em %. Quanto maior, mais risco.",
    "Drawdown": "Queda do equity vs pico (stress).",
    "VaR95": "VaR 95%: perda estimada para 5% piores dias.",
    "CVaR95": "CVaR 95%: média das perdas além do VaR (cauda).",
    "COST_BPS": "Custo total estimado em bps: spread+slippage+fees.",
    "SCORE": "Score multi-fator (tendência + meanrev + risco) penalizado por custo/regime.",
    "RUIN": "Probabilidade aproximada de ruína (Monte Carlo).",
    "REGIME": "Regime detectado (trend/vol/stress/transition).",
    "FEAR": "Índice proprietário (-1..+1) derivado de headlines. Fallback lexicon se sem OpenAI.",
}

# ============================================================
# UI THEME (Wall Street Dark)
# ============================================================

BLOOMBERG_CSS = """
<style>
:root{
  --bg:#00040a; --panel:#050b14; --panel2:#071225; --line:#0f1e34; --line2:#1a3456;
  --text:#e5e7eb; --muted:#93a4bf;
  --amber:#ffb000; --amber2:#ffcc4d; --cyan:#00d6ff;
  --good:#00d27a; --bad:#ff3b3b; --warn:#ffd166;
  --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Roboto Mono", "Courier New", monospace;
}
html, body { background: var(--bg) !important; color: var(--text); }
.stApp{
  background:
    linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px),
    radial-gradient(circle at 20% 12%, rgba(255,176,0,0.050), transparent 45%),
    radial-gradient(circle at 82% 20%, rgba(0,214,255,0.045), transparent 55%);
  background-size: 34px 34px, 34px 34px, 100% 100%, 100% 100%;
  background-position: center;
}
.block-container { padding-top: 64px !important; padding-bottom: 44px !important; }
section[data-testid="stSidebar"]{
  background: #000209 !important;
  border-right: 1px solid var(--line);
}
section[data-testid="stSidebar"] *{ font-family: var(--mono) !important; }
h1,h2,h3 { color: var(--text); font-weight: 950; letter-spacing: 0.2px; }
.stButton > button{
  background: linear-gradient(180deg, rgba(7,18,37,1) 0%, rgba(2,6,12,1) 100%) !important;
  border: 1px solid var(--line2) !important; color: var(--text) !important;
  border-radius: 12px !important; font-family: var(--mono) !important; font-weight: 950 !important;
  padding: 9px 12px !important;
}
.stButton > button:hover{
  border-color: var(--amber) !important;
  box-shadow: 0 0 0 1px rgba(255,176,0,0.35) inset, 0 0 18px rgba(255,176,0,0.10);
}
.small { color: var(--muted); font-size: 0.83rem; font-family: var(--mono); }
.hr{ border-top: 1px solid var(--line); margin: 12px 0; }

/* Tape */
.atlas-tape-wrap{
  position:fixed; top:0; left:0; right:0; z-index:9999; height:36px;
  background: rgba(0,2,9,0.98);
  border-bottom: 1px solid var(--line);
  overflow:hidden; display:flex; align-items:center;
}
.atlas-tape-move{
  white-space:nowrap; display:inline-block;
  animation: atlas-tape 22s linear infinite;
  padding-left:100%;
  font-family: var(--mono);
}
@keyframes atlas-tape{ 0%{ transform: translateX(0); } 100%{ transform: translateX(-170%); } }
.atlas-tape-item{ display:inline-block; margin-right:22px; font-size:0.82rem; color:var(--text); }
.tape-ticker{ color: var(--amber2); font-weight: 950; }
.green{ color: var(--good); font-weight: 950; }
.red{ color: var(--bad); font-weight: 950; }

/* Tooltips */
.tt{ display:inline-flex; align-items:center; gap:6px; font-family: var(--mono); }
.tt .qmark{
  width:16px;height:16px; border-radius:999px;
  background: rgba(255,255,255,0.06);
  border:1px solid var(--line2);
  display:inline-flex; align-items:center; justify-content:center;
  color: var(--amber2); font-weight:950; font-size:11px;
  cursor:help; position:relative;
}
.tt .qmark .tip{
  visibility:hidden; opacity:0; transition: opacity 0.15s ease;
  position:absolute; top:18px; left:0;
  min-width:260px; max-width:380px;
  background: rgba(5,11,20,0.98);
  border:1px solid var(--line2);
  border-radius:12px; padding:10px 12px;
  color: var(--text); font-size: 12px; line-height: 1.25rem;
  box-shadow: 0 0 20px rgba(0,0,0,0.40); z-index: 99999;
}
.tt .qmark:hover .tip{ visibility:visible; opacity:1; }

.kpi-card{
  background: rgba(5,11,20,0.72);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 12px 12px;
}
.kpi-title{
  color: var(--muted);
  font-size: 0.74rem;
  font-family: var(--mono);
  text-transform: uppercase;
}
.kpi-value{
  font-family: var(--mono);
  font-size: 1.25rem;
  font-weight: 950;
  letter-spacing: 0.2px;
}
.kpi-sub{
  color: var(--muted);
  font-family: var(--mono);
  font-size: 0.75rem;
}
</style>
"""

def apply_theme() -> None:
    st.markdown(BLOOMBERG_CSS, unsafe_allow_html=True)

def tt_label(label: str, help_text: str) -> str:
    safe_help = (help_text or "").replace("<", "&lt;").replace(">", "&gt;")
    safe_lbl = label.replace("<", "&lt;").replace(">", "&gt;")
    return f"""
    <span class="tt">
      <span>{safe_lbl}</span>
      <span class="qmark">?
        <span class="tip">{safe_help}</span>
      </span>
    </span>
    """

def kpi_card(title: str, value: str, subtitle: str = "", help_key: Optional[str] = None) -> None:
    help_txt = TOOLTIPS.get(help_key or title, "")
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-title">{tt_label(title, help_txt) if help_txt else title}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# UTILITIES
# ============================================================

def now_utc() -> dt.datetime:
    return dt.datetime.now(tz=UTC)

def to_utc_index(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    out = pd.to_datetime(idx, errors="coerce")
    if getattr(out, "tz", None) is None:
        out = out.tz_localize("UTC")
    else:
        out = out.tz_convert("UTC")
    return out

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def normalize_ticker(t: str) -> str:
    """
    Yahoo resolver:
    - BR stocks need .SA (PETR4 -> PETR4.SA)
    - Keep already suffixed or special patterns
    """
    t = (t or "").strip()
    if not t:
        return t
    raw = t.upper()

    if "." in raw or "^" in raw or "=" in raw or raw.endswith("-USD"):
        return raw

    # Brazil typical
    if len(raw) in (5, 6) and raw[:4].isalpha() and raw[-1].isdigit():
        return f"{raw}.SA"

    return raw

@st.cache_data(ttl=900, show_spinner=False)
def safe_download(ticker: str, min_rows: int = 30) -> Optional[pd.DataFrame]:
    ticker = normalize_ticker(ticker)
    combos = [("2y", "1d"), ("1y", "1d"), ("6mo", "1d"), ("3mo", "1d")]
    for period, interval in combos:
        try:
            df = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                threads=False,
                auto_adjust=False,
            )
            if df is not None and not df.empty and len(df) >= min_rows:
                return df
        except Exception:
            pass

    # final fallback
    try:
        df = yf.download(
            ticker, period="6mo", interval="1d",
            progress=False, threads=False, auto_adjust=True
        )
        if df is not None and not df.empty and len(df) >= min_rows:
            return df
    except Exception:
        pass

    return None

def standardize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    d = df.copy()
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)

    d.columns = [str(c).strip().lower() for c in d.columns]

    if "adj close" in d.columns:
        d["close_final"] = d["adj close"]
    elif "close" in d.columns:
        d["close_final"] = d["close"]
    else:
        raise ValueError("No close price column found.")

    for c in ("open", "high", "low"):
        if c not in d.columns:
            d[c] = d["close_final"]

    if "volume" not in d.columns:
        d["volume"] = np.nan

    d = d[["open", "high", "low", "close", "close_final", "volume"]].copy()
    d.index = to_utc_index(d.index)
    d = d.sort_index()
    d = d.dropna(subset=["close_final"])
    return d

# ============================================================
# SQLITE STORAGE
# ============================================================

class SQLiteStore:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        self._ensure()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _ensure(self) -> None:
        """
        Ensure DB schema exists and is compatible.

        This function is MIGRATION-SAFE:
        - If an old 'universe' table exists without the expected columns (ex: missing 'ticker'),
          it renames it to a backup and recreates the correct table.
        """
        with self._connect() as c:
            # --- Helpers
            def table_exists(name: str) -> bool:
                r = c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                    (name,),
                ).fetchone()
                return r is not None

            def table_columns(name: str) -> List[str]:
                if not table_exists(name):
                    return []
                cols = c.execute(f"PRAGMA table_info({name});").fetchall()
                return [str(x["name"]) for x in cols] if cols else []

            # --- If universe exists but schema is old/broken -> migrate
            if table_exists("universe"):
                cols = set(table_columns("universe"))
                expected = {"id", "category", "ticker", "name", "source", "is_active", "created_at"}

                # If missing critical column ticker, migrate
                if "ticker" not in cols:
                    backup_name = f"universe_old_backup_{int(time.time())}"
                    try:
                        c.execute(f"ALTER TABLE universe RENAME TO {backup_name};")
                    except Exception:
                        # If rename fails, drop to unblock (last resort)
                        try:
                            c.execute("DROP TABLE IF EXISTS universe;")
                        except Exception:
                            pass

                # If columns exist but are incomplete/incorrect, rebuild cleanly
                else:
                    # If it's missing major fields, rebuild (safe)
                    if not expected.issubset(cols):
                        backup_name = f"universe_old_backup_{int(time.time())}"
                        try:
                            c.execute(f"ALTER TABLE universe RENAME TO {backup_name};")
                        except Exception:
                            try:
                                c.execute("DROP TABLE IF EXISTS universe;")
                            except Exception:
                                pass

            # --- Create fresh universe table
            c.execute("""
            CREATE TABLE IF NOT EXISTS universe (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              category TEXT NOT NULL,
              ticker TEXT NOT NULL,
              name TEXT NOT NULL,
              source TEXT DEFAULT "",
              is_active INTEGER DEFAULT 1,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # --- Create indexes (now safe)
            try:
                c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_uni_ticker ON universe(ticker);")
            except Exception:
                # If index fails for any reason, recreate table from scratch (very rare)
                try:
                    c.execute("DROP TABLE IF EXISTS universe;")
                    c.execute("""
                    CREATE TABLE universe (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      category TEXT NOT NULL,
                      ticker TEXT NOT NULL,
                      name TEXT NOT NULL,
                      source TEXT DEFAULT "",
                      is_active INTEGER DEFAULT 1,
                      created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                    """)
                    c.execute("CREATE UNIQUE INDEX idx_uni_ticker ON universe(ticker);")
                except Exception:
                    pass

            c.execute("CREATE INDEX IF NOT EXISTS idx_uni_cat ON universe(category);")

            # --- Ledger table
            c.execute("""
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
            c.execute("CREATE INDEX IF NOT EXISTS idx_led_ts ON ledger(timestamp_utc);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_led_ticker ON ledger(ticker);")

    def reset_universe(self) -> None:
        with self._connect() as c:
            c.execute("DELETE FROM universe;")

    def upsert_universe(self, rows: List[Dict[str, Any]]) -> int:
        inserted = 0
        with self._connect() as c:
            for r in rows:
                t = normalize_ticker(str(r.get("ticker", "")).strip())
                if not t:
                    continue
                try:
                    c.execute(
                        "INSERT OR IGNORE INTO universe(category, ticker, name, source, is_active) VALUES(?,?,?,?,1);",
                        (r.get("category", ""), t, r.get("name", t), r.get("source", "")),
                    )
                    inserted += int(c.total_changes > 0)
                except Exception:
                    continue
        return inserted

    def get_universe_df(self, only_active: bool = True) -> pd.DataFrame:
        q = "SELECT * FROM universe"
        if only_active:
            q += " WHERE is_active = 1"
        q += " ORDER BY category, name;"
        with self._connect() as c:
            rows = c.execute(q).fetchall()
            return pd.DataFrame([dict(x) for x in rows])

    def deactivate_tickers(self, tickers: List[str]) -> int:
        if not tickers:
            return 0
        with self._connect() as c:
            n = 0
            for t in tickers:
                try:
                    c.execute("UPDATE universe SET is_active = 0 WHERE ticker = ?;", (normalize_ticker(t),))
                    n += c.total_changes
                except Exception:
                    pass
            return n

    def log_order(self, row: Dict[str, Any]) -> int:
        with self._connect() as c:
            cur = c.execute("""
                INSERT INTO ledger
                (timestamp_utc, ticker, side, order_type, tif, qty, notional, price_ref, limit_price,
                 stop, target, risk_pct, regime, score, cost_bps, status, tags, realized_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["timestamp_utc"], row["ticker"], row["side"], row["order_type"], row["tif"],
                int(row["qty"]), float(row["notional"]), float(row["price_ref"]), row.get("limit_price", None),
                row.get("stop", None), row.get("target", None), float(row["risk_pct"]), row.get("regime", ""),
                row.get("score", None), row.get("cost_bps", None), row.get("status", ""),
                row.get("tags", ""), float(row.get("realized_pnl", 0.0)),
            ))
            return int(cur.lastrowid)

    def read_ledger(self, limit: int = 500) -> pd.DataFrame:
        with self._connect() as c:
            rows = c.execute("SELECT * FROM ledger ORDER BY id DESC LIMIT ?;", (int(limit),)).fetchall()
            return pd.DataFrame([dict(x) for x in rows])

    def daily_realized_pnl(self, date_utc: str) -> float:
        with self._connect() as c:
            row = c.execute("""
                SELECT COALESCE(SUM(realized_pnl), 0.0) AS pnl
                FROM ledger
                WHERE substr(timestamp_utc, 1, 10) = ?;
            """, (date_utc,)).fetchone()
            return float(row["pnl"]) if row else 0.0

# ============================================================
# UNIVERSE BUILDER (GLOBAL)
# ============================================================

def _suffix_exchange(ticker: str, suffix: str) -> str:
    t = (ticker or "").strip()
    if not t:
        return ""
    t = t.upper()
    # If already has suffix or special:
    if "." in t or "^" in t or "=" in t or t.endswith("-USD"):
        return t
    return f"{t}{suffix}"

def _clean_symbol(sym: str) -> str:
    sym = str(sym).strip()
    sym = sym.replace("\xa0", " ")
    sym = sym.replace(".", "-")  # BRK.B -> BRK-B for Yahoo
    sym = sym.strip()
    return sym

def wiki_table_fetch(url: str) -> List[pd.DataFrame]:
    try:
        r = requests.get(url, timeout=18, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        return pd.read_html(r.text)
    except Exception:
        return []

def wiki_generic_universe(
    url: str,
    category: str,
    symbol_candidates: List[str],
    name_candidates: List[str],
    suffix: str = "",
    max_rows: Optional[int] = None,
    source: str = "wikipedia"
) -> List[Dict[str, Any]]:
    """
    Generic fetch from wikipedia tables with robust column detection.
    suffix: ".L", ".DE", ".PA", ".T", ".HK", etc (Yahoo)
    """
    dfs = wiki_table_fetch(url)
    if not dfs:
        return []

    rows: List[Dict[str, Any]] = []
    for df in dfs:
        cols = [str(c).lower().strip() for c in df.columns]
        df.columns = cols

        sym_col = None
        name_col = None

        for c in cols:
            if any(k.lower() in c for k in symbol_candidates):
                sym_col = c
                break
        for c in cols:
            if any(k.lower() in c for k in name_candidates):
                name_col = c
                break

        if sym_col is None:
            continue

        for _, r in df.iterrows():
            sym = _clean_symbol(r.get(sym_col, ""))
            if not sym:
                continue
            nm = str(r.get(name_col, sym)).strip() if name_col else sym

            tick = sym.upper()

            # BR via normalize later:
            if category.startswith("BR:") or category.startswith("Ações Brasil"):
                tick = normalize_ticker(tick)
            else:
                if suffix:
                    tick = _suffix_exchange(tick, suffix)

            rows.append({
                "category": category,
                "ticker": tick,
                "name": nm[:90],
                "source": source
            })

        if rows:
            break

    # Deduplicate
    seen = set()
    out = []
    for x in rows:
        if x["ticker"] not in seen:
            out.append(x)
            seen.add(x["ticker"])

    if max_rows is not None:
        out = out[: int(max_rows)]
    return out

def coingecko_crypto_top(n: int = 200) -> List[Dict[str, Any]]:
    """
    Crypto top list -> Yahoo tickers: SYMBOL-USD
    Note: nem toda moeda tem ticker no Yahoo. A validação pode desativar ruins.
    """
    rows: List[Dict[str, Any]] = []
    per_page = 250
    page = 1
    fetched = 0

    while fetched < n and page <= 3:
        try:
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": per_page,
                "page": page,
                "sparkline": "false",
            }
            r = requests.get(COINGECKO_TOP_URL, params=params, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                break
            data = r.json()
            if not isinstance(data, list) or not data:
                break

            for item in data:
                if fetched >= n:
                    break
                sym = str(item.get("symbol", "")).upper().strip()
                name = str(item.get("name", sym)).strip()
                if not sym:
                    continue
                # Yahoo convention:
                tick = f"{sym}-USD"
                rows.append({"category": "Cripto (Top MarketCap)", "ticker": tick, "name": name[:90], "source": "coingecko"})
                fetched += 1

            page += 1
        except Exception:
            break

    # Dedupe
    seen = set()
    out = []
    for x in rows:
        if x["ticker"] not in seen:
            out.append(x)
            seen.add(x["ticker"])
    return out[:n]

def curated_core_universe() -> List[Dict[str, Any]]:
    """
    Core curated: FX, Commodities, Indices, ETFs, BR bluechips, US megacaps.
    """
    rows: List[Dict[str, Any]] = []

    # --- Indices
    indices = [
        ("Índices", "^BVSP", "Ibovespa"),
        ("Índices", "^GSPC", "S&P 500"),
        ("Índices", "^IXIC", "Nasdaq Composite"),
        ("Índices", "^DJI", "Dow Jones"),
        ("Índices", "^RUT", "Russell 2000"),
        ("Índices", "^VIX", "VIX"),
        ("Índices", "^FTSE", "FTSE 100"),
        ("Índices", "^GDAXI", "DAX"),
        ("Índices", "^FCHI", "CAC 40"),
        ("Índices", "^N225", "Nikkei 225"),
        ("Índices", "^HSI", "Hang Seng"),
        ("Índices", "^STOXX50E", "EuroStoxx 50"),
        ("Índices", "DX-Y.NYB", "DXY (Dollar Index)"),
    ]
    for cat, t, nm in indices:
        rows.append({"category": cat, "ticker": t, "name": nm, "source": "curated"})

    # --- FX BRL crosses
    fx_brl = [
        ("FX vs BRL", "USDBRL=X", "USD/BRL"),
        ("FX vs BRL", "EURBRL=X", "EUR/BRL"),
        ("FX vs BRL", "GBPBRL=X", "GBP/BRL"),
        ("FX vs BRL", "CHFBRL=X", "CHF/BRL"),
        ("FX vs BRL", "JPYBRL=X", "JPY/BRL"),
        ("FX vs BRL", "CADBRL=X", "CAD/BRL"),
        ("FX vs BRL", "AUDBRL=X", "AUD/BRL"),
        ("FX vs BRL", "CNYBRL=X", "CNY/BRL"),
        ("FX vs BRL", "MXNBRL=X", "MXN/BRL"),
        ("FX vs BRL", "ZARBRL=X", "ZAR/BRL"),
    ]
    for cat, t, nm in fx_brl:
        rows.append({"category": cat, "ticker": t, "name": nm, "source": "curated"})

    # --- FX Majors
    fx_maj = [
        ("FX Majors", "EURUSD=X", "EUR/USD"),
        ("FX Majors", "GBPUSD=X", "GBP/USD"),
        ("FX Majors", "USDJPY=X", "USD/JPY"),
        ("FX Majors", "USDCHF=X", "USD/CHF"),
        ("FX Majors", "USDCAD=X", "USD/CAD"),
        ("FX Majors", "AUDUSD=X", "AUD/USD"),
        ("FX Majors", "NZDUSD=X", "NZD/USD"),
        ("FX Majors", "EURJPY=X", "EUR/JPY"),
        ("FX Majors", "GBPJPY=X", "GBP/JPY"),
    ]
    for cat, t, nm in fx_maj:
        rows.append({"category": cat, "ticker": t, "name": nm, "source": "curated"})

    # --- Commodities
    cmd = [
        ("Commodities", "GC=F", "Gold"),
        ("Commodities", "SI=F", "Silver"),
        ("Commodities", "PL=F", "Platinum"),
        ("Commodities", "PA=F", "Palladium"),
        ("Commodities", "CL=F", "WTI Oil"),
        ("Commodities", "BZ=F", "Brent Oil"),
        ("Commodities", "NG=F", "Natural Gas"),
        ("Commodities", "HG=F", "Copper"),
        ("Commodities", "ZS=F", "Soybeans"),
        ("Commodities", "ZC=F", "Corn"),
        ("Commodities", "KC=F", "Coffee"),
        ("Commodities", "SB=F", "Sugar"),
        ("Commodities", "CT=F", "Cotton"),
        ("Commodities", "LE=F", "Live Cattle"),
    ]
    for cat, t, nm in cmd:
        rows.append({"category": cat, "ticker": t, "name": nm, "source": "curated"})

    # --- ETFs Global + BR
    etfs = [
        ("ETFs Global", "SPY", "S&P500 ETF"),
        ("ETFs Global", "QQQ", "Nasdaq100 ETF"),
        ("ETFs Global", "IWM", "Russell2000 ETF"),
        ("ETFs Global", "DIA", "Dow ETF"),
        ("ETFs Global", "EEM", "Emerging Markets"),
        ("ETFs Global", "EFA", "Developed Markets"),
        ("ETFs Global", "TLT", "US 20Y Treasuries"),
        ("ETFs Global", "LQD", "IG Credit"),
        ("ETFs Global", "HYG", "High Yield Credit"),
        ("ETFs Global", "GLD", "Gold ETF"),
        ("ETFs Global", "SLV", "Silver ETF"),
        ("ETFs Global", "XLF", "US Financials"),
        ("ETFs Global", "XLK", "US Tech"),
        ("ETFs Global", "XLE", "US Energy"),
        ("ETFs Global", "XLV", "US Healthcare"),
        ("ETFs Global", "ARKK", "ARK Innovation"),
        ("ETFs Global", "VXX", "VIX ETN"),
        ("ETFs Brasil", "BOVA11.SA", "Ibovespa ETF"),
        ("ETFs Brasil", "SMAL11.SA", "Small Caps BR"),
        ("ETFs Brasil", "IVVB11.SA", "S&P500 BR ETF"),
        ("ETFs Brasil", "HASH11.SA", "Crypto BR ETF"),
    ]
    for cat, t, nm in etfs:
        rows.append({"category": cat, "ticker": t, "name": nm, "source": "curated"})

    # --- BR Bluechips baseline
    br = [
        ("Ações Brasil (Core)", "PETR4.SA", "Petrobras PN"),
        ("Ações Brasil (Core)", "VALE3.SA", "Vale ON"),
        ("Ações Brasil (Core)", "ITUB4.SA", "Itaú PN"),
        ("Ações Brasil (Core)", "BBDC4.SA", "Bradesco PN"),
        ("Ações Brasil (Core)", "ABEV3.SA", "Ambev"),
        ("Ações Brasil (Core)", "WEGE3.SA", "WEG"),
        ("Ações Brasil (Core)", "BBAS3.SA", "Banco do Brasil"),
        ("Ações Brasil (Core)", "B3SA3.SA", "B3"),
        ("Ações Brasil (Core)", "SUZB3.SA", "Suzano"),
        ("Ações Brasil (Core)", "PRIO3.SA", "PRIO"),
        ("Ações Brasil (Core)", "LREN3.SA", "Lojas Renner"),
        ("Ações Brasil (Core)", "RAIL3.SA", "Rumo"),
        ("Ações Brasil (Core)", "JBSS3.SA", "JBS"),
        ("Ações Brasil (Core)", "GGBR4.SA", "Gerdau PN"),
        ("Ações Brasil (Core)", "ELET3.SA", "Eletrobras"),
        ("Ações Brasil (Core)", "ELET6.SA", "Eletrobras PN"),
    ]
    for cat, t, nm in br:
        rows.append({"category": cat, "ticker": t, "name": nm, "source": "curated"})

    # --- US Megacaps
    us = [
        ("Ações EUA (Core)", "AAPL", "Apple"),
        ("Ações EUA (Core)", "MSFT", "Microsoft"),
        ("Ações EUA (Core)", "NVDA", "NVIDIA"),
        ("Ações EUA (Core)", "AMZN", "Amazon"),
        ("Ações EUA (Core)", "GOOGL", "Alphabet"),
        ("Ações EUA (Core)", "META", "Meta"),
        ("Ações EUA (Core)", "TSLA", "Tesla"),
        ("Ações EUA (Core)", "BRK-B", "Berkshire B"),
        ("Ações EUA (Core)", "JPM", "JPMorgan"),
        ("Ações EUA (Core)", "XOM", "ExxonMobil"),
    ]
    for cat, t, nm in us:
        rows.append({"category": cat, "ticker": t, "name": nm, "source": "curated"})

    # --- Crypto baseline
    crypto = [
        ("Cripto (Core)", "BTC-USD", "Bitcoin"),
        ("Cripto (Core)", "ETH-USD", "Ethereum"),
        ("Cripto (Core)", "SOL-USD", "Solana"),
        ("Cripto (Core)", "BNB-USD", "BNB"),
        ("Cripto (Core)", "XRP-USD", "XRP"),
        ("Cripto (Core)", "ADA-USD", "Cardano"),
        ("Cripto (Core)", "AVAX-USD", "Avalanche"),
        ("Cripto (Core)", "DOGE-USD", "Dogecoin"),
        ("Cripto (Core)", "LINK-USD", "Chainlink"),
    ]
    for cat, t, nm in crypto:
        rows.append({"category": cat, "ticker": t, "name": nm, "source": "curated"})

    return rows

class UniverseEngine:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def seed_core(self) -> int:
        return self.store.upsert_universe(curated_core_universe())

    def build_all(self, crypto_top_n: int = 200) -> Dict[str, Any]:
        """
        One-click "ALL" builder:
        - Core curated
        - IBOV
        - S&P500
        - Nasdaq-100
        - Dow 30
        - FTSE100
        - DAX
        - CAC40
        - EuroStoxx50
        - Nikkei225
        - Hang Seng
        - Crypto top N (CoinGecko)
        """
        inserted_total = 0
        errors = []

        def _add(rows: List[Dict[str, Any]]) -> int:
            nonlocal inserted_total
            n = self.store.upsert_universe(rows)
            inserted_total += n
            return n

        # core
        try:
            _add(curated_core_universe())
        except Exception as e:
            errors.append(f"core: {e}")

        # IBOV (BR .SA)
        try:
            rows = wiki_generic_universe(
                url=WIKI_IBOV_URL,
                category="Ações Brasil (IBOV)",
                symbol_candidates=["código", "ticker", "negociação"],
                name_candidates=["empresa", "nome", "companhia"],
                suffix="",
                source="wikipedia_ibov",
            )
            _add(rows)
        except Exception as e:
            errors.append(f"ibov: {e}")

        # SP500
        try:
            rows = wiki_generic_universe(
                url=WIKI_SP500_URL,
                category="Ações EUA (S&P500)",
                symbol_candidates=["symbol"],
                name_candidates=["security", "company", "name"],
                suffix="",
                source="wikipedia_sp500",
            )
            _add(rows)
        except Exception as e:
            errors.append(f"sp500: {e}")

        # Nasdaq-100
        try:
            rows = wiki_generic_universe(
                url=WIKI_NDX_URL,
                category="Ações EUA (Nasdaq-100)",
                symbol_candidates=["ticker", "symbol"],
                name_candidates=["company", "security", "name"],
                suffix="",
                source="wikipedia_nasdaq100",
            )
            _add(rows)
        except Exception as e:
            errors.append(f"nasdaq100: {e}")

        # Dow 30
        try:
            rows = wiki_generic_universe(
                url=WIKI_DOW_URL,
                category="Ações EUA (Dow 30)",
                symbol_candidates=["symbol", "ticker"],
                name_candidates=["company", "name"],
                suffix="",
                source="wikipedia_dow30",
            )
            _add(rows)
        except Exception as e:
            errors.append(f"dow30: {e}")

        # FTSE100 (Yahoo uses .L)
        try:
            rows = wiki_generic_universe(
                url=WIKI_FTSE_URL,
                category="Ações UK (FTSE100)",
                symbol_candidates=["epic", "ticker", "symbol"],
                name_candidates=["company", "constituent", "name"],
                suffix=".L",
                source="wikipedia_ftse100",
            )
            _add(rows)
        except Exception as e:
            errors.append(f"ftse100: {e}")

        # DAX (Yahoo uses .DE)
        try:
            rows = wiki_generic_universe(
                url=WIKI_DAX_URL,
                category="Ações DE (DAX)",
                symbol_candidates=["ticker", "symbol"],
                name_candidates=["company", "name"],
                suffix=".DE",
                source="wikipedia_dax",
            )
            _add(rows)
        except Exception as e:
            errors.append(f"dax: {e}")

        # CAC40 (Yahoo uses .PA)
        try:
            rows = wiki_generic_universe(
                url=WIKI_CAC_URL,
                category="Ações FR (CAC40)",
                symbol_candidates=["ticker", "symbol"],
                name_candidates=["company", "name"],
                suffix=".PA",
                source="wikipedia_cac40",
            )
            _add(rows)
        except Exception as e:
            errors.append(f"cac40: {e}")

        # EuroStoxx50 (mixed suffix; keep raw and let validate deactivate)
        try:
            rows = wiki_generic_universe(
                url=WIKI_STOXX50_URL,
                category="Ações EU (EuroStoxx50)",
                symbol_candidates=["ticker", "symbol"],
                name_candidates=["company", "name"],
                suffix="",
                source="wikipedia_eurostoxx50",
            )
            _add(rows)
        except Exception as e:
            errors.append(f"stoxx50: {e}")

        # Nikkei225 (Yahoo uses .T often numeric tickers)
        try:
            rows = wiki_generic_universe(
                url=WIKI_NIKKEI_URL,
                category="Ações JP (Nikkei225)",
                symbol_candidates=["ticker", "code", "symbol"],
                name_candidates=["company", "name"],
                suffix=".T",
                source="wikipedia_nikkei225",
            )
            _add(rows)
        except Exception as e:
            errors.append(f"nikkei225: {e}")

        # Hang Seng (Yahoo uses .HK; wiki may use "0005" codes)
        try:
            rows = wiki_generic_universe(
                url=WIKI_HSI_URL,
                category="Ações HK (Hang Seng)",
                symbol_candidates=["ticker", "code", "symbol"],
                name_candidates=["company", "name"],
                suffix=".HK",
                source="wikipedia_hsi",
            )
            _add(rows)
        except Exception as e:
            errors.append(f"hsi: {e}")

        # Crypto top N
        try:
            rows = coingecko_crypto_top(n=int(crypto_top_n))
            _add(rows)
        except Exception as e:
            errors.append(f"crypto_top: {e}")

        return {"inserted": inserted_total, "errors": errors}

    def validate_universe(self, universe_df: pd.DataFrame, sample_n: int = 160) -> Dict[str, Any]:
        if universe_df is None or universe_df.empty:
            return {"ok": False, "reason": "empty"}

        sub = universe_df.head(sample_n).copy()
        bad: List[str] = []
        okc = 0

        for _, r in sub.iterrows():
            t = str(r["ticker"]).strip()
            try:
                df = safe_download(t, min_rows=30)
                if df is None or df.empty:
                    bad.append(t)
                else:
                    okc += 1
            except Exception:
                bad.append(t)

        deac = self.store.deactivate_tickers(bad)
        return {"ok": True, "tested": len(sub), "ok_count": okc, "bad_count": len(bad), "deactivated": deac}

# ============================================================
# INDICATORS + RISK/REGIME/SCORE
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def compute_indicators(d: pd.DataFrame) -> pd.DataFrame:
    df = d.copy()
    close = df["close_final"].astype(float)

    df["ret"] = close.pct_change()
    df["logret"] = np.log(close / close.shift(1))

    df["SMA20"] = close.rolling(20).mean()
    df["SMA50"] = close.rolling(50).mean()

    df["STD20"] = close.rolling(20).std()
    df["ZScore"] = (close - df["SMA20"]) / (df["STD20"] + 1e-9)

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df["RSI14"] = 100 - (100 / (1 + rs))

    high = df["high"].astype(float)
    low = df["low"].astype(float)
    tr = pd.concat(
        [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
        axis=1,
    ).max(axis=1)
    df["ATR14"] = tr.rolling(14).mean()

    df["Equity"] = (1 + df["ret"].fillna(0)).cumprod()
    df["Peak"] = df["Equity"].cummax()
    df["Drawdown"] = (df["Equity"] - df["Peak"]) / df["Peak"]

    df["VolAnn"] = df["logret"].rolling(20).std() * np.sqrt(TRADING_DAYS) * 100

    df["Skew60"] = df["ret"].rolling(60).apply(lambda x: skew(x.dropna()), raw=False)
    df["Kurt60"] = df["ret"].rolling(60).apply(lambda x: kurtosis(x.dropna(), fisher=True), raw=False)

    def _var95(x: pd.Series) -> float:
        x = x.dropna()
        if len(x) < 10:
            return np.nan
        return float(np.quantile(x, 0.05))

    def _cvar95(x: pd.Series) -> float:
        x = x.dropna()
        if len(x) < 10:
            return np.nan
        var = float(np.quantile(x, 0.05))
        tail = x[x <= var]
        return float(tail.mean()) if len(tail) > 0 else np.nan

    df["VaR95"] = df["ret"].rolling(60).apply(_var95, raw=False)
    df["CVaR95"] = df["ret"].rolling(60).apply(_cvar95, raw=False)

    return df.dropna()

def compute_cost(spread_bps: int, slippage_bps: int, fee_bps: int, max_block_bps: int) -> Dict[str, Any]:
    total = int(spread_bps + slippage_bps + fee_bps)
    blocked = total >= int(max_block_bps)
    return {
        "total_bps": total,
        "blocked": blocked,
        "break_even_pct": total / 10000.0,
        "max_block_bps": int(max_block_bps),
    }

def regime_engine(d: pd.DataFrame, cost_bps: int) -> Dict[str, Any]:
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

    return {"label": label, "z": z, "vol": vol, "dd": dd, "slope": slope, "operability": score}

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

def meanrev_score(last: pd.Series) -> float:
    z = float(last["ZScore"])
    return float(clamp(50 + (-z * 18) - max(0, z - 1.0) * 12, 0, 100))

def risk_score(last: pd.Series) -> float:
    vol = float(last["VolAnn"])
    dd = float(last["Drawdown"])
    var95 = float(last.get("VaR95", 0.0))
    cvar95 = float(last.get("CVaR95", 0.0))

    v_pen = clamp((vol - 20) * 1.9, 0, 80)
    dd_pen = clamp(abs(dd) * 180, 0, 80)
    tail_pen = clamp(abs(cvar95) * 650, 0, 80) + clamp(abs(var95) * 500, 0, 60)

    return float(clamp(100 - (v_pen * 0.45 + dd_pen * 0.35 + tail_pen * 0.20), 0, 100))

def multi_score(d: pd.DataFrame, last: pd.Series, cost_bps: int, regime_label: str, weights: Dict[str, float]) -> Dict[str, Any]:
    ts = trend_score(last, d)
    mr = meanrev_score(last)
    rk = risk_score(last)

    wsum = float(weights["trend"] + weights["meanrev"] + weights["risk"])
    raw = ts * (weights["trend"] / wsum) + mr * (weights["meanrev"] / wsum) + rk * (weights["risk"] / wsum)

    p_cost = clamp(cost_bps * 2.8, 0, 80)
    p_reg = 45.0 if "STRESS" in regime_label else (25.0 if "VOL" in regime_label else 0.0)

    final = clamp(raw - (p_cost * 0.55 + p_reg * 0.45), 0, 100)

    return {
        "final_score": round(float(final), 1),
        "trend_score": round(float(ts), 1),
        "meanrev_score": round(float(mr), 1),
        "risk_score": round(float(rk), 1),
    }

def monte_carlo_ruin(win_rate: float, payoff: float, risk_per_trade: float, sims: int = 2200, trades: int = 220) -> float:
    win_rate = clamp(win_rate, 0.01, 0.99)
    payoff = clamp(payoff, 0.5, 10.0)
    risk_per_trade = clamp(risk_per_trade, 0.001, 0.2)

    outcomes = np.random.choice([1, 0], size=(sims, trades), p=[win_rate, 1 - win_rate])
    pnl = np.where(outcomes == 1, payoff * risk_per_trade, -risk_per_trade)
    equity = pnl.cumsum(axis=1)
    ruin = (equity < -0.50).any(axis=1)
    return float(ruin.mean() * 100)

def sizing_by_atr(price: float, atr: float, capital: float, risk_pct: float, stop_atr_mult: float) -> Dict[str, Any]:
    risk_cash = capital * (risk_pct / 100.0)
    stop_dist = atr * stop_atr_mult
    qty = int(max(0, risk_cash / (stop_dist + 1e-12)))
    return {"qty": qty, "stop_dist": stop_dist, "risk_cash": risk_cash}

def verdict_engine(regime: Dict[str, Any], cost: Dict[str, Any], ruin_pct: float, score: float,
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

    if float(regime["operability"]) < 35 and status != "BLOQUEIO":
        status = "DEFENSIVO"
        reasons.append("OPERABILITY_LOW")

    if score < 40 and status != "BLOQUEIO":
        status = "DEFENSIVO"
        reasons.append("SCORE_LOW")

    command = {"AUTORIZADO": "READY", "DEFENSIVO": "DEFENSIVE", "BLOQUEIO": "BLOCKED"}[status]
    return {"status": status, "command": command, "reasons": reasons or ["OK"]}

# ============================================================
# SAFETY GUARD (operational)
# ============================================================

@dataclass(frozen=True)
class SafetyConfig:
    tz_market: str = DEFAULT_MARKET_TZ
    open_hhmm: str = "10:00"
    close_hhmm: str = "17:55"
    auction_pre_open_start: str = "09:45"
    auction_pre_open_end: str = "10:00"
    auction_close_start: str = "17:45"
    auction_close_end: str = "18:10"
    max_daily_loss_pct: float = 3.0

class MockBroker:
    def ping(self) -> bool:
        return True
    def get_open_positions(self) -> List[Dict[str, Any]]:
        return []
    def get_account_state(self) -> Dict[str, Any]:
        return {"status": "OK", "broker": "MOCK"}

class SafetyGuard:
    def __init__(self, store: SQLiteStore, broker: MockBroker, cfg: SafetyConfig):
        self.store = store
        self.broker = broker
        self.cfg = cfg

    def _parse_hhmm(self, hhmm: str) -> Tuple[int, int]:
        h, m = hhmm.split(":")
        return int(h), int(m)

    def _now_market(self) -> dt.datetime:
        tz = pytz.timezone(self.cfg.tz_market)
        return dt.datetime.now(tz)

    def _in_range(self, now: dt.datetime, start: str, end: str) -> bool:
        sh, sm = self._parse_hhmm(start)
        eh, em = self._parse_hhmm(end)
        stt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
        enn = now.replace(hour=eh, minute=em, second=0, microsecond=0)
        return stt <= now <= enn

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
        date_utc = dt.datetime.utcnow().strftime("%Y-%m-%d")
        pnl = self.store.daily_realized_pnl(date_utc)
        limit = -(capital * (self.cfg.max_daily_loss_pct / 100.0))
        if pnl <= limit:
            return False, f"KILL_SWITCH_DAILY_LOSS pnl={pnl:.2f} limit={limit:.2f}"
        return True, "OK"

    def validate(self, ticker: str, capital: float) -> Dict[str, Any]:
        if not self.broker.ping():
            return {"ok": False, "reason": "BROKER_OFFLINE"}

        ok_time, r_time = self._is_trading_time()
        if not ok_time:
            return {"ok": False, "reason": r_time}

        ok_kill, r_kill = self._kill_switch(capital)
        if not ok_kill:
            return {"ok": False, "reason": r_kill}

        return {"ok": True, "reason": "OK"}

# ============================================================
# ALT DATA (RSS + sentiment fallback)
# ============================================================

def fetch_rss_headlines(url: str, limit: int = 10) -> List[str]:
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "xml")
        items = soup.find_all("item")
        out = []
        for it in items[:limit]:
            title = it.find("title")
            if title and title.text:
                out.append(title.text.strip())
        return out
    except Exception:
        return []

def naive_sentiment_score(headlines: List[str]) -> float:
    if not headlines:
        return 0.0
    neg = ["crash", "collapse", "selloff", "fear", "war", "recession", "defaults", "downgrade", "risk", "tension", "fall", "drops", "plunge"]
    pos = ["rally", "surge", "beats", "growth", "bull", "record", "upgrades", "optimism", "breakout", "higher", "gains", "soars"]
    score = 0
    txt = " ".join(headlines).lower()
    for w in neg:
        score -= txt.count(w)
    for w in pos:
        score += txt.count(w)
    return float(clamp(score / 15.0, -1.0, 1.0))

def causal_root_guess(chg_usdbrl: float, chg_ibov: float, chg_spx: float) -> str:
    if chg_usdbrl > 0 and chg_ibov < 0:
        return "Macro Risk-Off (USD↑, Bolsa↓)"
    if chg_usdbrl < 0 and chg_ibov < 0:
        return "Risco Idiossincrático BR (USD↓, Bolsa↓)"
    if chg_spx > 0 and chg_usdbrl < 0:
        return "Risk-On Global (SPX↑, USD↓)"
    return "Mixed / Inconclusive"

# ============================================================
# OPENAI COUNCIL ENGINE
# ============================================================

@dataclass(frozen=True)
class AIConfig:
    enabled: bool
    model: str = "gpt-4.1-mini"
    timeout_sec: int = 30
    max_output_tokens: int = 950

class CouncilEngine:
    def __init__(self, cfg: AIConfig):
        self.cfg = cfg
        self.client = None
        if cfg.enabled and OpenAI is not None:
            try:
                self.client = OpenAI(timeout=cfg.timeout_sec)
            except Exception:
                self.client = None

    def _api_ready(self) -> bool:
        if not self.cfg.enabled:
            return False
        if self.client is None:
            return False
        if not os.getenv("OPENAI_API_KEY", "").strip():
            return False
        return True

    def run(self, payload: Dict[str, Any], headlines: Dict[str, List[str]]) -> Dict[str, Any]:
        if not self._api_ready():
            return self._fallback(payload, headlines, reason="AI_DISABLED/NO_KEY/SKD_FAIL")

        try:
            prompt = self._build_prompt(payload, headlines)
            resp = self.client.responses.create(
                model=self.cfg.model,
                input=prompt,
                max_output_tokens=self.cfg.max_output_tokens,
            )
            text = getattr(resp, "output_text", None)
            if not text:
                text = str(resp)
            return {"ok": True, "mode": "openai", "text": text.strip()}
        except Exception as e:
            return self._fallback(payload, headlines, reason=f"OPENAI_ERROR: {e}")

    def _build_prompt(self, payload: Dict[str, Any], headlines: Dict[str, List[str]]) -> str:
        tech = json.dumps(payload, ensure_ascii=False)
        news = json.dumps(headlines, ensure_ascii=False)

        return f"""
Você é o ATLAS Council de um fundo quant institucional.
Simule 4 personas e produza um relatório operacional extremamente denso.

PERSONAS:
1) THE BULL (alpha): momentum, breakout, convexidade, gatilhos.
2) THE BEAR (risco): caudas, regime, macro ruim, custo, invalidações.
3) MACRO STRATEGIST: macro, geopolítica, FX/commodities, narrativa do dia.
4) THE JUDGE: veredito final com plano operacional (READY/DEFENSIVE/BLOCKED).

FORMATO OBRIGATÓRIO:
- BULL:
- BEAR:
- MACRO:
- JUDGE:
  - Command:
  - Setup (entry logic):
  - Risk (stop/size):
  - Targets:
  - Invalidations:
  - If-Then (cenários):
  - Checklist:

DADOS TÉCNICOS (JSON):
{tech}

HEADLINES RSS (JSON):
{news}

REGRAS:
- Responder em PT-BR.
- Não inventar números contábeis. Se faltar dado, diga "sem confirmação".
- Se ativo for FX/Cripto/Commodity, trate drivers macro e volatilidade.
"""

    def _fallback(self, payload: Dict[str, Any], headlines: Dict[str, List[str]], reason: str) -> Dict[str, Any]:
        reg = payload.get("regime", {})
        verdict = payload.get("verdict", {})
        score = payload.get("score", {})
        cost = payload.get("cost", {})
        fear = payload.get("altdata", {}).get("fear_greed", 0.0)

        lines = [
            f"[AI FALLBACK] ({reason})",
            f"REGIME: {reg.get('label','—')} | SCORE: {score.get('final_score','—')} | COST: {cost.get('total_bps','—')} bps",
            f"FEAR/GREED: {fear:+.2f} | COMMAND: {verdict.get('command','—')} ({verdict.get('status','—')})",
            "",
            "BULL: Se score alto e regime não hostil, buscar continuação (SMA20>SMA50) com stop por ATR.",
            "BEAR: Se VOL/STRESS ou custo alto, reduzir risco e evitar alavancagem.",
            "MACRO: Leia USDBRL, SPX e headlines como driver do dia (risk-on/off).",
            "JUDGE: Operar somente se invalidação estiver clara; sizing conservador.",
        ]
        return {"ok": True, "mode": "fallback", "text": "\n".join(lines)}

# ============================================================
# CHARTS
# ============================================================

def plot_candles(d: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=d.index, open=d["open"], high=d["high"], low=d["low"], close=d["close_final"], name="PX"
    ))
    fig.add_trace(go.Scatter(x=d.index, y=d["SMA20"], name="SMA20", opacity=0.85))
    fig.add_trace(go.Scatter(x=d.index, y=d["SMA50"], name="SMA50", opacity=0.65))
    fig.update_layout(template="plotly_dark", height=560, xaxis_rangeslider_visible=False, margin=dict(l=8, r=8, t=8, b=8))
    return fig

def plot_drawdown(d: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d.index, y=d["Drawdown"] * 100, name="Drawdown %"))
    fig.update_layout(template="plotly_dark", height=260, margin=dict(l=8, r=8, t=18, b=8), yaxis_title="Drawdown %")
    return fig

def plot_vol(d: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d.index, y=d["VolAnn"], name="VolAnn"))
    fig.update_layout(template="plotly_dark", height=260, margin=dict(l=8, r=8, t=18, b=8), yaxis_title="Vol %")
    return fig

def plot_returns_hist(d: pd.DataFrame) -> go.Figure:
    ret = d["ret"].dropna() * 100
    fig = px.histogram(ret, nbins=45, title="Retornos Diários (%) — distribuição")
    fig.update_layout(template="plotly_dark", height=280, margin=dict(l=8, r=8, t=30, b=8))
    return fig

def heatmap_corr(prices: pd.DataFrame) -> go.Figure:
    corr = prices.pct_change().dropna().corr()
    fig = px.imshow(corr, text_auto=True, aspect="auto", title="Risk Heatmap — Correlação (retornos)")
    fig.update_layout(template="plotly_dark", height=520, margin=dict(l=8, r=8, t=38, b=8))
    return fig

# ============================================================
# TAPE
# ============================================================

def render_tape(items: List[Dict[str, Any]]) -> None:
    if not items:
        line = "<span class='atlas-tape-item' style='color:var(--muted)'>TAPE: NO DATA (Clique Refresh)</span>"
    else:
        parts = []
        for it in items[:20]:
            cls = "green" if it["chg_pct"] >= 0 else "red"
            sign = "+" if it["chg_pct"] >= 0 else ""
            parts.append(
                f"<span class='atlas-tape-item'>"
                f"<span class='tape-ticker'>{it['ticker']}</span> "
                f"{it['price']:.2f} "
                f"<span class='{cls}'>({sign}{it['chg_pct']:.2f}%)</span></span>"
            )
        line = "".join(parts)

    st.markdown(
        f"""
        <div class="atlas-tape-wrap">
          <div class="atlas-tape-move">
            {line}{line}{line}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def build_tape_snapshot(tickers: List[str]) -> List[Dict[str, Any]]:
    out = []
    uniq = []
    for t in tickers:
        t = normalize_ticker(t)
        if t and t not in uniq:
            uniq.append(t)

    for t in uniq[:12]:
        try:
            df = safe_download(t, min_rows=5)
            if df is None or df.empty:
                continue
            d = standardize_ohlcv(df)
            s = d["close_final"].dropna()
            if len(s) < 2:
                continue
            last = float(s.iloc[-1])
            prev = float(s.iloc[-2])
            chg = (last / (prev + 1e-9) - 1.0) * 100
            out.append({"ticker": t, "price": last, "chg_pct": chg})
        except Exception:
            continue
    return out

# ============================================================
# MAIN APP
# ============================================================

def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="📟", layout="wide")
    apply_theme()

    store = SQLiteStore(DB_PATH)
    uni = UniverseEngine(store)
    broker = MockBroker()

    # Seed core universe always
    uni.seed_core()

    # Sidebar
    st.sidebar.subheader("UNIVERSE BUILDER — GLOBAL")

    if st.sidebar.button("⚡ BUILD ALL (World + Crypto Top 200)"):
        with st.sidebar.spinner("Building global universe..."):
            res = uni.build_all(crypto_top_n=200)
        st.sidebar.success(f"Inserted +{res['inserted']}")
        if res["errors"]:
            st.sidebar.warning("Algumas fontes falharam (normal às vezes):")
            for e in res["errors"][:6]:
                st.sidebar.caption(f"- {e}")

    if st.sidebar.button("🧨 RESET UNIVERSE (limpar)"):
        store.reset_universe()
        uni.seed_core()
        st.sidebar.success("Universe resetado. Core re-seedado.")

    # Optional validation sample
    st.sidebar.subheader("VALIDAÇÃO")
    validate_n = st.sidebar.slider("Amostra p/ validar (desativa ruins)", 40, 240, 140, 10)
    if st.sidebar.button("✅ VALIDATE (sample)"):
        df_uni = store.get_universe_df(True)
        with st.sidebar.spinner("Validating..."):
            res = uni.validate_universe(df_uni, sample_n=int(validate_n))
        st.sidebar.success(f"Testados {res['tested']} | OK {res['ok_count']} | Ruins {res['bad_count']} | Desativados {res['deactivated']}")

    st.sidebar.subheader("AI COUNCIL")
    ai_enabled = st.sidebar.toggle("Ativar OpenAI", value=bool(os.getenv("OPENAI_API_KEY", "").strip()))
    ai_cfg = AIConfig(enabled=ai_enabled, model="gpt-4.1-mini", timeout_sec=30, max_output_tokens=950)
    council = CouncilEngine(ai_cfg)

    st.sidebar.subheader("SAFETY")
    safety_cfg = SafetyConfig(
        tz_market=DEFAULT_MARKET_TZ,
        open_hhmm=st.sidebar.text_input("Market Open (HH:MM)", "10:00"),
        close_hhmm=st.sidebar.text_input("Market Close (HH:MM)", "17:55"),
        max_daily_loss_pct=float(st.sidebar.slider("Max Daily Loss %", 0.5, 10.0, 3.0, 0.5)),
    )
    safety_guard = SafetyGuard(store, broker, safety_cfg)

    st.sidebar.subheader("PROFILE")
    profile = st.sidebar.selectbox("Perfil", ["Trend", "MeanReversion", "Defensive"], index=0)
    profile_cfg = {
        "Trend": {"risk_cap_pct": 2.0, "stop_atr": 2.0, "target_r": 2.2, "max_cost_block_bps": 35, "strict_vol": 60, "strict_dd_pct": -35},
        "MeanReversion": {"risk_cap_pct": 1.5, "stop_atr": 1.6, "target_r": 1.6, "max_cost_block_bps": 28, "strict_vol": 55, "strict_dd_pct": -30},
        "Defensive": {"risk_cap_pct": 1.0, "stop_atr": 2.4, "target_r": 1.5, "max_cost_block_bps": 22, "strict_vol": 45, "strict_dd_pct": -20},
    }[profile]

    # Universe select
    universe_df = store.get_universe_df(only_active=True)

    colA, colB = st.columns([3, 1])
    with colA:
        st.markdown(f"# {APP_TITLE}")
        st.markdown(
            f"<span class='small'>UNIVERSE ATIVO: <b style='color:var(--amber2)'>{len(universe_df)}</b> | PROFILE: <b>{profile}</b></span>",
            unsafe_allow_html=True,
        )
    with colB:
        if st.button("🔁 Refresh Tape"):
            tape_list = ["^BVSP", "^GSPC", "USDBRL=X", "BTC-USD", "GC=F", "CL=F", "DX-Y.NYB"]
            st.session_state["tape_items"] = build_tape_snapshot(tape_list)

    if "tape_items" not in st.session_state:
        st.session_state["tape_items"] = []
    render_tape(st.session_state["tape_items"])
    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

    if universe_df.empty:
        st.error("Universe vazio. Clique em BUILD ALL.")
        return

    st.sidebar.subheader("ASSET SELECTION")
    cats = sorted(universe_df["category"].unique().tolist())
    cat = st.sidebar.selectbox("Classe", cats, index=0)

    sub = universe_df[universe_df["category"] == cat].copy()
    asset_name = st.sidebar.selectbox("Ativo", sub["name"].tolist(), index=0)
    row = sub[sub["name"] == asset_name].iloc[0].to_dict()

    ticker = normalize_ticker(str(row["ticker"]).strip())
    asset_display = f"{asset_name} ({ticker})"

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["DEEP DIVE", "SCREENER", "RISK HEATMAP", "LEDGER", "DIAGNOSTICS"])

    with tab1:
        st.subheader("DEEP DIVE — Institutional Mode")
        st.markdown(
            f"<span class='small'>ASSET: <b style='color:var(--amber2)'>{asset_display}</b> | CLASS: <b>{cat}</b></span>",
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns([1, 1, 1])

        with c1:
            st.markdown("**COST (bps)**")
            spread = st.number_input(tt_label("SPREAD", "Spread em bps (bid/ask)."), 0, 200, 6)
            slippage = st.number_input(tt_label("SLIPPAGE", "Slippage em bps (execução)."), 0, 200, 6)
            fee = st.number_input(tt_label("FEE", "Taxas/custos em bps."), 0, 200, 2)

        with c2:
            st.markdown("**RISK INPUTS**")
            win = st.slider(tt_label("WIN %", "Taxa de acerto estimada para Monte Carlo."), 30, 70, 45) / 100.0
            payoff = st.slider(tt_label("PAYOFF (R)", "R médio nos trades vencedores."), 1.0, 5.0, 2.0, 0.1)
            risk_pct = st.slider(tt_label("RISK/TRD %", "Risco por trade (% capital)."), 0.5, 5.0, 2.0, 0.1)
            capital = st.number_input(tt_label("CAPITAL", "Capital base para sizing."), min_value=100.0, value=10000.0, step=500.0)

        with c3:
            st.markdown("**UI**")
            lookback = st.slider("Lookback candles", 120, 520, 280, 20)
            tz_ui = st.selectbox("Timezone UI", [DEFAULT_UI_TZ, "UTC", "America/New_York", "Europe/Zurich"], index=0)

        analyze = st.button("🚀 ANALYZE", type="primary")

        if analyze:
            with st.spinner("Baixando dados + calculando indicadores..."):
                raw = safe_download(ticker, min_rows=80)
                if raw is None or raw.empty:
                    st.error("Sem dados do Yahoo para esse ticker (pode ser símbolo/sufixo).")
                    st.stop()

                d0 = standardize_ohlcv(raw)
                d = compute_indicators(d0)

            # Local UI index
            try:
                d_ui = d.copy()
                d_ui.index = d_ui.index.tz_convert(pytz.timezone(tz_ui))
            except Exception:
                d_ui = d.copy()

            last = d.iloc[-1]
            prev = d.iloc[-2]
            px_last = float(last["close_final"])
            chg_pct = float((px_last / (float(prev["close_final"]) + 1e-9) - 1.0) * 100)

            cost = compute_cost(int(spread), int(slippage), int(fee), int(profile_cfg["max_cost_block_bps"]))
            reg = regime_engine(d, cost["total_bps"])
            weights = {"trend": 0.50, "meanrev": 0.15, "risk": 0.35}
            score = multi_score(d, last, cost["total_bps"], reg["label"], weights)

            risk_eff = min(float(risk_pct), float(profile_cfg["risk_cap_pct"]))
            ruin = monte_carlo_ruin(win, payoff, risk_eff / 100.0)

            verdict = verdict_engine(
                regime=reg, cost=cost, ruin_pct=ruin, score=score["final_score"],
                strict_vol=float(profile_cfg["strict_vol"]),
                strict_dd_pct=float(profile_cfg["strict_dd_pct"]),
                ruin_threshold=22.0,
            )

            # RSS & sentiment
            headlines = {k: fetch_rss_headlines(v, limit=8) for k, v in RSS_FEEDS.items()}
            fear_greed = naive_sentiment_score(sum(headlines.values(), []))

            # Causal guess
            usd_chg = 0.0
            ibov_chg = 0.0
            spx_chg = 0.0
            try:
                tmap = {x["ticker"]: x for x in st.session_state.get("tape_items", [])}
                usd_chg = float(tmap.get("USDBRL=X", {}).get("chg_pct", 0.0))
                ibov_chg = float(tmap.get("^BVSP", {}).get("chg_pct", 0.0))
                spx_chg = float(tmap.get("^GSPC", {}).get("chg_pct", 0.0))
            except Exception:
                pass
            root_cause = causal_root_guess(usd_chg, ibov_chg, spx_chg)

            payload = {
                "ticker": ticker,
                "name": asset_name,
                "category": cat,
                "price": px_last,
                "chg_pct": chg_pct,
                "regime": reg,
                "score": score,
                "cost": cost,
                "ruin": ruin,
                "verdict": verdict,
                "altdata": {
                    "fear_greed": fear_greed,
                    "root_cause_guess": root_cause,
                    "usdbrl_chg": usd_chg,
                    "ibov_chg": ibov_chg,
                    "spx_chg": spx_chg,
                },
                "last_metrics": {
                    "ATR14": float(last["ATR14"]),
                    "ZScore": float(last["ZScore"]),
                    "RSI14": float(last["RSI14"]),
                    "VolAnn": float(last["VolAnn"]),
                    "Drawdown": float(last["Drawdown"]),
                    "VaR95": float(last.get("VaR95", np.nan)),
                    "CVaR95": float(last.get("CVaR95", np.nan)),
                    "Skew60": float(last.get("Skew60", np.nan)),
                    "Kurt60": float(last.get("Kurt60", np.nan)),
                },
            }

            # KPIs
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            with k1:
                kpi_card("PX_LAST", f"{px_last:,.2f}", "Preço atual", help_key="PX_LAST")
            with k2:
                kpi_card("CHG%", f"{chg_pct:+.2f}%", "Dia", help_key="CHG%")
            with k3:
                kpi_card("REGIME", reg["label"], f"Operability {reg['operability']}/100", help_key="REGIME")
            with k4:
                kpi_card("SCORE", f"{score['final_score']:.1f}", f"T:{score['trend_score']} MR:{score['meanrev_score']} R:{score['risk_score']}", help_key="SCORE")
            with k5:
                kpi_card("COST_BPS", f"{cost['total_bps']} bps", f"Break-even {cost['break_even_pct']*100:.2f}%", help_key="COST_BPS")
            with k6:
                kpi_card("RUIN", f"{ruin:.2f}%", verdict["command"], help_key="RUIN")

            st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

            # Charts
            st.plotly_chart(plot_candles(d_ui.tail(lookback)), use_container_width=True)
            a, b = st.columns([1, 1])
            with a:
                st.plotly_chart(plot_drawdown(d_ui.tail(lookback)), use_container_width=True)
            with b:
                st.plotly_chart(plot_vol(d_ui.tail(lookback)), use_container_width=True)

            st.plotly_chart(plot_returns_hist(d_ui.tail(lookback)), use_container_width=True)

            # AI report
            st.markdown("## 🧠 Relatório Institucional (Council)")
            st.caption("Bull + Bear + Macro + Judge. Se sem key, cai em fallback consistente.")
            council_out = council.run(payload, headlines=headlines)
            st.code(council_out["text"])

            # Order Ticket
            st.markdown("## 🎟️ Order Ticket (SIM + Safety)")
            side = st.selectbox("SIDE", ["BUY", "SELL"])
            order_type = st.selectbox("TYPE", ["MARKET", "LIMIT"])
            tif = st.selectbox("TIF", ["DAY", "GTC"])

            stop_atr = st.slider(tt_label("STOP xATR", "Stop como múltiplo do ATR14."), 1.0, 4.0, float(profile_cfg["stop_atr"]), 0.1)
            target_r = st.slider(tt_label("TARGET (R)", "Alvo em múltiplos do risco (R)."), 1.0, 5.0, float(profile_cfg["target_r"]), 0.1)

            atr = float(last["ATR14"])
            stop = px_last - stop_atr * atr if side == "BUY" else px_last + stop_atr * atr
            target = px_last + target_r * (px_last - stop) if side == "BUY" else px_last - target_r * (stop - px_last)

            sizing = sizing_by_atr(px_last, atr, capital, risk_eff, stop_atr)
            qty = int(sizing["qty"])
            notional = float(qty * px_last)

            limit_price = None
            if order_type == "LIMIT":
                limit_price = st.number_input("LIMIT PRICE", min_value=0.01, value=float(px_last), step=0.10)

            tags = st.text_input("TAGS", value=f"{profile}|{reg['label']}|{cat}")

            st.write({"qty": qty, "notional": notional, "stop": stop, "target": target, "risk_pct": risk_eff})

            if st.button("🧾 LOG ORDER (SQLite)"):
                safety = safety_guard.validate(ticker, capital)
                if not safety["ok"]:
                    st.error(f"SAFETY BLOCK: {safety['reason']}")
                else:
                    ts_utc = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                    store.log_order({
                        "timestamp_utc": ts_utc,
                        "ticker": ticker,
                        "side": side,
                        "order_type": order_type,
                        "tif": tif,
                        "qty": qty,
                        "notional": notional,
                        "price_ref": px_last,
                        "limit_price": limit_price,
                        "stop": stop,
                        "target": target,
                        "risk_pct": risk_eff,
                        "regime": reg["label"],
                        "score": score["final_score"],
                        "cost_bps": cost["total_bps"],
                        "status": verdict["status"],
                        "tags": tags,
                        "realized_pnl": 0.0,
                    })
                    st.success("ORDER LOGGED ✅")

            st.markdown("## 📚 Glossário (hover nos ?)")
            st.markdown(
                f"- **ZScore**: {TOOLTIPS['ZScore']}\n"
                f"- **RSI14**: {TOOLTIPS['RSI14']}\n"
                f"- **ATR14**: {TOOLTIPS['ATR14']}\n"
                f"- **VolAnn**: {TOOLTIPS['VolAnn']}\n"
                f"- **Score**: {TOOLTIPS['SCORE']}\n"
                f"- **Fear/Greed**: {TOOLTIPS['FEAR']}\n"
            )

    with tab2:
        st.subheader("SCREENER — Amostra Controlada")
        st.caption("Screener em amostras evita travamento e dá robustez.")

        sample_n = st.slider("Tamanho da amostra", 5, 120, 25)
        pick_cat = st.selectbox("Categoria do Screener", sorted(universe_df["category"].unique().tolist()), index=0)
        sub = universe_df[universe_df["category"] == pick_cat].copy().head(sample_n)

        if st.button("▶ Run Screener"):
            out = []
            prog = st.progress(0)

            for i, (_, rr) in enumerate(sub.iterrows()):
                t = str(rr["ticker"]).strip()
                try:
                    raw = safe_download(t, min_rows=80)
                    if raw is None or raw.empty:
                        prog.progress((i + 1) / len(sub))
                        continue
                    d0 = standardize_ohlcv(raw)
                    d = compute_indicators(d0)
                    last = d.iloc[-1]
                    out.append({
                        "ticker": t,
                        "px": float(last["close_final"]),
                        "z": float(last["ZScore"]),
                        "rsi": float(last["RSI14"]),
                        "vol%": float(last["VolAnn"]),
                        "dd%": float(last["Drawdown"] * 100),
                        "var95%": float(last.get("VaR95", np.nan) * 100),
                    })
                except Exception:
                    pass
                prog.progress((i + 1) / len(sub))

            if not out:
                st.warning("Sem resultados (amostra pode ter tickers inválidos). Rode VALIDATE sample.")
            else:
                df = pd.DataFrame(out)
                df["z_abs"] = df["z"].abs()
                df = df.sort_values(["z_abs", "vol%"], ascending=[False, True]).drop(columns=["z_abs"])
                st.dataframe(df, use_container_width=True, height=560)

    with tab3:
        st.subheader("RISK HEATMAP — Correlação de Watchlist")
        st.caption("Evita exposição duplicada ao mesmo fator. Use 6-20 ativos.")

        # Default watchlist
        default_watch = ["^BVSP", "^GSPC", "USDBRL=X", "BTC-USD", "GC=F", "CL=F", "DX-Y.NYB", ticker]
        choices = sorted(universe_df["ticker"].unique().tolist())
        default_sel = [normalize_ticker(x) for x in default_watch if normalize_ticker(x) in choices]

        selected = st.multiselect("Selecione ativos", choices, default=default_sel)

        if st.button("📊 Gerar Heatmap"):
            if len(selected) < 3:
                st.warning("Selecione pelo menos 3 ativos.")
            else:
                prices = {}
                bad = []
                with st.spinner("Baixando séries..."):
                    for t in selected[:28]:
                        raw = safe_download(t, min_rows=80)
                        if raw is None or raw.empty:
                            bad.append(t)
                            continue
                        d0 = standardize_ohlcv(raw)
                        prices[t] = d0["close_final"].astype(float)

                if len(prices) < 3:
                    st.error("Poucos ativos com dados válidos.")
                else:
                    pxdf = pd.DataFrame(prices).dropna()
                    st.plotly_chart(heatmap_corr(pxdf.tail(250)), use_container_width=True)
                    if bad:
                        st.info(f"Sem dados (ignorado): {bad[:12]}")

    with tab4:
        st.subheader("LEDGER — SQLite")
        df = store.read_ledger(limit=600)
        if df.empty:
            st.info("Ledger vazio.")
        else:
            st.dataframe(df, use_container_width=True, height=600)

    with tab5:
        st.subheader("DIAGNOSTICS")
        st.write({
            "db_path": DB_PATH,
            "universe_active": int(len(universe_df)),
            "ai_enabled": bool(ai_enabled),
            "openai_key_set": bool(os.getenv("OPENAI_API_KEY", "").strip()),
            "broker": broker.get_account_state(),
            "time_utc": now_utc().isoformat(),
        })
        st.markdown("### Observação importante sobre 'TODOS os tickers do mundo'")
        st.write(
            "Não existe um único endpoint universal e limpo (sem pagar) que entregue 100% de todos os tickers com alta confiabilidade. "
            "O que esse ATLAS faz é o melhor caminho institucional: junta múltiplas fontes (Wikipedia + Yahoo + CoinGecko + curado), "
            "categoriza e permite validação automática (desativando inválidos)."
        )

if __name__ == "__main__":
    main()
