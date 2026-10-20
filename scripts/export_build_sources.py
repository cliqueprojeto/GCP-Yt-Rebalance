"""Pacote revisável de fontes para os builds; exclui mídia, histórico e credenciais."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    files={ROOT/"README.md",ROOT/".gitignore",ROOT/".gitattributes"}
    for folder in ("apps","scripts","tests",".github","models"):
        for path in (ROOT/folder).rglob("*"):
            if path.is_file() and path.suffix in (".py",".spec",".txt",".lock",".json",".nsi",".yml",".yaml",".md") and "__pycache__" not in path.parts and "weights" not in path.parts and "audio" not in path.parts:
                files.add(path)
    for path in (ROOT/"assets/branding").iterdir():
        if path.is_file() and path.suffix.lower() in (".png",".ico",".icns",".json",".md"): files.add(path)
    files.update((ROOT/"docs").glob("*.md"))
    files.update((ROOT/"docs/adr").glob("*.md"))
    for name in ("model-acquisition.json","downloader-components.json","native-v03-2026-10-20.json"):
        path=ROOT/"docs/evidence"/name
        if path.is_file(): files.add(path)
    manifest=[]
    destination=ROOT/"dist/GCP Yt Rebalance - Fontes para build Mac Linux.zip"
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(files):
            relative=path.relative_to(ROOT).as_posix()
            content=path.read_bytes()
            # O manifesto deve coincidir com o checkout Git, também no Windows.
            # Preserva UTF-8/BOM; normaliza somente CRLF dos arquivos de texto.
            if path.suffix.lower() in (".py",".spec",".txt",".lock",".json",".nsi",".yml",".yaml",".md") or path.name in (".gitignore",".gitattributes"):
                content=content.replace(b"\r\n",b"\n")
            manifest.append(dict(path=relative,bytes=len(content),sha256=hashlib.sha256(content).hexdigest()))
            archive.writestr(relative,content)
        archive.writestr("BUILD-SOURCES.json",json.dumps(dict(product="GCP Yt Rebalance",kind="source-only, not an installer",files=manifest),ensure_ascii=False,indent=2))
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for entry in manifest: assert hashlib.sha256(archive.read(entry["path"])).hexdigest()==entry["sha256"]
    checksum=hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(f"{checksum}  {destination.name}\n",encoding="utf-8")
    print(json.dumps(dict(file=str(destination),bytes=destination.stat().st_size,files=len(manifest),sha256=checksum,installer=False),ensure_ascii=False,indent=2))


if __name__=="__main__": main()
