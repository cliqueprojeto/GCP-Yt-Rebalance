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


DESKTOP_ENTRY=(f'[Desktop Entry]\nType=Application\nName={PRODUCT}\nGenericName=Audio and video toolkit\n'
               'Comment=Desenvolvido por Bruno Albertini — Gestão Cultural Pro\n'
               'Comment[en]=Download, split and convert audio and video locally\n'
               'Comment[es]=Descarga, separa y convierte audio y video localmente\n'
               'Exec=gcp-yt-rebalance\nIcon=gcp-yt-rebalance\nTerminal=false\nStartupWMClass=GCP Yt Rebalance\n'
               'Categories=AudioVideo;Audio;Video;\nKeywords=karaoke;audio;video;download;stems;\n')

RPM_REQUIRES=", ".join(f"{lib}()(64bit)" for lib in ("libX11.so.6","libXext.so.6","libXrender.so.1","libXft.so.2","libfontconfig.so.1",
    "libfreetype.so.6","libxcb.so.1","libz.so.1","libgomp.so.1","libstdc++.so.6","libcrypt.so.1"))


def write_checksum(path):
    with path.open("rb") as file: digest=hashlib.file_digest(file,"sha256").hexdigest()
    path.with_suffix(path.suffix+".sha256").write_text(f"{digest}  {path.name}\n",encoding="utf-8")
    return digest


def build_rpm(stage):
    """RPM a partir da mesma árvore do DEB (Fedora, openSUSE, RHEL e derivados)."""
    if not shutil.which("rpmbuild"): raise RuntimeError("rpmbuild ausente (apt-get install rpm)")
    top=Path(tempfile.mkdtemp(prefix="rpm-",dir=ROOT/"build"))
    for folder in ("BUILD","RPMS","SOURCES","SPECS","SRPMS","BUILDROOT"): (top/folder).mkdir()
    spec=top/"SPECS/gcp-yt-rebalance.spec"
    spec.write_text(f"""Name: gcp-yt-rebalance
Version: {VERSION}
Release: 1
Summary: Audio, video and karaoke toolkit with local processing
License: LicenseRef-Proprietary
URL: https://gestaoculturalpro.com.br
Packager: Bruno Albertini
Vendor: Gestão Cultural Pro
BuildArch: x86_64
AutoReqProv: no
Requires: {RPM_REQUIRES}, xdg-utils
%global __strip /bin/true
%global debug_package %{{nil}}
%global _build_id_links none
%global __os_install_post %{{nil}}
%global __brp_check_rpaths %{{nil}}
%global _binary_payload w6T0.xzdio

%description
GCP Yt Rebalance: downloads, vocal and instrument separation and audio
conversion processed locally, with every component included.
Desenvolvido por Bruno Albertini — Gestão Cultural Pro.

%install
mkdir -p %{{buildroot}}
cp -a "{stage}/opt" "{stage}/usr" %{{buildroot}}/

%files
%defattr(-,root,root,-)
/opt/gcp-yt-rebalance
/usr/bin/gcp-yt-rebalance
/usr/share/applications/gcp-yt-rebalance.desktop
/usr/share/icons/hicolor/*/apps/gcp-yt-rebalance.png
""",encoding="utf-8")
    subprocess.run(["rpmbuild","-bb","--define",f"_topdir {top}",str(spec)],check=True)
    built=next((top/"RPMS/x86_64").glob("*.rpm"))
    output=ROOT/f"dist/gcp-yt-rebalance-{VERSION}-1.x86_64.rpm"; output.parent.mkdir(exist_ok=True)
    if output.exists(): raise FileExistsError(output)
    shutil.move(str(built),output)
    return output


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
        output=ROOT/f"dist/GCP-Yt-Rebalance-{VERSION}-macOS-{arch}.dmg"
        if output.exists(): raise FileExistsError(output)
        subprocess.run(["hdiutil","create","-volname",PRODUCT,"-srcfolder",str(stage),"-format","UDZO","-ov",str(output)],check=True)
    elif sys.platform=="linux" and platform.machine()=="x86_64":
        source=ROOT/f"dist/native/{PRODUCT}"
        payload=validate_payload(source,"linux-x86_64")
        destination=stage/"opt/gcp-yt-rebalance"
        shutil.copytree(source,destination,symlinks=True)
        size=sum(p.stat().st_size for p in source.rglob("*") if p.is_file())
        applications=stage/"usr/share/applications"; applications.mkdir(parents=True)
        (applications/"gcp-yt-rebalance.desktop").write_text(DESKTOP_ENTRY,encoding="utf-8")
        for size_px in (16,32,64,128,256,512):
            icons=stage/f"usr/share/icons/hicolor/{size_px}x{size_px}/apps"; icons.mkdir(parents=True)
            shutil.copyfile(ROOT/f"assets/branding/taskbar-{size_px}.png",icons/"gcp-yt-rebalance.png")
        launcher=stage/"usr/bin"; launcher.mkdir(parents=True)
        (launcher/"gcp-yt-rebalance").write_text('#!/bin/sh\nexec "/opt/gcp-yt-rebalance/GCP Yt Rebalance" "$@"\n',encoding="utf-8")
        (launcher/"gcp-yt-rebalance").chmod(0o755)
        rpm_output=build_rpm(stage)
        control=stage/"DEBIAN"; control.mkdir()
        (control/"control").write_text(f"Package: gcp-yt-rebalance\nVersion: {VERSION}\nArchitecture: amd64\nMaintainer: Bruno Albertini\nSection: sound\nPriority: optional\nInstalled-Size: {math.ceil(size/1024)}\nDepends: libc6 (>= 2.35), libstdc++6, libgcc-s1, libgomp1, libx11-6, libxext6, libxrender1, libxft2, libfontconfig1, libfreetype6, libxcb1, xdg-utils\nHomepage: https://gestaoculturalpro.com.br\nDescription: GCP Yt Rebalance\n Áudio, vídeo e karaokê com processamento local: downloads, separação de voz\n e instrumentos e conversão. Todos os componentes incluídos.\n Desenvolvido por Bruno Albertini — Gestão Cultural Pro.\n",encoding="utf-8")
        output=ROOT/f"dist/gcp-yt-rebalance_{VERSION}_amd64.deb"
        if output.exists(): raise FileExistsError(output)
        subprocess.run(["dpkg-deb","-Zxz","--root-owner-group","--build",str(stage),str(output)],check=True)
        write_checksum(rpm_output)
    else: raise RuntimeError("Execute o empacotamento no SO e arquitetura alvo.")
    write_checksum(output)
    (ROOT/"artifacts/ci/native-payload.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    with output.open("rb") as file: digest=hashlib.file_digest(file,"sha256").hexdigest()
    record=dict(file=output.name,version=VERSION,bytes=output.stat().st_size,sha256=digest,host=platform.platform(),architecture=platform.machine(),payload_bytes=payload["payload_bytes"],architecture_verified=True,model_verified=True,installation_tested=False,signed=False,clean_vm_tested=False,public_release=False)
    (ROOT/"artifacts/ci/package.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    print(json.dumps(record,indent=2))


if __name__=="__main__": main()
