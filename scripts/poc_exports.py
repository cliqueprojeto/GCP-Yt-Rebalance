"""POC de exportação local: formatos reais, sem depender de FFmpeg no PATH."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    import numpy as np
    import soundfile as sf
    import lameenc
    audio, rate = sf.read(args.input, dtype="float32", always_2d=True)
    if len(audio) == 0 or not np.isfinite(audio).all() or np.max(np.abs(audio)) > 1:
        raise ValueError("Entrada vazia, não finita ou acima de full scale; definir ganho explicitamente")
    if audio.shape[1] not in (1, 2):
        raise ValueError("Esta POC valida apenas mono ou estéreo")
    args.out.mkdir(parents=True, exist_ok=False)
    # Conversão explícita: arredondamento e saturação apenas dos extremos PCM16.
    pcm = np.clip(np.rint(audio.astype(np.float64) * 32768), -32768, 32767).astype("<i2")
    sf.write(args.out / "audio.wav", audio, rate, subtype="FLOAT")
    sf.write(args.out / "audio.flac", audio, rate, subtype="PCM_24")
    (args.out / "audio.pcm").write_bytes(pcm.tobytes(order="C"))
    raw = dict(format="signed integer PCM", bits_per_sample=16, endianness="little",
               channels=audio.shape[1], sample_rate=rate, interleaved=True,
               frames=len(audio), duration_seconds=len(audio) / rate)
    (args.out / "audio.pcm.json").write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(192)
    encoder.set_in_sample_rate(rate)
    encoder.set_channels(audio.shape[1])
    encoder.set_quality(2)
    (args.out / "audio.mp3").write_bytes(encoder.encode(pcm.tobytes()) + encoder.flush())
    results = []
    for extension in ("wav", "flac", "pcm", "mp3"):
        path = args.out / f"audio.{extension}"
        result = dict(format=extension, bytes=path.stat().st_size,
                      sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        if extension == "pcm":
            decoded = np.fromfile(path, dtype="<i2").reshape(-1, audio.shape[1])
            if not np.array_equal(decoded, pcm):
                raise ValueError("PCM divergente")
            result.update(frames=len(decoded), parameters=raw, roundtrip_exact=True)
        else:
            decoded, actual_rate = sf.read(path, dtype="float32", always_2d=True)
            if actual_rate != rate or decoded.shape[1] != audio.shape[1] or not np.isfinite(decoded).all():
                raise ValueError(f"Formato inválido: {extension}")
            difference = len(decoded) - len(audio)
            if (extension != "mp3" and difference != 0) or abs(difference) > rate * 0.1:
                raise ValueError(f"Duração incompatível: {extension}")
            result.update(frames=len(decoded), sample_rate=actual_rate, channels=decoded.shape[1],
                          subtype=sf.info(path).subtype, duration_delta_seconds=difference / rate)
            if extension == "wav" and not np.array_equal(decoded, audio):
                raise ValueError("WAV float divergente")
            if extension == "flac":
                error = float(np.max(np.abs(decoded.astype(np.float64) - audio)))
                if error > 1 / (2 ** 23):
                    raise ValueError("FLAC fora da tolerância de quantização 24-bit")
                result["quantization_max_abs_error"] = error
            if extension == "mp3":
                result["requested_bitrate_kbps"] = 192
                result["note"] = "Com perdas. Padding/delay do codificador registrado; não equivale a qualidade original."
        results.append(result)
    report = dict(status="passed_library_decode_checks", ffprobe_validation="pending_binary_unavailable",
                  input_sha256=hashlib.sha256(args.input.read_bytes()).hexdigest(), outputs=results)
    (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
