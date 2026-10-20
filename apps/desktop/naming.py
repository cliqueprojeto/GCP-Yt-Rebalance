"""Nomes legíveis e proteção contra sobrescrita."""
from pathlib import Path
import re
import unicodedata

LABELS = {"convert": "Convertido", "instrumental": "Instrumental", "vocals": "Voz", "both": "Voz e instrumental", "stems": "Instrumentos", "video": "Vídeo"}
SUFFIXES = {"audio": "convertido", "vocals": "Voz", "instrumental": "Instrumental", "drums": "Bateria", "bass": "Baixo", "other": "Outros", "video": "Video"}


def safe_name(value, limit=160):
    value = unicodedata.normalize("NFC", str(value))
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    value = re.sub(r"\s+", " ", value) or "Sem título"
    if value.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}:
        value = "_" + value
    return value[:limit].rstrip(" .")


def result_folder(destination, title, operation):
    base = f"{safe_name(title, 56)} — {LABELS[operation]}"
    for number in range(1, 10000):
        path = Path(destination) / (base if number == 1 else f"{base} ({number})")
        if not path.exists():
            return path
    raise FileExistsError("Há muitos resultados com o mesmo nome nesta pasta.")


def output_name(title, stem, extension):
    return f"{safe_name(title)}_{SUFFIXES[stem]}.{extension.lower()}"
