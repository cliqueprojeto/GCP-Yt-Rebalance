"""Checksums dos arquivos instaladores efetivamente presentes."""
import hashlib
from pathlib import Path

root=Path(__file__).resolve().parents[1]
for pattern in ("*Setup*.exe","*.dmg","*.deb","*.rpm","*.pkg.tar.zst"):
    for path in (root/"dist").glob(pattern):
        with path.open("rb") as file: digest=hashlib.file_digest(file,"sha256").hexdigest()
        path.with_suffix(path.suffix+".sha256").write_text(f"{digest}  {path.name}\n",encoding="utf-8")
        print(f"{path.name}: {digest}")
