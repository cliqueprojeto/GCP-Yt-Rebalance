"""Deriva formatos de ícone preservando o arquivo escolhido pelo titular."""
from pathlib import Path
import hashlib
import json
import shutil
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SIZES = (16, 32, 64, 128, 256, 512)


def generate(source=ROOT / "Ícone_Sistema", target=ROOT / "assets/branding"):
    target.mkdir(parents=True, exist_ok=True)
    original = target / "gcp-yt-rebalance-icon.png"
    if source.resolve() != original.resolve():
        shutil.copyfile(source, original)
    with Image.open(original) as image:
        if image.format != "PNG" or image.width != image.height:
            raise ValueError("É necessário um PNG quadrado; não recortar a arte automaticamente.")
        image.load()
        for size in SIZES:
            image.resize((size, size), Image.Resampling.LANCZOS).save(target / f"icon-{size}.png")
        image.save(target / "gcp-yt-rebalance.ico", sizes=[(s, s) for s in SIZES if s <= 256])
        image.save(target / "gcp-yt-rebalance.icns", sizes=[(s, s) for s in SIZES if s >= 16])
        # Prancha de inspeção: tamanhos nativos em faixas, fundo navy.
        preview = Image.new("RGB", (900, 880), "#101322")
        draw = ImageDraw.Draw(preview)
        x = 16
        for size in SIZES[:-1]:
            draw.text((x, 12), f"{size}px", fill="white")
            preview.paste(image.resize((size, size), Image.Resampling.LANCZOS), (x, 40))
            x += max(size + 20, 70)
        draw.text((16, 315), "512px", fill="white")
        preview.paste(image.resize((512, 512), Image.Resampling.LANCZOS), (16, 340))
        draw.text((550, 500), "GCP Yt Rebalance", fill="white")
        preview.save(target / "preview.png")
    files = []
    for path in sorted(target.iterdir()):
        if path.suffix not in {".png", ".ico", ".icns"}:
            continue
        with Image.open(path) as im:
            item = dict(file=path.name, bytes=path.stat().st_size,
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        format=im.format, dimensions=list(im.size))
            if im.format == "ICO":
                item["sizes"] = sorted([list(s) for s in im.ico.sizes()])
            elif im.format == "ICNS":
                item["sizes"] = [list(s) for s in im.info.get("sizes", [])]
            files.append(item)
    manifest = dict(product="GCP Yt Rebalance", developer="Bruno Albertini",
                    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), files=files)
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Gerados {len(files)} ativos. Original SHA-256: {manifest['source_sha256']}")
    return manifest


if __name__ == "__main__":
    generate()
