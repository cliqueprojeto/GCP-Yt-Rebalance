"""Reúne avisos e inventário dos componentes usados no pacote experimental."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "vendor/notices"
TARGET.mkdir(parents=True, exist_ok=True)
packages = []
for name in ("torch", "numpy", "demucs", "safetensors", "soundfile", "julius", "einops", "pyinstaller", "Pillow", "customtkinter", "darkdetect"):
    distribution = importlib.metadata.distribution(name)
    texts = []
    for file in distribution.files or []:
        if any(part.lower().startswith(("license", "copying", "notice", "copyright")) for part in file.parts):
            path = distribution.locate_file(file)
            if path.is_file() and path.stat().st_size < 2_000_000:
                texts.append(f"\n--- {file} ---\n" + path.read_text(encoding="utf-8", errors="replace"))
    (TARGET / f"{name}.txt").write_text("\n".join(texts) or "Consultar licença no pacote de origem.", encoding="utf-8")
    packages.append(dict(name=name, version=distribution.version))
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.is_file():
    (TARGET / "Python.txt").write_bytes(python_license.read_bytes())
for directory in (Path(sys.base_prefix) / "tcl/tcl8.6", Path(sys.base_prefix) / "tcl/tk8.6"):
    for name in ("license.terms", "license.txt"):
        source = directory / name
        if source.is_file():
            (TARGET / f"{directory.name}-{name}").write_bytes(source.read_bytes())
version = subprocess.run([str(ROOT / "vendor/ffmpeg/ffmpeg.exe"), "-version"], capture_output=True, text=True, check=True)
(TARGET / "ffmpeg-build.txt").write_text(version.stdout + "\n" + version.stderr, encoding="utf-8")
files = []
for folder in (ROOT / "vendor/ffmpeg", ROOT / "models/weights", ROOT / "vendor/download"):
    for path in sorted(folder.iterdir()):
        if path.is_file():
            files.append(dict(path=path.relative_to(ROOT).as_posix(), bytes=path.stat().st_size,
                              sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
record = dict(product="GCP Yt Rebalance", version="0.3.0", platform="Windows x64",
              packages=packages, files=files,
              ffmpeg_archive_sha256="46e480b5509ce50061158621cac3d1930836475fadf60c72da9aca15fd830620",
              ffmpeg_origin="https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n8.1-latest-win64-lgpl-shared-8.1.zip",
              public_distribution_approved=False)
(TARGET / "components.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
(TARGET / "LEIA-ME.txt").write_text("GCP Yt Rebalance — versão experimental para teste local.\nDesenvolvido por Bruno Albertini\nGestão Cultural Pro — https://gestaoculturalpro.com.br\n\nNão é uma release pública. Auditoria de redistribuição de pesos e de todas as dependências ainda pendente.\nFFmpeg LGPL fornecido por BtbN; compilação e hashes em components.json e ffmpeg-build.txt.\nFFmpeg: https://ffmpeg.org/legal.html\nOrigem dos pesos: https://huggingface.co/adefossez/HTDemucs\n", encoding="utf-8")
print(f"Inventariados {len(files)} arquivos e {len(packages)} pacotes principais")
