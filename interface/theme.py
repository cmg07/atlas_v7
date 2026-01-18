import streamlit as st

BLOOMBERG_CSS = """
<style>
:root{
  --bg:#00040a; --panel:#050b14; --line:#0f1e34; --line2:#1a3456;
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
    radial-gradient(circle at 20% 12%, rgba(255,176,0,0.045), transparent 42%),
    radial-gradient(circle at 82% 20%, rgba(0,214,255,0.040), transparent 50%);
  background-size: 34px 34px, 34px 34px, 100% 100%, 100% 100%;
  background-position: center;
}
.block-container { padding-top: 62px !important; padding-bottom: 44px !important; }
section[data-testid="stSidebar"]{ background: #000209 !important; border-right: 1px solid var(--line); }
section[data-testid="stSidebar"] *{ font-family: var(--mono) !important; }
h1,h2,h3 { color: var(--text); font-weight: 900; letter-spacing: 0.2px; }
.small { color: var(--muted); font-size: 0.83rem; font-family: var(--mono); }
.hr{ border-top: 1px solid var(--line); margin: 12px 0; }

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

.atlas-tape-wrap{
  position:fixed; top:0; left:0; right:0; z-index:9999; height:36px;
  background: rgba(0,2,9,0.98); border-bottom: 1px solid var(--line);
  overflow:hidden; display:flex; align-items:center;
}
.atlas-tape-move{
  white-space:nowrap; display:inline-block; animation: atlas-tape 22s linear infinite;
  padding-left:100%; font-family: var(--mono);
}
@keyframes atlas-tape{ 0%{ transform: translateX(0); } 100%{ transform: translateX(-170%); } }
.atlas-tape-item{ display:inline-block; margin-right:22px; font-size:0.82rem; color:var(--text); }
.tape-ticker{ color: var(--amber2); font-weight: 950; }
.green{ color: var(--good); font-weight: 950; }
.red{ color: var(--bad); font-weight: 950; }
</style>
"""

def apply_theme():
    st.markdown(BLOOMBERG_CSS, unsafe_allow_html=True)
