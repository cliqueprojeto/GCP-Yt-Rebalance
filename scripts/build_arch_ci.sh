#!/usr/bin/env bash
set -euo pipefail
cd /work
test "$(uname -m)" = x86_64
pacman -Syu --noconfirm --needed xorg-server-xvfb xorg-xauth ttf-dejavu jq \
  desktop-file-utils glibc gcc-libs libx11 libxext libxrender libxft fontconfig \
  freetype2 libxcb zlib xdg-utils libxcrypt-compat
mkdir -p artifacts/arch dist
cat /etc/os-release > artifacts/arch/os-release.txt
pacman -Q > artifacts/arch/system-packages.txt
# Esta imagem de teste não recebe Python, FFmpeg nem o motor via pacman.
if pacman -Q python ffmpeg > artifacts/arch/external-runtime-check.txt 2>&1; then
  echo 'Runtime externo inesperado no teste' >&2
  exit 1
fi
for dependency in python ffmpeg; do
  if pacman -Q "$dependency" >/dev/null 2>&1; then exit 1; fi
done
useradd --create-home --uid 1001 builder
build=$(mktemp -d /tmp/gcp-arch-build.XXXXXX)
cp packaging/arch/PKGBUILD packaging/arch/NOTICE-PRIVATE.txt "$build/"
cp dist/gcp-yt-rebalance_0.3.0_amd64.deb "$build/"
chown -R builder:builder "$build"
printf '\nPKGEXT=".pkg.tar.zst"\nPACKAGER="Bruno Albertini"\nCOMPRESSZST=(zstd -c -T2 -6 -)\n' >> /etc/makepkg.conf
runuser -u builder -- bash -c 'cd "$1"; makepkg --verifysource; makepkg --printsrcinfo > .SRCINFO; makepkg --cleanbuild --noconfirm' bash "$build"
package="$build/gcp-yt-rebalance-bin-0.3.0-1-x86_64.pkg.tar.zst"
test -f "$package"
cp "$package" dist/
cp "$build/.SRCINFO" artifacts/arch/.SRCINFO
cp packaging/arch/PKGBUILD packaging/arch/NOTICE-PRIVATE.txt artifacts/arch/
pacman -U --noconfirm "$package"
pacman -Qip "$package" > artifacts/arch/package-info.txt
desktop-file-validate /usr/share/applications/gcp-yt-rebalance.desktop
jq -r '.files[] | select(has("sha256")) | "\(.sha256)  \(.path)"' \
  artifacts/arch-input/native-payload.json > /tmp/gcp-arch-payload.sha256
(cd /opt/gcp-yt-rebalance && sha256sum -c /tmp/gcp-arch-payload.sha256) \
  > artifacts/arch/payload-check.txt
smoke=$(mktemp -d /tmp/gcp-arch-smoke.XXXXXX)
cp artifacts/arch-input/fixture.wav "$smoke/fixture.wav"
chown -R builder:builder "$smoke"
runuser -u builder -- env -u PYTHONPATH -u PYTHONHOME PATH=/usr/bin:/bin \
  timeout 240s xvfb-run -a gcp-yt-rebalance --self-test "$smoke/health.json"
jq -e '.status == "passed" and .gui_queue_conversion and .preferences_save_reload and .models_verified' "$smoke/health.json"
for format in WAV PCM FLAC MP3; do
  work="$smoke/$format"
  mkdir "$work"
  jq -n --arg source "$smoke/fixture.wav" --arg destination "$smoke" --arg format "$format" \
    '{source:$source,destination:$destination,operation:"convert",format:$format,bits:16,rate:44100,bitrate:192,threads:2,id:"0123456789abcdef0123456789abcdef"}' > "$work/request.json"
  chown -R builder:builder "$work"
  runuser -u builder -- timeout 240s gcp-yt-rebalance --worker "$work/request.json"
  jq -e '.phase == "Concluído"' <(tail -n 1 "$work/events.jsonl")
done
mkdir "$smoke/stems"
jq '.operation="stems" | .format="WAV"' "$smoke/WAV/request.json" > "$smoke/stems/request.json"
chown -R builder:builder "$smoke/stems"
runuser -u builder -- timeout 240s gcp-yt-rebalance --worker "$smoke/stems/request.json"
jq -e '.phase == "Concluído"' <(tail -n 1 "$smoke/stems/events.jsonl")
cp "$smoke/health.json" artifacts/arch/health.json
find "$smoke" -name relatorio.json -exec cp --parents '{}' /work/artifacts/arch/ \;
pacman -R --noconfirm gcp-yt-rebalance-bin
test ! -e /usr/bin/gcp-yt-rebalance
test ! -e /opt/gcp-yt-rebalance
jq -n '{status:"passed",private:true,aur_published:false,makepkg_nonroot:true,payload_hashes_verified:true,desktop_entry_valid:true,installed_gui:true,conversions:["WAV","PCM","FLAC","MP3"],stems:true,uninstalled:true,fixture:"own synthetic signal; not musical quality validation"}' > artifacts/arch/summary.json
(cd dist && sha256sum gcp-yt-rebalance-bin-0.3.0-1-x86_64.pkg.tar.zst > gcp-yt-rebalance-bin-0.3.0-1-x86_64.pkg.tar.zst.sha256)
