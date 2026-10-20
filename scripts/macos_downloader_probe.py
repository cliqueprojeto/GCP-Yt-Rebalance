"""Compara o sidecar universal original com a redução usada pelo empacotador."""
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from native_contract import architectures
from prepare_ci import acquire, LOCK, ROOT


def version(path):
    result=subprocess.run([str(path),"--version"],capture_output=True,text=True,timeout=60)
    return dict(returncode=result.returncode,stdout=result.stdout.strip(),stderr=result.stderr.strip())


def main():
    if sys.platform!="darwin": raise RuntimeError("Probe requer macOS nativo")
    folder=ROOT/"build/sidecar-probe"; folder.mkdir(parents=True,exist_ok=False)
    report=ROOT/"artifacts/ci"; report.mkdir(parents=True,exist_ok=True)
    source=acquire("https://github.com/yt-dlp/yt-dlp/releases/download/2026.08.19/yt-dlp_macos","yt-dlp_macos",LOCK["yt_dlp"]["yt-dlp_macos"])
    original=folder/"original"; shutil.copy2(source,original); original.chmod(0o755)
    thin=folder/"thin"
    subprocess.run(["lipo",str(original),"-thin",platform.machine(),"-output",str(thin)],check=True)
    thin.chmod(0o755)
    subprocess.run(["codesign","--force","--sign","-",str(thin)],check=True)
    preserved=folder/"preserved"; shutil.copy2(original,preserved)
    subprocess.run(["codesign","--force","--sign","-",str(preserved)],check=True)
    results=dict(machine=platform.machine(),architectures=sorted(architectures(original)),original=version(original),thin=version(thin),preserved_signed=version(preserved))
    (report/"macos-downloader-probe.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    print(json.dumps(results,indent=2),flush=True)
    assert results["original"]["returncode"]==results["preserved_signed"]["returncode"]==0
    assert results["original"]["stdout"]==results["preserved_signed"]["stdout"]=="2026.08.19"


if __name__=="__main__": main()
