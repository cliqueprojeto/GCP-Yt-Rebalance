"""Separação CPU offline usando apenas safetensors oficial verificado e áudio local."""
import argparse
import hashlib
import json
from pathlib import Path
import threading
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    if args.threads < 1:
        parser.error("threads deve ser positivo")
    import numpy as np
    import psutil
    import soundfile as sf
    import torch
    from safetensors import safe_open
    from demucs.hf import load_safetensors_model
    from demucs.apply import apply_model
    torch.set_num_threads(args.threads)
    torch.manual_seed(0)
    root = Path(__file__).resolve().parents[1]
    record = json.loads((root / "docs/evidence/model-acquisition.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(args.weights.read_bytes()).hexdigest()
    if digest != record["upstream_sha256"]:
        raise ValueError("Pesos não correspondem ao artefato oficial verificado")
    with safe_open(str(args.weights), framework="pt") as tensors:
        metadata = tensors.metadata()
        if metadata.get("klass") != "demucs.htdemucs.HTDemucs" or "structure" in metadata:
            raise ValueError("Classe ou estrutura fora do contrato desta POC")
    # O loader recebe somente o arquivo oficial com hash conferido; sem get_model/hub/rede.
    args.out.mkdir(parents=True, exist_ok=False)
    process = psutil.Process()
    peak = [process.memory_info().rss]
    stop = threading.Event()
    def monitor():
        while not stop.wait(0.02):
            peak[0] = max(peak[0], process.memory_info().rss)
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    started = time.perf_counter()
    cpu_start = process.cpu_times()
    report = dict(status="started", weights_sha256=digest, threads=args.threads,
                  shifts=0, overlap=0.25, measurement="RSS amostrado do processo a cada 20 ms")
    try:
        model = load_safetensors_model(args.weights).cpu().eval()
        audio, sample_rate = sf.read(args.input, dtype="float32", always_2d=True)
        if sample_rate != model.samplerate or audio.shape[1] != 2:
            raise ValueError("Esta POC exige estéreo no sample rate do modelo; conversão explícita pendente")
        if not np.isfinite(audio).all() or len(audio) < 2:
            raise ValueError("Entrada vazia ou inválida")
        report.update(input_sha256=hashlib.sha256(args.input.read_bytes()).hexdigest(),
                      frames=len(audio), sample_rate=sample_rate, channels=2,
                      duration_seconds=len(audio) / sample_rate, segment_seconds=float(model.segment))
        wav = torch.from_numpy(audio.T.copy())
        ref = wav.mean(0)
        mean = ref.mean()
        std = ref.std() + 1e-8
        inference_start = time.perf_counter()
        with torch.inference_mode():
            output = apply_model(model, ((wav - mean) / std)[None], shifts=0, split=True,
                                 overlap=0.25, device="cpu", num_workers=0)[0] * std + mean
        report["inference_seconds"] = time.perf_counter() - inference_start
        if output.shape != (4, 2, len(audio)) or not torch.isfinite(output).all():
            raise ValueError("Saída incompatível, truncada ou não finita")
        stems = {name: source.numpy().T for name, source in zip(model.sources, output)}
        stems["instrumental"] = sum(stems[name] for name in ("drums", "bass", "other"))
        report["outputs"] = []
        for name, stem in stems.items():
            path = args.out / f"{name}.wav"
            # Float preserva picos sem clamp ou normalização individual oculta.
            sf.write(path, stem, sample_rate, subtype="FLOAT")
            decoded, actual_rate = sf.read(path, dtype="float32", always_2d=True)
            if actual_rate != sample_rate or not np.array_equal(decoded, stem):
                raise ValueError("Roundtrip WAV float divergente")
            report["outputs"].append(dict(stem=name, frames=len(decoded), bytes=path.stat().st_size,
                peak=float(np.abs(stem).max()), samples_over_full_scale=int((np.abs(stem) > 1).sum()),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(), roundtrip_exact=True))
        report["status"] = "passed_format_and_duration_only"
        report["quality_approved"] = False
    except Exception as error:
        report.update(status="failed", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        stop.set()
        thread.join()
        times = process.cpu_times()
        report.update(wall_seconds=time.perf_counter() - started,
                      cpu_seconds=times.user + times.system - cpu_start.user - cpu_start.system,
                      sampled_peak_rss_bytes=peak[0])
        (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
