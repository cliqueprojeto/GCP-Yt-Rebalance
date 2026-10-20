"""Pequenas integrações nativas; processamento continua totalmente local."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

HIDDEN = getattr(subprocess,"CREATE_NO_WINDOW",0)


def process_options():
    return dict(creationflags=HIDDEN) if os.name=="nt" else dict(start_new_session=True)


def state_directory():
    if os.name=="nt": return Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"GestaoCulturalPro/GCPYtRebalance"
    if sys.platform=="darwin": return Path.home()/"Library/Application Support/GestaoCulturalPro/GCPYtRebalance"
    return Path(os.environ.get("XDG_STATE_HOME",str(Path.home()/".local/state")))/"GestaoCulturalPro/GCPYtRebalance"


def open_directory(path):
    if os.name=="nt": os.startfile(str(path))
    else:
        opener="/usr/bin/open" if sys.platform=="darwin" else shutil.which("xdg-open")
        if not opener: raise OSError("O sistema não disponibilizou um gerenciador de arquivos.")
        subprocess.Popen([opener,str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
