"""Validação de arquitetura e integridade dos payloads Mac/Linux sem executá-los."""
import hashlib
import json
from pathlib import Path
import struct

MODEL_SHA="d9fa14133cfcc034a6758923bb3a8ca9f8dfd0b582134643bbf83f72c17576dd"


def digest(path):
    with Path(path).open("rb") as file: return hashlib.file_digest(file,"sha256").hexdigest()


def architectures(path):
    with Path(path).open("rb") as file: header=file.read(1024)
    if header[:4]==b"\x7fELF":
        if len(header)<20 or header[4]!=2 or header[5] not in (1,2): raise ValueError("ELF inválido ou não é 64 bits")
        machine=struct.unpack_from("<H" if header[5]==1 else ">H",header,18)[0]
        return {"linux-x86_64"} if machine==62 else {"linux-arm64"} if machine==183 else {"unknown"}
    thin={b"\xcf\xfa\xed\xfe":"<",b"\xfe\xed\xfa\xcf":">"}
    fat={b"\xca\xfe\xba\xbe":(">",20),b"\xbe\xba\xfe\xca":("<",20),b"\xca\xfe\xba\xbf":(">",32),b"\xbf\xba\xfe\xca":("<",32)}
    if header[:4] in thin:
        if len(header)<8: raise ValueError("Mach-O truncado")
        cpus=[struct.unpack_from(thin[header[:4]]+"I",header,4)[0]]
    elif header[:4] in fat:
        endian,width=fat[header[:4]]
        if len(header)<8: raise ValueError("Mach-O universal truncado")
        count=struct.unpack_from(endian+"I",header,4)[0]
        if not 1<=count<=16 or len(header)<8+count*width: raise ValueError("Tabela Mach-O inválida")
        cpus=[struct.unpack_from(endian+"I",header,8+i*width)[0] for i in range(count)]
    else: raise ValueError(f"Binário não é ELF/Mach-O: {path}")
    return {"macos-x86_64" if cpu==0x01000007 else "macos-arm64" if cpu==0x0100000c else "unknown" for cpu in cpus}


def manifest(folder):
    folder=Path(folder).resolve(strict=True)
    result=[]
    for path in sorted(folder.rglob("*")):
        if not path.resolve().is_relative_to(folder): raise ValueError(f"Link aponta para fora do pacote: {path}")
        relative=path.relative_to(folder).as_posix()
        if path.is_symlink(): result.append(dict(path=relative,link=str(path.readlink())))
        elif path.is_file(): result.append(dict(path=relative,bytes=path.stat().st_size,sha256=digest(path)))
    return result


def verify_manifest(folder,entries):
    root=Path(folder).resolve(strict=True)
    if manifest(root)!=entries: raise ValueError("O pacote instalado difere do payload validado")


def validate_payload(folder,target,product="GCP Yt Rebalance"):
    root=Path(folder).resolve(strict=True)
    mac=target.startswith("macos-")
    main=root/"Contents/MacOS"/product if mac else root/product
    base=root/"Contents/Frameworks" if mac else root/"_internal"
    tools=[main,base/"vendor/ffmpeg/ffmpeg",base/"vendor/ffmpeg/ffprobe",base/"vendor/download/yt-dlp",base/"vendor/download/node"]
    for path in tools:
        if not path.is_file() or not path.resolve().is_relative_to(root): raise ValueError(f"Componente ausente ou externo: {path}")
        if target not in architectures(path): raise ValueError(f"Arquitetura incorreta em {path}")
        if not path.stat().st_mode & 0o111: raise ValueError(f"Componente sem permissão de execução: {path}")
    model=base/"models/weights/955717e8.safetensors"
    if not model.is_file() or digest(model)!=MODEL_SHA: raise ValueError("Modelo ausente ou checksum inválido")
    entries=manifest(root)
    return dict(target=target,files=entries,payload_bytes=sum(e.get("bytes",0) for e in entries),
                main_executable_sha256=digest(main),model_sha256=MODEL_SHA)


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("installed",type=Path)
    parser.add_argument("manifest",type=Path)
    parser.add_argument("--health",type=Path)
    parser.add_argument("--package-record",type=Path)
    args=parser.parse_args()
    payload=json.loads(args.manifest.read_text(encoding="utf-8"))
    verify_manifest(args.installed,payload["files"])
    if args.package_record:
        if not args.health: parser.error("--package-record exige --health")
        health=json.loads(args.health.read_text(encoding="utf-8"))
        record=json.loads(args.package_record.read_text(encoding="utf-8"))
        if health.get("status")!="passed" or health.get("version")!=record.get("version") or not health.get("gui_queue_conversion"):
            raise ValueError("A primeira execução instalada não passou")
        record.update(installation_tested=True,installed_payload_verified=True)
        args.package_record.write_text(json.dumps(record,indent=2),encoding="utf-8")
    print("Installed payload SHA-256 and links: passed")
