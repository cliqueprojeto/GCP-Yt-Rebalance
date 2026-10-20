"""Fixa todos os wheels efetivamente adquiridos, com hashes, para instalação offline."""
from pathlib import Path
import hashlib
import json
import zipfile
from email.parser import Parser

root = Path(__file__).resolve().parents[1]
records = []
for path in sorted((root / ".cache/wheels").glob("*.whl")):
    with zipfile.ZipFile(path) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))
        metadata = Parser().parsestr(archive.read(name).decode())
    records.append(dict(name=metadata["Name"], version=metadata["Version"],
                        file=path.name, bytes=path.stat().st_size,
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
if not records:
    raise SystemExit("Nenhum wheel para fixar")
lock = root / "scripts/requirements-poc-windows-x64.lock"
lock.write_text("# CPython 3.12 Windows x64; experimento, não lock de produção\n" +
                "\n".join(f"{r['name']}=={r['version']} --hash=sha256:{r['sha256']}" for r in records) + "\n", encoding="utf-8")
(root / "docs/evidence/wheels.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
print(f"{len(records)} wheels fixados; {sum(r['bytes'] for r in records)} bytes comprimidos. Não é tamanho de instalador.")
