"""Download real de vídeo/áudio e duas legendas próprias via yt-dlp + FFmpeg."""
import argparse
from functools import partial
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/desktop"))
from platform_support import process_options
from process_job import Job


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--exe",type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--fixture",type=Path,default=ROOT/"artifacts/v02-final-offline/fixture.mp4")
    args=parser.parse_args(); args.out.mkdir(parents=True,exist_ok=False)
    server_root=args.out/"server"; server_root.mkdir()
    shutil.copyfile(args.fixture,server_root/"fixture.mp4")
    for language,line in (("pt","Legenda própria em português"),("en","Own caption in English")):
        (server_root/f"{language}.vtt").write_text(f"WEBVTT\n\n00:00.000 --> 00:00.400\n{line}\n",encoding="utf-8")
    (server_root/"video.html").write_text('<html><head><meta charset="utf-8"><title>Teste de legendas próprias</title></head><body><video src="fixture.mp4" controls><track kind="subtitles" src="pt.vtt" srclang="pt" label="Português"><track kind="subtitles" src="en.vtt" srclang="en" label="English"></video></body></html>',encoding="utf-8")
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args): pass
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(server_root.resolve())))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}"
    env=os.environ.copy(); env["GCP_REBALANCE_TEST_SERVER"]=base
    if args.exe:
        env["PATH"]=str(Path(os.environ.get("SystemRoot","C:/Windows"))/"System32") if os.name=="nt" else "/usr/bin:/bin"
        for name in ("PYTHONHOME","PYTHONPATH","VIRTUAL_ENV"): env.pop(name,None)
    command=[str(args.exe.resolve())] if args.exe else [sys.executable,str(ROOT/"apps/desktop/main.py")]
    def worker(request,label):
        work=args.out/label; work.mkdir()
        request.update(id=uuid.uuid4().hex,wait_for_gate=True,url=base+"/video.html")
        path=work/"request.json"; path.write_text(json.dumps(request),encoding="utf-8")
        process=subprocess.Popen([*command,"--worker",str(path.resolve())],env=env,**process_options())
        job=Job(process); (work/"start.gate").touch()
        try: code=process.wait(timeout=180)
        finally: job.close(); process.wait(timeout=15)
        events=[json.loads(line) for line in (work/"events.jsonl").read_text(encoding="utf-8").splitlines()]
        assert code==0 and events[-1]["phase"] in ("Link analisado","Concluído"),events[-1]
        return work,events[-1]
    try:
        work,event=worker(dict(kind="inspect"),"inspect")
        metadata=json.loads((work/"metadata.json").read_text(encoding="utf-8"))
        assert {item["language"] for item in metadata["subtitles"]}=={"pt","en"},metadata
        cases=[]
        for mode in ("video","audio"):
            _,event=worker(dict(kind="download",destination=str(args.out.resolve()),download_mode=mode,resolution=0,
                operation="convert",format="WAV",bits=16,rate=44100,bitrate=192,threads=2,
                subtitles=[dict(language=lang,automatic=False) for lang in ("pt","en")]),mode)
            output=Path(event["destination"])
            report=json.loads((output/"relatorio.json").read_text(encoding="utf-8"))
            assert len(report["subtitles"])==2
            texts=[(output/item["file"]).read_text(encoding="utf-8-sig") for item in report["subtitles"]]
            assert any("português" in text for text in texts) and any("English" in text for text in texts)
            assert all("00:00:00,000 --> 00:00:00,400" in text for text in texts)
            cases.append(dict(mode=mode,subtitles=report["subtitles"],status="passed"))
            print(f"PASS {mode} + pt/en SRT",flush=True)
        (args.out/"summary.json").write_text(json.dumps(dict(status="passed",frozen=bool(args.exe),own_media=True,cases=cases),ensure_ascii=False,indent=2),encoding="utf-8")
    finally: server.shutdown(); server.server_close()


if __name__=="__main__": main()
