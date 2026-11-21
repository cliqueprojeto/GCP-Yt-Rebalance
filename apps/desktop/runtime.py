"""Caminhos de recursos do protótipo Windows autocontido."""
from pathlib import Path
import sys

PRODUCT = "GCP Yt Rebalance"
VERSION = "0.4.0"
MODEL_SHA256 = "d9fa14133cfcc034a6758923bb3a8ca9f8dfd0b582134643bbf83f72c17576dd"
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


def ffmpeg(name="ffmpeg"):
    path = BASE / "vendor/ffmpeg" / (name+ (".exe" if sys.platform=="win32" else ""))
    if not path.is_file():
        raise RuntimeError(f"{name} não encontrado no pacote. Extraia novamente a versão completa.")
    return path


def download_tool(name):
    path=BASE/"vendor/download"/(name+(".exe" if sys.platform=="win32" else ""))
    if not path.is_file(): raise RuntimeError(f"{name} não encontrado no pacote completo.")
    return path
