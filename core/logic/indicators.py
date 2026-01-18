from __future__ import annotations
import numpy as np
import pandas as pd
import streamlit as st
from scipy.stats import kurtosis, skew

TRADING_DAYS = 252

class IndicatorEngine:
    @staticmethod
    @st.cache_data(ttl=600, show_spinner=False)
    def calculate(df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy()
        close = d["close_final"].astype(float)

        d["ret"] = close.pct_change()
        d["logret"] = np.log(close / close.shift(1))

        d["SMA20"] = close.rolling(20).mean()
        d["SMA50"] = close.rolling(50).mean()

        d["STD20"] = close.rolling(20).std()
        d["ZScore"] = (close - d["SMA20"]) / (d["STD20"] + 1e-9)

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        d["RSI14"] = 100 - (100 / (1 + rs))

        high = d["high"].astype(float)
        low = d["low"].astype(float)
        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1
        ).max(axis=1)
        d["ATR14"] = tr.rolling(14).mean()

        d["Equity"] = (1 + d["ret"].fillna(0)).cumprod()
        d["Peak"] = d["Equity"].cummax()
        d["Drawdown"] = (d["Equity"] - d["Peak"]) / d["Peak"]

        d["VolAnn"] = d["logret"].rolling(20).std() * np.sqrt(TRADING_DAYS) * 100
        d["Skew60"] = d["ret"].rolling(60).apply(lambda x: skew(x.dropna()), raw=False)
        d["Kurt60"] = d["ret"].rolling(60).apply(lambda x: kurtosis(x.dropna(), fisher=True), raw=False)

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

        d["VaR95"] = d["ret"].rolling(60).apply(_var95, raw=False)
        d["CVaR95"] = d["ret"].rolling(60).apply(_cvar95, raw=False)

        return d.dropna()
