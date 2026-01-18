# ATLAS v6.0 (Modular)

## Rodar no Windows (PowerShell)
```powershell
cd C:\Users\caiom\atlas_v6
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate
python -m pip install -r requirements.txt
streamlit run main.py

