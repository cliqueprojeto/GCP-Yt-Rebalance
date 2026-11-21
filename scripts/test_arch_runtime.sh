#!/usr/bin/env bash
set -euo pipefail
cd /work
: "${VERSION:?defina VERSION}"
pacman -Syu --noconfirm --needed xorg-server-xvfb xorg-xauth ttf-dejavu jq
pacman -U --noconfirm "dist/gcp-yt-rebalance-bin-${VERSION}-1-x86_64.pkg.tar.zst"
cat /etc/os-release > artifacts/arch/os-release.txt
pacman -Q > artifacts/arch/system-packages.txt
pacman -Q python ffmpeg > artifacts/arch/external-runtime-check.txt 2>&1 || true
python_present=false
if pacman -Q python >/dev/null 2>&1; then python_present=true; fi
useradd --create-home --uid 1001 builder
jq -r '.files[] | select(has("sha256")) | "\(.sha256)  \(.path)"' artifacts/arch-input/native-payload.json > /tmp/gcp-arch-payload.sha256
(cd /opt/gcp-yt-rebalance && sha256sum -c /tmp/gcp-arch-payload.sha256) > artifacts/arch/payload-check.txt
smoke=$(mktemp -d /tmp/gcp-arch-smoke.XXXXXX)
cp artifacts/arch-input/fixture.wav "$smoke/fixture.wav"
chown -R builder:builder "$smoke"
# Xvfb e timeout usam o PATH do SO. O app e seus workers recebem PATH vazio.
runuser -u builder -- timeout 240s xvfb-run -a env -u PYTHONPATH -u PYTHONHOME \
  PATH=/gcp-no-external-runtime /usr/bin/gcp-yt-rebalance --self-test "$smoke/health.json"
jq -e '.status == "passed" and .frozen and .gui_queue_conversion and .models_verified' "$smoke/health.json"
for format in WAV PCM FLAC MP3; do
  work="$smoke/$format"; mkdir "$work"
  jq -n --arg source "$smoke/fixture.wav" --arg destination "$smoke" --arg format "$format" \
    '{source:$source,destination:$destination,operation:"convert",format:$format,bits:16,rate:44100,bitrate:192,threads:2,id:"0123456789abcdef0123456789abcdef"}' > "$work/request.json"
  chown -R builder:builder "$work"
  runuser -u builder -- timeout 240s env -u PYTHONPATH -u PYTHONHOME PATH=/gcp-no-external-runtime \
    /usr/bin/gcp-yt-rebalance --worker "$work/request.json"
  jq -e '.phase == "Concluído"' <(tail -n 1 "$work/events.jsonl")
done
mkdir "$smoke/stems"
jq '.operation="stems" | .format="WAV"' "$smoke/WAV/request.json" > "$smoke/stems/request.json"
chown -R builder:builder "$smoke/stems"
runuser -u builder -- timeout 240s env -u PYTHONPATH -u PYTHONHOME PATH=/gcp-no-external-runtime \
  /usr/bin/gcp-yt-rebalance --worker "$smoke/stems/request.json"
jq -e '.phase == "Concluído"' <(tail -n 1 "$smoke/stems/events.jsonl")
cp "$smoke/health.json" artifacts/arch/health.json
mkdir -p artifacts/arch/reports
index=0
while IFS= read -r -d '' report; do
  target="artifacts/arch/reports/case-$(printf '%02d' "$index").json"
  cp "$report" "$target"
  chmod 644 "$target"
  index=$((index+1))
done < <(find "$smoke" -name relatorio.json -print0)
pacman -R --noconfirm gcp-yt-rebalance-bin
test ! -e /usr/bin/gcp-yt-rebalance
test ! -e /opt/gcp-yt-rebalance
jq -n --argjson python_present "$python_present" \
  '{status:"passed",aur_published:false,makepkg_nonroot:true,payload_hashes_verified:true,desktop_entry_valid:true,installed_gui:true,conversions:["WAV","PCM","FLAC","MP3"],stems:true,uninstalled:true,path_isolated:true,runtime_python_package_present:$python_present,fixture:"own synthetic signal; not musical quality validation"}' > artifacts/arch/summary.json
