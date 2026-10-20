"""Aquisição EXPLÍCITA de insumos públicos da POC; nunca chamado pelo produto."""
import hashlib
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REVISION = "cbc8a9b1a87023b7fd74e7b3412e6321c0eab003"
TRACKS = [
    ("male-dense", "CSoul", "32913", "CSoul_-_Somebody_Help_Me.mp3", "Somebody Help Me — CSoul feat. Down With Ben e Admiral Bob"),
    ("female", "Numeron", "38368", "Numeron_-_Life_Story.mp3", "Life Story — Numeron feat. myvanillaworld (The Writer)"),
    ("acoustic", "tobias_weber", "57449", "tobias_weber_-_Up_2_Us.mp3", "Up 2 Us — Aussens@iter feat. Mr. Yesterday"),
]


def download(url, path, limit=150_000_000, sha256=None):
    if path.exists():
        data = path.read_bytes()
        if sha256 and hashlib.sha256(data).hexdigest() != sha256:
            raise ValueError("Checksum do cache diverge do upstream")
        return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    try:
        with urllib.request.urlopen(url, timeout=60) as response, partial.open("xb") as out:
            count = 0
            while chunk := response.read(1024 * 1024):
                count += len(chunk)
                if count > limit:
                    raise ValueError("Insumo excedeu limite explícito")
                out.write(chunk)
        digest = hashlib.sha256(partial.read_bytes()).hexdigest()
        if sha256 and digest != sha256:
            raise ValueError("Checksum não confere")
        partial.rename(path)
        return dict(bytes=count, sha256=digest)
    finally:
        partial.unlink(missing_ok=True)


def main():
    evidence = ROOT / "docs/evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    records = []
    for key, artist, upload, filename, attribution in TRACKS:
        page = f"https://ccmixter.org/files/{artist}/{upload}"
        html = urllib.request.urlopen(page, timeout=30).read().decode()
        if not re.search(r'rel="license"\s+href="https?://creativecommons.org/licenses/by/3.0/', html):
            raise ValueError(f"Licença CC BY 3.0 não confirmada: {key}")
        api = f"https://ccmixter.org/api/query/api?ids={upload}&f=json&dataview=links_dl"
        data = json.load(urllib.request.urlopen(api, timeout=30))[0]
        # Escolha apenas o MP3 de preview/mix, nunca ZIP ou entrada arbitrária.
        item = next(x for x in data["files"] if x["file_name"] == filename)
        url = item["download_url"]
        if not url.startswith(f"https://ccmixter.org/content/{artist}/"):
            raise ValueError("Origem inesperada")
        path = ROOT / "tests/fixtures/audio" / f"{key}.mp3"
        record = dict(id=key, attribution=attribution, source=page, download=url,
                      license="CC-BY-3.0", license_url="https://creativecommons.org/licenses/by/3.0/",
                      modifications="Nenhuma no arquivo adquirido; saídas de POC são derivações de separação.",
                      profile_verified_by_listening=False)
        try:
            record.update(download(url, path))
            record["status"] = "downloaded"
        except Exception as error:
            record.update(status="unavailable", error_type=type(error).__name__, error=str(error))
        records.append(record)
        (evidence / "audio-sources.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{key}: {record['status']}", flush=True)
    api = f"https://huggingface.co/api/models/adefossez/HTDemucs/revision/{REVISION}?blobs=true"
    metadata = json.load(urllib.request.urlopen(api, timeout=30))
    file = next(x for x in metadata["siblings"] if x["rfilename"] == "955717e8.safetensors")
    digest = file["lfs"]["sha256"]
    url = f"https://huggingface.co/adefossez/HTDemucs/resolve/{REVISION}/955717e8.safetensors"
    result = download(url, ROOT / "models/weights/955717e8.safetensors", sha256=digest)
    record = dict(repository="adefossez/HTDemucs", revision=REVISION, url=url,
                  upstream_sha256=digest, redistribution_approved=False,
                  license_status="Card sem licença explícita; distribuição pendente de confirmação", **result)
    (evidence / "model-acquisition.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Pesos oficiais verificados: {result['bytes']} bytes", flush=True)


if __name__ == "__main__":
    main()
