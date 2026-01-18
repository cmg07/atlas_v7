from __future__ import annotations
from typing import List, Dict
import streamlit as st

def tape_render(items: List[Dict]):
    if not items:
        line = "<span class='atlas-tape-item' style='color:var(--muted)'>TAPE: NO DATA (F2 REFRESH)</span>"
    else:
        parts = []
        for it in items[:18]:
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
