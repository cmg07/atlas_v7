from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st


@dataclass(frozen=True)
class DataConfig:
    min_rows: int = 30


class DataRouter:
    """
    Yahoo -> Bridge -> Local
    Dogma: nunca roda no BOOT, só quando usuário manda ANALYZE / SCREENER / TAPE.
    """

    def __init__(self, cfg: DataConfig):
        self.cfg = cfg

    @staticmethod
@st.cache_data(ttl=900, show_spinner=False)
def _yahoo_cached(ticker: str, period: str, interval: str) -> pd.DataFrame:
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return yf.download(
            ticker,
            period=period,
            interval=interval,
            threads=False,
            progress=False,
            auto_adjust=False
        )

    def fetch_prices(
        self,
        ticker: str,
        priority_source: str = "",
        bridge_key: str = "",
        bridge_path: str = "data/bridge_prices.csv",
        local_prices_dir: str = "data/prices",
    ) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:

        attempts: List[Dict[str, Any]] = []
        used = None
        combos = [("2y", "1d"), ("1y", "1d"), ("6mo", "1d")]

        def to_utc(df: pd.DataFrame) -> pd.DataFrame:
            idx = pd.to_datetime(df.index, errors="coerce")
            if getattr(idx, "tz", None) is None:
                idx = idx.tz_localize("UTC")
            else:
                idx = idx.tz_convert("UTC")
            df = df.copy()
            df.index = idx
            return df

        def try_yahoo() -> Optional[pd.DataFrame]:
            nonlocal used
            for period, interval in combos:
                t0 = time.time()
                try:
                    df = self._yahoo_cached(ticker, period, interval)
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    if df is None or df.empty or len(df) < self.cfg.min_rows:
                        raise ValueError("insufficient")
                    df.columns = [c.lower() for c in df.columns]

                    if "adj close" in df.columns:
                        df["close_final"] = df["adj close"]
                    elif "close" in df.columns:
                        df["close_final"] = df["close"]
                    else:
                        raise ValueError("no close")

                    df = df.dropna(subset=["close_final"])
                    for col in ["open", "high", "low"]:
                        if col not in df.columns:
                            df[col] = df["close_final"]
                    if "volume" not in df.columns:
                        df["volume"] = np.nan

                    df = df[["open","high","low","close","close_final","volume"]].copy()
                    df = to_utc(df)
                    used = "yahoo"
                    attempts.append({"source":"yahoo","period":period,"ok":True,"rows":len(df),"ms":int((time.time()-t0)*1000)})
                    return df
                except Exception as e:
                    attempts.append({"source":"yahoo","period":period,"ok":False,"err":str(e),"rows":0,"ms":int((time.time()-t0)*1000)})
            return None

        def try_bridge() -> Optional[pd.DataFrame]:
            nonlocal used
            t0 = time.time()
            if not os.path.exists(bridge_path):
                attempts.append({"source":"bridge","ok":False,"rows":0,"ms":int((time.time()-t0)*1000)})
                return None
            try:
                df = pd.read_csv(bridge_path)
                df.columns = [c.lower().strip() for c in df.columns]
                need = {"date","ticker","open","high","low","close"}
                if not need.issubset(df.columns):
                    return None

                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).set_index("date").sort_index()

                key = (bridge_key or "").strip().upper()
                if key:
                    out = df[df["ticker"].astype(str).str.upper().eq(key)].copy()
                else:
                    out = df[df["ticker"].astype(str).str.upper().eq(ticker.upper())].copy()

                if out.empty or len(out) < self.cfg.min_rows:
                    attempts.append({"source":"bridge","ok":False,"rows":0,"ms":int((time.time()-t0)*1000)})
                    return None

                out["close_final"] = out["close"]
                if "volume" not in out.columns:
                    out["volume"] = np.nan

                out = out[["open","high","low","close","close_final","volume"]].copy()
                out = to_utc(out)
                used = "bridge"
                attempts.append({"source":"bridge","ok":True,"rows":len(out),"ms":int((time.time()-t0)*1000)})
                return out
            except Exception:
                attempts.append({"source":"bridge","ok":False,"rows":0,"ms":int((time.time()-t0)*1000)})
                return None

        def try_local() -> Optional[pd.DataFrame]:
            nonlocal used
            t0 = time.time()
            os.makedirs(local_prices_dir, exist_ok=True)
            safe = re.sub(r"[^\w\-\.\=]+", "_", ticker)
            path = os.path.join(local_prices_dir, f"{safe}.csv")
            if not os.path.exists(path):
                attempts.append({"source":"local","ok":False,"rows":0,"ms":int((time.time()-t0)*1000)})
                return None
            try:
                df = pd.read_csv(path)
                df.columns = [c.lower().strip() for c in df.columns]
                if "date" not in df.columns or "close" not in df.columns:
                    return None
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).set_index("date").sort_index()
                for col in ["open","high","low"]:
                    if col not in df.columns:
                        df[col] = df["close"]
                if "volume" not in df.columns:
                    df["volume"] = np.nan
                df["close_final"] = df["close"]
                df = df[["open","high","low","close","close_final","volume"]].dropna()
                df = to_utc(df)
                if len(df) < self.cfg.min_rows:
                    return None
                used = "local"
                attempts.append({"source":"local","ok":True,"rows":len(df),"ms":int((time.time()-t0)*1000)})
                return df
            except Exception:
                attempts.append({"source":"local","ok":False,"rows":0,"ms":int((time.time()-t0)*1000)})
                return None

        order = ["yahoo","bridge","local"]
        ps = (priority_source or "").strip().lower()
        if ps in order:
            order = [ps] + [x for x in order if x != ps]

        out = None
        for src in order:
            out = {"yahoo":try_yahoo, "bridge":try_bridge, "local":try_local}[src]()
            if out is not None and not out.empty:
                break

        if out is None or out.empty:
            return None, {"ok":False,"source":None,"attempts":attempts,"reason":"no data"}

        return out, {"ok":True,"source":used,"attempts":attempts}
