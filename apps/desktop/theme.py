"""Tokens visuais com pares (claro, escuro) usados por todos os widgets.

CustomTkinter aceita tuplas (cor_clara, cor_escura) e troca automaticamente
quando o modo de aparência muda; por isso nenhuma tela precisa ser recriada
ao alternar o tema.
"""
import sys
import tkinter.font as tkfont
from runtime import BASE

# Superfícies
BG = ("#F4F6FB", "#0B0F1E")
SIDEBAR = ("#FFFFFF", "#0F1426")
SURFACE = ("#FFFFFF", "#141A2E")
SURFACE_2 = ("#F1F3FA", "#1A2139")
INPUT = ("#F7F8FC", "#0E1325")
BORDER = ("#E2E6F0", "#252D47")
BORDER_STRONG = ("#CDD3E3", "#343E60")
HOVER = ("#EEF0F8", "#1F2742")

# Texto
TEXT = ("#121528", "#F2F3FA")
TEXT_2 = ("#4A5170", "#B6BCD4")
MUTED = ("#7A819C", "#7F87A6")

# Marca
ACCENT = ("#7C4DFF", "#8B5CF6")
ACCENT_HOVER = ("#6A3BEB", "#7C4DEB")
ACCENT_SOFT = ("#EEE8FF", "#251C45")
ACCENT_TEXT = ("#5B2FD6", "#C9B5FF")
CYAN = ("#0EA5E9", "#38BDF8")
CYAN_HOVER = ("#0284C7", "#0EA5E9")
PINK = ("#DB2777", "#F472B6")
SUCCESS = ("#059669", "#34D399")
SUCCESS_SOFT = ("#E3F7EF", "#10291F")
WARNING = ("#D97706", "#FBBF24")
DANGER = ("#DC2626", "#F87171")
TRACK = ("#E4E7F1", "#232B45")

# Paletas dos ícones em blocos (fundo, traço)
TINTS = {
    "violet": (("#EEE8FF", "#2A2150"), ("#6D3FF0", "#B79CFF")),
    "cyan": (("#E0F4FD", "#0F2A3B"), ("#0284C7", "#5CCBFA")),
    "pink": (("#FDE7F1", "#3A1530"), ("#BE185D", "#F58BC4")),
    "green": (("#E3F7EF", "#0F2B22"), ("#047857", "#5EE0AE")),
    "amber": (("#FEF3DC", "#33260E"), ("#B45309", "#FCD27A")),
    "blue": (("#E6EDFF", "#17213F"), ("#2F55D4", "#8FA9FF")),
}

FAMILY = "TkDefaultFont"


def load_fonts(root):
    """Registra a fonte Inter incluída (Windows/Linux) e escolhe a melhor família."""
    global FAMILY
    try:
        import customtkinter as ctk
        for name in ("Inter-Regular.otf", "Inter-Bold.otf"):
            path = BASE / "assets/fonts" / name
            if path.is_file() and sys.platform != "darwin":
                ctk.FontManager.load_font(str(path))
    except Exception:
        pass
    try:
        available = set(tkfont.families(root))
    except Exception:
        available = set()
    for family in ("Inter", "Segoe UI Variable Text", "Segoe UI", "SF Pro Text", ".AppleSystemUIFont",
                   "Helvetica Neue", "Ubuntu", "Cantarell", "DejaVu Sans"):
        if family in available:
            FAMILY = family
            break
    return FAMILY


def font(size=13, weight="normal"):
    return (FAMILY, size, "bold" if weight == "bold" else "normal")


def pick(pair, mode):
    """Retorna o lado claro/escuro de um par de cores."""
    if isinstance(pair, str):
        return pair
    return pair[1] if mode == "dark" else pair[0]
