from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd
from database.sqlite_store import SQLiteStore


DEFAULT_UNIVERSE = [
    {"name": "PETROBRAS PN", "category": "Ações Brasil", "ticker_yahoo": "PETR4.SA", "currency_code": "BRL", "base": "spot", "country": "BR", "exchange": "B3", "priority_source": "yahoo", "bridge_key": "PETR4"},
    {"name": "VALE ON",      "category": "Ações Brasil", "ticker_yahoo": "VALE3.SA", "currency_code": "BRL", "base": "spot", "country": "BR", "exchange": "B3", "priority_source": "yahoo", "bridge_key": "VALE3"},
    {"name": "ITAU PN",      "category": "Ações Brasil", "ticker_yahoo": "ITUB4.SA", "currency_code": "BRL", "base": "spot", "country": "BR", "exchange": "B3", "priority_source": "yahoo", "bridge_key": "ITUB4"},
    {"name": "IBOV",         "category": "Índices",      "ticker_yahoo": "^BVSP", "currency_code": "BRL", "base": "index", "country": "BR", "exchange": "B3", "priority_source": "yahoo", "bridge_key": "^BVSP"},
    {"name": "S&P 500",      "category": "Índices",      "ticker_yahoo": "^GSPC", "currency_code": "USD", "base": "index", "country": "US", "exchange": "SP", "priority_source": "yahoo", "bridge_key": "^GSPC"},
    {"name": "USD/BRL",      "category": "Mercado de Câmbio", "ticker_yahoo": "BRL=X", "currency_code": "BRL", "base": "fx", "country": "BR", "exchange": "FX", "priority_source": "yahoo", "bridge_key": "USDBRL"},
    {"name": "BTC",          "category": "Cripto",       "ticker_yahoo": "BTC-USD", "currency_code": "USD", "base": "crypto", "country": "GLOBAL", "exchange": "CRYPTO", "priority_source": "yahoo", "bridge_key": "BTC"},
    {"name": "GOLD",         "category": "Commodities",  "ticker_yahoo": "GC=F", "currency_code": "USD", "base": "cmdty", "country": "GLOBAL", "exchange": "CM", "priority_source": "yahoo", "bridge_key": "GOLD"},
]


class UniverseLoader:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def ensure_seed(self) -> int:
        existing = self.store.get_universe()
        if existing:
            return 0
        return self.store.upsert_universe_rows(DEFAULT_UNIVERSE)

    def load(self) -> pd.DataFrame:
        """
        Carrega do SQLite e normaliza tickers BR automaticamente.
        """
        self.ensure_seed()
        df = pd.DataFrame(self.store.get_universe())
        if df.empty:
            return df

        from core.data.ticker_resolver import TickerResolver

        def _fix_row(r):
            t = str(r.get("ticker_yahoo", "")).strip()
            c = str(r.get("category", "")).strip()
            resolved = TickerResolver.resolve(t, c)
            return resolved if resolved else t

        df["ticker_yahoo"] = df.apply(_fix_row, axis=1)
        return df

    def import_csv(self, path: str) -> int:
        df = pd.read_csv(path, sep=None, engine="python")
        df.columns = [c.strip().lower() for c in df.columns]

        rows: List[Dict[str, Any]] = []
        for _, r in df.iterrows():
            rows.append({
                "name": r.get("name", ""),
                "category": r.get("category", ""),
                "ticker_yahoo": r.get("ticker_yahoo", ""),
                "currency_code": r.get("currency_code", ""),
                "base": r.get("base", "spot"),
                "country": r.get("country", ""),
                "exchange": r.get("exchange", ""),
                "priority_source": r.get("priority_source", ""),
                "bridge_key": r.get("bridge_key", ""),
            })
        return self.store.upsert_universe_rows(rows)
