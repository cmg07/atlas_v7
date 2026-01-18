from __future__ import annotations
import streamlit as st

GLOSS = {
    "ATR14": "Average True Range (14) = medida de volatilidade absoluta. Stop em ATR evita ruído.",
    "Z-Score": "Distância em desvios-padrão da média (SMA20). |Z| alto = movimento esticado.",
    "RSI14": "Índice de Força Relativa (14). >70 esticado, <30 descontado (não é gatilho sozinho).",
    "VolAnn": "Volatilidade anualizada (20d). Quanto maior, maior ruído e maior stop necessário.",
    "Drawdown": "Queda desde o topo recente. Stress = drawdown profundo + instabilidade.",
    "VaR / CVaR": "Risco de cauda: VaR = pior perda no quantil; CVaR = média das perdas além do VaR.",
    "Score": "Pontuação multi-fator combinando tendência, reversão e risco, penalizada por custo/regime.",
    "Cost (bps)": "Custo total em bps (spread+slippage+fee). Edge mínimo precisa superar isso.",
    "Regime": "Estado do mercado: tendência / transição / vol hostil / stress. Regime manda na estratégia.",
    "Ruin %": "Probabilidade de ruína via Monte Carlo sob premissas do setup (win rate, payoff, risco).",
}

def render_glossary():
    st.subheader("HELP — Glossário Operacional")
    st.caption("Definições curtas, institucionais e úteis (sem texto inútil).")

    for k, v in GLOSS.items():
        st.markdown(f"**{k}** — {v}")
