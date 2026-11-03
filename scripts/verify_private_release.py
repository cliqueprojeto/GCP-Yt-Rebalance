"""Compara os anexos no GitHub com o manifesto e os checksums locais aprovados."""
import argparse
import hashlib
import json
from pathlib import Path
from release_transfer import REPO, TAG, gh, ROOT


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--published',action='store_true')
    parser.add_argument('--require-clean',action='store_true')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    repo=json.loads(gh('repo','view',REPO,'--json','isPrivate'))
    if not repo['isPrivate']: raise ValueError('O projeto deve permanecer privado')
    releases=json.loads(gh('api',f'repos/{REPO}/releases','--paginate','--slurp'))
    record=next(item for page in releases for item in page if item['tag_name']==TAG)
    if record['draft']==args.published or not record['prerelease']:
        raise ValueError('Estado inesperado do pré-lançamento privado')
    pages=json.loads(gh('api',f'repos/{REPO}/releases/{record["id"]}/assets','--paginate','--slurp'))
    assets={item['name']:item for page in pages for item in page}
    stage=ROOT/'dist/release-v0.3.0'
    manifest=json.loads((stage/'release-assets-0.3.0.json').read_text(encoding='utf-8'))
    expected={item['name']:(item['bytes'],item['sha256']) for item in manifest['assets']}
    for name in [*(item['name']+'.sha256' for item in manifest['assets']),'SHA256SUMS-0.3.0.txt','release-assets-0.3.0.json']:
        path=stage/name
        with path.open('rb') as stream: checksum=hashlib.file_digest(stream,'sha256').hexdigest()
        expected[name]=(path.stat().st_size,checksum)
    for name,(size,checksum) in expected.items():
        asset=assets.get(name,{})
        if asset.get('state')!='uploaded' or asset.get('size')!=size or asset.get('digest')!='sha256:'+checksum:
            raise ValueError(f'Anexo ausente ou divergente no GitHub: {name}')
    if args.require_clean and any(name.startswith('transfer-') for name in assets):
        raise ValueError('Ainda existem blocos de transporte no rascunho')
    result=dict(repository=REPO,private=True,tag=TAG,draft=record['draft'],prerelease=True,
                url=record['html_url'],target_commit=record['target_commitish'],verified_assets=len(expected),
                sha256_verified=True,installers=5,aur_published=False)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2),encoding='utf-8',newline='\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
