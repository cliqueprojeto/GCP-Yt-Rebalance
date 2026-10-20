"""E2E do downloader real contra mídia própria servida por HTTP efêmero local."""
import argparse
from functools import partial
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/desktop"))
from process_job import Job
from platform_support import process_options


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--exe",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--all-modes",action="store_true")
    parser.add_argument("--fixture",type=Path,default=ROOT/"artifacts/windows-exe-smoke-01/fixture.mp4")
    parser.add_argument("--youtube",action="store_true",help="Teste público CC BY da Blender Foundation, apenas vídeo e áudio")
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    source=args.fixture
    if not source.is_file(): raise SystemExit("Execute primeiro smoke_windows.py para gerar a mídia própria")
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args): pass
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(source.parent)))
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    base=f"http://127.0.0.1:{server.server_port}"
    env=os.environ.copy(); env["GCP_REBALANCE_TEST_SERVER"]=base
    runtime=args.out.resolve()/"runtime"; runtime.mkdir()
    env["TEMP"]=env["TMP"]=str(runtime)
    if args.exe:
        env["PATH"]=str(Path(os.environ["SystemRoot"])/"System32") if os.name=="nt" else "/usr/bin:/bin"
        for name in ("PYTHONHOME","PYTHONPATH","VIRTUAL_ENV"): env.pop(name,None)
    command=[str(args.exe.resolve())] if args.exe else [sys.executable,str(ROOT/"apps/desktop/main.py")]
    results=[]
    try:
        modes=["video","audio","instrumental","stems"] if args.all_modes and not args.youtube else ["video","audio"]
        for mode in modes:
            work=args.out/mode; work.mkdir()
            url="https://www.youtube.com/watch?v=aqz-KE-bpKQ" if args.youtube else base+"/fixture.mp4"
            request=dict(kind="download",url=url,destination=str(args.out.resolve()),id=uuid.uuid4().hex,
                download_mode=mode,resolution=360 if args.youtube else 0,operation="convert",format="WAV",bits=16,rate=44100,bitrate=192,threads=2,wait_for_gate=True)
            path=work/"request.json"; path.write_text(json.dumps(request),encoding="utf-8")
            process=subprocess.Popen([*command,"--worker",str(path.resolve())],env=env,**process_options())
            job=Job(process); (work/"start.gate").touch(); start=time.monotonic()
            try: code=process.wait(timeout=240)
            finally: job.close(); process.wait(timeout=15)
            events=[json.loads(line) for line in (work/"events.jsonl").read_text(encoding="utf-8").splitlines()]
            if code or events[-1]["phase"]!="Concluído": raise RuntimeError(f"{mode}: {events[-1]}")
            output=Path(events[-1]["destination"])
            report=json.loads((output/"relatorio.json").read_text(encoding="utf-8"))
            expected=4 if mode=="stems" else 1
            assert len(list(output.glob("*.wav")))==expected if mode!="video" else bool(list(output.glob("*.mp4"))+list(output.glob("*.mkv")))
            results.append(dict(mode=mode,status="passed",seconds=time.monotonic()-start,destination=str(output),report=report))
            print(f"PASS download/{mode}",flush=True)
        description="Big Buck Bunny — Blender Foundation; https://peach.blender.org/about/; CC BY 3.0; mídia obtida do canal oficial Blender" if args.youtube else "mídia sintética própria em servidor HTTP efêmero; exceção limitada à suíte"
        report=dict(status="passed",frozen=bool(args.exe),source=description,cases=results)
        (args.out/"summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        if args.youtube:
            (args.out/"ATTRIBUTION.txt").write_text("(c) copyright 2008, Blender Foundation / www.bigbuckbunny.org\nCreative Commons Attribution 3.0\nhttps://peach.blender.org/about/\nFonte: https://www.youtube.com/watch?v=aqz-KE-bpKQ\nTransformação: download em resolução reduzida e extração de áudio para teste local.\n",encoding="utf-8")
    finally:
        server.shutdown(); server.server_close()


if __name__=="__main__": main()
