#!/usr/bin/env bash
set -euo pipefail
cd /work
: "${VERSION:?defina VERSION}"
test "$(uname -m)" = x86_64
pacman -Syu --noconfirm --needed xorg-server-xvfb xorg-xauth ttf-dejavu jq \
  desktop-file-utils glibc gcc-libs libx11 libxext libxrender libxft fontconfig \
  freetype2 libxcb zlib xdg-utils libxcrypt-compat
mkdir -p artifacts/arch dist
cat /etc/os-release > artifacts/arch/build-os-release.txt
pacman -Q > artifacts/arch/build-system-packages.txt
useradd --create-home --uid 1001 builder
build=$(mktemp -d /tmp/gcp-arch-build.XXXXXX)
cp packaging/arch/PKGBUILD packaging/arch/NOTICE.txt "$build/"
cp "dist/gcp-yt-rebalance_${VERSION}_amd64.deb" "$build/"
deb_sha=$(sha256sum "$build/gcp-yt-rebalance_${VERSION}_amd64.deb" | cut -d" " -f1)
sed -i "s/^pkgver=.*/pkgver=${VERSION}/; s/('SKIP'/('${deb_sha}'/" "$build/PKGBUILD"
grep -q "$deb_sha" "$build/PKGBUILD"
chown -R builder:builder "$build"
printf '\nPKGEXT=".pkg.tar.zst"\nPACKAGER="Bruno Albertini"\nCOMPRESSZST=(zstd -c -T2 -6 -)\n' >> /etc/makepkg.conf
runuser -u builder -- bash -c 'cd "$1"; makepkg --verifysource; makepkg --printsrcinfo > .SRCINFO; makepkg --cleanbuild --noconfirm' bash "$build"
package="$build/gcp-yt-rebalance-bin-${VERSION}-1-x86_64.pkg.tar.zst"
test -f "$package"
cp "$package" dist/
cp "$build/.SRCINFO" artifacts/arch/.SRCINFO
cp "$build/PKGBUILD" packaging/arch/NOTICE.txt artifacts/arch/
pacman -Qip "$package" > artifacts/arch/package-info.txt
bsdtar -xOf "$package" usr/share/applications/gcp-yt-rebalance.desktop > "$build/gcp-yt-rebalance.desktop"
desktop-file-validate "$build/gcp-yt-rebalance.desktop"
(cd dist && sha256sum "gcp-yt-rebalance-bin-${VERSION}-1-x86_64.pkg.tar.zst" > "gcp-yt-rebalance-bin-${VERSION}-1-x86_64.pkg.tar.zst.sha256")
chmod 644 dist/*.pkg.tar.zst* artifacts/arch/* 2>/dev/null || true
