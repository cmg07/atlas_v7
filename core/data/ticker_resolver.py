from __future__ import annotations

import re


class TickerResolver:
    """
    Resolve tickers BR (B3) para o padrão Yahoo.
    Regra institucional: Ações Brasil -> .SA
    """

    _BAD = {"0", "000000", "NAN", "NONE", ""}

    @staticmethod
    def is_valid_ticker_syntax(t: str) -> bool:
        if t is None:
            return False
        s = str(t).strip().upper()

        if not s or s in TickerResolver._BAD:
            return False

        # rejeita números puros
        if re.fullmatch(r"\d+", s):
            return False

        # rejeita lixo de csv tipo "1;1644"
        if ";" in s or " " in s or "\t" in s:
            return False

        # muito longo = lixo
        if len(s) > 20:
            return False

        # aceita padrões comuns: PETR4, PETR4.SA, BRL=X, ^BVSP, BTC-USD, GC=F
        if re.fullmatch(r"[\^]?[A-Z0-9\.\=\-]+", s) is None:
            return False

        return True

    @staticmethod
    def resolve(ticker: str, category: str) -> str:
        t = str(ticker or "").strip().upper()
        c = str(category or "").strip()

        if not TickerResolver.is_valid_ticker_syntax(t):
            return ""

        # Regra: Brasil (Ações Brasil) -> .SA
        if c == "Ações Brasil":
            # já está resolvido
            if t.endswith(".SA"):
                return t

            # não mexer em tickers especiais
            if t.startswith("^") or t.endswith("=X") or t.endswith("=F") or "-USD" in t:
                return t

            # se não tem ponto, anexar .SA
            if "." not in t:
                return t + ".SA"

        return t
