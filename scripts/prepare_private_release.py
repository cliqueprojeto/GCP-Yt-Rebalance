"""Verifica a lista explícita de instaladores e prepara evidências da release privada."""
import hashlib
import json
import os
import shutil
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def write_zip(path,entries):
    with zipfile.ZipFile(path,'w') as output:
        for name,content in entries.items():
            info=zipfile.ZipInfo(name,(2026,11,2,0,0,0))
            info.external_attr=0o100644 << 16
            output.writestr(info,content,compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None: raise ValueError('ZIP inválido')


def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    dist=ROOT/'dist'
    stage=dist/'release-v0.3.0'; stage.mkdir(exist_ok=True)
    evidence=json.loads((ROOT/'docs/evidence/native-v03-2026-10-20.json').read_text(encoding='utf-8'))
    files=[]
    for target in evidence['targets']:
        record=target['package']; path=dist/record['file']
        if not record['installation_tested'] or digest(path)!=record['sha256']:
            raise ValueError(f'Instalador não validado: {path.name}')
        files.append(path)
    windows=dist/'GCP Yt Rebalance Setup 0.3.0.exe'
    expected='c21cb9ff715834ff64847bbe0143402fcdf7c6d1508d38d81b1b9c8ca3fb5eb9'
    if digest(windows)!=expected: raise ValueError('Instalador Windows diverge da revisão instalada em 20/10')
    files.append(windows)
    source=ROOT/'artifacts/native-39410186466/linux-amd64/artifacts'
    archive=stage/'GCP-Yt-Rebalance-0.3.0-Linux-Test-Evidence.zip'
    entries={'native-payload.json':source/'ci/native-payload.json','fixture.wav':source/'v03-final-offline/fixture.wav'}
    for name in ('health.json','summary.json'): entries[name]=source/'v03-final-offline'/name
    write_zip(archive,{name:path.read_bytes() for name,path in entries.items()})
    files.append(archive)
    arch=dist/'gcp-yt-rebalance-bin-0.3.0-1-x86_64.pkg.tar.zst'
    if arch.exists():
        report=json.loads((ROOT/'artifacts/arch-release/artifacts/arch/summary.json').read_text(encoding='utf-8'))
        if report['status']!='passed': raise ValueError('Pacote Arch sem teste aprovado')
        expected=arch.with_suffix(arch.suffix+'.sha256').read_text(encoding='utf-8').split()[0]
        if digest(arch)!=expected: raise ValueError('Checksum Arch divergente')
        files.append(arch)
        recipe=stage/'GCP-Yt-Rebalance-0.3.0-Arch-PKGBUILD.zip'
        write_zip(recipe,{name:(ROOT/'packaging/arch'/name).read_bytes().replace(b'\r\n',b'\n') for name in ('PKGBUILD','.SRCINFO','NOTICE-PRIVATE.txt','README.md')})
        files.append(recipe)
        arch_evidence=stage/'GCP-Yt-Rebalance-0.3.0-Arch-Test-Evidence.zip'
        base=ROOT/'artifacts/arch-release/artifacts/arch'
        write_zip(arch_evidence,{name:(base/name).read_bytes() for name in ('summary.json','health.json','package-info.txt','os-release.txt','system-packages.txt','container-image.json','runtime-container-image.json','payload-check.txt')})
        files.append(arch_evidence)
    records=[]
    for path in files:
        checksum=digest(path)
        name=path.name.replace('GCP Yt Rebalance Setup 0.3.0.exe','GCP-Yt-Rebalance-0.3.0-Windows-x64-Setup.exe').replace('GCP Yt Rebalance-','GCP-Yt-Rebalance-')
        target=stage/name
        if path.resolve()!=target.resolve():
            if not target.exists():
                try: os.link(path,target)
                except OSError: shutil.copy2(path,target)
            if digest(target)!=checksum: raise ValueError(f'Anexo existente diverge: {name}')
        target.with_suffix(target.suffix+'.sha256').write_text(f'{checksum}  {name}\n',encoding='utf-8',newline='\n')
        records.append(dict(name=name,bytes=target.stat().st_size,sha256=checksum))
    manifest=stage/'release-assets-0.3.0.json'
    manifest.write_text(json.dumps(dict(product='GCP Yt Rebalance',version='0.3.0',visibility='private',prerelease=True,assets=records),ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    (stage/'SHA256SUMS-0.3.0.txt').write_text(''.join(f"{r['sha256']}  {r['name']}\n" for r in records),encoding='utf-8',newline='\n')
    print(json.dumps(records,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
