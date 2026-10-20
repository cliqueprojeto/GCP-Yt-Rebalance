"""Sonda de exportação do HTDemucs original. NÃO valida pesos/qualidade musical."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time
import traceback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    report = dict(status="started", trained_weights=False, purpose="export feasibility only")
    start = time.perf_counter()
    try:
        import numpy as np
        import torch
        import onnx
        import onnxruntime as ort
        from demucs.htdemucs import HTDemucs
        from audio_metrics import compare
        torch.manual_seed(0)
        torch.set_num_threads(2)
        report["versions"] = {p: importlib.metadata.version(p) for p in ("torch", "demucs", "onnx", "onnxruntime", "numpy")}
        # Arquitetura padrão, quatro fontes. Nenhum peso nem áudio baixado.
        model = HTDemucs(sources=["drums", "bass", "other", "vocals"]).cpu().eval()
        report["parameters"] = sum(p.numel() for p in model.parameters())
        report["stage"] = "pytorch_forward"
        audio = torch.randn(1, 2, int(model.samplerate * model.segment)) * 0.01
        report["input_shape"] = list(audio.shape)
        with torch.no_grad():
            reference = model(audio)
        report["output_shape"] = list(reference.shape)
        report["stage"] = "onnx_export"
        path = args.out / "htdemucs-untrained.onnx"
        with torch.no_grad():
            torch.onnx.export(model, audio, str(path), opset_version=17,
                              input_names=["mixture"], output_names=["stems"])
        onnx.checker.check_model(str(path))
        report["stage"] = "onnx_runtime_cpu"
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        session = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
        candidate = session.run(None, {"mixture": audio.numpy()})[0]
        report["metrics"] = compare(reference.numpy(), candidate)
        report["model_bytes"] = path.stat().st_size
        report["model_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        report["status"] = "executed_untrained_probe_not_quality_approval"
    except Exception as error:
        report["status"] = "failed"
        report["error_type"] = type(error).__name__
        report["error"] = str(error)
        (args.out / "traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        report["elapsed_seconds"] = time.perf_counter() - start
        (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
