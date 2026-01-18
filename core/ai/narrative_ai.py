from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict
from openai import OpenAI

@dataclass(frozen=True)
class OpenAIConfig:
    enabled: bool
    model: str
    timeout_sec: int
    max_output_tokens: int

class NarrativeAI:
    """
    IA real via OpenAI.
    Se API/key falhar -> fallback operacional mínimo.
    """
    def __init__(self, cfg: OpenAIConfig):
        self.cfg = cfg
        self.client = None
        if cfg.enabled:
            try:
                self.client = OpenAI(timeout=cfg.timeout_sec)
            except Exception:
                self.client = None

    def generate(self, technical_json: Dict[str, Any]) -> Dict[str, Any]:
        if not self.cfg.enabled or self.client is None:
            return self._fallback(technical_json, "AI_DISABLED_OR_SDK_FAIL")

        if not os.getenv("OPENAI_API_KEY", "").strip():
            return self._fallback(technical_json, "OPENAI_API_KEY_NOT_SET")

        try:
            prompt = self._build_prompt(technical_json)
            resp = self.client.responses.create(
                model=self.cfg.model,
                input=prompt,
                max_output_tokens=self.cfg.max_output_tokens,
            )
            text = getattr(resp, "output_text", "") or str(resp)
            return {"ok": True, "mode": "openai", "analysis": text.strip()}
        except Exception as e:
            return self._fallback(technical_json, f"OPENAI_ERROR: {e}")

    def _build_prompt(self, technical_json: Dict[str, Any]) -> str:
        compact = json.dumps(technical_json, ensure_ascii=False)
        return (
            "Você é um Quant Trader institucional e Risk Manager.\n"
            "Com base no JSON técnico, gere análise operacional.\n"
            "Formato:\n"
            "1) Estado do preço\n"
            "2) Regime e implicações\n"
            "3) Risco oculto / caudas\n"
            "4) Custo e break-even\n"
            "5) Plano de trade (condicional)\n"
            "6) Checklist final\n\n"
            f"JSON:\n{compact}\n"
        )

    def _fallback(self, technical_json: Dict[str, Any], reason: str) -> Dict[str, Any]:
        reg = technical_json.get("regime", {})
        cost = technical_json.get("cost", {})
        verdict = technical_json.get("verdict", {})
        return {
            "ok": True,
            "mode": "fallback",
            "analysis": (
                f"[AI FALLBACK] ({reason})\n"
                f"- Regime: {reg.get('label','—')}\n"
                f"- Custo: {cost.get('total_bps','—')} bps\n"
                f"- Comando: {verdict.get('command','—')} ({verdict.get('status','—')})\n"
                "Sugestão: reduza custo/risco e reanalise."
            )
        }
