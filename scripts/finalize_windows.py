"""Registra a entrega somente após testes do executável real."""
import hashlib
import json
from pathlib import Path
import shutil
import pefile

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist/windows/GCP Yt Rebalance.exe"
SMOKE = ROOT / "artifacts/windows-exe-smoke-01"
summary = json.loads((SMOKE / "summary.json").read_text(encoding="utf-8"))
assert summary["status"] == "passed" and summary["frozen_executable"] and summary["path_isolated"]
assert any(c["operation"] == "stems" and c["status"] == "passed" for c in summary["cases"])
with pefile.PE(str(EXE), fast_load=True) as binary:
    assert binary.FILE_HEADER.Machine == 0x8664
digest = hashlib.sha256(EXE.read_bytes()).hexdigest()
record = dict(product="GCP Yt Rebalance", developer="Bruno Albertini", version="0.1.0-experimental",
              artifact="dist/windows/GCP Yt Rebalance.exe", kind="portable self-extracting executable",
              architecture="Windows x64", bytes=EXE.stat().st_size,
              sha256=digest, signed=False,
              runtime_components_embedded=["Python 3.12", "Tcl/Tk 8.6", "PyTorch 2.2.2 CPU", "HTDemucs safetensors", "FFmpeg", "ffprobe"],
              tested_host="Windows 11 10.0.26300 AMD64", clean_machine_tested=False,
              smoke_summary=summary, music_quality_approved=False, online_downloads_enabled=False,
              public_release_approved=False)
evidence = ROOT / "docs/evidence"
(evidence / "windows-executable.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
shutil.copyfile(SMOKE / "health.json", evidence / "windows-executable-health.json")
for case in summary["cases"]:
    if "report" in case:
        source = Path(case["report"])
        name = case["operation"] + "-" + case.get("source_type", ".wav").lstrip(".") + "-" + case["format"]
        shutil.copyfile(source, evidence / f"windows-executable-{name}.json")
(EXE.parent / "SHA256SUMS.txt").write_text(f"{digest}  {EXE.name}\n", encoding="utf-8")
readme = """GCP Yt Rebalance — 0.1.0 experimental (Windows x64)
Desenvolvido por Bruno Albertini
Gestão Cultural Pro — https://gestaoculturalpro.com.br

Abra GCP Yt Rebalance.exe. Python, motor CPU, modelo e FFmpeg/ffprobe estão incluídos.
A primeira abertura extrai os componentes localmente e pode demorar.
Selecione áudio/vídeo local, pasta de saída, operação e formato; clique em Processar arquivo.
Use Abrir resultado após concluir. Cada tarefa cria uma subpasta nova, sem sobrescrever resultados.
PCM bruto: inteiro com sinal, little-endian, estéreo, parâmetros em JSON.

Funcional: conversão WAV/PCM/FLAC/MP3, remoção vocal, voz isolada, voz+instrumental, quatro stems.
Experimental: qualidade de separação musical ainda não aprovada; pode preservar resíduos vocais.
Ainda ausentes: download por URL, player A/B, fila múltipla, GPU e instalador definitivo.
Executável portátil sem assinatura digital; não é uma release pública.
Testado neste Windows com PATH isolado. Teste em máquina limpa ainda pendente.
Histórico e pasta preferida ficam em LOCALAPPDATA/GestaoCulturalPro/GCPYtRebalance.
Nenhum áudio é enviado à rede. Não há telemetria ou download de modelos durante o uso.
"""
(EXE.parent / "LEIA-ME.txt").write_text(readme, encoding="utf-8")
print(json.dumps({key: record[key] for key in ("artifact", "bytes", "sha256", "clean_machine_tested")}, indent=2))
