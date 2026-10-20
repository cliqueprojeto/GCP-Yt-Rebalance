"""Finaliza evidências apenas quando o instalador e o binário real passaram."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    installer = ROOT / "dist/GCP Yt Rebalance Setup 0.2.0.exe"
    installation = read(ROOT / "artifacts/v02-installer/summary.json")
    offline = read(ROOT / "artifacts/v02-final-offline/summary.json")
    online = read(ROOT / "artifacts/v02-final-youtube/summary.json")
    downloads = read(ROOT / "artifacts/v02-final-downloads/summary.json")
    for record in (installation, offline, online, downloads):
        assert record["status"] == "passed"
    with installer.open("rb") as file:
        digest = hashlib.file_digest(file,"sha256").hexdigest()
    assert digest == installation["installer_sha256"]
    assert offline["frozen_executable"] and offline["path_isolated"]
    assert online["frozen"] and downloads["frozen"]
    assert len(downloads["cases"]) == 4
    components = {}
    payload = ROOT/"dist/v0.2/GCP Yt Rebalance"
    for path in payload.rglob("*"):
        if not path.is_file(): continue
        relative = path.relative_to(payload).as_posix()
        group = next((label for prefix,label in (
            ("_internal/torch/","PyTorch CPU"),
            ("_internal/models/","Modelo"),
            ("_internal/vendor/ffmpeg/","FFmpeg e bibliotecas"),
            ("_internal/vendor/download/","Downloader e Node"),
            ("_internal/assets/","Marca")) if relative.startswith(prefix)),"Runtime, interface e outros")
        components[group] = components.get(group,0) + path.stat().st_size
    evidence = ROOT / "docs/evidence/windows-v02"
    evidence.mkdir(exist_ok=True,parents=True)
    for folder,name in (("v02-installer","installer"),("v02-final-offline","offline"),
                        ("v02-final-youtube","youtube"),("v02-final-downloads","downloads")):
        shutil.copyfile(ROOT/f"artifacts/{folder}/summary.json",evidence/f"{name}.json")
    shutil.copyfile(ROOT/"artifacts/v02-final-offline/health.json",evidence/"gui-health.json")
    shutil.copyfile(ROOT/"vendor/notices/components.json",evidence/"components.json")
    record = dict(product="GCP Yt Rebalance", version="0.2.0", developer="Bruno Albertini",
                  artifact=installer.relative_to(ROOT).as_posix(), kind="complete Windows x64 installer",
                  bytes=installer.stat().st_size, sha256=digest, signed=False,
                  installed_payload_bytes=installation["payload_bytes"],
                  installed_payload_files=installation["payload_files"],
                  payload_size_breakdown_bytes=components,
                  tested_host="Windows 11 10.0.26300 AMD64", clean_vm_tested=False,
                  public_release_approved=False, musical_quality_approved=False,
                  other_platform_installers_delivered=False,
                  tests=["unit: 13 passed", "offline formats and 4 stems", "GUI queue and history routing",
                         "YouTube video and audio", "4 download modes on owned synthetic media",
                         "installation, complete payload hashes, installed startup and uninstallation"])
    (evidence/"release.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
    (ROOT/"dist/SHA256SUMS-0.2.0.txt").write_text(f"{digest}  {installer.name}\n",encoding="utf-8")
    print(json.dumps(record,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
