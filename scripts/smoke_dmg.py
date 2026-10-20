"""Monta o DMG gerado, copia o .app e testa a primeira execução instalada."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
from native_contract import verify_manifest, digest

ROOT=Path(__file__).resolve().parents[1]


def main():
    if sys.platform!="darwin": raise RuntimeError("Requer macOS nativo")
    package=json.loads((ROOT/"artifacts/ci/package.json").read_text())
    dmg=ROOT/"dist"/package["file"]
    assert digest(dmg)==package["sha256"]
    payload=json.loads((ROOT/"artifacts/ci/native-payload.json").read_text(encoding="utf-8"))
    destination=ROOT/"artifacts/installed-macos"; destination.mkdir(exist_ok=False)
    mount=destination/"volume"; mount.mkdir()
    subprocess.run(["hdiutil","attach","-readonly","-nobrowse","-mountpoint",str(mount),str(ROOT/"dist"/package["file"])],check=True)
    try:
        target=destination/"GCP Yt Rebalance.app"
        subprocess.run(["ditto",str(mount/target.name),str(target)],check=True)
        verify_manifest(target,payload["files"])
        subprocess.run(["codesign","--verify","--deep","--strict",str(target)],check=True)
        shutil.copyfile(ROOT/"artifacts/v03-final-offline/fixture.wav",destination/"fixture.wav")
        subprocess.run([str(target/"Contents/MacOS/GCP Yt Rebalance"),"--self-test",str(destination/"health.json")],check=True,timeout=240)
        health=json.loads((destination/"health.json").read_text())
        assert health["status"]=="passed" and health["gui_queue_conversion"] and health["preferences_save_reload"]
        package.update(installation_tested=True,installed_payload_verified=True)
        (ROOT/"artifacts/ci/package.json").write_text(json.dumps(package,indent=2),encoding="utf-8")
    finally: subprocess.run(["hdiutil","detach",str(mount)],check=True)


if __name__=="__main__": main()
