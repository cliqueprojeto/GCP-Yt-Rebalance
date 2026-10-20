"""Sinal próprio reproduzível para testar o pipeline; não contém voz ou música real."""
import argparse
from pathlib import Path
import numpy as np
import soundfile as sf

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
if args.out.exists():
    raise SystemExit("Destino já existe; escolha outro caminho")
rate = 44100
t = np.arange(int(rate * 22.05)) / rate
rng = np.random.default_rng(7)
left = (0.1 * np.sin(2 * np.pi * 220 * t) + 0.08 * np.sin(2 * np.pi * 440 * t)
        + 0.01 * rng.standard_normal(len(t))) * (np.sin(np.pi * np.minimum(t, 1) / 2) ** 2)
right = 0.1 * np.sin(2 * np.pi * 330 * t) + 0.05 * np.sin(2 * np.pi * 660 * t)
audio = np.stack([left, right], axis=1).astype("float32")
args.out.parent.mkdir(parents=True, exist_ok=True)
sf.write(args.out, audio, rate, subtype="FLOAT")
print(f"{args.out}: {len(audio)} frames, {len(audio) / rate}s; sintético, sem voz")
