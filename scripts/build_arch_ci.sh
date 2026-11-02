#!/usr/bin/env bash
set -euo pipefail
cd /work
test "$(uname -m)" = x86_64
pacman -Syu --noconfirm --needed xorg-server-xvfb xorg-xauth ttf-dejavu jq \
  desktop-file-utils glibc gcc-libs libx11 libxext libxrender libxft fontconfig \
  freetype2 libxcb zlib xdg-utils libxcrypt-compat
mkdir -p artifacts/arch dist
cat /etc/os-release > artifacts/arch/build-os-release.txt
pacman -Q > artifacts/arch/build-system-packages.txt
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
pacman -Qip "$package" > artifacts/arch/package-info.txt
bsdtar -xOf "$package" usr/share/applications/gcp-yt-rebalance.desktop > "$build/gcp-yt-rebalance.desktop"
desktop-file-validate "$build/gcp-yt-rebalance.desktop"
(cd dist && sha256sum gcp-yt-rebalance-bin-0.3.0-1-x86_64.pkg.tar.zst > gcp-yt-rebalance-bin-0.3.0-1-x86_64.pkg.tar.zst.sha256)
