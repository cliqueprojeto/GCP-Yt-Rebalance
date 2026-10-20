"""Produz DMG ou DEB real somente a partir do build nativo validado."""
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/desktop"))
from runtime import PRODUCT,VERSION
from native_contract import validate_payload


def main():
    health=json.loads((ROOT/"artifacts/v03-final-offline/health.json").read_text(encoding="utf-8"))
    summary=json.loads((ROOT/"artifacts/v03-final-offline/summary.json").read_text(encoding="utf-8"))
    assert health["status"]==summary["status"]=="passed" and health["frozen"]
    assert health["version"]==VERSION and health["preferences_save_reload"] and health["subtitle_selection_ui"]
    if sys.platform not in ("darwin","linux"): raise RuntimeError("Requer macOS ou Linux nativo")
    (ROOT/"build").mkdir(exist_ok=True)
    (ROOT/"artifacts/ci").mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix="package-",dir=ROOT/"build"))
    stage.chmod(0o755)
    if sys.platform=="darwin":
        source=ROOT/f"dist/native/{PRODUCT}.app"
        arch="arm64" if platform.machine()=="arm64" else "x86_64"
        payload=validate_payload(source,"macos-"+arch)
        subprocess.run(["ditto",str(source),str(stage/source.name)],check=True)
        (stage/"Applications").symlink_to("/Applications",target_is_directory=True)
        output=ROOT/f"dist/{PRODUCT}-{VERSION}-macOS-{arch}.dmg"
        if output.exists(): raise FileExistsError(output)
        subprocess.run(["hdiutil","create","-volname",PRODUCT,"-srcfolder",str(stage),"-format","UDZO","-ov",str(output)],check=True)
    elif sys.platform=="linux" and platform.machine()=="x86_64":
        source=ROOT/f"dist/native/{PRODUCT}"
        payload=validate_payload(source,"linux-x86_64")
        destination=stage/"opt/gcp-yt-rebalance"
        shutil.copytree(source,destination,symlinks=True)
        control=stage/"DEBIAN"; control.mkdir()
        size=sum(p.stat().st_size for p in source.rglob("*") if p.is_file())
        (control/"control").write_text(f"Package: gcp-yt-rebalance\nVersion: {VERSION}\nArchitecture: amd64\nMaintainer: Bruno Albertini\nSection: sound\nPriority: optional\nInstalled-Size: {math.ceil(size/1024)}\nDepends: libc6 (>= 2.35), libstdc++6, libgcc-s1, libgomp1, libx11-6, libxext6, libxrender1, libxft2, libfontconfig1, libfreetype6, libxcb1, xdg-utils\nHomepage: https://gestaoculturalpro.com.br\nDescription: GCP Yt Rebalance\n Conversão e separação CPU local com componentes incluídos.\n Desenvolvido por Bruno Albertini — Gestão Cultural Pro.\n",encoding="utf-8")
        applications=stage/"usr/share/applications"; applications.mkdir(parents=True)
        (applications/"gcp-yt-rebalance.desktop").write_text(f'[Desktop Entry]\nType=Application\nName={PRODUCT}\nComment=Desenvolvido por Bruno Albertini — Gestão Cultural Pro\nExec="/opt/gcp-yt-rebalance/{PRODUCT}"\nIcon=gcp-yt-rebalance\nTerminal=false\nCategories=AudioVideo;Audio;\n',encoding="utf-8")
        for size in (16,32,64,128,256,512):
            icons=stage/f"usr/share/icons/hicolor/{size}x{size}/apps"; icons.mkdir(parents=True)
            shutil.copyfile(ROOT/f"assets/branding/taskbar-{size}.png",icons/"gcp-yt-rebalance.png")
        output=ROOT/f"dist/gcp-yt-rebalance_{VERSION}_amd64.deb"
        if output.exists(): raise FileExistsError(output)
        subprocess.run(["dpkg-deb","--root-owner-group","--build",str(stage),str(output)],check=True)
    else: raise RuntimeError("Execute o empacotamento no SO e arquitetura alvo.")
    (ROOT/"artifacts/ci/native-payload.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    with output.open("rb") as file: digest=hashlib.file_digest(file,"sha256").hexdigest()
    output.with_suffix(output.suffix+".sha256").write_text(f"{digest}  {output.name}\n",encoding="utf-8")
    record=dict(file=output.name,version=VERSION,bytes=output.stat().st_size,sha256=digest,host=platform.platform(),architecture=platform.machine(),payload_bytes=payload["payload_bytes"],architecture_verified=True,model_verified=True,installation_tested=False,signed=False,clean_vm_tested=False,public_release=False)
    (ROOT/"artifacts/ci/package.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    print(json.dumps(record,indent=2))


if __name__=="__main__": main()
