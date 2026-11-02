"""Transporte em blocos de instaladores já validados; restrito à release privada 0.3.0."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
REPO='cliqueprojeto/GCP-Yt-Rebalance'
TAG='v0.3.0'
MANIFEST='transfer-v0.3.0.json'
ALLOWED={
 'gcp-yt-rebalance_0.3.0_amd64.deb':'443518f3d56ff929f0cbe4d2d3b6402fce40f100bd94a0cf27cdd09a03d71dcc',
 'GCP-Yt-Rebalance-0.3.0-macOS-arm64.dmg':'d5532a97c5101c08aea3d16e3c3c1650fbe00df2117348bb1b128ac6ebb5730f',
 'GCP-Yt-Rebalance-0.3.0-macOS-x86_64.dmg':'08c97bde35defe8102ac7319e245ce3a082f484b2f47e26755d926208cc36f20',
 'GCP-Yt-Rebalance-0.3.0-Windows-x64-Setup.exe':'c21cb9ff715834ff64847bbe0143402fcdf7c6d1508d38d81b1b9c8ca3fb5eb9',
}


def gh(*args):
    environment=os.environ.copy(); environment['GODEBUG']='http2client=0'
    return subprocess.check_output(['gh',*args],text=True,encoding='utf-8',env=environment)


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def release():
    if not json.loads(gh('repo','view',REPO,'--json','isPrivate'))['isPrivate']:
        raise ValueError('Somente repositório privado autorizado')
    pages=json.loads(gh('api',f'repos/{REPO}/releases','--paginate','--slurp'))
    record=next(r for page in pages for r in page if r['tag_name']==TAG)
    if not record['draft']: raise ValueError('Transporte exige o rascunho criado para esta entrega')
    return record


def validate(data):
    if data.get('repository')!=REPO or data.get('tag')!=TAG: raise ValueError('Destino inválido')
    if {f['name'] for f in data['files']}!=set(ALLOWED) or len(data['files'])!=len(ALLOWED):
        raise ValueError('Lista de instaladores inválida')
    for item in data['files']:
        if item['sha256']!=ALLOWED[item['name']]: raise ValueError('Hash de instalador não autorizado')
        for index,chunk in enumerate(item['chunks']):
            expected=f"transfer-v0.3.0-{item['sha256'][:12]}-{index:04d}.part"
            if chunk['name']!=expected or not 0<chunk['bytes']<=16*1024**2:
                raise ValueError('Bloco ou caminho inválido')
        if sum(c['bytes'] for c in item['chunks'])!=item['bytes']: raise ValueError('Tamanho inválido')


def split(folder):
    folder.mkdir(parents=True,exist_ok=True)
    files=[]
    for name,expected in ALLOWED.items():
        source=ROOT/'dist/release-v0.3.0'/name
        if sha(source)!=expected: raise ValueError(f'Insumo divergente: {name}')
        chunks=[]
        with source.open('rb') as stream:
            while content:=stream.read(16*1024**2):
                chunk_name=f'transfer-v0.3.0-{expected[:12]}-{len(chunks):04d}.part'
                target=folder/chunk_name
                digest=hashlib.sha256(content).hexdigest()
                if not target.exists(): target.write_bytes(content)
                if sha(target)!=digest: raise ValueError('Bloco local divergente')
                chunks.append(dict(name=chunk_name,bytes=len(content),sha256=digest))
        files.append(dict(name=name,bytes=source.stat().st_size,sha256=expected,chunks=chunks))
    data=dict(repository=REPO,tag=TAG,files=files)
    validate(data)
    (folder/MANIFEST).write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(f'Prepared {len(files)} installers, {sum(len(f["chunks"]) for f in files)} chunks',flush=True)


def upload(folder,select):
    record=release()
    data=json.loads((folder/MANIFEST).read_text()); validate(data)
    assets=json.loads(gh('api',f'repos/{REPO}/releases/{record["id"]}/assets','--paginate','--slurp'))
    existing={a['name']:a for page in assets for a in page if a['state']=='uploaded'}
    if MANIFEST not in existing:
        gh('release','upload',TAG,'--repo',REPO,str(folder/MANIFEST))
    chunks=[c for f in data['files'] if not select or f['name']==select for c in f['chunks']]
    def send(chunk):
        asset=existing.get(chunk['name'])
        if asset and asset['size']==chunk['bytes'] and asset.get('digest')=='sha256:'+chunk['sha256']:
            return
        if sha(folder/chunk['name'])!=chunk['sha256']: raise ValueError('Bloco mudou antes do envio')
        for attempt in range(3):
            try:
                gh('release','upload',TAG,'--repo',REPO,str(folder/chunk['name']),'--clobber')
                print('Uploaded '+chunk['name'],flush=True)
                return
            except subprocess.CalledProcessError:
                if attempt==2: raise
    with ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(send,chunks))


def join(item,folder,output):
    target=output/item['name']; partial=target.with_suffix(target.suffix+'.partial')
    try:
        with partial.open('wb') as destination:
            for chunk in item['chunks']:
                path=folder/chunk['name']
                if path.stat().st_size!=chunk['bytes'] or sha(path)!=chunk['sha256']:
                    raise ValueError('Bloco recebido diverge')
                with path.open('rb') as source:
                    while content:=source.read(1024**2): destination.write(content)
        if sha(partial)!=item['sha256']: raise ValueError('Instalador reconstituído diverge')
        if target.exists() and sha(target)!=item['sha256']: raise FileExistsError(target)
        partial.replace(target)
    finally: partial.unlink(missing_ok=True)


def assemble(output,select):
    release()
    folder=ROOT/'.cache/release-transfer'; folder.mkdir(parents=True,exist_ok=True)
    output.mkdir(parents=True,exist_ok=True)
    gh('release','download',TAG,'--repo',REPO,'--pattern',MANIFEST,'--dir',str(folder),'--clobber')
    data=json.loads((folder/MANIFEST).read_text()); validate(data)
    for item in data['files']:
        if select and item['name']!=select: continue
        gh('release','download',TAG,'--repo',REPO,'--pattern',f'transfer-v0.3.0-{item["sha256"][:12]}-*.part','--dir',str(folder),'--clobber')
        join(item,folder,output)
        print('Reassembled and verified '+item['name'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=('split','upload','assemble'))
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--select',choices=tuple(ALLOWED))
    args=parser.parse_args()
    if args.mode=='split': split(args.directory)
    elif args.mode=='upload': upload(args.directory,args.select)
    else: assemble(args.directory,args.select)
