"""Verifica aplicativo e workers reais; uso: --source ou --exe caminho."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
import wave
import math
import struct

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/desktop"))
from process_job import Job
from platform_support import HIDDEN, process_options
from runtime import ffmpeg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="store_true")
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--separation", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.source and not args.exe:
        parser.error("Escolha --source ou --exe")
    args.out.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, str(ROOT / "apps/desktop/main.py")] if args.source else [str(args.exe.resolve())]
    environment = os.environ.copy()
    runtime_temp = args.out.resolve() / "runtime-temp"
    runtime_temp.mkdir()
    environment["TEMP"] = str(runtime_temp)
    environment["TMP"] = str(runtime_temp)
    if not args.source:
        environment["PATH"] = str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32") if os.name=="nt" else "/usr/bin:/bin"
        for name in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
            environment.pop(name, None)
    source = args.out / "fixture.wav"
    rate = 44100
    # 0,4s de sinal próprio: teste de formato, não teste musical.
    samples = [int(0.1 * 32767 * math.sin(2 * math.pi * 440 * i / rate)) for i in range(int(rate * 0.4))]
    with wave.open(str(source), "wb") as file:
        file.setnchannels(2)
        file.setsampwidth(2)
        file.setframerate(rate)
        file.writeframes(b"".join(struct.pack("<hh", sample, sample) for sample in samples))
    video = args.out / "fixture.mp4"
    subprocess.run([str(ffmpeg()), "-nostdin", "-v", "error", "-n",
        "-f", "lavfi", "-i", "color=c=black:s=160x90:d=0.4", "-i", str(source.resolve()),
        "-shortest", "-c:v", "mpeg4", "-c:a", "aac", str(video.resolve())], check=True,
        timeout=30, creationflags=HIDDEN)
    health = args.out / "health.json"
    process = subprocess.Popen([*command, "--self-test", str(health.resolve())], env=environment, **process_options())
    health_job = Job(process)
    try:
        code = process.wait(timeout=180)
    finally:
        health_job.close()
        process.wait(timeout=15)
    if code or not health.is_file() or json.loads(health.read_text(encoding="utf-8"))["status"] != "passed":
        raise RuntimeError(f"Self-test falhou: {health}")
    results = []
    cases = [("convert", fmt, bits, sample_rate, source) for fmt, bits, sample_rate in (("WAV", 16, 44100), ("PCM", 24, 48000), ("FLAC", 24, 44100), ("MP3", 16, 44100))]
    cases.append(("convert", "WAV", 24, 48000, video))
    if args.separation:
        cases.append(("stems", "WAV", 24, 44100, source))
    for case_index, (operation, fmt, bits, sample_rate, input_file) in enumerate(cases):
        work = args.out / f"{case_index:02d}-{operation}-{fmt}"
        work.mkdir()
        request = dict(source=str(input_file.resolve()), destination=str(args.out.resolve()), operation=operation,
                       format=fmt, bits=bits, rate=sample_rate, bitrate=192, threads=2, id=uuid.uuid4().hex, wait_for_gate=True)
        path = work / "request.json"
        path.write_text(json.dumps(request), encoding="utf-8")
        process = subprocess.Popen([*command, "--worker", str(path.resolve())], env=environment, **process_options())
        job = Job(process)
        (work / "start.gate").touch()
        start = time.monotonic()
        try:
            code = process.wait(timeout=240)
        finally:
            job.close()
            process.wait(timeout=15)
        events = [json.loads(line) for line in (work / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        if code or events[-1]["phase"] != "Concluído":
            raise RuntimeError(f"Falha em {operation}/{fmt}: {events[-1]}")
        output = Path(events[-1]["destination"])
        report = json.loads((output / "relatorio.json").read_text(encoding="utf-8"))
        expected = 4 if operation == "stems" else 1
        assert len(report["outputs"]) == expected
        assert not (args.out / f".gcp-{request['id']}.partial").exists()
        results.append(dict(operation=operation, source_type=input_file.suffix, format=fmt, status="passed", elapsed_seconds=time.monotonic() - start,
                            report=str(output / "relatorio.json")))
        print(f"PASS {operation}/{fmt}", flush=True)
    # Worker parado no gate: Job Object deve encerrá-lo sem deixar processo vivo.
    work = args.out / "cancel"
    work.mkdir()
    request["id"] = uuid.uuid4().hex
    path = work / "request.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    process = subprocess.Popen([*command, "--worker", str(path.resolve())], env=environment, **process_options())
    job = Job(process)
    time.sleep(1)
    assert process.poll() is None
    job.close()
    process.wait(timeout=15)
    assert not (work / "events.jsonl").exists()
    results.append(dict(operation="cancel_supervised_worker_at_gate", status="passed", exit_code=process.returncode))
    # Verificação separada de descendente: o filho nasce depois de o pai entrar no Job.
    import psutil
    tree = args.out / "cancel-tree"
    tree.mkdir()
    helper = tree / "parent.py"
    helper.write_text("import subprocess,sys,time\nfrom pathlib import Path\np=Path(sys.argv[1])\nwhile not (p/'gate').exists(): time.sleep(.02)\nc=subprocess.Popen([sys.executable,'-c','import time;time.sleep(120)'])\n(p/'child.pid').write_text(str(c.pid))\nc.wait()\n", encoding="utf-8")
    parent = subprocess.Popen([sys.executable, str(helper.resolve()), str(tree.resolve())], **process_options())
    job = Job(parent)
    (tree / "gate").touch()
    deadline = time.monotonic() + 15
    while not (tree / "child.pid").exists() and time.monotonic() < deadline:
        time.sleep(.05)
    child_pid = int((tree / "child.pid").read_text())
    assert psutil.pid_exists(child_pid)
    job.close()
    parent.wait(timeout=15)
    deadline = time.monotonic() + 10
    def child_running():
        try: return psutil.Process(child_pid).status()!=psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess: return False
    while child_running() and time.monotonic() < deadline:
        time.sleep(.05)
    assert not child_running()
    results.append(dict(operation="cancel_parent_and_descendant", status="passed"))
    report = dict(status="passed", frozen_executable=not args.source, path_isolated=not args.source,
                  fixture="Sinal sintético próprio de 0,4s; sem voz", cases=results)
    (args.out / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
