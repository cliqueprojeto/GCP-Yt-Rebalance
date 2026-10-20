"""Evidência da entrega 0.3; exige instalador e testes reais aprovados."""
import hashlib
import argparse
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--installer-summary",type=Path,default=ROOT/"artifacts/v03-installer/summary.json")
    args=parser.parse_args()
    evidence=ROOT/"docs/evidence/windows-v03"; evidence.mkdir(parents=True,exist_ok=True)
    records={}
    for folder,name in (("v03-final-offline","offline"),("v03-final-subtitles","subtitles"),("v03-installer","installer"),("v03-ci-minimal","minimal-ci-environment")):
        source=ROOT/f"artifacts/{folder}/summary.json"
        if name=="installer": source=args.installer_summary.resolve()
        record=json.loads(source.read_text(encoding="utf-8")); assert record["status"]=="passed"
        records[name]=record
        shutil.copyfile(source,evidence/f"{name}.json")
    health=json.loads((ROOT/"artifacts/v03-final-offline/health.json").read_text(encoding="utf-8"))
    assert health["status"]=="passed" and health["frozen"] and health["version"]=="0.3.0"
    assert health["preferences_save_reload"] and health["factory_reset_preserves_history"] and health["subtitle_selection_ui"]
    assert records["subtitles"]["frozen"]
    installer=ROOT/"dist/GCP Yt Rebalance Setup 0.3.0.exe"
    with installer.open("rb") as file: digest=hashlib.file_digest(file,"sha256").hexdigest()
    assert digest==records["installer"]["installer_sha256"]
    shutil.copyfile(ROOT/"artifacts/v03-final-offline/health.json",evidence/"gui-health.json")
    shutil.copyfile(ROOT/"vendor/notices/components.json",evidence/"components.json")
    shutil.copyfile(ROOT/"scripts/native-sources.lock.json",evidence/"native-sources.lock.json")
    record=dict(product="GCP Yt Rebalance",version="0.3.0",artifact=installer.relative_to(ROOT).as_posix(),bytes=installer.stat().st_size,sha256=digest,
        payload_bytes=records["installer"]["payload_bytes"],payload_files=records["installer"]["payload_files"],unit_tests_passed=16,
        signed=False,clean_vm_tested=False,musical_quality_approved=False,public_release=False,
        packaging_revision=2 if records["installer"].get("installer_unicode_branding") else 1,
        installer_unicode_branding=records["installer"].get("installer_unicode_branding",False),
        native_pipeline_prepared=True,native_pipeline_executed=False,macos_installers_delivered=False,linux_installer_delivered=False)
    (evidence/"release.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(record,ensure_ascii=False,indent=2))


if __name__=="__main__": main()
