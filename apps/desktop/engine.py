"""Motor experimental offline. Nenhum shell, download de modelo ou chamada HTTP."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from runtime import BASE, MODEL_SHA256, VERSION, ffmpeg
from naming import result_folder, output_name

HIDDEN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
OPERATIONS = {"instrumental", "vocals", "both", "stems", "convert"}
FORMATS = {"WAV", "PCM", "FLAC", "MP3"}
PROGRESS_RANGE = (0, 100)


def emit(work, phase, progress=None, **fields):
    if progress is not None:
        progress = PROGRESS_RANGE[0] + progress / 100 * (PROGRESS_RANGE[1] - PROGRESS_RANGE[0])
    with (work / "events.jsonl").open("a", encoding="utf-8") as file:
        file.write(json.dumps(dict(phase=phase, progress=progress, **fields), ensure_ascii=False) + "\n")


def validate(request):
    source = Path(request["source"]).resolve(strict=True)
    destination = Path(request["destination"]).resolve(strict=True)
    if not source.is_file() or not destination.is_dir():
        raise ValueError("Selecione um arquivo de entrada e uma pasta de saída existentes.")
    if source.suffix.lower() not in {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".mp4", ".mkv", ".mov", ".webm", ".avi"}:
        raise ValueError("Formato de entrada não habilitado nesta versão.")
    if source.stat().st_size > 10 * 1024 ** 3:
        raise ValueError("Arquivo excede o limite experimental de 10 GiB.")
    if request["operation"] not in OPERATIONS or request["format"] not in FORMATS:
        raise ValueError("Operação ou formato inválido.")
    if request["rate"] not in (44100, 48000) or request["bits"] not in (16, 24, 32):
        raise ValueError("Taxa ou profundidade inválida.")
    if request["format"] == "FLAC" and request["bits"] == 32:
        raise ValueError("Escolha 16 ou 24 bits para FLAC.")
    if request["bitrate"] not in (128, 192, 256, 320):
        raise ValueError("Bitrate MP3 inválido.")
    if not 1 <= request["threads"] <= 8:
        raise ValueError("Número de threads inválido.")
    return source, destination


def probe(source):
    result = subprocess.run([str(ffmpeg("ffprobe")), "-v", "error", "-protocol_whitelist", "file,pipe",
        "-show_format", "-show_streams", "-of", "json", str(source)], capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=30, creationflags=HIDDEN)
    if result.returncode:
        raise ValueError("Não foi possível ler o arquivo. Verifique se está íntegro e possui áudio sem proteção.")
    metadata = json.loads(result.stdout)
    streams = [s for s in metadata.get("streams", []) if s["codec_type"] == "audio"]
    if not streams:
        raise ValueError("O arquivo não contém uma faixa de áudio compatível.")
    duration = float(metadata.get("format", {}).get("duration", streams[0].get("duration", 0)))
    if not math.isfinite(duration) or duration <= 0 or duration > 1800:
        raise ValueError("Duração inválida ou acima do limite experimental de 30 minutos.")
    return duration, streams[0]


def transcode(source, target, arguments, work, duration, low, high):
    started = time.monotonic()
    log = work / "ffmpeg-errors.txt"
    with log.open("w", encoding="utf-8") as errors:
        command = [str(ffmpeg()), "-nostdin", "-hide_banner", "-loglevel", "error", "-n",
            "-protocol_whitelist", "file,pipe", "-i", str(source), "-map", "0:a:0", "-vn",
            "-map_metadata", "-1", *arguments, "-progress", "pipe:1", "-nostats", str(target)]
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors, text=True,
                              encoding="utf-8", errors="replace", creationflags=HIDDEN) as process:
            for line in process.stdout:
                if line.startswith("out_time_us="):
                    try:
                        fraction = min(1, max(0, int(line.strip().split("=", 1)[1]) / 1e6 / duration))
                    except ValueError:
                        continue
                    eta = (time.monotonic() - started) * (1 - fraction) / fraction if fraction > 0.02 else None
                    emit(work, "Convertendo", low + fraction * (high - low), eta_seconds=eta, phase_key="conversion")
            if process.wait():
                raise RuntimeError("Falha na conversão de áudio. Verifique espaço livre e compatibilidade do arquivo.")


def export(source, target, request, work, duration, low, high):
    fmt, bits = request["format"], request["bits"]
    codec = {"WAV": f"pcm_s{bits}le", "PCM": f"pcm_s{bits}le", "FLAC": "flac", "MP3": "libmp3lame"}[fmt]
    arguments = ["-ar", str(request["rate"]), "-ac", "2", "-c:a", codec]
    if fmt == "PCM":
        arguments += ["-f", f"s{bits}le"]
    elif fmt == "FLAC":
        arguments += ["-sample_fmt", "s16" if bits == 16 else "s32"]
        if bits == 24:
            arguments += ["-bits_per_raw_sample", "24"]
    elif fmt == "MP3":
        arguments += ["-b:a", f"{request['bitrate']}k"]
    transcode(source, target, arguments, work, duration, low, high)
    if fmt == "PCM":
        params = dict(sample_rate=request["rate"], channels=2, bits_per_sample=bits,
                      representation="signed integer", endianness="little", interleaved=True)
        frame_bytes = 2 * bits // 8
        if not target.stat().st_size or target.stat().st_size % frame_bytes:
            raise RuntimeError("PCM exportado tem tamanho inválido.")
        params["frames"] = target.stat().st_size // frame_bytes
        if abs(params["frames"] / request["rate"] - duration) > 0.15:
            raise RuntimeError("Duração do PCM diverge da entrada.")
        target.with_suffix(".pcm.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
        return params
    actual_duration, stream = probe(target)
    if abs(actual_duration - duration) > 0.15:
        raise RuntimeError("Duração exportada diverge da entrada.")
    expected = {"WAV": codec, "FLAC": "flac", "MP3": "mp3"}[fmt]
    if stream["codec_name"] != expected or int(stream["sample_rate"]) != request["rate"] or stream["channels"] != 2:
        raise RuntimeError("Parâmetros exportados divergentes.")
    return dict(codec=stream["codec_name"], sample_rate=int(stream["sample_rate"]), channels=stream["channels"],
                duration=actual_duration, bits=stream.get("bits_per_raw_sample") or stream.get("bits_per_sample"),
                bitrate=stream.get("bit_rate"))


def copy_attachments(attachments,stage,work):
    result=[]
    for source,name in attachments:
        source=Path(source).resolve(strict=True)
        if not source.is_relative_to(Path(work).resolve()) or Path(name).name!=name or not name.endswith(".srt") or source.stat().st_size>20*1024*1024:
            raise ValueError("Arquivo de legenda inválido.")
        target=stage/name
        with source.open("rb") as incoming,target.open("xb") as outgoing:
            shutil.copyfileobj(incoming,outgoing)
        result.append(dict(file=name,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    return result


def execute(request, work,attachments=()):
    source, destination = validate(request)
    emit(work, "Verificando arquivo", 0)
    duration, stream = probe(source)
    required = max(512 * 1024 ** 2, int(duration * 48000 * 2 * 4 * 10))
    if shutil.disk_usage(destination).free < required:
        raise OSError("Espaço livre insuficiente na pasta de saída para esta tarefa.")
    identifier = request["id"]
    if len(identifier) != 32 or any(c not in "0123456789abcdef" for c in identifier):
        raise ValueError("Identificador de tarefa inválido.")
    stage = destination / f".gcp-{identifier}.partial"
    title = request.get("title") or source.stem
    final = result_folder(destination, title, request["operation"])
    if final.exists():
        raise FileExistsError("Destino já existe. Inicie uma nova tarefa para preservar os arquivos.")
    stage.mkdir(exist_ok=False)
    started = time.perf_counter()
    results = []
    try:
        emit(work, "Arquivo verificado", 2, duration=duration, codec=stream["codec_name"])
        with tempfile.TemporaryDirectory(prefix="audio-", dir=work) as temporary:
            temporary = Path(temporary)
            choices = {"convert": [("audio", source)]}
            gain = 1.0
            if request["operation"] != "convert":
                import numpy as np
                import soundfile as sf
                import torch
                from safetensors import safe_open
                from demucs.hf import load_safetensors_model
                from demucs.apply import apply_model
                emit(work, "Verificando modelo local", 3)
                weights = BASE / "models/weights/955717e8.safetensors"
                if not weights.is_file() or hashlib.sha256(weights.read_bytes()).hexdigest() != MODEL_SHA256:
                    raise RuntimeError("Modelo local ausente ou com integridade inválida. Obtenha novamente o pacote completo.")
                with safe_open(str(weights), framework="pt") as file:
                    metadata = file.metadata()
                    if metadata.get("klass") != "demucs.htdemucs.HTDemucs" or "structure" in metadata:
                        raise RuntimeError("Estrutura de modelo não autorizada.")
                normalized = temporary / "entrada.wav"
                transcode(source, normalized, ["-ar", "44100", "-ac", "2", "-c:a", "pcm_f32le"], work, duration, 3, 8)
                torch.set_num_threads(request["threads"])
                torch.manual_seed(0)
                emit(work, "Carregando modelo CPU", 8)
                model = load_safetensors_model(weights).cpu().eval()
                audio, sample_rate = sf.read(normalized, dtype="float32", always_2d=True)
                if not np.isfinite(audio).all():
                    raise ValueError("A entrada contém amostras inválidas.")
                wav = torch.from_numpy(audio.T.copy())
                ref = wav.mean(0)
                mean, std = ref.mean(), ref.std() + 1e-8
                count = [0]
                segments = len(range(0, len(audio), int(float(model.segment) * 44100 * 0.75)))
                inference_started = time.monotonic()
                def progress(event):
                    if event["state"] == "end":
                        count[0] += 1
                        elapsed = time.monotonic() - inference_started
                        emit(work, "Separando no dispositivo CPU", 10 + 68 * min(1, count[0] / segments),
                             eta_seconds=elapsed / count[0] * max(0, segments - count[0]),
                             segments_done=count[0], segments_total=segments, phase_key="separation")
                emit(work, "Separando no dispositivo CPU", 10)
                with torch.inference_mode():
                    stems = apply_model(model, ((wav - mean) / std)[None], shifts=0, split=True,
                        overlap=0.25, num_workers=0, device="cpu", callback=progress)[0] * std + mean
                if tuple(stems.shape) != (4, 2, len(audio)) or not torch.isfinite(stems).all():
                    raise RuntimeError("O modelo retornou áudio inválido ou truncado.")
                separated = {name: value.numpy().T.copy() for name, value in zip(model.sources, stems)}
                separated["instrumental"] = sum(separated[name] for name in ("drums", "bass", "other"))
                # Ganho conjunto mantém a relação entre stems e evita clipping na conversão inteira.
                peak = max(float(np.max(np.abs(value))) for value in separated.values())
                gain = min(1, 0.999 / peak) if peak else 1
                names = {"instrumental": ["instrumental"], "vocals": ["vocals"],
                         "both": ["vocals", "instrumental"], "stems": ["vocals", "drums", "bass", "other"]}[request["operation"]]
                choices[request["operation"]] = []
                for name in names:
                    path = temporary / f"{name}.wav"
                    sf.write(path, separated[name] * gain, sample_rate, subtype="FLOAT")
                    choices[request["operation"]].append((name, path))
            selected = choices[request["operation"]]
            ext = request["format"].lower()
            for index, (name, path) in enumerate(selected):
                low = (3 if request["operation"] == "convert" else 80) + (index / len(selected)) * (96 if request["operation"] == "convert" else 19)
                high = (3 if request["operation"] == "convert" else 80) + ((index + 1) / len(selected)) * (96 if request["operation"] == "convert" else 19)
                target = stage / output_name(title, name, ext)
                actual = export(path, target, request, work, duration, low, high)
                results.append(dict(file=target.name, bytes=target.stat().st_size, parameters=actual,
                    sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
            report = dict(product="GCP Yt Rebalance", version=VERSION, input_name=source.name,
                          duration=duration, operation=request["operation"], format=request["format"],
                          common_gain=gain, outputs=results, elapsed_seconds=time.perf_counter() - started,
                          engine="HTDemucs CPU experimental" if request["operation"] != "convert" else "FFmpeg local",
                          quality_note="Qualidade musical ainda não validada na matriz de três faixas.")
            report["subtitles"]=copy_attachments(attachments,stage,work)
            (stage / "relatorio.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        stage.rename(final)
        emit(work, "Concluído", 100, destination=str(final))
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def worker(request_path):
    path = Path(request_path).resolve(strict=True)
    work = path.parent
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
        identifier = request.get("id", "")
        if not isinstance(identifier,str) or len(identifier)!=32 or any(c not in "0123456789abcdef" for c in identifier):
            raise ValueError("Identificador de tarefa inválido.")
        if request.get("wait_for_gate"):
            deadline = time.monotonic() + 30
            while not (work / "start.gate").exists():
                if time.monotonic() > deadline:
                    raise TimeoutError("Não foi possível iniciar a tarefa supervisionada.")
                time.sleep(0.05)
        if request.get("kind") == "inspect":
            from download import inspect_url
            info = inspect_url(request["url"], work)
            (work / "metadata.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
            emit(work, "Link analisado", 100)
        elif request.get("kind") == "download":
            from download import download_task
            download_task(request, work)
        else:
            execute(request, work)
        return 0
    except Exception as error:
        # Sem traceback nem metadados da mídia em logs persistentes.
        emit(work, "Erro", None, message=str(error) if isinstance(error, (ValueError, RuntimeError, OSError)) else "Falha interna ao processar o arquivo.")
        return 1
