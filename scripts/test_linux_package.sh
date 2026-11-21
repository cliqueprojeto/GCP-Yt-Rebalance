#!/usr/bin/env bash
# Instala o pacote em um container limpo (sem Python/FFmpeg) e testa o app instalado.
set -euo pipefail
cd /work
kind="$1"
if [ "$kind" = deb ]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y xvfb xauth fonts-dejavu-core jq ca-certificates
  apt-get install -y ./pkg/gcp-yt-rebalance_*_amd64.deb
else
  dnf install -y xorg-x11-server-Xvfb xorg-x11-xauth dejavu-sans-fonts jq which findutils
  dnf install -y ./pkg/gcp-yt-rebalance-*.x86_64.rpm
fi
jq -r '.files[] | select(has("sha256")) | "\(.sha256)  \(.path)"' pkg/evidence/native-payload.json > /tmp/rebalance-payload.sha256
(cd /opt/gcp-yt-rebalance && sha256sum -c --quiet /tmp/rebalance-payload.sha256)
check=/tmp/rebalance-check; mkdir -p "$check"
cp pkg/evidence/fixture.wav "$check/fixture.wav"
timeout 300s xvfb-run -a gcp-yt-rebalance --self-test "$check/health.json"
jq -e '.status == "passed" and .gui_queue_conversion and .preferences_save_reload and .support_page' "$check/health.json"
for format in WAV PCM FLAC MP3; do
  mkdir -p "$check/$format"
  jq -n --arg format "$format" --arg dir "$check" '{source:($dir+"/fixture.wav"),destination:$dir,operation:"convert",format:$format,bits:16,rate:44100,bitrate:192,threads:2,id:"0123456789abcdef0123456789abcdef"}' > "$check/$format/request.json"
  timeout 240s "/opt/gcp-yt-rebalance/GCP Yt Rebalance" --worker "$check/$format/request.json"
  jq -e '.phase == "Concluído"' <(tail -n 1 "$check/$format/events.jsonl")
done
mkdir -p "$check/stems"
jq '.operation="stems" | .format="WAV"' "$check/WAV/request.json" > "$check/stems/request.json"
timeout 300s "/opt/gcp-yt-rebalance/GCP Yt Rebalance" --worker "$check/stems/request.json"
jq -e '.phase == "Concluído"' <(tail -n 1 "$check/stems/events.jsonl")
if [ "$kind" = deb ]; then apt-get remove -y gcp-yt-rebalance; else dnf remove -y gcp-yt-rebalance; fi
test ! -e /opt/gcp-yt-rebalance/_internal
echo "PASS $kind"
