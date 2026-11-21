"""Interface responsiva, downloads, fila, histórico, apoio e atualizações."""
import json
import math
import os
from pathlib import Path
import queue as queue_module
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image
from runtime import BASE, PRODUCT, VERSION
from process_job import Job
from ui_icons import glyph
from preferences import FACTORY_QUALITY, QUALITY_OPTIONS, quality_defaults
from platform_support import process_options, state_directory, open_directory
import theme as T
from theme import font
import i18n
from i18n import t
import artwork
import updater

BRAND_URL = "https://gestaoculturalpro.com.br"
STRIPE_URL = "https://donate.stripe.com/fZu4gzeBSfhbd7451F6Ri00"
PIX_CODE = ("00020126850014br.gov.bcb.pix0136e474b71b-7491-4eac-992f-632652e5a4eb0223DEV GESTAO CULTURAL PRO"
            "5204000053039865802BR5915BRUNO ALBERTINI6006BRASIL62200516ChromeExtensions63042B27")

# Páginas (chave interna → ícone). A ordem define a navegação.
NAV = {"home": "home", "downloads": "download", "separate": "mic", "convert": "convert", "queue": "queue",
       "history": "history", "settings": "settings", "support": "heart", "about": "info"}
NAV_GROUPS = ((None, ("home",)), ("nav.group.tools", ("downloads", "separate", "convert")),
              ("nav.group.activity", ("queue", "history")), ("nav.group.app", ("settings", "support", "about")))
OPS = {"both": "layers", "instrumental": "mic", "vocals": "audio", "stems": "sparkles", "convert": "convert"}
MODES = {"audio": "music", "video": "video", "instrumental": "mic", "stems": "layers"}
TASK_STATES = ("waiting", "processing", "done", "error", "cancelled")
PHASES = {"Convertendo": "phase.converting", "Verificando arquivo": "phase.checking_file", "Arquivo verificado": "phase.file_ok",
          "Verificando modelo local": "phase.checking_model", "Carregando modelo CPU": "phase.loading_model",
          "Separando no dispositivo CPU": "phase.separating", "Concluído": "phase.done", "Link analisado": "phase.link_done",
          "Erro": "phase.error", "Buscando informações do link": "phase.inspecting", "Fonte identificada": "phase.source_ok",
          "Baixando mídia": "phase.downloading"}
