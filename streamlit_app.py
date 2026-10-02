"""Ponto de entrada do painel no Streamlit Community Cloud.

O painel fica em app/app.py; este arquivo apenas o executa.
Local:  streamlit run streamlit_app.py   (ou streamlit run app/app.py)
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "app" / "app.py"), run_name="__main__")
