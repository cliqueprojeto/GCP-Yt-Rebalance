"""Inventário reproduzível; ausência de dependência nunca vira aprovação."""
import importlib.metadata
import importlib.util
import json
import os
import platform
from pathlib import Path
import shutil
import sys


def collect():
    packages = {}
    for name in ("torch", "demucs", "onnx", "onnxruntime", "numpy", "Pillow", "psutil", "soundfile"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return dict(platform=platform.platform(), architecture=platform.machine(),
                processor=os.getenv("PROCESSOR_IDENTIFIER", platform.processor()),
                logical_cpus=os.cpu_count(), python=sys.version,
                tools={name: shutil.which(name) for name in ("git", "rustc", "cargo", "node", "ffmpeg", "ffprobe")},
                packages=packages)


if __name__ == "__main__":
    output = Path("docs/evidence/environment.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(collect(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output.read_text(encoding="utf-8"))
