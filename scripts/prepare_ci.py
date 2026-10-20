"""Aquisição explícita de build. Nunca executado pelo aplicativo instalado."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.request import urlopen
import zipfile

ROOT=Path(__file__).resolve().parents[1]
LOCK=json.loads((ROOT/"scripts/native-sources.lock.json").read_text(encoding="utf-8"))
CACHE=ROOT/".cache/ci"


def sha(path):
    with Path(path).open("rb") as file: return hashlib.file_digest(file,"sha256").hexdigest()


def acquire(url,name,expected):
    CACHE.mkdir(parents=True,exist_ok=True)
    target=CACHE/name
    if not target.exists():
        partial=target.with_suffix(target.suffix+".partial")
        try:
            with urlopen(url,timeout=90) as source,partial.open("wb") as out:
                count=0
                while chunk:=source.read(1024*1024):
                    count+=len(chunk)
                    if count>2*1024**3: raise ValueError("Insumo excede 2 GiB")
                    out.write(chunk)
            if sha(partial)!=expected: raise ValueError(f"Checksum divergente: {name}")
            partial.replace(target)
        finally: partial.unlink(missing_ok=True)
    if sha(target)!=expected: raise ValueError(f"Cache divergente: {name}")
    return target


def unpack(archive,target):
    target=Path(target).resolve(); target.mkdir(parents=True,exist_ok=True)
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as package:
            for name in package.namelist():
                if not (target/name).resolve().is_relative_to(target): raise ValueError("Caminho de arquivo inválido")
            package.extractall(target)
    else:
        with tarfile.open(archive) as package: package.extractall(target,filter="data")


def dependencies():
    wheels=ROOT/".cache/ci-wheels"; wheels.mkdir(parents=True,exist_ok=True)
    base=[sys.executable,"-m","pip"]
    subprocess.run([*base,"download","--only-binary=:all:","--no-deps","-d",str(wheels),"-r",str(ROOT/"scripts/requirements-desktop-native.txt")],check=True)
    torch="torch==2.2.2" if sys.platform=="darwin" else "torch==2.2.2+cpu"
    command=[*base,"download","--only-binary=:all:","--no-deps","-d",str(wheels),torch]
    if sys.platform!="darwin": command += ["--index-url","https://download.pytorch.org/whl/cpu"]
    subprocess.run(command,check=True)
    subprocess.run([*base,"install","--no-index","--no-deps",*[str(path) for path in sorted(wheels.glob("*.whl"))]],check=True)
    evidence=ROOT/"artifacts/ci"; evidence.mkdir(parents=True,exist_ok=True)
    (evidence/"wheels.json").write_text(json.dumps([dict(file=p.name,sha256=sha(p),bytes=p.stat().st_size) for p in sorted(wheels.glob("*.whl"))],indent=2),encoding="utf-8")
    (evidence/"python-freeze.txt").write_text(subprocess.check_output([*base,"freeze"],text=True),encoding="utf-8")


def native_ffmpeg(build,notices):
    sources={}
    for key in ("ffmpeg","lame"):
        item=LOCK[key]; archive=acquire(item["url"],item["filename"],item["sha256"])
        unpack(archive,build/key)
        sources[key]=next(p for p in (build/key).iterdir() if p.is_dir())
        shutil.copyfile(archive,notices/archive.name)
    prefix=build/"prefix"
    lame_args=[str(sources["lame"]/"configure"),f"--prefix={prefix}","--disable-shared","--enable-static","--disable-frontend","--disable-nasm","--with-pic"]
    subprocess.run(lame_args,cwd=sources["lame"],check=True)
    subprocess.run(["make","-j2"],cwd=sources["lame"],check=True)
    subprocess.run(["make","install"],cwd=sources["lame"],check=True)
    args=[str(sources["ffmpeg"]/"configure"),f"--prefix={prefix}","--disable-autodetect","--disable-doc","--disable-debug","--disable-ffplay","--disable-shared","--enable-static","--enable-libmp3lame",f"--extra-cflags=-I{prefix/'include'}",f"--extra-ldflags=-L{prefix/'lib'}"]
    subprocess.run(args,cwd=sources["ffmpeg"],check=True)
    subprocess.run(["make","-j2"],cwd=sources["ffmpeg"],check=True)
    for name in ("ffmpeg","ffprobe"):
        shutil.copy2(sources["ffmpeg"]/name,ROOT/"vendor/ffmpeg"/name)
    for key in ("ffmpeg","lame"):
        for path in sources[key].glob("COPYING*"):
            if path.is_file(): shutil.copyfile(path,notices/f"{key}-{path.name}")
    (notices/"ffmpeg-build-command.json").write_text(json.dumps(dict(lame=lame_args,ffmpeg=args,source_hashes=LOCK),indent=2),encoding="utf-8")


def runtime():
    (ROOT/"build").mkdir(exist_ok=True)
    build=Path(tempfile.mkdtemp(prefix="native-ci-",dir=ROOT/"build"))
    notices=ROOT/"vendor/notices"; notices.mkdir(parents=True,exist_ok=True)
    for folder in ("vendor/ffmpeg","vendor/download","models/weights"): (ROOT/folder).mkdir(parents=True,exist_ok=True)
    from_model="https://huggingface.co/adefossez/HTDemucs/resolve/cbc8a9b1a87023b7fd74e7b3412e6321c0eab003/955717e8.safetensors"
    model=acquire(from_model,"955717e8.safetensors","d9fa14133cfcc034a6758923bb3a8ca9f8dfd0b582134643bbf83f72c17576dd")
    shutil.copyfile(model,ROOT/"models/weights"/model.name)
    windows=os.name=="nt"
    architecture="arm64" if platform.machine().lower() in ("arm64","aarch64") else "x64"
    if not windows and sys.platform!="darwin" and architecture!="x64": raise RuntimeError("Linux ARM ainda não é alvo")
    node_name=f"node-v25.6.1-{'win' if windows else 'darwin' if sys.platform=='darwin' else 'linux'}-{architecture}.{ 'zip' if windows else 'tar.xz'}"
    node=acquire(f"https://nodejs.org/dist/v25.6.1/{node_name}",node_name,LOCK["node"][node_name])
    unpack(node,build/"node")
    executable=next((build/"node").rglob("node.exe" if windows else "bin/node"))
    shutil.copy2(executable,ROOT/"vendor/download"/("node.exe" if windows else "node"))
    for license_file in (build/"node").rglob("LICENSE"):
        shutil.copyfile(license_file,notices/"node-LICENSE.txt"); break
    name="yt-dlp.exe" if windows else "yt-dlp_macos" if sys.platform=="darwin" else "yt-dlp_linux"
    downloader=acquire(f"https://github.com/yt-dlp/yt-dlp/releases/download/2026.08.19/{name}",name,LOCK["yt_dlp"][name])
    shutil.copy2(downloader,ROOT/"vendor/download"/("yt-dlp.exe" if windows else "yt-dlp"))
    for name in ("LICENSE","THIRD_PARTY_LICENSES.txt"):
        url=f"https://raw.githubusercontent.com/yt-dlp/yt-dlp/2026.08.19/{name}"
        with urlopen(url,timeout=60) as source: (notices/f"yt-dlp-{name}").write_bytes(source.read())
    if windows:
        item=LOCK["windows_ffmpeg"]
        archive=acquire(item["url"],"ffmpeg-windows.zip",item["sha256"]); unpack(archive,build/"ffmpeg")
        for path in next((build/"ffmpeg").glob("*/bin")).iterdir():
            if path.is_file(): shutil.copy2(path,ROOT/"vendor/ffmpeg"/path.name)
        for path in (build/"ffmpeg").rglob("LICENSE*"):
            if path.is_file(): shutil.copyfile(path,notices/f"ffmpeg-{path.name}")
        nsis=acquire("https://downloads.sourceforge.net/project/nsis/NSIS%203/3.12/nsis-3.12.zip","nsis-3.12.zip","56581f90db321581c5381193d796fffcf2d24b2f8fed2160a6c6a3baa67f2c4f")
        unpack(nsis,ROOT/".tools")
    else:
        native_ffmpeg(build,notices)
        for folder in (ROOT/"vendor/ffmpeg",ROOT/"vendor/download"):
            for path in folder.iterdir(): path.chmod(0o755)
    for distribution in importlib.metadata.distributions():
        for file in distribution.files or []:
            if file.name.lower().startswith(("license","copying","notice")):
                path=distribution.locate_file(file)
                if path.is_file() and path.stat().st_size<2_000_000:
                    (notices/f"{distribution.metadata['Name']}-{file.name}").write_bytes(path.read_bytes())
    python_license=Path(sys.base_prefix)/"LICENSE.txt"
    if python_license.is_file(): shutil.copyfile(python_license,notices/"Python.txt")
    inventory=[dict(file=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for folder in (ROOT/"vendor/ffmpeg",ROOT/"vendor/download",ROOT/"models/weights") for p in folder.rglob("*") if p.is_file()]
    (notices/"components.json").write_text(json.dumps(dict(platform=platform.platform(),machine=platform.machine(),sources=LOCK,files=inventory,public_distribution_approved=False),indent=2),encoding="utf-8")


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--python",action="store_true"); parser.add_argument("--runtime",action="store_true")
    args=parser.parse_args()
    if args.python: dependencies()
    if args.runtime: runtime()
