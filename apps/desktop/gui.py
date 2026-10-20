"""Interface responsiva, downloads, fila e histórico local."""
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
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

BG, PANEL, CARD, BORDER, MUTED, PURPLE = "#0D1020", "#14182B", "#1A2036", "#343D5C", "#AFB6CE", "#855BE8"
NAV = {"Início":"home", "Downloads":"download", "Separar Áudio":"audio", "Fila":"queue", "Histórico":"history", "Configurações":"settings", "Sobre":"info"}
OPS = {"Voz + instrumental":"both", "Remover vocais — instrumental":"instrumental", "Isolar voz — acapella":"vocals", "Separar voz, bateria, baixo e outros":"stems", "Somente converter":"convert"}
MODES = {"Baixar áudio":"audio", "Baixar vídeo com áudio":"video", "Baixar e remover vocais":"instrumental", "Baixar e separar instrumentos":"stems"}


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def duration_label(seconds):
    if seconds is None or not math.isfinite(float(seconds)):
        return "Calculando pelo andamento real…"
    seconds = max(0, math.ceil(seconds))
    return f"~{seconds} s restantes nesta etapa" if seconds < 60 else f"~{seconds//60} min {seconds%60:02d} s restantes nesta etapa"


class App:
    def __init__(self, root, state_dir=None, testing=False):
        self.root, self.testing = root, testing
        self.state_dir = state_dir or state_directory()
        self.process = self.job = self.work = self.active = None
        self.queue, self.history, self.files, self.dialogs = [], [], [], []
        self.paused, self.metadata, self.last_output = False, None, None
        self.offset, self.target_progress, self.shown_progress = 0,0,0
        self.eta_deadline, self.phase_key = None, None
        self.current_page, self.queue_widgets = "Início", {}
        self.wrap_labels = []
        self.card_count = 0
        self.subtitle_selection = {}
        self.subtitle_url = None
        self.icons = {name:ctk.CTkImage(glyph(name),size=(20,20)) for name in set(NAV.values()) | {"folder","file","plus","cancel","play","pause","check","trash","link"}}
        self.source = tk.StringVar(value="Nenhum arquivo selecionado")
        music = Path.home()/"Music"
        self.destination = tk.StringVar(value=str(music if music.is_dir() else Path.home()))
        self.operation = tk.StringVar(value=next(iter(OPS)))
        self.format, self.bits = tk.StringVar(value="WAV"),tk.StringVar(value="16")
        self.rate, self.bitrate, self.threads = tk.StringVar(value="44100"),tk.StringVar(value="192"),tk.StringVar(value="2")
        self.url, self.mode, self.resolution = tk.StringVar(),tk.StringVar(value=next(iter(MODES))),tk.StringVar(value="Melhor disponível")
        self.motion = tk.BooleanVar(value=True)
        self.saved_quality = quality_defaults()
        self.status = tk.StringVar(value="Pronto para começar")
        self.detail = tk.StringVar(value="Seu áudio é processado neste computador.")
        self.eta = tk.StringVar()
        try:
            data = json.loads((self.state_dir/"history.json").read_text(encoding="utf-8"))
            self.history = data[-200:] if isinstance(data,list) else []
        except (ValueError,OSError): pass
        self.load_settings()
        ctk.set_appearance_mode("dark")
        root.title(PRODUCT); root.geometry("1180x780"); root.minsize(880,600)
        root.configure(fg_color=BG); root.protocol("WM_DELETE_WINDOW",self.close)
        root.grid_columnconfigure(1,weight=1); root.grid_rowconfigure(0,weight=1)
        self.sidebar = ctk.CTkFrame(root,width=212,corner_radius=0,fg_color=PANEL)
        self.sidebar.grid(row=0,column=0,sticky="nsew"); self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(10,weight=1)
        logo = ctk.CTkImage(Image.open(BASE/"assets/branding/taskbar-128.png"),size=(52,52))
        ctk.CTkLabel(self.sidebar,text="",image=logo).grid(row=0,column=0,pady=(20,5))
        ctk.CTkLabel(self.sidebar,text=PRODUCT,font=("Segoe UI",16,"bold")).grid(row=1,column=0,padx=10)
        ctk.CTkLabel(self.sidebar,text="ÁUDIO • VÍDEO • KARAOKÊ",font=("Segoe UI",10),text_color=MUTED).grid(row=2,column=0,pady=(4,14))
        self.nav={}
        for index,(name,icon) in enumerate(NAV.items()):
            button=self.button(self.sidebar,name,lambda p=name:self.page(p),icon=icon,fg="transparent",width=184,anchor="w")
            button.grid(row=index+3,column=0,padx=14,pady=3,sticky="ew"); self.nav[name]=button
        self.footer=ctk.CTkFrame(self.sidebar,fg_color="transparent")
        self.footer.grid(row=11,column=0,padx=12,pady=14,sticky="sew")
        ctk.CTkLabel(self.footer,text="Desenvolvido por Bruno Albertini",font=("Segoe UI",10),text_color=MUTED,wraplength=184).pack(anchor="w")
        self.button(self.footer,"Gestão Cultural Pro ↗",self.brand,fg="transparent",height=30).pack(fill="x",pady=(6,0))
        self.main=ctk.CTkFrame(root,fg_color=BG,corner_radius=0)
        self.main.grid(row=0,column=1,sticky="nsew"); self.main.grid_columnconfigure(0,weight=1); self.main.grid_rowconfigure(1,weight=1)
        heading=ctk.CTkFrame(self.main,fg_color="transparent")
        heading.grid(row=0,column=0,padx=26,pady=(23,14),sticky="ew"); heading.grid_columnconfigure(0,weight=1)
        self.title=ctk.CTkLabel(heading,text="",font=("Segoe UI",25,"bold"),anchor="w")
        self.title.grid(row=0,column=0,sticky="ew")
        self.subtitle=ctk.CTkLabel(heading,text="Baixe, separe e transforme. Seus arquivos ficam com você.",font=("Segoe UI",12),text_color=MUTED,anchor="w")
        self.subtitle.grid(row=1,column=0,sticky="ew",pady=(4,0))
        self.badge=ctk.CTkLabel(heading,text=f"v{VERSION} • CPU local",fg_color="#25213D",corner_radius=10,text_color="#D1BEFF",width=120,height=28)
        self.badge.grid(row=0,column=1,padx=(8,0))
        self.scroll=ctk.CTkScrollableFrame(self.main,fg_color=BG,corner_radius=0,scrollbar_button_color="#424C70",scrollbar_button_hover_color=PURPLE)
        self.scroll.grid(row=1,column=0,padx=(20,14),sticky="nsew")
        self.bottom=ctk.CTkFrame(self.main,fg_color=PANEL,corner_radius=16,border_width=1,border_color=BORDER)
        self.bottom.grid(row=2,column=0,sticky="ew",padx=24,pady=(12,16)); self.bottom.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(self.bottom,textvariable=self.status,font=("Segoe UI",13,"bold"),anchor="w").grid(row=0,column=0,sticky="ew",padx=16,pady=(12,2))
        self.pulse=ctk.CTkLabel(self.bottom,text="●",text_color="#6EE7B7",width=22); self.pulse.grid(row=0,column=1,padx=12)
        self.bar=ctk.CTkProgressBar(self.bottom,height=7,progress_color=PURPLE,fg_color="#2B334C"); self.bar.set(0)
        self.bar.grid(row=1,column=0,columnspan=2,padx=16,pady=7,sticky="ew")
        self.detail_label=ctk.CTkLabel(self.bottom,textvariable=self.detail,font=("Segoe UI",11),text_color=MUTED,anchor="w",justify="left",wraplength=650)
        self.detail_label.grid(row=2,column=0,columnspan=2,padx=16,sticky="ew")
        actions=ctk.CTkFrame(self.bottom,fg_color="transparent"); actions.grid(row=3,column=0,columnspan=2,sticky="ew",padx=16,pady=(6,12)); actions.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(actions,textvariable=self.eta,text_color="#CEBEFA",font=("Segoe UI",11),anchor="w").grid(row=0,column=0,sticky="w")
        self.cancel_button=self.button(actions,"Cancelar atual",self.cancel,icon="cancel",height=32,width=125)
        self.cancel_button.grid(row=0,column=1,padx=6); self.cancel_button.configure(state="disabled")
        self.button(actions,"Abrir resultado",lambda:self.open_folder(self.last_output),icon="folder",height=32,width=130).grid(row=0,column=2)
        root.bind("<Configure>",self.resize,add="+")
        self.page("Início"); root.after(400,self.set_window_icon); root.after(120,self.poll); root.after(40,self.animate)

    def button(self,parent,text,command,icon=None,fg=CARD,**kw):
        return ctk.CTkButton(parent,text=text,command=command,image=self.icons.get(icon),compound="left",fg_color=fg,
            hover_color="#4A3778" if fg==PURPLE else "#2B3451",border_color=BORDER,border_width=0 if fg in (PURPLE,"transparent") else 1,
            corner_radius=10,font=("Segoe UI",12),height=kw.pop("height",39),text_color="#F3F2FC",**kw)

    def set_window_icon(self):
        try:
            if os.name=="nt": self.root.iconbitmap(str(BASE/"assets/branding/taskbar.ico"))
            self.window_icons=[tk.PhotoImage(file=str(BASE/f"assets/branding/taskbar-{s}.png")) for s in (16,32,64)]
            self.root.iconphoto(True,*self.window_icons)
        except tk.TclError: pass

    def resize(self,event):
        if event.widget!=self.root: return
        width=max(420,self.root._reverse_window_scaling(self.root.winfo_width())-290)
        self.detail_label.configure(wraplength=width-50)
        self.title.configure(font=("Segoe UI",21 if width<680 else 25,"bold"))
        self.badge.grid_remove() if width<680 else self.badge.grid()
        for label in self.wrap_labels:
            if label.winfo_exists(): label.configure(wraplength=width-35)

    def label(self,parent,text,**kw):
        label=ctk.CTkLabel(parent,text=text,font=("Segoe UI",12),text_color=MUTED,anchor="w",justify="left",wraplength=max(380,self.root._reverse_window_scaling(self.root.winfo_width())-325),**kw)
        self.wrap_labels.append(label)
        return label

    def card(self,title=None,subtitle=None):
        card=ctk.CTkFrame(self.scroll,fg_color=CARD,corner_radius=16,border_width=1,border_color=BORDER)
        card.pack(fill="x",padx=4,pady=(0,14))
        if title: ctk.CTkLabel(card,text=title,font=("Segoe UI",16,"bold"),anchor="w").pack(fill="x",padx=20,pady=(17,5))
        if subtitle: self.label(card,subtitle).pack(fill="x",padx=20,pady=(0,10))
        self.card_count+=1
        if self.motion.get() and not self.testing and self.card_count<=6:
            def fade(step=0):
                if not card.winfo_exists(): return
                start,end=(81,65,117),(52,61,92)
                color="#"+"".join(f"{round(a+(b-a)*step/10):02x}" for a,b in zip(start,end))
                card.configure(border_color=color)
                if step<10: self.root.after(22,lambda:fade(step+1))
            fade()
        return card

    def page(self,name):
        self.current_page=name; self.queue_widgets={}; self.wrap_labels=[]; self.card_count=0
        for child in self.scroll.winfo_children(): child.destroy()
        for item,button in self.nav.items(): button.configure(fg_color="#36264F" if item==name else "transparent",text_color="#E6DAFF" if item==name else MUTED)
        titles={"Início":"Seu próximo som começa aqui","Separar Áudio":"Dê uma nova voz à sua música","Downloads":"Seu próximo download","Fila":"Tudo no seu ritmo","Histórico":"Seus últimos resultados","Configurações":"Do seu jeito","Sobre":PRODUCT}
        self.title.configure(text=titles[name])
        self.subtitle.configure(text={"Fila":"Uma tarefa ativa por vez. Adicione outras durante o processamento.","Histórico":"Resultados locais, com acesso direto à pasta de saída.","Downloads":"Cole um link e consulte as opções disponíveis."}.get(name,"Baixe, separe e transforme. Seus arquivos ficam com você."))
        if name in ("Início","Separar Áudio"): self.local_form()
        elif name=="Downloads": self.download_form()
        elif name=="Fila": self.queue_page()
        elif name=="Histórico": self.history_page()
        elif name=="Configurações": self.settings_form()
        else:
            card=self.card(PRODUCT,"Desenvolvido por Bruno Albertini\nGestão Cultural Pro")
            import platform
            self.label(card,f"Versão {VERSION} • {platform.system()} {platform.machine()}\n\nProcessamento CPU totalmente local. Sem envio de áudio, cadastro ou telemetria.\n\nA qualidade depende da mixagem e pode preservar resquícios vocais.\n\nMotor, modelo, FFmpeg/ffprobe, downloader e runtime JavaScript incluídos. Esta versão segue em validação de qualidade musical e compatibilidade.").pack(fill="x",padx=20,pady=15)
            self.button(card,"Gestão Cultural Pro ↗",self.brand,icon="link").pack(anchor="w",padx=20,pady=(0,18))
        self.scroll._parent_canvas.yview_moveto(0)

    def field_row(self,card,title,variable,command,icon="folder"):
        self.label(card,title).pack(fill="x",padx=20,pady=(10,5))
        row=ctk.CTkFrame(card,fg_color="transparent"); row.pack(fill="x",padx=20,pady=(0,12)); row.grid_columnconfigure(0,weight=1)
        ctk.CTkEntry(row,textvariable=variable,state="readonly",height=42,corner_radius=10,fg_color=BG,border_color=BORDER,border_width=1).grid(row=0,column=0,sticky="ew")
        self.button(row,"Escolher",command,icon=icon,width=108,height=42).grid(row=0,column=1,padx=(8,0))

    def option(self,parent,variable,values,command=None):
        return ctk.CTkOptionMenu(parent,variable=variable,values=values,command=command,height=40,fg_color=BG,button_color="#373050",button_hover_color=PURPLE,dropdown_fg_color=PANEL,dropdown_hover_color="#36264F",corner_radius=9,dynamic_resizing=False)

    def format_controls(self,card):
        grid=ctk.CTkFrame(card,fg_color="transparent"); grid.pack(fill="x",padx=20,pady=(0,8))
        for col in (0,1): grid.grid_columnconfigure(col,weight=1,uniform="options")
        fields=(("Formato",self.format,["WAV","PCM","FLAC","MP3"]),("Profundidade (bits)",self.bits,["16","24","32"]),("Taxa (Hz)",self.rate,["44100","48000"]),("MP3 (kbps)",self.bitrate,["128","192","256","320"]))
        self.format_widgets={}
        for index,(title,var,values) in enumerate(fields):
            row,col=index//2*2,index%2
            self.label(grid,title).grid(row=row,column=col,sticky="w",padx=(0,12),pady=(10,4))
            widget=ctk.CTkComboBox(grid,variable=var,values=values,state="readonly",height=40,corner_radius=9,border_width=1,border_color=BORDER,fg_color=BG,button_color="#373050",button_hover_color=PURPLE,dropdown_fg_color=PANEL,command=lambda _:self.update_format())
            widget.grid(row=row+1,column=col,sticky="ew",padx=(0,12),pady=(0,6)); self.format_widgets[title]=widget
        self.format_note=self.label(card,""); self.format_note.pack(fill="x",padx=20,pady=(5,12)); self.update_format()

    def update_format(self):
        fmt=self.format.get()
        if fmt=="FLAC" and self.bits.get()=="32": self.bits.set("24")
        self.format_widgets["Profundidade (bits)"].configure(values=["16","24"] if fmt=="FLAC" else ["16","24","32"],state="disabled" if fmt=="MP3" else "readonly")
        self.format_widgets["MP3 (kbps)"].configure(state="readonly" if fmt=="MP3" else "disabled")
        self.format_note.configure(text={"WAV":"WAV PCM sem compressão, com a profundidade selecionada.","PCM":"PCM bruto: inteiro com sinal • little-endian • estéreo. JSON com taxa, bits e canais acompanha o arquivo.","FLAC":"FLAC sem perdas, em 16 ou 24 bits. Converter uma fonte com perdas não recupera detalhes perdidos.","MP3":"MP3 com perdas, no bitrate selecionado. Ideal para compatibilidade e arquivos menores."}[fmt])

    def local_form(self):
        card=self.card("1. Escolha seus arquivos","Selecione áudio ou vídeo. Você pode adicionar vários arquivos à fila.")
        self.field_row(card,"Arquivo de entrada",self.source,self.choose_files,"file")
        self.field_row(card,"Pasta para salvar os resultados",self.destination,self.choose_destination)
        card=self.card("2. Escolha a transformação")
        self.option(card,self.operation,list(OPS)).pack(fill="x",padx=20,pady=15)
        self.format_controls(card)
        row=ctk.CTkFrame(card,fg_color="transparent"); row.pack(fill="x",padx=20,pady=18)
        self.button(row,"Adicionar à fila",self.enqueue_local,icon="plus",fg=PURPLE,width=180).pack(side="left")
        self.button(row,"Ver fila",lambda:self.page("Fila"),icon="queue",width=110).pack(side="right")
        card=self.card(); self.label(card,"Seus resultados terão nomes como Música_Voz.wav e Música_Instrumental.wav. Cada tarefa cria uma pasta legível e preserva resultados anteriores.").pack(fill="x",padx=18,pady=14)

    def download_form(self):
        card=self.card("1. Cole o link","YouTube, Vimeo, SoundCloud, Archive.org ou link HTTPS direto de mídia.")
        row=ctk.CTkFrame(card,fg_color="transparent"); row.pack(fill="x",padx=20,pady=(8,14)); row.grid_columnconfigure(0,weight=1)
        entry=ctk.CTkEntry(row,textvariable=self.url,height=44,corner_radius=10,border_width=1,border_color=BORDER,fg_color=BG,placeholder_text="https://www.youtube.com/watch?v=…")
        entry.grid(row=0,column=0,sticky="ew"); entry.bind("<Return>",lambda _:self.analyze())
        self.button(row,"Analisar link",self.analyze,icon="link",width=130,height=44).grid(row=0,column=1,padx=(8,0))
        info=ctk.CTkFrame(card,fg_color=BG,corner_radius=10); info.pack(fill="x",padx=20,pady=(0,16))
        data=self.metadata if self.metadata and self.metadata.get("url")==self.url.get().strip() else None
        if not data: self.label(info,"Analise o link para consultar título, duração e resoluções.").pack(fill="x",padx=14,pady=14)
        else:
            self.label(info,data["title"]).pack(fill="x",padx=14,pady=(12,5))
            if data.get("playlist"):
                mapping={f"{i+1}. {item['title'][:70]}":item["url"] for i,item in enumerate(data["playlist"])}
                def select(value):
                    self.url.set(mapping[value]); self.metadata=None; self.analyze()
                var=tk.StringVar(value="Escolha um vídeo da playlist")
                self.option(info,var,["Escolha um vídeo da playlist",*mapping],lambda v:select(v) if v in mapping else None).pack(fill="x",padx=14,pady=12)
            else:
                seconds=data.get("duration",0)
                self.label(info,f"{int(seconds//60)}:{int(seconds%60):02d} • "+("Vídeo e áudio" if data.get("video_available") else "Áudio")).pack(fill="x",padx=14,pady=(0,12))
        card=self.card("2. Escolha o download")
        self.option(card,self.mode,list(MODES),lambda _:self.root.after_idle(lambda:self.page("Downloads"))).pack(fill="x",padx=20,pady=15)
        if MODES[self.mode.get()]=="video":
            self.label(card,"Resolução do vídeo").pack(anchor="w",padx=20)
            values=["Melhor disponível"]+[f"{n}p" for n in data.get("resolutions",[])] if data else QUALITY_OPTIONS["resolution"]
            if self.resolution.get() not in values:
                preferred=int(self.resolution.get()[:-1]) if self.resolution.get().endswith("p") else 0
                allowed=[n for n in data.get("resolutions",[]) if n<=preferred]
                self.resolution.set(f"{max(allowed)}p" if allowed else values[0])
            self.option(card,self.resolution,values).pack(fill="x",padx=20,pady=(5,15))
            self.label(card,"Vídeo com áudio incluído. MP4 quando possível, ou MKV conforme os codecs oferecidos pela fonte.").pack(fill="x",padx=20,pady=(0,12))
        else:
            self.format_controls(card)
        self.subtitle_controls(data)
        self.field_row(card,"Pasta de saída",self.destination,self.choose_destination)
        self.button(card,"Adicionar download à fila",self.enqueue_download,icon="download",fg=PURPLE,width=245).pack(anchor="w",padx=20,pady=(2,18))
        card=self.card(); self.label(card,"As opções dependem da fonte. Vídeo será salvo em MP4 quando possível ou contêiner compatível. Use conteúdo que você tenha direito de baixar. Limites: 30 minutos e até 2 GiB por download.").pack(fill="x",padx=18,pady=14)

    def subtitle_controls(self,data):
        card=self.card("Legendas disponíveis","Selecione um ou mais idiomas. Serão salvos como arquivos SRT junto ao resultado, sem gravar sobre o vídeo.")
        self.button(card,"Carregar opções de legendas",self.analyze,icon="link").pack(anchor="w",padx=20,pady=12)
        if not data or data.get("playlist"):
            self.label(card,"Cole um link de vídeo e carregue as opções para consultar os idiomas disponíveis.").pack(fill="x",padx=20,pady=(0,15))
            return
        if self.subtitle_url!=data["url"]:
            self.subtitle_selection={}; self.subtitle_url=data["url"]
        tracks=data.get("subtitles",[])
        if not tracks:
            self.label(card,"A fonte não informou legendas disponíveis para este vídeo.").pack(fill="x",padx=20,pady=(0,15))
            return
        search=tk.StringVar()
        ctk.CTkEntry(card,textvariable=search,placeholder_text="Buscar idioma ou código, por exemplo português, pt ou en",height=38,border_color=BORDER,fg_color=BG).pack(fill="x",padx=20,pady=(0,8))
        rows=ctk.CTkScrollableFrame(card,height=180,fg_color=BG,corner_radius=10)
        rows.pack(fill="x",padx=20,pady=(0,8))
        count=self.label(card,""); count.pack(fill="x",padx=20,pady=(0,14))
        def update_count():
            count.configure(text=f"{sum(var.get() for var in self.subtitle_selection.values())} idioma(s) selecionado(s) • limite de 20 por tarefa • automática = gerada pela plataforma")
        def populate(*_):
            for child in rows.winfo_children(): child.destroy()
            query=search.get().casefold().strip()
            for item in tracks:
                label=f"{item['name']} • {item['language']} • "+("automática" if item["automatic"] else "publicada")
                if query and query not in label.casefold(): continue
                key=(item["automatic"],item["language"])
                var=self.subtitle_selection.setdefault(key,tk.BooleanVar(value=False))
                ctk.CTkCheckBox(rows,text=label,variable=var,command=update_count,fg_color=PURPLE,hover_color="#A784ED",font=("Segoe UI",12)).pack(anchor="w",padx=8,pady=7)
            update_count()
        search.trace_add("write",populate); populate()

    def settings_form(self):
        card=self.card("Preferências locais")
        self.field_row(card,"Pasta padrão de saída",self.destination,self.choose_destination)
        self.label(card,"Qualidade padrão para as próximas tarefas. Salve para manter após fechar o aplicativo.").pack(fill="x",padx=20,pady=10)
        self.format_controls(card)
        self.label(card,"Resolução preferida para vídeo (quando disponível)").pack(anchor="w",padx=20)
        self.option(card,self.resolution,QUALITY_OPTIONS["resolution"]).pack(fill="x",padx=20,pady=(5,15))
        self.label(card,"Threads de CPU para separação").pack(anchor="w",padx=20)
        self.option(card,self.threads,["1","2","4","8"]).pack(fill="x",padx=20,pady=(5,15))
        ctk.CTkSwitch(card,text="Animações suaves",variable=self.motion,progress_color=PURPLE).pack(anchor="w",padx=20,pady=12)
        self.button(card,"Salvar preferências",self.save_settings,icon="check",fg=PURPLE).pack(anchor="w",padx=20,pady=16)
        self.button(card,"Restaurar padrões de fábrica",self.reset_settings,icon="settings").pack(anchor="w",padx=20,pady=(0,18))
        card=self.card("Privacidade e recursos")
        self.label(card,"Sem cadastro, assinatura ou envio de áudio. O histórico fica neste computador.\n\nUma tarefa ativa por vez limita o uso de CPU e memória. Importação de arquivos de até 10 GiB e 30 minutos.").pack(fill="x",padx=20,pady=16)

    def choose_files(self):
        paths=filedialog.askopenfilenames(title="Escolher áudio ou vídeo",filetypes=[("Áudio e vídeo","*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.opus *.mp4 *.mkv *.mov *.webm *.avi")])
        if paths:
            self.files=list(paths); self.source.set(Path(paths[0]).name if len(paths)==1 else f"{len(paths)} arquivos selecionados • {Path(paths[0]).name}")

    def choose_destination(self):
        path=filedialog.askdirectory(title="Pasta para salvar os resultados")
        if path: self.destination.set(path)

    def base_request(self):
        return dict(destination=self.destination.get(),format=self.format.get(),bits=int(self.bits.get()),rate=int(self.rate.get()),bitrate=int(self.bitrate.get()),threads=int(self.threads.get()),id=uuid.uuid4().hex,wait_for_gate=True)

    def add_task(self,request,name):
        if len([t for t in self.queue if t["state"] in ("Aguardando","Processando")])>=100: raise ValueError("A fila atingiu o limite de 100 tarefas.")
        self.queue.append(dict(request=request,name=name,state="Aguardando",progress=0,destination=None))
        self.status.set("Tarefa adicionada à fila")

    def enqueue_local(self):
        from engine import validate
        if not self.files: self.choose_files()
        if not self.files: return
        try:
            requests=[]
            for source in self.files:
                req=dict(self.base_request(),source=source,operation=OPS[self.operation.get()]); validate(req); requests.append(req)
            for req in requests: self.add_task(req,Path(req["source"]).name)
            self.save_settings(quiet=True); self.page("Fila")
        except Exception as error: self.dialog("Verifique os dados da tarefa",str(error))

    def enqueue_download(self):
        from download import validate_url
        from urllib.parse import urlparse
        try:
            url=validate_url(self.url.get())
            selected=[dict(language=key[1],automatic=key[0]) for key,var in self.subtitle_selection.items() if var.get()] if self.subtitle_url==url else []
            if len(selected)>20: raise ValueError("Selecione no máximo 20 idiomas de legenda por tarefa.")
            req=dict(self.base_request(),kind="download",url=url,operation="convert",download_mode=MODES[self.mode.get()],resolution=0 if self.resolution.get()=="Melhor disponível" else int(self.resolution.get()[:-1]),subtitles=selected)
            if not Path(req["destination"]).is_dir(): raise ValueError("Escolha uma pasta de saída existente.")
            data=self.metadata if self.metadata and self.metadata.get("url")==url else None
            if data and data.get("playlist"): raise ValueError("Escolha um vídeo da playlist antes de adicioná-lo à fila.")
            self.add_task(req,data["title"] if data else "Download • "+(urlparse(url).hostname or "Link"))
            self.save_settings(quiet=True); self.page("Fila")
        except Exception as error: self.dialog("Não foi possível adicionar o download",str(error))

    def analyze(self):
        from download import validate_url
        try:
            url=validate_url(self.url.get())
            if self.process: raise ValueError("Aguarde a tarefa atual para analisar outro link. Você pode adicionar o download à fila sem análise prévia.")
            self.url.set(url)
            self.start_task(dict(request=dict(kind="inspect",url=url,id=uuid.uuid4().hex,wait_for_gate=True),name="Análise do link",state="Aguardando",progress=0))
        except Exception as error: self.dialog("Verifique o link",str(error))

    def queue_page(self):
        row=ctk.CTkFrame(self.scroll,fg_color="transparent"); row.pack(fill="x",padx=4,pady=(0,14))
        self.button(row,"Retomar fila" if self.paused else "Pausar após a atual",self.toggle_pause,icon="play" if self.paused else "pause").pack(side="left")
        self.button(row,"Adicionar arquivos",self.add_files_queue,icon="plus",fg=PURPLE).pack(side="right")
        if not self.queue: self.card("Sua fila está livre","Adicione arquivos ou links para acompanhar cada etapa aqui.")
        for task in self.queue:
            card=self.card()
            heading=self.label(card,task["name"]); heading.configure(font=("Segoe UI",13,"bold"),text_color="#F3F2FC")
            heading.pack(fill="x",padx=16,pady=(14,4))
            req=task["request"]
            labels={value:key for key,value in (MODES if req.get("kind")=="download" else OPS).items()}
            action=labels.get(req.get("download_mode") or req.get("operation"),"Tarefa")
            self.label(card,action+" • "+req.get("format","")).pack(fill="x",padx=16)
            state=ctk.CTkLabel(card,text=task["state"],text_color="#CEBEFA",anchor="w"); state.pack(fill="x",padx=16,pady=5)
            bar=ctk.CTkProgressBar(card,height=5,progress_color=PURPLE); bar.set(task.get("progress",0)/100); bar.pack(fill="x",padx=16,pady=(0,12))
            row=ctk.CTkFrame(card,fg_color="transparent"); row.pack(fill="x",padx=16,pady=(0,14))
            if task["state"]=="Aguardando": self.button(row,"Remover",lambda t=task:self.remove_task(t),icon="trash",height=30).pack(side="left")
            elif task["state"] in ("Erro","Cancelado"): self.button(row,"Tentar novamente",lambda t=task:self.retry(t),icon="play",height=30).pack(side="left")
            elif task.get("destination"): self.button(row,"Abrir pasta",lambda t=task:self.open_folder(t["destination"]),icon="folder",height=30).pack(side="left")
            self.queue_widgets[id(task)]=(state,bar)

    def add_files_queue(self):
        self.choose_files()
        if self.files: self.enqueue_local()

    def toggle_pause(self):
        self.paused=not self.paused; self.page("Fila")

    def remove_task(self,task):
        if task is not self.active: self.queue.remove(task); self.page("Fila")

    def retry(self,task):
        self.add_task(dict(task["request"],id=uuid.uuid4().hex),task["name"]); self.page("Fila")

    def history_page(self):
        row=ctk.CTkFrame(self.scroll,fg_color="transparent"); row.pack(fill="x",padx=4,pady=(0,14))
        self.button(row,"Apagar histórico",self.clear_history,icon="trash").pack(side="right")
        if not self.history: self.card("Ainda não há resultados","Suas atividades aparecerão aqui depois do processamento.")
        for item in reversed(self.history):
            card=self.card()
            title=self.label(card,item.get("name","Arquivo")); title.configure(font=("Segoe UI",13,"bold"),text_color="#F3F2FC")
            title.pack(fill="x",padx=16,pady=(14,4))
            self.label(card,f"{item.get('date','')} • {item.get('status','')}").pack(fill="x",padx=16,pady=(0,8))
            dest=item.get("destination")
            if dest:
                title.configure(cursor="hand2",text_color="#CAB6FF"); title.bind("<Button-1>",lambda _,p=dest:self.open_folder(p))
                self.button(card,"Abrir pasta do resultado",lambda p=dest:self.open_folder(p),icon="folder",height=32).pack(anchor="w",padx=16,pady=(0,14))
            else: self.label(card,"Registro antigo: destino não registrado.").pack(fill="x",padx=16,pady=(0,14))

    def start_task(self,task):
        try:
            directory=self.state_dir/"temporary"; directory.mkdir(parents=True,exist_ok=True)
            self.work=Path(tempfile.mkdtemp(prefix="task-",dir=directory)); path=self.work/"request.json"; atomic_json(path,task["request"])
            cmd=[sys.executable]
            if not getattr(sys,"frozen",False): cmd.append(str(Path(__file__).with_name("main.py")))
            self.process=subprocess.Popen([*cmd,"--worker",str(path)],**process_options())
            self.job=Job(self.process); self.active=task; task.update(state="Processando",started=time.monotonic())
            self.offset=0; self.worker_error=False; self.completed_event=False; self.eta_deadline=None; self.phase_key=None
            self.target_progress=self.shown_progress=0; self.cancel_button.configure(state="normal")
            self.status.set("Iniciando • "+task["name"][:85]); self.detail.set("Preparando os componentes locais…")
            (self.work/"start.gate").touch()
        except Exception as error:
            if self.job: self.job.close(); self.job=None
            if self.process:
                if self.process.poll() is None: self.process.kill()
                self.process.wait(timeout=15); self.process=None
            if self.work: shutil.rmtree(self.work,ignore_errors=True); self.work=None
            task.update(state="Erro",error=str(error)); self.active=None
            self.dialog("Não foi possível iniciar a tarefa",str(error))

    def read_events(self):
        path=self.work/"events.jsonl"
        if not path.exists(): return
        with path.open("rb") as stream:
            stream.seek(self.offset)
            while True:
                line=stream.readline()
                if not line or not line.endswith(b"\n"): break
                event=json.loads(line); self.offset=stream.tell(); self.status.set(event["phase"])
                key=event.get("phase_key",event["phase"])
                if key!=self.phase_key: self.phase_key=key; self.eta_deadline=None
                if event.get("eta_seconds") is not None: self.eta_deadline=time.monotonic()+max(0,float(event["eta_seconds"]))
                if event.get("progress") is not None: self.target_progress=float(event["progress"]); self.active["progress"]=self.target_progress
                if "duration" in event: self.detail.set(f"{self.active['name'][:65]} • {event['duration']:.1f} s • {event.get('codec','')} → {self.active['request'].get('format','')}")
                if "segments_done" in event: self.detail.set(f"{self.active['name'][:65]} • segmento {event['segments_done']} de {event['segments_total']} • CPU")
                if "message" in event: self.worker_error=True; self.active["error"]=event["message"]
                if "destination" in event: self.active["destination"]=event["destination"]; self.last_output=Path(event["destination"])
                if "title" in event: self.active["name"]=event["title"]
                if event["phase"] in ("Concluído","Link analisado"): self.completed_event=True

    def finish(self,state):
        task=self.active; inspect=task["request"].get("kind")=="inspect"
        if self.job: self.job.close(); self.job=None
        if self.process: self.process.wait(timeout=15)
        self.process=None
        if inspect and state=="Concluído": self.metadata=json.loads((self.work/"metadata.json").read_text(encoding="utf-8"))
        task.update(state=state,progress=100 if state=="Concluído" else task.get("progress",0))
        if not inspect:
            req=task["request"]; destination=Path(req["destination"]).resolve(); stage=destination/f".gcp-{req['id']}.partial"
            if stage.is_dir() and stage.parent==destination: shutil.rmtree(stage,ignore_errors=True)
            self.history.append(dict(date=datetime.now().strftime("%d/%m/%Y %H:%M"),name=task["name"],status=state,destination=task.get("destination"),elapsed_seconds=time.monotonic()-task["started"]))
            self.history=self.history[-200:]
            try: atomic_json(self.state_dir/"history.json",self.history)
            except OSError: pass
        if self.work: shutil.rmtree(self.work,ignore_errors=True)
        self.work=self.active=None; self.cancel_button.configure(state="disabled"); self.eta_deadline=None; self.eta.set("")
        self.status.set(("Link analisado • opções atualizadas" if inspect else "Concluído • resultado pronto") if state=="Concluído" else "Tarefa cancelada" if state=="Cancelado" else "Não foi possível concluir")
        if state=="Erro": self.dialog("Não foi possível concluir",task.get("error","O processamento foi interrompido. Tente novamente."),retry=lambda:self.analyze() if inspect else self.retry(task))
        if inspect and self.current_page=="Downloads": self.page("Downloads")
        elif self.current_page in ("Fila","Histórico"): self.page(self.current_page)

    def poll(self):
        try:
            if self.process:
                self.read_events()
                if time.monotonic()-self.active["started"]>6*3600:
                    self.cancel(); self.dialog("Tempo limite excedido","A tarefa foi encerrada após 6 horas. Tente um trecho menor.")
                elif self.process.poll() is not None:
                    self.read_events(); self.finish("Concluído" if self.process.returncode==0 and self.completed_event and not self.worker_error else "Erro")
            elif not self.paused:
                task=next((t for t in self.queue if t["state"]=="Aguardando"),None)
                if task: self.start_task(task)
            if self.active:
                self.eta.set(duration_label(max(0,self.eta_deadline-time.monotonic())) if self.eta_deadline is not None else duration_label(None))
                widgets=self.queue_widgets.get(id(self.active))
                if widgets: widgets[0].configure(text=self.status.get()); widgets[1].set(self.active.get("progress",0)/100)
        except Exception:
            if self.process: self.cancel()
            self.dialog("Erro ao acompanhar a tarefa","O processamento foi encerrado com segurança. Você pode tentar novamente.")
        self.root.after(180,self.poll)

    def animate(self):
        difference=self.target_progress-self.shown_progress
        self.shown_progress+=difference*.22 if self.motion.get() else difference
        self.bar.set(max(0,min(1,self.shown_progress/100)))
        colors=["#8061BB","#A486EA","#CDB6FF","#A486EA"]
        self.pulse.configure(text_color=colors[int(time.monotonic()*3)%4] if self.active and self.motion.get() else "#6EE7B7")
        self.root.after(40,self.animate)

    def cancel(self):
        if self.process:
            self.job.close(); self.job=None; self.process.wait(timeout=15); self.finish("Cancelado"); self.target_progress=0

    def open_folder(self,path):
        try:
            if not path or not Path(path).is_dir(): raise OSError("A pasta não foi registrada, foi movida ou não existe mais neste computador.")
            open_directory(Path(path))
        except OSError as error: self.dialog("Não foi possível abrir a pasta",str(error))

    def dialog(self,title,text,retry=None,confirm=None):
        self.dialogs.append(dict(title=title,text=text))
        if self.testing: return
        win=ctk.CTkToplevel(self.root); win.title(PRODUCT); win.geometry("540x320"); win.resizable(False,False); win.configure(fg_color=PANEL); win.transient(self.root)
        ctk.CTkLabel(win,text="?" if confirm else "!",font=("Segoe UI",30,"bold"),text_color="#D5B8FF",fg_color="#352347",corner_radius=24,width=48,height=48).pack(pady=(20,10))
        ctk.CTkLabel(win,text=title,font=("Segoe UI",18,"bold"),wraplength=480).pack()
        ctk.CTkLabel(win,text=text,font=("Segoe UI",12),text_color=MUTED,wraplength=470,justify="center").pack(padx=24,pady=12,fill="both",expand=True)
        row=ctk.CTkFrame(win,fg_color="transparent"); row.pack(pady=(0,18))
        self.button(row,"Cancelar" if confirm else "Entendi",win.destroy,width=115).pack(side="left",padx=5)
        action=confirm or retry
        if action:
            def apply(): win.destroy(); action()
            self.button(row,"Confirmar" if confirm else "Tentar novamente",apply,icon="check" if confirm else "play",fg=PURPLE).pack(side="left",padx=5)
        win.after(100,lambda:(win.grab_set(),win.focus_force())); win.bind("<Escape>",lambda _:win.destroy())

    def clear_history(self):
        def clear(): self.history=[]; atomic_json(self.state_dir/"history.json",[]); self.page("Histórico")
        self.dialog("Apagar o histórico local?","Os arquivos exportados serão preservados. Apenas os registros de atividade serão apagados.",confirm=clear)

    def load_settings(self):
        try:
            settings=json.loads((self.state_dir/"settings.json").read_text(encoding="utf-8"))
            if not isinstance(settings,dict): settings={}
            destination=settings.get("destination")
            if isinstance(destination,str) and destination and Path(destination).is_dir(): self.destination.set(destination)
            self.motion.set(bool(settings.get("motion",True)))
            self.saved_quality=quality_defaults(settings.get("quality"))
        except (ValueError,OSError,TypeError): self.saved_quality=quality_defaults()
        for key,value in self.saved_quality.items(): getattr(self,key).set(value)

    def save_settings(self,quiet=False):
        try:
            if not quiet:
                self.saved_quality=quality_defaults({key:getattr(self,key).get() for key in FACTORY_QUALITY})
                for key,value in self.saved_quality.items(): getattr(self,key).set(value)
            atomic_json(self.state_dir/"settings.json",dict(schema=2,destination=self.destination.get(),motion=self.motion.get(),quality=self.saved_quality))
            if not quiet: self.status.set("Preferências salvas neste computador")
        except OSError:
            if not quiet: self.dialog("Preferências não salvas","Não foi possível gravar as preferências neste computador.")

    def reset_settings(self):
        self.dialog("Restaurar padrões de fábrica?","Restaura formato WAV 16 bits, 44.100 Hz, MP3 192 kbps, CPU 2 threads, resolução e pasta padrão. Histórico e arquivos exportados serão preservados.",confirm=self.restore_factory_settings)

    def restore_factory_settings(self):
        for key,value in FACTORY_QUALITY.items(): getattr(self,key).set(value)
        music=Path.home()/"Music"
        self.destination.set(str(music if music.is_dir() else Path.home()))
        self.motion.set(True); self.operation.set(next(iter(OPS))); self.mode.set(next(iter(MODES)))
        self.subtitle_selection={}; self.subtitle_url=None
        self.save_settings(); self.page("Configurações")
        self.status.set("Padrões de fábrica restaurados")

    def brand(self):
        import webbrowser
        webbrowser.open("https://gestaoculturalpro.com.br",new=2)

    def close(self):
        if self.process:
            def stop(): self.paused=True; self.cancel(); self.root.destroy()
            self.dialog("Fechar durante o processamento?","A tarefa atual será cancelada e os temporários removidos.",confirm=stop)
        else: self.root.destroy()