UPDATE_FREQUENCIES = {"startup": 0, "daily": 86400, "weekly": 7 * 86400, "biweekly": 14 * 86400, "monthly": 30 * 86400, "never": None}
AUDIO_TYPES = "*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.opus *.mp4 *.mkv *.mov *.webm *.avi"


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def duration_label(seconds):
    if seconds is None or not math.isfinite(float(seconds)):
        return t("eta.calculating")
    seconds = max(0, math.ceil(seconds))
    return t("eta.seconds", s=seconds) if seconds < 60 else t("eta.minutes", m=seconds // 60, s=f"{seconds % 60:02d}")


def phase_label(phase):
    if phase.startswith("Baixando legenda "):
        return t("phase.subtitle", lang=phase.rsplit(" ", 1)[-1])
    key = PHASES.get(phase)
    return t(key) if key else phase


class App:
    def __init__(self, root, state_dir=None, testing=False):
        self.root, self.testing = root, testing
        self.state_dir = state_dir or state_directory()
        self.process = self.job = self.work = self.active = None
        self.queue, self.history, self.files, self.dialogs = [], [], [], []
        self.paused, self.metadata, self.last_output = False, None, None
        self.offset, self.target_progress, self.shown_progress = 0, 0, 0
        self.eta_deadline, self.phase_key, self.phase_raw = None, None, None
        self.current_page, self.queue_widgets = "home", {}
        self.wrap_labels, self.card_count, self._icons = [], 0, {}
        self.subtitle_selection, self.subtitle_url = {}, None
        self.layout_class, self._resize_job = None, None
        self.update_info, self.update_events = None, queue_module.Queue()
        self.update_state, self.update_dialog = "idle", None
        self.status_key = ("status.ready", {})
        self.source = tk.StringVar()
        music = Path.home() / "Music"
        self.destination = tk.StringVar(value=str(music if music.is_dir() else Path.home()))
        self.operation = tk.StringVar(value="both")
        self.format, self.bits = tk.StringVar(value="WAV"), tk.StringVar(value="16")
        self.rate, self.bitrate, self.threads = tk.StringVar(value="44100"), tk.StringVar(value="192"), tk.StringVar(value="2")
        self.url, self.mode, self.resolution = tk.StringVar(), tk.StringVar(value="audio"), tk.StringVar(value="Melhor disponível")
        self.motion, self.auto_update = tk.BooleanVar(value=True), tk.BooleanVar(value=True)
        self.update_frequency, self.last_update_check = tk.StringVar(value="startup"), 0.0
        self.language, self.appearance = tk.StringVar(value=i18n.detect()), tk.StringVar(value="dark")
        self.saved_quality = quality_defaults()
        self.status, self.detail, self.eta = tk.StringVar(), tk.StringVar(), tk.StringVar()
        try:
            data = json.loads((self.state_dir / "history.json").read_text(encoding="utf-8"))
            self.history = data[-200:] if isinstance(data, list) else []
        except (ValueError, OSError):
            pass
        self.load_settings()
        i18n.set_language(self.language.get())
        ctk.set_appearance_mode(self.appearance.get())
        T.load_fonts(root)
        root.title(PRODUCT); root.geometry("1240x800"); root.minsize(880, 600)
        root.configure(fg_color=T.BG); root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<Configure>", self.resize, add="+")
        self.build()
        root.after(400, self.set_window_icon); root.after(120, self.poll); root.after(40, self.animate)
        if self.update_due() and not testing:
            root.after(2500, lambda: self.check_updates(manual=False))

    # ───────────────────────────── estrutura ─────────────────────────────
    def build(self):
        root = self.root
        for child in root.winfo_children():
            if not isinstance(child, ctk.CTkToplevel):
                child.destroy()
        self.wrap_labels, self._icons = [], {}
        root.grid_columnconfigure(0, weight=0); root.grid_columnconfigure(1, weight=1); root.grid_rowconfigure(0, weight=1)
        self.build_sidebar()
        self.main = ctk.CTkFrame(root, fg_color=T.BG, corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1); self.main.grid_rowconfigure(1, weight=1)
        self.build_topbar()
        self.scroll = ctk.CTkScrollableFrame(self.main, fg_color=T.BG, corner_radius=0,
                                             scrollbar_button_color=T.BORDER_STRONG, scrollbar_button_hover_color=T.ACCENT)
        self.scroll.grid(row=1, column=0, padx=(22, 10), sticky="nsew")
        self.build_status_panel()
        if self.active:
            if self.phase_raw: self.status.set(phase_label(self.phase_raw))
        else:
            self.set_status(self.status_key[0], **self.status_key[1])
            self.detail.set(t("status.detail_idle"))
        self.page(self.current_page)

    def icon(self, name, size=18, color=None, stroke=2.0):
        color = color or T.TEXT_2
        key = (name, size, color, stroke)
        if key not in self._icons:
            light = glyph(name, T.pick(color, "light"), size, stroke)
            dark = glyph(name, T.pick(color, "dark"), size, stroke)
            self._icons[key] = ctk.CTkImage(light_image=light, dark_image=dark, size=(size, size))
        return self._icons[key]

    def tile(self, parent, name, tint="violet", size=38, icon_size=19, radius=11):
        bg, fg = T.TINTS[tint]
        return ctk.CTkLabel(parent, text="", image=self.icon(name, icon_size, fg), fg_color=bg, corner_radius=radius,
                            width=size, height=size)

    def build_sidebar(self):
        side = self.sidebar = ctk.CTkFrame(self.root, width=248, corner_radius=0, fg_color=T.SIDEBAR,
                                           border_width=0)
        side.grid(row=0, column=0, sticky="nsew"); side.grid_propagate(False)
        side.grid_columnconfigure(0, weight=1); side.grid_rowconfigure(1, weight=1)
        ctk.CTkFrame(self.root, width=1, fg_color=T.BORDER, corner_radius=0).grid(row=0, column=0, sticky="nse")
        brand = ctk.CTkFrame(side, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(20, 12))
        logo = ctk.CTkImage(artwork.logo_tile(128), size=(44, 44))
        ctk.CTkLabel(brand, text="", image=logo).grid(row=0, column=0, rowspan=2, padx=(0, 11))
        ctk.CTkLabel(brand, text=PRODUCT, font=font(15, "bold"), text_color=T.TEXT, anchor="w").grid(row=0, column=1, sticky="sw")
        ctk.CTkLabel(brand, text=t("app.tagline"), font=font(11), text_color=T.MUTED, anchor="w").grid(row=1, column=1, sticky="nw")
        nav = self.nav_frame = ctk.CTkFrame(side, fg_color="transparent")
        nav.grid(row=1, column=0, sticky="nsew", padx=12)
        nav.grid_columnconfigure(0, weight=1)
        self.nav, self.nav_bars, self.nav_badges, row = {}, {}, {}, 0
        for header, pages in NAV_GROUPS:
            if header:
                ctk.CTkLabel(nav, text=t(header).upper(), font=font(10, "bold"), text_color=T.MUTED, anchor="w",
                             height=18).grid(row=row, column=0, sticky="ew", padx=12, pady=(12, 3))
                row += 1
            for name in pages:
                holder = ctk.CTkFrame(nav, fg_color="transparent", height=38)
                holder.grid(row=row, column=0, sticky="ew", pady=1); holder.grid_columnconfigure(1, weight=1)
                bar = ctk.CTkFrame(holder, width=3, height=20, corner_radius=2, fg_color="transparent")
                bar.grid(row=0, column=0, padx=(0, 3))
                button = ctk.CTkButton(holder, text=t(f"nav.{name}"), command=lambda p=name: self.page(p),
                                       image=self.icon(NAV[name], 18, T.TEXT_2), compound="left", anchor="w",
                                       fg_color="transparent", hover_color=T.HOVER, text_color=T.TEXT_2,
                                       font=font(13), height=36, corner_radius=10)
                button.grid(row=0, column=1, sticky="ew")
                if name == "queue":
                    badge = ctk.CTkLabel(button, text="", font=font(10, "bold"), fg_color=T.ACCENT, text_color="#FFFFFF",
                                         corner_radius=9, width=22, height=18)
                    self.nav_badges[name] = badge
                self.nav[name], self.nav_bars[name] = button, bar
                row += 1
        self.footer = ctk.CTkFrame(side, fg_color="transparent")
        self.footer.grid(row=2, column=0, sticky="sew", padx=14, pady=(8, 14))
        self.footer.grid_columnconfigure(0, weight=1)
        self.ready_pill = ctk.CTkLabel(self.footer, text="", font=font(11, "bold"), fg_color=T.SUCCESS_SOFT,
                                       text_color=T.SUCCESS, corner_radius=12, height=26, anchor="w")
        self.ready_pill.grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.version_label = ctk.CTkLabel(self.footer, text=t("app.version", v=VERSION), font=font(11), text_color=T.MUTED, anchor="w")
        self.version_label.grid(row=1, column=0, sticky="w", pady=(0, 8))
        credit = ctk.CTkFrame(self.footer, fg_color=T.SURFACE_2, corner_radius=12, border_width=1, border_color=T.BORDER)
        credit.grid(row=2, column=0, sticky="ew")
        line = ctk.CTkFrame(credit, fg_color="transparent"); line.pack(fill="x", padx=12, pady=(9, 0))
        ctk.CTkLabel(line, text=t("credit.by"), font=font(11), text_color=T.MUTED).pack(side="left")
        ctk.CTkLabel(line, text=" Bruno Albertini", font=font(11, "bold"), text_color=T.ACCENT_TEXT).pack(side="left")
        brand_link = ctk.CTkLabel(credit, text="Gestão Cultural Pro  ↗", font=font(11), text_color=T.TEXT_2, anchor="w", cursor="hand2")
        brand_link.pack(fill="x", padx=12, pady=(0, 9)); brand_link.bind("<Button-1>", lambda _: self.brand())
        self.update_queue_badge(); self.update_ready_pill()

    def build_topbar(self):
        bar = self.topbar = ctk.CTkFrame(self.main, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=(30, 26), pady=(22, 12)); bar.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(bar, fg_color="transparent"); head.grid(row=0, column=0, sticky="ew")
        eyebrow = ctk.CTkFrame(head, fg_color="transparent"); eyebrow.pack(anchor="w")
        ctk.CTkLabel(eyebrow, text="", image=self.icon("sparkles", 14, T.ACCENT_TEXT)).pack(side="left", padx=(0, 6))
        self.eyebrow = ctk.CTkLabel(eyebrow, text="", font=font(11, "bold"), text_color=T.ACCENT_TEXT)
        self.eyebrow.pack(side="left")
        self.title = ctk.CTkLabel(head, text="", font=font(26, "bold"), text_color=T.TEXT, anchor="w")
        self.title.pack(anchor="w", pady=(2, 0))
        self.subtitle = ctk.CTkLabel(head, text="", font=font(13), text_color=T.TEXT_2, anchor="w", justify="left")
        self.subtitle.pack(anchor="w", pady=(2, 0))
        tools = self.top_tools = ctk.CTkFrame(bar, fg_color="transparent"); tools.grid(row=0, column=1, sticky="ne")
        self.update_pill = ctk.CTkButton(tools, text="", command=self.open_update_dialog, image=self.icon("upload-cloud", 16, "#FFFFFF"),
                                         fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER, text_color="#FFFFFF", font=font(12, "bold"),
                                         height=36, corner_radius=12)
        self.lang_menu = ctk.CTkSegmentedButton(tools, values=list(i18n.SHORT.values()), command=self.change_language_short,
                                                font=font(12, "bold"), height=36, corner_radius=12, fg_color=T.SURFACE_2,
                                                selected_color=T.SURFACE, selected_hover_color=T.SURFACE, unselected_color=T.SURFACE_2,
                                                unselected_hover_color=T.HOVER, text_color=T.TEXT)
        self.lang_menu.set(i18n.SHORT[i18n.current()])
        self.lang_menu.grid(row=0, column=1, padx=(8, 0))
        self.theme_button = self.icon_button(tools, "sun" if self.is_dark() else "moon", self.toggle_theme)
        self.theme_button.grid(row=0, column=2, padx=(8, 0))
        heart = self.icon_button(tools, "heart", lambda: self.page("support"), color=T.PINK)
        heart.grid(row=0, column=3, padx=(8, 0))
        self.refresh_update_pill()

    def icon_button(self, parent, name, command, color=None):
        return ctk.CTkButton(parent, text="", image=self.icon(name, 18, color or T.TEXT_2), command=command, width=40, height=36,
                             fg_color=T.SURFACE, hover_color=T.HOVER, border_width=1, border_color=T.BORDER, corner_radius=12)

    def build_status_panel(self):
        panel = self.bottom = ctk.CTkFrame(self.main, fg_color=T.SURFACE, corner_radius=16, border_width=1, border_color=T.BORDER)
        panel.grid(row=2, column=0, sticky="ew", padx=(30, 26), pady=(10, 16)); panel.grid_columnconfigure(1, weight=1)
        self.pulse = self.tile(panel, "bolt", "green", 40, 19, 12)
        self.pulse.grid(row=0, column=0, rowspan=2, padx=(14, 12), pady=(12, 4))
        ctk.CTkLabel(panel, textvariable=self.status, font=font(13, "bold"), text_color=T.TEXT, anchor="w").grid(row=0, column=1, sticky="sew", pady=(12, 0))
        self.detail_label = ctk.CTkLabel(panel, textvariable=self.detail, font=font(11), text_color=T.MUTED, anchor="w", justify="left", wraplength=560)
        self.detail_label.grid(row=1, column=1, sticky="new")
        actions = ctk.CTkFrame(panel, fg_color="transparent"); actions.grid(row=0, column=2, rowspan=2, padx=14, pady=(12, 4), sticky="e")
        ctk.CTkLabel(actions, textvariable=self.eta, text_color=T.ACCENT_TEXT, font=font(11)).pack(side="left", padx=(0, 10))
        self.cancel_button = self.button(actions, t("btn.cancel_current"), self.cancel, icon="cancel", height=34, style="ghost")
        self.cancel_button.pack(side="left", padx=(0, 6)); self.cancel_button.configure(state="normal" if self.process else "disabled")
        self.button(actions, t("btn.open_result"), lambda: self.open_folder(self.last_output), icon="folder", height=34).pack(side="left")
        self.bar = ctk.CTkProgressBar(panel, height=6, progress_color=T.ACCENT, fg_color=T.TRACK, corner_radius=3)
        self.bar.set(max(0, min(1, self.shown_progress / 100)))
        self.bar.grid(row=2, column=0, columnspan=3, padx=16, pady=(6, 14), sticky="ew")

    # ───────────────────────────── componentes ─────────────────────────────
    def button(self, parent, text, command, icon=None, style="secondary", **kw):
        styles = {
            "primary": dict(fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER, text_color="#FFFFFF", border_width=0, icolor="#FFFFFF"),
            "cyan": dict(fg_color=T.CYAN, hover_color=T.CYAN_HOVER, text_color="#FFFFFF", border_width=0, icolor="#FFFFFF"),
            "secondary": dict(fg_color=T.SURFACE, hover_color=T.HOVER, text_color=T.TEXT, border_width=1, icolor=T.TEXT_2),
            "ghost": dict(fg_color="transparent", hover_color=T.HOVER, text_color=T.TEXT_2, border_width=1, icolor=T.TEXT_2),
            "link": dict(fg_color="transparent", hover_color=T.HOVER, text_color=T.CYAN, border_width=0, icolor=T.CYAN),
        }
        s = dict(styles[style]); icolor = s.pop("icolor")
        return ctk.CTkButton(parent, text=text, command=command, image=self.icon(icon, 17, icolor) if icon else None, compound="left",
                             border_color=T.BORDER, corner_radius=kw.pop("corner_radius", 11), font=kw.pop("font", font(13, "bold" if style in ("primary", "cyan") else "normal")),
                             height=kw.pop("height", 40), **s, **kw)

    def set_window_icon(self):
        try:
            if os.name == "nt": self.root.iconbitmap(str(BASE / "assets/branding/taskbar.ico"))
            self.window_icons = [tk.PhotoImage(file=str(BASE / f"assets/branding/taskbar-{s}.png")) for s in (16, 32, 64)]
            self.root.iconphoto(True, *self.window_icons)
        except tk.TclError:
            pass

    def content_width(self):
        try:
            return max(420, self.root._reverse_window_scaling(self.root.winfo_width()) - 300)
        except Exception:
            return 900

    def resize(self, event):
        if event.widget != self.root: return
        width = self.content_width()
        if hasattr(self, "detail_label") and self.detail_label.winfo_exists():
            self.detail_label.configure(wraplength=max(160, width - 450))
            self.title.configure(font=font(22 if width < 700 else 26, "bold"))
            self.lang_menu.grid_remove() if width < 640 else self.lang_menu.grid()
            try:
                height = self.root._reverse_window_scaling(self.root.winfo_height())
                self.ready_pill.grid_remove() if height < 690 else self.ready_pill.grid()
                self.version_label.grid_remove() if height < 640 else self.version_label.grid()
            except Exception:
                pass
        for label in self.wrap_labels:
            if label.winfo_exists(): label.configure(wraplength=max(120, int(width * label._wrap_ratio) - 60))
        layout = "wide" if width >= 980 else "medium" if width >= 760 else "narrow"
        if layout != self.layout_class:
            self.layout_class = layout
            if self.current_page in ("home", "support", "separate", "downloads") and not self.testing:
                if self._resize_job: self.root.after_cancel(self._resize_job)
                self._resize_job = self.root.after(160, lambda: self.page(self.current_page, keep_scroll=True))

    def label(self, parent, text, ratio=1.0, **kw):
        options = dict(font=font(12), text_color=T.TEXT_2, anchor="w", justify="left")
        options.update(kw)
        label = ctk.CTkLabel(parent, text=text, wraplength=max(120, int(self.content_width() * ratio) - 60), **options)
        label._wrap_ratio = ratio
        self.wrap_labels.append(label)
        return label

    def card(self, title=None, subtitle=None, parent=None, icon=None, tint="violet", pack=True):
        card = ctk.CTkFrame(parent or self.scroll, fg_color=T.SURFACE, corner_radius=18, border_width=1, border_color=T.BORDER)
        if pack: card.pack(fill="x", padx=4, pady=(0, 16))
        if title:
            head = ctk.CTkFrame(card, fg_color="transparent"); head.pack(fill="x", padx=22, pady=(18, 4))
            if icon: self.tile(head, icon, tint, 36, 18, 10).pack(side="left", padx=(0, 12))
            box = ctk.CTkFrame(head, fg_color="transparent"); box.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(box, text=title, font=font(16, "bold"), text_color=T.TEXT, anchor="w").pack(fill="x")
            if subtitle: self.label(box, subtitle, ratio=.93 if parent is None else .45, font=font(12), text_color=T.MUTED).pack(fill="x", pady=(1, 0))
        elif subtitle:
            self.label(card, subtitle).pack(fill="x", padx=22, pady=(16, 6))
        self.card_count += 1
        if self.motion.get() and not self.testing and self.card_count <= 6:
            mode = "dark" if self.is_dark() else "light"
            start = T.pick(T.ACCENT, mode); end = T.pick(T.BORDER, mode)
            def fade(step=0):
                if not card.winfo_exists(): return
                if step >= 12: card.configure(border_color=T.BORDER); return
                a = tuple(int(start[i:i + 2], 16) for i in (1, 3, 5)); b = tuple(int(end[i:i + 2], 16) for i in (1, 3, 5))
                card.configure(border_color="#" + "".join(f"{round(x + (y - x) * step / 12):02x}" for x, y in zip(a, b)))
                self.root.after(24, lambda: fade(step + 1))
            fade()
        return card

    def section_title(self, text, action=None):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent"); row.pack(fill="x", padx=4, pady=(6, 10))
        ctk.CTkLabel(row, text=text, font=font(18, "bold"), text_color=T.TEXT, anchor="w").pack(side="left")
        if action: action(row)
        return row

    def hoverable(self, frame, command, widgets=()):
        def enter(_): frame.configure(border_color=T.ACCENT)
        def leave(_): frame.configure(border_color=T.BORDER)
        for widget in (frame, *widgets):
            widget.bind("<Enter>", enter, add="+"); widget.bind("<Leave>", leave, add="+")
            widget.bind("<Button-1>", lambda _: command(), add="+")
            try: widget.configure(cursor="hand2")
            except (tk.TclError, ValueError): pass

    def all_children(self, widget):
        for child in widget.winfo_children():
            yield child
            yield from self.all_children(child)

    def choice(self, parent, var, codes, labels=None, command=None):
        """Menu com códigos internos estáveis e rótulos traduzidos."""
        labels = labels or {}
        show = lambda code: labels.get(code, code)
        reverse = {show(code): code for code in codes}
        display = tk.StringVar(value=show(var.get()))
        def selected(value):
            var.set(reverse.get(value, value))
            if command: command(var.get())
        frame = ctk.CTkFrame(parent, fg_color=T.INPUT, corner_radius=11, border_width=1, border_color=T.BORDER)
        menu = ctk.CTkOptionMenu(frame, variable=display, values=[show(c) for c in codes], command=selected, height=38,
                                 fg_color=T.INPUT, button_color=T.INPUT, button_hover_color=T.HOVER, text_color=T.TEXT,
                                 text_color_disabled=T.MUTED, dropdown_fg_color=T.SURFACE, dropdown_hover_color=T.ACCENT_SOFT,
                                 dropdown_text_color=T.TEXT, dropdown_font=font(12), font=font(13), corner_radius=10, dynamic_resizing=False)
        menu.pack(fill="x", padx=2, pady=2)
        trace = var.trace_add("write", lambda *_: display.set(show(var.get())))
        def cleanup(event):
            if event.widget is frame:
                try: var.trace_remove("write", trace)
                except (tk.TclError, ValueError): pass
        frame.bind("<Destroy>", cleanup, add="+")
        frame.menu = menu
        return frame

    def entry(self, parent, variable, placeholder=None, readonly=False):
        return ctk.CTkEntry(parent, textvariable=variable, placeholder_text=placeholder, state="readonly" if readonly else "normal",
                            height=42, corner_radius=11, fg_color=T.INPUT, border_color=T.BORDER, border_width=1,
                            text_color=T.TEXT, placeholder_text_color=T.MUTED, font=font(13))

    def option_tiles(self, parent, var, items, columns=2, on_change=None):
        """Seleção em blocos (substitui menus para escolhas principais)."""
        grid = ctk.CTkFrame(parent, fg_color="transparent"); grid.pack(fill="x", padx=22, pady=(8, 6))
        for c in range(columns): grid.grid_columnconfigure(c, weight=1, uniform="tiles")
        tints = ("violet", "cyan", "pink", "blue", "green")
        for index, (code, icon_name, title, text) in enumerate(items):
            selected = var.get() == code
            box = ctk.CTkFrame(grid, fg_color=T.ACCENT_SOFT if selected else T.SURFACE_2, corner_radius=14,
                               border_width=2 if selected else 1, border_color=T.ACCENT if selected else T.BORDER)
            box.grid(row=index // columns, column=index % columns, sticky="nsew", padx=5, pady=5)
            tile = self.tile(box, icon_name, tints[index % len(tints)], 36, 18, 10); tile.pack(anchor="w", padx=14, pady=(14, 8))
            head = ctk.CTkLabel(box, text=title, font=font(13, "bold"), text_color=T.TEXT, anchor="w"); head.pack(fill="x", padx=14)
            body = self.label(box, text, ratio=1 / columns, font=font(11), text_color=T.MUTED); body.pack(fill="x", padx=14, pady=(2, 14))
            def choose(c=code):
                var.set(c)
                if on_change: on_change(c)
                self.page(self.current_page, keep_scroll=True)
            for widget in (box, tile, head, body):
                widget.bind("<Button-1>", lambda _, f=choose: f(), add="+")
                try: widget.configure(cursor="hand2")
                except (tk.TclError, ValueError): pass
            if not selected:
                box.bind("<Enter>", lambda _, b=box: b.configure(border_color=T.BORDER_STRONG), add="+")
                box.bind("<Leave>", lambda _, b=box: b.configure(border_color=T.BORDER), add="+")
        return grid

    # ───────────────────────────── navegação ─────────────────────────────
    def page(self, name, keep_scroll=False):
        if name not in NAV: name = "home"
        position = self.scroll._parent_canvas.yview()[0] if keep_scroll else 0
        self.current_page = name; self.queue_widgets = {}; self.card_count = 0
        for child in self.scroll.winfo_children(): child.destroy()
        self.wrap_labels = [w for w in self.wrap_labels if w.winfo_exists()]
        for item, button in self.nav.items():
            active = item == name
            button.configure(fg_color=T.ACCENT_SOFT if active else "transparent", text_color=T.ACCENT_TEXT if active else T.TEXT_2,
                             font=font(13, "bold" if active else "normal"), image=self.icon(NAV[item], 18, T.ACCENT_TEXT if active else T.TEXT_2))
            self.nav_bars[item].configure(fg_color=T.ACCENT if active else "transparent")
        self.eyebrow.configure(text=t(f"page.{name}.eyebrow").upper())
        self.title.configure(text=t(f"page.{name}.title"))
        self.subtitle.configure(text=t(f"page.{name}.subtitle"))
        builders = {"home": self.home_page, "downloads": self.download_form, "separate": self.separate_form, "convert": self.convert_form,
                    "queue": self.queue_page, "history": self.history_page, "settings": self.settings_form, "support": self.support_page,
                    "about": self.about_page}
        builders[name]()
        self.root.update_idletasks() if keep_scroll else None
        self.scroll._parent_canvas.yview_moveto(position)

    # ───────────────────────────── início ─────────────────────────────
    def stats(self):
        done = [h for h in self.history if h.get("status") in ("Concluído", "done")]
        seconds = sum(float(h.get("elapsed_seconds") or 0) for h in done)
        minutes = seconds / 60
        return [("check-circle", "green", str(len(done)), t("home.stat.done")),
                ("clock", "cyan", f"{minutes:.0f} min" if minutes >= 1 else f"{seconds:.0f} s", t("home.stat.time")),
                ("layers", "violet", "12+", t("home.stat.formats")),
                ("shield", "pink", "100%", t("home.stat.private"))]

    def home_page(self):
        wide = self.content_width() >= 1180
        top = ctk.CTkFrame(self.scroll, fg_color="transparent"); top.pack(fill="x", padx=4, pady=(0, 18))
        top.grid_columnconfigure(0, weight=3 if wide else 1)
        if wide: top.grid_columnconfigure(1, weight=2)
        hero = ctk.CTkFrame(top, fg_color=T.SURFACE, corner_radius=20, border_width=2, border_color=T.ACCENT_SOFT)
        hero.grid(row=0, column=0, sticky="nsew", padx=(0, 16 if wide else 0))
        hero.grid_columnconfigure(1, weight=1)
        art = ctk.CTkImage(light_image=artwork.hero_art("light"), dark_image=artwork.hero_art("dark"), size=(196, 140))
        ctk.CTkLabel(hero, text="", image=art).grid(row=0, column=0, rowspan=3, padx=(18, 6), pady=18)
        ctk.CTkLabel(hero, text=t("home.hero.title"), font=font(20, "bold"), text_color=T.TEXT, anchor="w").grid(row=0, column=1, sticky="sw", padx=(4, 22), pady=(26, 0))
        self.label(hero, t("home.hero.text"), ratio=.55 if wide else .7, font=font(13), text_color=T.TEXT_2).grid(row=1, column=1, sticky="new", padx=(4, 22), pady=(6, 0))
        buttons = ctk.CTkFrame(hero, fg_color="transparent"); buttons.grid(row=2, column=1, sticky="nw", padx=(4, 22), pady=(14, 24))
        self.button(buttons, t("btn.choose_files"), self.home_choose_files, icon="file", style="cyan", height=42).pack(side="left", padx=(0, 10))
        self.button(buttons, t("btn.paste_link"), lambda: self.page("downloads"), icon="link", height=42).pack(side="left")
        stats = ctk.CTkFrame(top, fg_color="transparent")
        if wide: stats.grid(row=0, column=1, sticky="nsew")
        else: stats.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        columns = 2 if wide else 4
        for c in range(columns): stats.grid_columnconfigure(c, weight=1, uniform="stats")
        for index, (icon_name, tint, value, caption) in enumerate(self.stats()):
            box = ctk.CTkFrame(stats, fg_color=T.SURFACE, corner_radius=18, border_width=1, border_color=T.BORDER)
            pad_x = (0, 8) if index % columns == 0 else (8, 0) if index % columns == columns - 1 else (4, 4)
            box.grid(row=index // columns, column=index % columns, sticky="nsew", padx=pad_x, pady=(0, 12) if wide and index < 2 else 0)
            self.tile(box, icon_name, tint, 36, 18, 10).pack(anchor="w", padx=16, pady=(16, 8))
            ctk.CTkLabel(box, text=value, font=font(24, "bold"), text_color=T.TEXT, anchor="w").pack(fill="x", padx=16)
            ctk.CTkLabel(box, text=caption, font=font(11), text_color=T.MUTED, anchor="w").pack(fill="x", padx=16, pady=(0, 16))
        self.section_title(t("home.tools"))
        grid = ctk.CTkFrame(self.scroll, fg_color="transparent"); grid.pack(fill="x", padx=4, pady=(0, 16))
        width = self.content_width()
        columns = 4 if width >= 980 else 2
        for c in range(columns): grid.grid_columnconfigure(c, weight=1, uniform="tools")
        card_w = int((width - 40 - 16 * (columns - 1)) / columns)
        tools = (("download", "downloads", "download", ("MP4", "MP3", "WAV")), ("karaoke", "separate", "mic", ("KARAOKÊ", "VOZ", "WAV")),
                 ("stems", "separate", "layers", ("STEMS", "4×", "FLAC")), ("convert", "convert", "convert", ("WAV", "FLAC", "MP3")))
        for index, (kind, target, icon_name, chips) in enumerate(tools):
            box = ctk.CTkFrame(grid, fg_color=T.SURFACE, corner_radius=18, border_width=1, border_color=T.BORDER)
            box.grid(row=index // columns, column=index % columns, sticky="nsew", padx=(0 if index % columns == 0 else 8, 0 if index % columns == columns - 1 else 8), pady=(0, 16))
            bw = max(160, card_w - 4); bh = max(80, int(bw * (.5 if columns == 4 else .36)))
            image = ctk.CTkImage(light_image=artwork.banner(kind, "light", chips, bw * 2, bh * 2), dark_image=artwork.banner(kind, "dark", chips, bw * 2, bh * 2), size=(bw, bh))
            banner = ctk.CTkLabel(box, text="", image=image, corner_radius=16); banner.pack(fill="x", padx=2, pady=(2, 0))
            head = ctk.CTkFrame(box, fg_color="transparent"); head.pack(fill="x", padx=16, pady=(12, 2))
            tile = self.tile(head, icon_name, ("violet", "cyan", "pink", "blue")[index], 30, 16, 9); tile.pack(side="left", padx=(0, 10))
            title = ctk.CTkLabel(head, text=t(f"tool.{kind}.title"), font=font(15, "bold"), text_color=T.TEXT, anchor="w"); title.pack(side="left")
            body = self.label(box, t(f"tool.{kind}.text"), ratio=1 / columns, font=font(12), text_color=T.MUTED); body.pack(fill="x", padx=16, pady=(4, 16))
            def go(k=kind, p=target):
                if k == "karaoke": self.operation.set("instrumental")
                elif k == "stems": self.operation.set("stems")
                elif k == "convert": self.operation.set("convert")
                self.page(p)
            self.hoverable(box, go, (banner, head, tile, title, body))
        recent = [h for h in reversed(self.history)][:3]
        card = self.card(t("home.recent"), t("home.recent.empty") if not recent else None, icon="history", tint="amber")
        for item in recent:
            self.history_row(card, item)
        if recent: ctk.CTkFrame(card, height=8, fg_color="transparent").pack()

    def home_choose_files(self):
        self.choose_files()
        if self.files:
            if self.operation.get() == "convert": self.operation.set("both")
            self.page("separate")

    # ───────────────────────────── formulários locais ─────────────────────────────
    def file_zone(self, card):
        zone = ctk.CTkFrame(card, fg_color=T.SURFACE_2, corner_radius=16, border_width=2, border_color=T.BORDER_STRONG)
        zone.pack(fill="x", padx=22, pady=(10, 6))
        tile = self.tile(zone, "upload-cloud", "violet", 52, 26, 15); tile.pack(pady=(20, 8))
        name = self.files[0] if self.files else None
        text = (Path(name).name if len(self.files) == 1 else t("files.many", n=len(self.files), first=Path(name).name)) if name else t("files.zone.title")
        head = ctk.CTkLabel(zone, text=text, font=font(14, "bold"), text_color=T.TEXT); head.pack(padx=20)
        hint = ctk.CTkLabel(zone, text=t("files.zone.hint"), font=font(11), text_color=T.MUTED); hint.pack(padx=20, pady=(2, 8))
        pick = self.button(zone, t("btn.choose_files") if not name else t("btn.change_files"), self.choose_files_refresh, icon="file", style="cyan", height=38)
        pick.pack(pady=(4, 20))
        self.hoverable(zone, self.choose_files_refresh, (tile, head, hint))

    def choose_files_refresh(self):
        self.choose_files()
        self.page(self.current_page, keep_scroll=True)

    def field_row(self, card, title, variable, command, icon="folder"):
        ctk.CTkLabel(card, text=title, font=font(12, "bold"), text_color=T.TEXT_2, anchor="w").pack(fill="x", padx=22, pady=(12, 6))
        row = ctk.CTkFrame(card, fg_color="transparent"); row.pack(fill="x", padx=22, pady=(0, 14)); row.grid_columnconfigure(0, weight=1)
        self.entry(row, variable, readonly=True).grid(row=0, column=0, sticky="ew")
        self.button(row, t("btn.choose"), command, icon=icon, height=42).grid(row=0, column=1, padx=(8, 0))

    def format_controls(self, card):
        grid = ctk.CTkFrame(card, fg_color="transparent"); grid.pack(fill="x", padx=22, pady=(4, 4))
        for col in (0, 1): grid.grid_columnconfigure(col, weight=1, uniform="options")
        fields = (("fmt.format", self.format, QUALITY_OPTIONS["format"]), ("fmt.bits", self.bits, QUALITY_OPTIONS["bits"]),
                  ("fmt.rate", self.rate, QUALITY_OPTIONS["rate"]), ("fmt.bitrate", self.bitrate, QUALITY_OPTIONS["bitrate"]))
        self.format_widgets = {}
        for index, (key, var, values) in enumerate(fields):
            row, col = index // 2 * 2, index % 2
            ctk.CTkLabel(grid, text=t(key), font=font(12, "bold"), text_color=T.TEXT_2, anchor="w").grid(row=row, column=col, sticky="w", padx=(0 if col == 0 else 8, 0 if col else 8), pady=(10, 5))
            widget = self.choice(grid, var, values, command=lambda _: self.update_format())
            widget.grid(row=row + 1, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0 if col else 8)); self.format_widgets[key] = widget.menu
        note = ctk.CTkFrame(card, fg_color=T.SURFACE_2, corner_radius=12); note.pack(fill="x", padx=22, pady=(14, 6))
        ctk.CTkLabel(note, text="", image=self.icon("info", 16, T.ACCENT_TEXT)).pack(side="left", padx=(12, 8), pady=10)
        self.format_note = self.label(note, "", ratio=.9, font=font(12), text_color=T.TEXT_2); self.format_note.pack(side="left", fill="x", expand=True, pady=10, padx=(0, 12))
        self.update_format()

    def update_format(self):
        fmt = self.format.get()
        if fmt == "FLAC" and self.bits.get() == "32": self.bits.set("24")
        self.format_widgets["fmt.bits"].configure(values=["16", "24"] if fmt == "FLAC" else ["16", "24", "32"], state="disabled" if fmt == "MP3" else "normal")
        self.format_widgets["fmt.bitrate"].configure(state="normal" if fmt == "MP3" else "disabled")
        self.format_note.configure(text=t(f"fmt.note.{fmt.lower()}"))

    def separate_form(self):
        if self.operation.get() == "convert": self.operation.set("both")
        self.local_form(separate=True)

    def convert_form(self):
        self.operation.set("convert")
        self.local_form(separate=False)

    def local_form(self, separate=True):
        card = self.card(t("form.files.title"), t("form.files.subtitle"), icon="file", tint="violet")
        self.file_zone(card)
        self.field_row(card, t("form.destination"), self.destination, self.choose_destination)
        if separate:
            card = self.card(t("form.separate.title"), t("form.separate.subtitle"), icon="mic", tint="cyan")
            items = [(code, OPS[code], t(f"op.{code}"), t(f"op.{code}.text")) for code in ("both", "instrumental", "vocals", "stems")]
            self.option_tiles(card, self.operation, items, columns=2 if self.content_width() < 980 else 4)
            ctk.CTkFrame(card, height=6, fg_color="transparent").pack()
            card = self.card(t("form.output.title"), t("form.output.subtitle"), icon="settings", tint="blue")
        else:
            card = self.card(t("form.convert.title"), t("form.convert.subtitle"), icon="convert", tint="blue")
        self.format_controls(card)
        row = ctk.CTkFrame(card, fg_color="transparent"); row.pack(fill="x", padx=22, pady=(14, 22))
        self.button(row, t("btn.add_queue"), self.enqueue_local, icon="plus", style="primary", width=200, height=44).pack(side="left")
        self.button(row, t("btn.view_queue"), lambda: self.page("queue"), icon="queue", height=44).pack(side="right")
        tip = ctk.CTkFrame(self.scroll, fg_color=T.ACCENT_SOFT, corner_radius=14); tip.pack(fill="x", padx=4, pady=(0, 16))
        ctk.CTkLabel(tip, text="", image=self.icon("sparkles", 16, T.ACCENT_TEXT)).pack(side="left", padx=(16, 10), pady=14)
        self.label(tip, t("form.tip"), ratio=.9, font=font(12), text_color=T.ACCENT_TEXT).pack(side="left", fill="x", expand=True, pady=12, padx=(0, 16))

    # ───────────────────────────── downloads ─────────────────────────────
    def download_form(self):
        card = self.card(t("dl.link.title"), t("dl.link.subtitle"), icon="link", tint="violet")
        row = ctk.CTkFrame(card, fg_color="transparent"); row.pack(fill="x", padx=22, pady=(10, 12)); row.grid_columnconfigure(0, weight=1)
        entry = self.entry(row, self.url, "https://www.youtube.com/watch?v=…"); entry.configure(height=46)
        entry.grid(row=0, column=0, sticky="ew"); entry.bind("<Return>", lambda _: self.analyze())
        self.button(row, t("btn.analyze"), self.analyze, icon="search", style="primary", height=46).grid(row=0, column=1, padx=(8, 0))
        info = ctk.CTkFrame(card, fg_color=T.SURFACE_2, corner_radius=14); info.pack(fill="x", padx=22, pady=(0, 20))
        data = self.metadata if self.metadata and self.metadata.get("url") == self.url.get().strip() else None
        if not data:
            ctk.CTkLabel(info, text="", image=self.icon("video", 18, T.MUTED)).pack(side="left", padx=(14, 10), pady=14)
            self.label(info, t("dl.info.empty"), ratio=.85, text_color=T.MUTED).pack(side="left", fill="x", expand=True, pady=14)
        else:
            body = ctk.CTkFrame(info, fg_color="transparent"); body.pack(fill="x", padx=14, pady=12)
            self.tile(body, "video", "cyan", 40, 20, 11).pack(side="left", padx=(0, 12))
            text = ctk.CTkFrame(body, fg_color="transparent"); text.pack(side="left", fill="x", expand=True)
            self.label(text, data["title"], ratio=.8, font=font(13, "bold"), text_color=T.TEXT).pack(fill="x")
            if data.get("playlist"):
                mapping = {f"{i + 1}. {item['title'][:70]}": item["url"] for i, item in enumerate(data["playlist"])}
                placeholder = t("dl.playlist.choose")
                def select(value):
                    if value in mapping:
                        self.url.set(mapping[value]); self.metadata = None; self.analyze()
                var = tk.StringVar(value=placeholder)
                self.choice(text, var, [placeholder, *mapping], command=select).pack(fill="x", pady=(8, 0))
            else:
                seconds = data.get("duration", 0)
                kind = t("dl.kind.video") if data.get("video_available") else t("dl.kind.audio")
                self.label(text, f"{int(seconds // 60)}:{int(seconds % 60):02d} • {kind}", ratio=.8, text_color=T.MUTED).pack(fill="x", pady=(2, 0))
        card = self.card(t("dl.mode.title"), t("dl.mode.subtitle"), icon="download", tint="cyan")
        items = [(code, MODES[code], t(f"mode.{code}"), t(f"mode.{code}.text")) for code in MODES]
        self.option_tiles(card, self.mode, items, columns=2 if self.content_width() < 980 else 4)
        if self.mode.get() == "video":
            ctk.CTkLabel(card, text=t("dl.resolution"), font=font(12, "bold"), text_color=T.TEXT_2, anchor="w").pack(fill="x", padx=22, pady=(12, 6))
            values = ["Melhor disponível"] + [f"{n}p" for n in data.get("resolutions", [])] if data else QUALITY_OPTIONS["resolution"]
            if self.resolution.get() not in values:
                preferred = int(self.resolution.get()[:-1]) if self.resolution.get().endswith("p") else 0
                allowed = [n for n in data.get("resolutions", []) if n <= preferred]
                self.resolution.set(f"{max(allowed)}p" if allowed else values[0])
            self.choice(card, self.resolution, values, {"Melhor disponível": t("res.best")}).pack(fill="x", padx=22, pady=(0, 8))
            self.label(card, t("dl.video.note"), text_color=T.MUTED).pack(fill="x", padx=22, pady=(4, 6))
        else:
            self.format_controls(card)
        self.field_row(card, t("form.destination"), self.destination, self.choose_destination)
        self.button(card, t("btn.add_download"), self.enqueue_download, icon="download", style="primary", height=44).pack(anchor="w", padx=22, pady=(4, 22))
        self.subtitle_controls(data)
        tip = ctk.CTkFrame(self.scroll, fg_color=T.SURFACE_2, corner_radius=14); tip.pack(fill="x", padx=4, pady=(0, 16))
        ctk.CTkLabel(tip, text="", image=self.icon("shield", 16, T.TEXT_2)).pack(side="left", padx=(16, 10), pady=14)
        self.label(tip, t("dl.legal"), ratio=.9, font=font(12), text_color=T.MUTED).pack(side="left", fill="x", expand=True, pady=12, padx=(0, 16))

    def subtitle_controls(self, data):
        card = self.card(t("subs.title"), t("subs.subtitle"), icon="queue", tint="amber")
        self.button(card, t("btn.load_subs"), self.analyze, icon="refresh").pack(anchor="w", padx=22, pady=(10, 12))
        if not data or data.get("playlist"):
            self.label(card, t("subs.empty"), text_color=T.MUTED).pack(fill="x", padx=22, pady=(0, 18))
            return
        if self.subtitle_url != data["url"]:
            self.subtitle_selection = {}; self.subtitle_url = data["url"]
        tracks = data.get("subtitles", [])
        if not tracks:
            self.label(card, t("subs.none"), text_color=T.MUTED).pack(fill="x", padx=22, pady=(0, 18))
            return
        search = tk.StringVar()
        self.entry(card, search, t("subs.search")).pack(fill="x", padx=22, pady=(0, 8))
        rows = ctk.CTkScrollableFrame(card, height=180, fg_color=T.SURFACE_2, corner_radius=12)
        rows.pack(fill="x", padx=22, pady=(0, 8))
        count = self.label(card, "", text_color=T.MUTED); count.pack(fill="x", padx=22, pady=(0, 16))
        def update_count():
            count.configure(text=t("subs.count", n=sum(var.get() for var in self.subtitle_selection.values())))
        def populate(*_):
            for child in rows.winfo_children(): child.destroy()
            query = search.get().casefold().strip()
            for item in tracks:
                label = f"{item['name']} • {item['language']} • " + (t("subs.auto") if item["automatic"] else t("subs.published"))
                if query and query not in label.casefold(): continue
                key = (item["automatic"], item["language"])
                var = self.subtitle_selection.setdefault(key, tk.BooleanVar(value=False))
                ctk.CTkCheckBox(rows, text=label, variable=var, command=update_count, fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                                border_color=T.BORDER_STRONG, text_color=T.TEXT, font=font(12)).pack(anchor="w", padx=8, pady=6)
            update_count()
        search.trace_add("write", populate); populate()

    # ───────────────────────────── configurações ─────────────────────────────
    def settings_form(self):
        card = self.card(t("set.look.title"), t("set.look.subtitle"), icon="sun", tint="amber")
        grid = ctk.CTkFrame(card, fg_color="transparent"); grid.pack(fill="x", padx=22, pady=(8, 6))
        grid.grid_columnconfigure((0, 1), weight=1, uniform="look")
        ctk.CTkLabel(grid, text=t("set.theme"), font=font(12, "bold"), text_color=T.TEXT_2, anchor="w").grid(row=0, column=0, sticky="w", pady=(4, 6))
        ctk.CTkLabel(grid, text=t("set.language"), font=font(12, "bold"), text_color=T.TEXT_2, anchor="w").grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(4, 6))
        themes = {"system": t("theme.system"), "light": t("theme.light"), "dark": t("theme.dark")}
        seg = ctk.CTkSegmentedButton(grid, values=list(themes.values()), command=lambda v: self.set_appearance({b: a for a, b in themes.items()}[v]),
                                     font=font(12, "bold"), height=38, corner_radius=11, fg_color=T.SURFACE_2, selected_color=T.ACCENT,
                                     selected_hover_color=T.ACCENT_HOVER, unselected_color=T.SURFACE_2, unselected_hover_color=T.HOVER, text_color=T.TEXT)
        seg.set(themes.get(self.appearance.get(), themes["dark"])); seg.grid(row=1, column=0, sticky="ew")
        langs = dict(i18n.NAMES)
        self.choice(grid, self.language, list(langs), langs, command=self.change_language).grid(row=1, column=1, sticky="ew", padx=(12, 0))
        ctk.CTkSwitch(card, text=t("set.motion"), variable=self.motion, progress_color=T.ACCENT, text_color=T.TEXT, font=font(12),
                      command=lambda: self.save_settings(quiet=True)).pack(anchor="w", padx=22, pady=(16, 20))
        card = self.card(t("set.quality.title"), t("set.quality.subtitle"), icon="settings", tint="violet")
        self.field_row(card, t("set.destination"), self.destination, self.choose_destination)
        self.format_controls(card)
        grid = ctk.CTkFrame(card, fg_color="transparent"); grid.pack(fill="x", padx=22, pady=(8, 4))
        grid.grid_columnconfigure((0, 1), weight=1, uniform="q")
        ctk.CTkLabel(grid, text=t("set.resolution"), font=font(12, "bold"), text_color=T.TEXT_2, anchor="w").grid(row=0, column=0, sticky="w", pady=(6, 5))
        ctk.CTkLabel(grid, text=t("set.threads"), font=font(12, "bold"), text_color=T.TEXT_2, anchor="w").grid(row=0, column=1, sticky="w", padx=(16, 0), pady=(6, 5))
        self.choice(grid, self.resolution, QUALITY_OPTIONS["resolution"], {"Melhor disponível": t("res.best")}).grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.choice(grid, self.threads, QUALITY_OPTIONS["threads"]).grid(row=1, column=1, sticky="ew", padx=(8, 0))
        row = ctk.CTkFrame(card, fg_color="transparent"); row.pack(fill="x", padx=22, pady=(18, 22))
        self.button(row, t("btn.save_prefs"), self.save_settings, icon="check", style="primary").pack(side="left")
        self.button(row, t("btn.factory"), self.reset_settings, icon="refresh", style="ghost").pack(side="left", padx=10)
        self.update_card()
        card = self.card(t("set.privacy.title"), t("set.privacy.text"), icon="shield", tint="green")
        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()

    def update_card(self, parent=None):
        card = self.card(t("upd.title"), t("upd.subtitle"), icon="upload-cloud", tint="blue", parent=parent)
        body = ctk.CTkFrame(card, fg_color=T.SURFACE_2, corner_radius=12); body.pack(fill="x", padx=22, pady=(10, 8))
        ctk.CTkLabel(body, text=t("upd.current", v=VERSION), font=font(13, "bold"), text_color=T.TEXT, anchor="w").pack(fill="x", padx=14, pady=(12, 0))
        self.update_status_label = ctk.CTkLabel(body, text=self.update_status_text(), font=font(12), text_color=T.MUTED, anchor="w", justify="left")
        self.update_status_label.pack(fill="x", padx=14, pady=(2, 12))
        ctk.CTkLabel(card, text=t("upd.frequency"), font=font(12, "bold"), text_color=T.TEXT_2, anchor="w").pack(fill="x", padx=22, pady=(10, 6))
        self.choice(card, self.update_frequency, list(UPDATE_FREQUENCIES), {c: t(f"upd.freq.{c}") for c in UPDATE_FREQUENCIES},
                    command=lambda _: self.save_settings(quiet=True)).pack(fill="x", padx=22, pady=(0, 6))
        row = ctk.CTkFrame(card, fg_color="transparent"); row.pack(fill="x", padx=22, pady=(8, 22))
        self.button(row, t("btn.check_updates"), lambda: self.check_updates(manual=True), icon="refresh").pack(side="left")
        if self.update_info:
            self.button(row, t("btn.install_update", v=self.update_info["version"]), self.open_update_dialog, icon="download", style="primary").pack(side="left", padx=10)
        self.button(row, t("btn.releases"), lambda: webbrowser.open(updater.RELEASES_PAGE, new=2), icon="external", style="link").pack(side="right")

    # ───────────────────────────── apoio ─────────────────────────────
    def support_page(self):
        card = self.card()
        head = ctk.CTkFrame(card, fg_color="transparent"); head.pack(fill="x", padx=22, pady=20)
        logo = ctk.CTkImage(artwork.logo_tile(160), size=(64, 64))
        ctk.CTkLabel(head, text="", image=logo).pack(side="left", padx=(0, 16))
        box = ctk.CTkFrame(head, fg_color="transparent"); box.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(box, text=t("credit.full"), font=font(15, "bold"), text_color=T.TEXT, anchor="w").pack(fill="x")
        link = ctk.CTkLabel(box, text="Gestão Cultural Pro  ↗", font=font(13), text_color=T.CYAN, anchor="w", cursor="hand2")
        link.pack(fill="x", pady=(2, 4)); link.bind("<Button-1>", lambda _: self.brand())
        self.label(box, t("support.intro"), ratio=.75, text_color=T.TEXT_2).pack(fill="x")
        wide = self.content_width() >= 760
        grid = ctk.CTkFrame(self.scroll, fg_color="transparent"); grid.pack(fill="x", padx=4, pady=(0, 16))
        grid.grid_columnconfigure(0, weight=1, uniform="support")
        if wide: grid.grid_columnconfigure(1, weight=1, uniform="support")
        pix = self.card(parent=grid, pack=False)
        pix.grid(row=0, column=0, sticky="nsew", padx=(0, 8 if wide else 0), pady=(0, 0 if wide else 16))
        ctk.CTkLabel(pix, text=t("support.pix.eyebrow"), font=font(11, "bold"), text_color=T.CYAN, anchor="w").pack(fill="x", padx=22, pady=(20, 10))
        frame = ctk.CTkFrame(pix, fg_color="#FFFFFF", corner_radius=16); frame.pack(padx=22, pady=(0, 10))
        try:
            qr = Image.open(BASE / "assets/support/pix-qr.png")
            ctk.CTkLabel(frame, text="", image=ctk.CTkImage(qr, size=(232, 232))).pack(padx=14, pady=14)
        except OSError:
            ctk.CTkLabel(frame, text="PIX", text_color="#111111", width=232, height=232).pack(padx=14, pady=14)
        ctk.CTkLabel(pix, text=t("support.pix.scan"), font=font(12), text_color=T.MUTED).pack(pady=(0, 10))
        self.pix_button = self.button(pix, t("btn.copy_pix"), lambda: self.copy(PIX_CODE, self.pix_button, t("btn.copied")), icon="copy", style="cyan", height=44)
        self.pix_button.pack(fill="x", padx=22)
        code_box = ctk.CTkTextbox(pix, height=84, fg_color=T.INPUT, border_color=T.BORDER, border_width=1, corner_radius=10,
                                  text_color=T.TEXT_2, font=("Courier", 11), wrap="char")
        code_box.insert("1.0", PIX_CODE); code_box.configure(state="disabled")
        toggle = self.button(pix, "▸  " + t("support.pix.show"), None, style="link", height=30, font=font(12))
        def flip():
            if code_box.winfo_ismapped():
                code_box.pack_forget(); toggle.configure(text="▸  " + t("support.pix.show"))
            else:
                code_box.pack(fill="x", padx=22, pady=(0, 18), after=toggle); toggle.configure(text="▾  " + t("support.pix.hide"))
        toggle.configure(command=flip); toggle.pack(anchor="w", padx=16, pady=(8, 16))
        stripe = self.card(parent=grid, pack=False)
        stripe.grid(row=0 if wide else 1, column=1 if wide else 0, sticky="nsew", padx=(8 if wide else 0, 0))
        ctk.CTkLabel(stripe, text=t("support.stripe.eyebrow"), font=font(11, "bold"), text_color=T.CYAN, anchor="w").pack(fill="x", padx=22, pady=(20, 14))
        self.tile(stripe, "heart", "pink", 96, 44, 26).pack(anchor="w", padx=22, pady=(0, 20))
        ctk.CTkLabel(stripe, text=t("support.stripe.title"), font=font(20, "bold"), text_color=T.TEXT, anchor="w").pack(fill="x", padx=22)
        self.label(stripe, t("support.stripe.text"), ratio=.45 if wide else .9, text_color=T.TEXT_2).pack(fill="x", padx=22, pady=(6, 16))
        self.button(stripe, t("btn.stripe") + "  ↗", lambda: webbrowser.open(STRIPE_URL, new=2), icon="card", height=46).pack(fill="x", padx=22)
        self.stripe_copy = self.button(stripe, t("btn.copy_stripe"), lambda: self.copy(STRIPE_URL, self.stripe_copy, t("btn.copied")), icon="copy", style="link", height=32, font=font(12, "bold"))
        self.stripe_copy.pack(anchor="w", padx=16, pady=(10, 0))
        spacer = ctk.CTkFrame(stripe, fg_color="transparent", height=1); spacer.pack(fill="both", expand=True, padx=4, pady=4)
        self.label(stripe, t("support.voluntary"), ratio=.45 if wide else .9, font=font(11), text_color=T.MUTED).pack(fill="x", padx=22, pady=(20, 22), side="bottom")

    def copy(self, text, button=None, done_text=None):
        try:
            self.root.clipboard_clear(); self.root.clipboard_append(text); self.root.update()
        except tk.TclError:
            pass
        self.set_status("status.copied")
        if button is not None and button.winfo_exists():
            original = button.cget("text"); button.configure(text=done_text or original)
            self.root.after(1800, lambda: button.winfo_exists() and button.configure(text=original))

    # ───────────────────────────── sobre ─────────────────────────────
    def about_page(self):
        import platform
        card = self.card()
        head = ctk.CTkFrame(card, fg_color="transparent"); head.pack(fill="x", padx=22, pady=22)
        ctk.CTkLabel(head, text="", image=ctk.CTkImage(artwork.logo_tile(192), size=(76, 76))).pack(side="left", padx=(0, 18))
        box = ctk.CTkFrame(head, fg_color="transparent"); box.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(box, text=PRODUCT, font=font(22, "bold"), text_color=T.TEXT, anchor="w").pack(fill="x")
        ctk.CTkLabel(box, text=f"{t('app.version', v=VERSION)} • {platform.system()} {platform.machine()}", font=font(12), text_color=T.MUTED, anchor="w").pack(fill="x", pady=(2, 6))
        chips = ctk.CTkFrame(box, fg_color="transparent"); chips.pack(fill="x")
        for text, tint in ((t("about.chip.local"), "green"), (t("about.chip.offline"), "cyan"), (t("about.chip.free"), "violet")):
            bg, fg = T.TINTS[tint]
            ctk.CTkLabel(chips, text=f"  {text}  ", font=font(11, "bold"), fg_color=bg, text_color=fg, corner_radius=10, height=24).pack(side="left", padx=(0, 6))
        grid = ctk.CTkFrame(self.scroll, fg_color="transparent"); grid.pack(fill="x", padx=4, pady=(0, 16))
        columns = 3 if self.content_width() >= 900 else 1
        for c in range(columns): grid.grid_columnconfigure(c, weight=1, uniform="about")
        for index, (icon_name, tint, key) in enumerate((("shield", "green", "about.privacy"), ("drive", "cyan", "about.components"), ("info", "amber", "about.quality"))):
            box = self.card(parent=grid, pack=False)
            box.grid(row=index // columns, column=index % columns, sticky="nsew", padx=(0 if index % columns == 0 else 8, 0 if index % columns == columns - 1 else 8), pady=(0, 16 if columns == 1 else 0))
            self.tile(box, icon_name, tint, 38, 19, 11).pack(anchor="w", padx=20, pady=(20, 10))
            ctk.CTkLabel(box, text=t(key + ".title"), font=font(14, "bold"), text_color=T.TEXT, anchor="w").pack(fill="x", padx=20)
            self.label(box, t(key + ".text"), ratio=1 / columns, font=font(12), text_color=T.MUTED).pack(fill="x", padx=20, pady=(4, 20))
        card = self.card(t("credit.full"), t("about.credit.text"), icon="heart", tint="pink")
        row = ctk.CTkFrame(card, fg_color="transparent"); row.pack(fill="x", padx=22, pady=(10, 22))
        self.button(row, "gestaoculturalpro.com.br  ↗", self.brand, icon="link").pack(side="left")
        self.button(row, t("nav.support"), lambda: self.page("support"), icon="heart", style="primary").pack(side="left", padx=10)
        card = self.card(t("about.license.title"), t("about.license.text"), icon="shield", tint="blue")
        row = ctk.CTkFrame(card, fg_color="transparent"); row.pack(fill="x", padx=22, pady=(10, 22))
        self.button(row, t("btn.view_license") + "  ↗", lambda: webbrowser.open(updater.REPOSITORY_PAGE + "/blob/main/LICENSE", new=2), icon="file").pack(side="left")
        self.button(row, t("btn.source_code") + "  ↗", lambda: webbrowser.open(updater.REPOSITORY_PAGE, new=2), icon="link", style="ghost").pack(side="left", padx=10)

    # ───────────────────────────── fila e histórico ─────────────────────────────
    def queue_page(self):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent"); row.pack(fill="x", padx=4, pady=(0, 14))
        self.button(row, t("btn.resume_queue") if self.paused else t("btn.pause_queue"), self.toggle_pause, icon="play" if self.paused else "pause").pack(side="left")
        self.button(row, t("btn.add_files"), self.add_files_queue, icon="plus", style="primary").pack(side="right")
        if not self.queue:
            card = self.card()
            self.tile(card, "queue", "violet", 56, 26, 16).pack(pady=(28, 10))
            ctk.CTkLabel(card, text=t("queue.empty.title"), font=font(16, "bold"), text_color=T.TEXT).pack()
            ctk.CTkLabel(card, text=t("queue.empty.text"), font=font(12), text_color=T.MUTED).pack(pady=(4, 28))
        for task in self.queue:
            card = self.card()
            req = task["request"]
            top = ctk.CTkFrame(card, fg_color="transparent"); top.pack(fill="x", padx=18, pady=(16, 6)); top.grid_columnconfigure(1, weight=1)
            kind = req.get("download_mode") if req.get("kind") == "download" else req.get("operation")
            icon_name = MODES.get(kind, "download") if req.get("kind") == "download" else OPS.get(kind, "file")
            self.tile(top, icon_name, "cyan" if req.get("kind") == "download" else "violet", 40, 20, 11).grid(row=0, column=0, rowspan=2, padx=(0, 12))
            ctk.CTkLabel(top, text=task["name"][:90], font=font(13, "bold"), text_color=T.TEXT, anchor="w").grid(row=0, column=1, sticky="ew")
            action = t(f"mode.{kind}") if req.get("kind") == "download" else t(f"op.{kind}") if kind in OPS else t("queue.task")
            ctk.CTkLabel(top, text=f"{action} • {req.get('format', '')}", font=font(11), text_color=T.MUTED, anchor="w").grid(row=1, column=1, sticky="ew")
            state_key = task["state"]
            colors = {"waiting": "amber", "processing": "violet", "done": "green", "error": "pink", "cancelled": "blue"}
            bg, fg = T.TINTS[colors.get(state_key, "blue")]
            text = phase_label(self.phase_raw) if task is self.active and self.phase_raw else t(f"state.{state_key}")
            state = ctk.CTkLabel(top, text=f"  {text}  ", font=font(11, "bold"), fg_color=bg, text_color=fg, corner_radius=10, height=24)
            state.grid(row=0, column=2, rowspan=2, padx=(10, 0))
            bar = ctk.CTkProgressBar(card, height=6, progress_color=T.SUCCESS if state_key == "done" else T.ACCENT, fg_color=T.TRACK)
            bar.set(task.get("progress", 0) / 100); bar.pack(fill="x", padx=18, pady=(6, 12))
            has_action = state_key in ("waiting", "error", "cancelled") or bool(task.get("destination"))
            row = ctk.CTkFrame(card, fg_color="transparent", height=1)
            row.pack(fill="x", padx=18, pady=(0, 16) if has_action else (0, 4))
            if state_key == "waiting": self.button(row, t("btn.remove"), lambda t_=task: self.remove_task(t_), icon="trash", height=32, style="ghost").pack(side="left")
            elif state_key in ("error", "cancelled"): self.button(row, t("btn.retry"), lambda t_=task: self.retry(t_), icon="refresh", height=32).pack(side="left")
            elif task.get("destination"): self.button(row, t("btn.open_folder"), lambda t_=task: self.open_folder(t_["destination"]), icon="folder", height=32).pack(side="left")
            self.queue_widgets[id(task)] = (state, bar)

    def add_files_queue(self):
        self.choose_files()
        if self.files: self.enqueue_local()

    def toggle_pause(self):
        self.paused = not self.paused; self.page("queue")

    def remove_task(self, task):
        if task is not self.active: self.queue.remove(task); self.update_queue_badge(); self.page("queue")

    def retry(self, task):
        self.add_task(dict(task["request"], id=uuid.uuid4().hex), task["name"]); self.page("queue")

    def history_row(self, parent, item):
        row = ctk.CTkFrame(parent, fg_color=T.SURFACE_2, corner_radius=12); row.pack(fill="x", padx=22, pady=(4, 4))
        row.grid_columnconfigure(1, weight=1)
        status = item.get("status", "")
        ok = status in ("Concluído", "done")
        tint = "green" if ok else "pink" if status in ("Erro", "error") else "blue"
        self.tile(row, "check-circle" if ok else "info", tint, 34, 17, 10).grid(row=0, column=0, rowspan=2, padx=12, pady=10)
        title = ctk.CTkLabel(row, text=item.get("name", t("history.file"))[:90], font=font(13, "bold"), text_color=T.TEXT, anchor="w")
        title.grid(row=0, column=1, sticky="sew", pady=(10, 0))
        ctk.CTkLabel(row, text=f"{item.get('date', '')} • {self.history_status(status)}", font=font(11), text_color=T.MUTED, anchor="w").grid(row=1, column=1, sticky="new", pady=(0, 10))
        dest = item.get("destination")
        if dest:
            self.button(row, t("btn.open_folder"), lambda p=dest: self.open_folder(p), icon="folder", height=32).grid(row=0, column=2, rowspan=2, padx=12)
            title.configure(cursor="hand2"); title.bind("<Button-1>", lambda _, p=dest: self.open_folder(p))
        return row

    def history_status(self, status):
        legacy = {"Concluído": "done", "Erro": "error", "Cancelado": "cancelled"}
        return t(f"state.{legacy.get(status, status)}") if legacy.get(status, status) in TASK_STATES else status

    def history_page(self):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent"); row.pack(fill="x", padx=4, pady=(0, 14))
        self.button(row, t("btn.clear_history"), self.clear_history, icon="trash", style="ghost").pack(side="right")
        if not self.history:
            card = self.card()
            self.tile(card, "history", "amber", 56, 26, 16).pack(pady=(28, 10))
            ctk.CTkLabel(card, text=t("history.empty.title"), font=font(16, "bold"), text_color=T.TEXT).pack()
            ctk.CTkLabel(card, text=t("history.empty.text"), font=font(12), text_color=T.MUTED).pack(pady=(4, 28))
            return
        card = self.card(t("history.list"), t("history.count", n=len(self.history)), icon="history", tint="amber")
        for item in reversed(self.history):
            self.history_row(card, item)
        ctk.CTkFrame(card, height=14, fg_color="transparent").pack()

    # ───────────────────────────── seleção ─────────────────────────────
    def choose_files(self):
        paths = filedialog.askopenfilenames(title=t("dialog.choose_files"), filetypes=[(t("dialog.filetypes"), AUDIO_TYPES)])
        if paths:
            self.files = list(paths)
            self.source.set(Path(paths[0]).name if len(paths) == 1 else t("files.many", n=len(paths), first=Path(paths[0]).name))

    def choose_destination(self):
        path = filedialog.askdirectory(title=t("form.destination"))
        if path: self.destination.set(path)

    # ───────────────────────────── tarefas ─────────────────────────────
    def base_request(self):
        return dict(destination=self.destination.get(), format=self.format.get(), bits=int(self.bits.get()), rate=int(self.rate.get()),
                    bitrate=int(self.bitrate.get()), threads=int(self.threads.get()), id=uuid.uuid4().hex, wait_for_gate=True)

    def add_task(self, request, name):
        if len([x for x in self.queue if x["state"] in ("waiting", "processing")]) >= 100: raise ValueError(t("err.queue_full"))
        self.queue.append(dict(request=request, name=name, state="waiting", progress=0, destination=None))
        self.set_status("status.added"); self.update_queue_badge()

    def enqueue_local(self):
        from engine import validate
        if not self.files: self.choose_files()
        if not self.files: return
        try:
            operation = self.operation.get() if self.operation.get() in OPS else "both"
            requests = []
            for source in self.files:
                req = dict(self.base_request(), source=source, operation=operation); validate(req); requests.append(req)
            for req in requests: self.add_task(req, Path(req["source"]).name)
            self.save_settings(quiet=True); self.page("queue")
        except Exception as error: self.dialog(t("err.check_task"), str(error))

    def enqueue_download(self):
        from download import validate_url
        from urllib.parse import urlparse
        try:
            url = validate_url(self.url.get())
            selected = [dict(language=key[1], automatic=key[0]) for key, var in self.subtitle_selection.items() if var.get()] if self.subtitle_url == url else []
            if len(selected) > 20: raise ValueError(t("err.subs_limit"))
            req = dict(self.base_request(), kind="download", url=url, operation="convert", download_mode=self.mode.get() if self.mode.get() in MODES else "audio",
                       resolution=0 if self.resolution.get() == "Melhor disponível" else int(self.resolution.get()[:-1]), subtitles=selected)
            if not Path(req["destination"]).is_dir(): raise ValueError(t("err.destination"))
            data = self.metadata if self.metadata and self.metadata.get("url") == url else None
            if data and data.get("playlist"): raise ValueError(t("err.playlist"))
            self.add_task(req, data["title"] if data else "Download • " + (urlparse(url).hostname or "Link"))
            self.save_settings(quiet=True); self.page("queue")
        except Exception as error: self.dialog(t("err.download_add"), str(error))

    def analyze(self):
        from download import validate_url
        try:
            url = validate_url(self.url.get())
            if self.process: raise ValueError(t("err.busy_analyze"))
            self.url.set(url)
            self.start_task(dict(request=dict(kind="inspect", url=url, id=uuid.uuid4().hex, wait_for_gate=True), name=t("queue.inspect"), state="waiting", progress=0))
        except Exception as error: self.dialog(t("err.check_link"), str(error))

    def set_status(self, key, **values):
        self.status_key = (key, values)
        self.status.set(t(key, **values))

    def update_queue_badge(self):
        badge = getattr(self, "nav_badges", {}).get("queue")
        if not badge or not badge.winfo_exists(): return
        pending = len([x for x in self.queue if x["state"] in ("waiting", "processing")])
        if pending:
            badge.configure(text=str(pending)); badge.place(relx=1, x=-10, rely=.5, anchor="e")
        else:
            badge.place_forget()

    def update_ready_pill(self):
        pill = getattr(self, "ready_pill", None)
        if not pill or not pill.winfo_exists(): return
        busy = bool(self.active)
        bg, fg = T.TINTS["violet"] if busy else (T.SUCCESS_SOFT, T.SUCCESS)
        pill.configure(text=f"  ●  {t('pill.busy') if busy else t('pill.ready')}  ", fg_color=bg, text_color=fg)

    def start_task(self, task):
        try:
            directory = self.state_dir / "temporary"; directory.mkdir(parents=True, exist_ok=True)
            self.work = Path(tempfile.mkdtemp(prefix="task-", dir=directory)); path = self.work / "request.json"; atomic_json(path, task["request"])
            cmd = [sys.executable]
            if not getattr(sys, "frozen", False): cmd.append(str(Path(__file__).with_name("main.py")))
            self.process = subprocess.Popen([*cmd, "--worker", str(path)], **process_options())
            self.job = Job(self.process); self.active = task; task.update(state="processing", started=time.monotonic())
            self.offset = 0; self.worker_error = False; self.completed_event = False; self.eta_deadline = None; self.phase_key = None; self.phase_raw = None
            self.target_progress = self.shown_progress = 0; self.cancel_button.configure(state="normal")
            self.set_status("status.starting", name=task["name"][:85]); self.detail.set(t("status.preparing"))
            self.update_ready_pill(); self.pulse.configure(image=self.icon("bolt", 19, T.TINTS["violet"][1]), fg_color=T.TINTS["violet"][0])
            (self.work / "start.gate").touch()
        except Exception as error:
            if self.job: self.job.close(); self.job = None
            if self.process:
                if self.process.poll() is None: self.process.kill()
                self.process.wait(timeout=15); self.process = None
            if self.work: shutil.rmtree(self.work, ignore_errors=True); self.work = None
            task.update(state="error", error=str(error)); self.active = None
            self.dialog(t("err.start"), str(error))

    def read_events(self):
        path = self.work / "events.jsonl"
        if not path.exists(): return
        with path.open("rb") as stream:
            stream.seek(self.offset)
            while True:
                line = stream.readline()
                if not line or not line.endswith(b"\n"): break
                event = json.loads(line); self.offset = stream.tell()
                self.phase_raw = event["phase"]; self.status_key = ("status.raw", {}); self.status.set(phase_label(event["phase"]))
                key = event.get("phase_key", event["phase"])
                if key != self.phase_key: self.phase_key = key; self.eta_deadline = None
                if event.get("eta_seconds") is not None: self.eta_deadline = time.monotonic() + max(0, float(event["eta_seconds"]))
                if event.get("progress") is not None: self.target_progress = float(event["progress"]); self.active["progress"] = self.target_progress
                if "duration" in event: self.detail.set(f"{self.active['name'][:65]} • {event['duration']:.1f} s • {event.get('codec', '')} → {self.active['request'].get('format', '')}")
                if "segments_done" in event: self.detail.set(t("status.segments", name=self.active["name"][:65], done=event["segments_done"], total=event["segments_total"]))
                if "message" in event: self.worker_error = True; self.active["error"] = event["message"]
                if "destination" in event: self.active["destination"] = event["destination"]; self.last_output = Path(event["destination"])
                if "title" in event: self.active["name"] = event["title"]
                if event["phase"] in ("Concluído", "Link analisado"): self.completed_event = True

    def finish(self, state):
        task = self.active; inspect = task["request"].get("kind") == "inspect"
        if self.job: self.job.close(); self.job = None
        if self.process: self.process.wait(timeout=15)
        self.process = None
        if inspect and state == "done": self.metadata = json.loads((self.work / "metadata.json").read_text(encoding="utf-8"))
        task.update(state=state, progress=100 if state == "done" else task.get("progress", 0))
        if not inspect:
            req = task["request"]; destination = Path(req["destination"]).resolve(); stage = destination / f".gcp-{req['id']}.partial"
            if stage.is_dir() and stage.parent == destination: shutil.rmtree(stage, ignore_errors=True)
            self.history.append(dict(date=datetime.now().strftime("%d/%m/%Y %H:%M"), name=task["name"], status=state, destination=task.get("destination"),
                                     elapsed_seconds=time.monotonic() - task["started"]))
            self.history = self.history[-200:]
            try: atomic_json(self.state_dir / "history.json", self.history)
            except OSError: pass
        if self.work: shutil.rmtree(self.work, ignore_errors=True)
        self.work = self.active = None; self.phase_raw = None
        self.cancel_button.configure(state="disabled"); self.eta_deadline = None; self.eta.set("")
        self.update_ready_pill(); self.update_queue_badge()
        self.pulse.configure(image=self.icon("bolt", 19, T.TINTS["green"][1]), fg_color=T.TINTS["green"][0])
        self.set_status(("status.link_done" if inspect else "status.done") if state == "done" else "status.cancelled" if state == "cancelled" else "status.failed")
        if state == "error": self.dialog(t("status.failed"), task.get("error", t("err.interrupted")), retry=lambda: self.analyze() if inspect else self.retry(task))
        if inspect and self.current_page == "downloads": self.page("downloads", keep_scroll=True)
        elif self.current_page in ("queue", "history", "home"): self.page(self.current_page, keep_scroll=True)

    def poll(self):
        try:
            if self.process:
                self.read_events()
                if time.monotonic() - self.active["started"] > 6 * 3600:
                    self.cancel(); self.dialog(t("err.timeout.title"), t("err.timeout.text"))
                elif self.process.poll() is not None:
                    self.read_events(); self.finish("done" if self.process.returncode == 0 and self.completed_event and not self.worker_error else "error")
            elif not self.paused:
                task = next((x for x in self.queue if x["state"] == "waiting"), None)
                if task: self.start_task(task)
            if self.active:
                self.eta.set(duration_label(max(0, self.eta_deadline - time.monotonic())) if self.eta_deadline is not None else duration_label(None))
                widgets = self.queue_widgets.get(id(self.active))
                if widgets and widgets[0].winfo_exists(): widgets[0].configure(text=f"  {self.status.get()}  "); widgets[1].set(self.active.get("progress", 0) / 100)
            self.drain_update_events()
        except Exception:
            if self.process: self.cancel()
            self.dialog(t("err.track.title"), t("err.track.text"))
        self.root.after(180, self.poll)

    def animate(self):
        difference = self.target_progress - self.shown_progress
        self.shown_progress += difference * .22 if self.motion.get() else difference
        if self.bar.winfo_exists(): self.bar.set(max(0, min(1, self.shown_progress / 100)))
        self.root.after(40, self.animate)

    def cancel(self):
        if self.process:
            self.job.close(); self.job = None; self.process.wait(timeout=15); self.finish("cancelled"); self.target_progress = 0

    def open_folder(self, path):
        try:
            if not path or not Path(path).is_dir(): raise OSError(t("err.folder_missing"))
            open_directory(Path(path))
        except OSError as error: self.dialog(t("err.folder"), str(error))

    # ───────────────────────────── diálogos ─────────────────────────────
    def dialog(self, title, text, retry=None, confirm=None, icon=None, tint=None, actions=None):
        self.dialogs.append(dict(title=title, text=text))
        if self.testing: return None
        win = ctk.CTkToplevel(self.root); win.title(PRODUCT); self.center(win, 560, 340); win.resizable(False, False)
        win.configure(fg_color=T.SURFACE); win.transient(self.root)
        tint = tint or ("violet" if confirm else "pink")
        self.tile(win, icon or ("info" if confirm else "info"), tint, 56, 26, 18).pack(pady=(26, 12))
        ctk.CTkLabel(win, text=title, font=font(18, "bold"), text_color=T.TEXT, wraplength=480).pack(padx=24)
        ctk.CTkLabel(win, text=text, font=font(12), text_color=T.TEXT_2, wraplength=470, justify="center").pack(padx=28, pady=12, fill="both", expand=True)
        row = ctk.CTkFrame(win, fg_color="transparent"); row.pack(pady=(0, 22))
        self.button(row, t("btn.cancel") if (confirm or actions) else t("btn.ok"), win.destroy, width=120).pack(side="left", padx=5)
        action = confirm or retry
        if action:
            def apply(): win.destroy(); action()
            self.button(row, t("btn.confirm") if confirm else t("btn.retry"), apply, icon="check" if confirm else "refresh", style="primary").pack(side="left", padx=5)
        for label, callback, icon_name in actions or ():
            def run(cb=callback): win.destroy(); cb()
            self.button(row, label, run, icon=icon_name, style="primary").pack(side="left", padx=5)
        win.after(100, lambda: (win.grab_set(), win.focus_force())); win.bind("<Escape>", lambda _: win.destroy())
        return win

    def center(self, win, width, height):
        try:
            self.root.update_idletasks()
            scale = self.root._get_window_scaling()
            x = self.root.winfo_rootx() + (self.root.winfo_width() - int(width * scale)) // 2
            y = self.root.winfo_rooty() + (self.root.winfo_height() - int(height * scale)) // 3
            win.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
        except Exception:
            win.geometry(f"{width}x{height}")

    def clear_history(self):
        def clear(): self.history = []; atomic_json(self.state_dir / "history.json", []); self.page("history")
        self.dialog(t("history.clear.title"), t("history.clear.text"), confirm=clear, icon="trash")

    # ───────────────────────────── preferências ─────────────────────────────
    def load_settings(self):
        try:
            settings = json.loads((self.state_dir / "settings.json").read_text(encoding="utf-8"))
            if not isinstance(settings, dict): settings = {}
            destination = settings.get("destination")
            if isinstance(destination, str) and destination and Path(destination).is_dir(): self.destination.set(destination)
            self.motion.set(bool(settings.get("motion", True)))
            self.auto_update.set(bool(settings.get("auto_update", True)))
            frequency = settings.get("update_frequency", "startup" if self.auto_update.get() else "never")
            self.update_frequency.set(frequency if frequency in UPDATE_FREQUENCIES else "startup")
            try: self.last_update_check = float(settings.get("last_update_check", 0))
            except (TypeError, ValueError): self.last_update_check = 0.0
            if settings.get("language") in i18n.NAMES: self.language.set(settings["language"])
            if settings.get("appearance") in ("system", "light", "dark"): self.appearance.set(settings["appearance"])
            self.saved_quality = quality_defaults(settings.get("quality"))
        except (ValueError, OSError, TypeError): self.saved_quality = quality_defaults()
        for key, value in self.saved_quality.items(): getattr(self, key).set(value)

    def save_settings(self, quiet=False):
        try:
            if not quiet:
                self.saved_quality = quality_defaults({key: getattr(self, key).get() for key in FACTORY_QUALITY})
                for key, value in self.saved_quality.items(): getattr(self, key).set(value)
            atomic_json(self.state_dir / "settings.json", dict(schema=3, destination=self.destination.get(), motion=self.motion.get(),
                        quality=self.saved_quality, language=self.language.get(), appearance=self.appearance.get(), auto_update=self.update_frequency.get() != "never",
                        update_frequency=self.update_frequency.get(), last_update_check=self.last_update_check))
            if not quiet: self.set_status("status.saved")
        except OSError:
            if not quiet: self.dialog(t("err.prefs.title"), t("err.prefs.text"))

    def reset_settings(self):
        self.dialog(t("set.factory.title"), t("set.factory.text"), confirm=self.restore_factory_settings, icon="refresh")

    def restore_factory_settings(self):
        for key, value in FACTORY_QUALITY.items(): getattr(self, key).set(value)
        music = Path.home() / "Music"
        self.destination.set(str(music if music.is_dir() else Path.home()))
        self.motion.set(True); self.auto_update.set(True); self.update_frequency.set("startup"); self.operation.set("both"); self.mode.set("audio")
        self.subtitle_selection = {}; self.subtitle_url = None
        self.save_settings(); self.page("settings")
        self.set_status("status.factory")

    def is_dark(self):
        return ctk.get_appearance_mode().lower() == "dark"

    def set_appearance(self, mode):
        self.appearance.set(mode); ctk.set_appearance_mode(mode); self.save_settings(quiet=True)
        if hasattr(self, "theme_button") and self.theme_button.winfo_exists():
            self.root.after(60, lambda: self.theme_button.configure(image=self.icon("sun" if self.is_dark() else "moon", 18, T.TEXT_2)))
        if self.current_page == "settings": self.root.after(80, lambda: self.page("settings", keep_scroll=True))

    def toggle_theme(self):
        self.set_appearance("light" if self.is_dark() else "dark")

    def change_language_short(self, short):
        code = next((c for c, s in i18n.SHORT.items() if s == short), "pt")
        self.change_language(code)

    def change_language(self, code):
        if code not in i18n.NAMES: return
        self.language.set(code); i18n.set_language(code); self.save_settings(quiet=True)
        self.root.after_idle(self.build)

    def brand(self):
        webbrowser.open(BRAND_URL, new=2)

    # ───────────────────────────── atualizações ─────────────────────────────
    def update_status_text(self):
        state = self.update_state
        if state == "checking": return t("upd.checking")
        if state == "available" and self.update_info: return t("upd.available", v=self.update_info["version"])
        if state == "latest": return t("upd.latest")
        if state == "error": return t("upd.error")
        return t("upd.idle")

    def refresh_update_pill(self):
        pill = getattr(self, "update_pill", None)
        if not pill or not pill.winfo_exists(): return
        if self.update_info:
            pill.configure(text=t("upd.pill", v=self.update_info["version"])); pill.grid(row=0, column=0)
        else:
            pill.grid_remove()
        label = getattr(self, "update_status_label", None)
        if label is not None and label.winfo_exists(): label.configure(text=self.update_status_text())

    def update_due(self):
        interval = UPDATE_FREQUENCIES.get(self.update_frequency.get())
        if interval is None: return False
        return time.time() - self.last_update_check >= interval

    def check_updates(self, manual=False):
        if self.update_state in ("checking", "downloading"): return
        self.last_update_check = time.time(); self.save_settings(quiet=True)
        self.update_state = "checking"; self.refresh_update_pill()
        def work():
            try:
                info = updater.check_latest(VERSION)
                self.update_events.put(("checked", info, manual))
            except Exception as error:
                self.update_events.put(("check_error", str(error), manual))
        threading.Thread(target=work, daemon=True).start()

    def drain_update_events(self):
        while True:
            try: event = self.update_events.get_nowait()
            except queue_module.Empty: break
            kind = event[0]
            if kind == "checked":
                info, manual = event[1], event[2]
                self.update_info = info; self.update_state = "available" if info else "latest"
                self.refresh_update_pill()
                if info and manual: self.open_update_dialog()
                elif manual: self.dialog(t("upd.latest.title"), t("upd.latest"), icon="check-circle", tint="green")
                if self.current_page == "settings": self.page("settings", keep_scroll=True)
            elif kind == "check_error":
                self.update_state = "error"; self.refresh_update_pill()
                if event[2]: self.dialog(t("upd.error.title"), t("upd.error") + "\n\n" + event[1][:300], icon="upload-cloud", tint="blue")
            elif kind == "progress":
                done, total = event[1], event[2]
                dialog = self.update_dialog
                if dialog and dialog["win"].winfo_exists():
                    dialog["bar"].set(done / total if total else 0)
                    dialog["label"].configure(text=t("upd.downloading", done=f"{done / 1048576:.1f}", total=f"{total / 1048576:.1f}"))
            elif kind == "downloaded":
                self.update_state = "available"
                path = event[1]
                if self.update_dialog and self.update_dialog["win"].winfo_exists(): self.update_dialog["win"].destroy()
                self.install_update(path)
            elif kind == "download_error":
                self.update_state = "available"
                if self.update_dialog and self.update_dialog["win"].winfo_exists(): self.update_dialog["win"].destroy()
                self.dialog(t("upd.error.title"), event[1][:400], icon="upload-cloud", tint="blue")

    def open_update_dialog(self):
        info = self.update_info
        if not info or self.testing: return
        if self.update_dialog and self.update_dialog["win"].winfo_exists():
            self.update_dialog["win"].focus_force(); return
        win = ctk.CTkToplevel(self.root); win.title(PRODUCT); self.center(win, 600, 460); win.resizable(False, False)
        win.configure(fg_color=T.SURFACE); win.transient(self.root)
        self.tile(win, "upload-cloud", "violet", 56, 26, 18).pack(pady=(24, 10))
        ctk.CTkLabel(win, text=t("upd.dialog.title", v=info["version"]), font=font(19, "bold"), text_color=T.TEXT).pack()
        ctk.CTkLabel(win, text=t("upd.dialog.subtitle", current=VERSION), font=font(12), text_color=T.MUTED).pack(pady=(2, 10))
        notes = ctk.CTkTextbox(win, height=170, fg_color=T.SURFACE_2, border_width=1, border_color=T.BORDER, corner_radius=12,
                               text_color=T.TEXT_2, font=font(12), wrap="word")
        notes.insert("1.0", (info.get("notes") or t("upd.no_notes"))[:4000]); notes.configure(state="disabled")
        notes.pack(fill="x", padx=26)
        label = ctk.CTkLabel(win, text=t("upd.asset", name=info["asset"]["name"]) if info.get("asset") else t("upd.no_asset"), font=font(11), text_color=T.MUTED)
        label.pack(pady=(10, 4))
        bar = ctk.CTkProgressBar(win, height=6, progress_color=T.ACCENT, fg_color=T.TRACK); bar.set(0); bar.pack(fill="x", padx=26, pady=(2, 10))
        row = ctk.CTkFrame(win, fg_color="transparent"); row.pack(pady=(4, 20))
        self.button(row, t("btn.later"), win.destroy, width=110).pack(side="left", padx=5)
        self.button(row, t("btn.release_page"), lambda: webbrowser.open(info.get("page") or updater.RELEASES_PAGE, new=2), icon="external", style="ghost").pack(side="left", padx=5)
        install = self.button(row, t("btn.download_install"), None, icon="download", style="primary")
        def start():
            if not info.get("asset"):
                webbrowser.open(info.get("page") or updater.RELEASES_PAGE, new=2); return
            install.configure(state="disabled"); self.update_state = "downloading"
            def work():
                try:
                    path = updater.download(info, lambda done, total: self.update_events.put(("progress", done, total)))
                    self.update_events.put(("downloaded", path))
                except Exception as error:
                    self.update_events.put(("download_error", str(error)))
            threading.Thread(target=work, daemon=True).start()
        install.configure(command=start); install.pack(side="left", padx=5)
        self.update_dialog = dict(win=win, bar=bar, label=label)
        win.after(100, lambda: (win.grab_set(), win.focus_force())); win.bind("<Escape>", lambda _: win.destroy())

    def install_update(self, path):
        try:
            outcome = updater.install(path)
        except Exception as error:
            self.dialog(t("upd.error.title"), str(error)[:400], icon="upload-cloud", tint="blue"); return
        if outcome == "quit":
            if self.process:
                self.paused = True; self.cancel()
            self.root.after(300, self.root.destroy)
        else:
            self.dialog(t("upd.installed.title"), t(f"upd.installed.{outcome}", path=str(path)), icon="check-circle", tint="green")

    def close(self):
        if self.process:
            def stop(): self.paused = True; self.cancel(); self.root.destroy()
            self.dialog(t("close.title"), t("close.text"), confirm=stop)
        else: self.root.destroy()
