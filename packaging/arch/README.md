# Arch Linux — GCP Yt Rebalance

Desenvolvido por Bruno Albertini | [Gestão Cultural Pro](https://gestaoculturalpro.com.br)

## Instalação

Baixe `gcp-yt-rebalance-bin-<versão>-1-x86_64.pkg.tar.zst` e o `.sha256` da
[release mais recente](https://github.com/cliqueprojeto/GCP-Yt-Rebalance/releases/latest). Na pasta do download:

```bash
sha256sum -c gcp-yt-rebalance-bin-*-x86_64.pkg.tar.zst.sha256
sudo pacman -U ./gcp-yt-rebalance-bin-*-x86_64.pkg.tar.zst
```

Abra pelo menu ou execute `gcp-yt-rebalance`. Em Wayland é necessário XWayland.
Motor, modelo, Python embarcado, FFmpeg/ffprobe, yt-dlp e Node estão incluídos; o pacman
resolve apenas bibliotecas do sistema. Para remover: `sudo pacman -R gcp-yt-rebalance-bin`.

## Reconstrução local

Coloque o `.deb` da mesma versão ao lado do `PKGBUILD`, troque `SKIP` pelo SHA-256 do `.deb`
e execute `makepkg -si` como usuário comum. A opção `!strip` preserva os executáveis PyInstaller.
O pipeline de release faz exatamente isso em um container `archlinux:base-devel` e testa a
instalação em um container `archlinux:base` limpo.
