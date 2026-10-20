"""Instala o pacote real em destino isolado e verifica payload e primeira execução."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/desktop"))
from process_job import Job


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=ROOT/"artifacts/v03-installer")
    args=parser.parse_args()
    output=args.out.resolve()
    assert output.is_relative_to((ROOT/"artifacts").resolve())
    output.mkdir(exist_ok=False)
    target = (output / "installed").resolve()
    assert target.is_relative_to((ROOT / "artifacts").resolve()) and not target.exists()
    installer = ROOT / "dist/GCP Yt Rebalance Setup 0.3.0.exe"
    # Unicode do instalador precisa ser correto também fora da UI do aplicativo.
    import pefile
    metadata={}
    with pefile.PE(str(installer)) as binary:
        for group in binary.FileInfo or []:
            for info in group:
                for table in getattr(info,"StringTable",[]): metadata.update(table.entries)
    assert "Gestão Cultural Pro" in metadata[b"LegalCopyright"].decode("utf-8")
    result = subprocess.run([str(installer), "/S", "/TESTMODE", f"/D={target}"], timeout=300)
    assert result.returncode == 0, result.returncode
    assert (target / "gcp-install.marker").read_text() == "GCP Yt Rebalance 0.3.0"
    original = ROOT / "dist/v0.3/GCP Yt Rebalance"
    files = list(p for p in original.rglob("*") if p.is_file())
    for file in files:
        assert digest(file) == digest(target / file.relative_to(original)), file
    shutil.copyfile(ROOT / "artifacts/v03-final-offline/fixture.wav", output / "fixture.wav")
    environment = os.environ.copy()
    environment["PATH"] = str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32")
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
        environment.pop(key, None)
    health = output / "health.json"
    process = subprocess.Popen([str(target / "GCP Yt Rebalance.exe"), "--self-test", str(health)], env=environment)
    job = Job(process)
    try:
        code = process.wait(timeout=180)
    finally:
        job.close()
        process.wait(timeout=15)
    assert code == 0
    check = json.loads(health.read_text(encoding="utf-8"))
    assert check["status"] == "passed" and check["gui_queue_conversion"] and check["history_open_routing"]
    # Destino absoluto verificado acima; o desinstalador remove apenas seu próprio payload.
    assert target.is_relative_to((ROOT / "artifacts").resolve())
    assert (target / "gcp-install.marker").read_text() == "GCP Yt Rebalance 0.3.0"
    uninstall = subprocess.run([str(target / "Desinstalar.exe"), "/S", "/TESTMODE", f"_?={target}"], timeout=120)
    assert uninstall.returncode == 0
    assert not (target / "GCP Yt Rebalance.exe").exists()
    assert not (target / "_internal").exists()
    record = dict(status="passed", installer_sha256=digest(installer),
                  installer_bytes=installer.stat().st_size, payload_files=len(files),
                  payload_bytes=sum(p.stat().st_size for p in files),
                  payload_hashes_verified=True, installer_unicode_branding=True, installation=True, installed_gui_health=check,
                  uninstallation=True, test_mode=True, shortcuts_registry_tested=False,
                  path_isolated=True, clean_vm=False)
    (output / "summary.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
