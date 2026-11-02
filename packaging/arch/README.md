# Arch Linux — GCP Yt Rebalance 0.3.0

Desenvolvido por Bruno Albertini — [Gestão Cultural Pro](https://gestaoculturalpro.com.br).

Distribuição privada autorizada pelo titular. Não foi publicado pacote no AUR
oficial. AUR é um repositório público de receitas PKGBUILD, não uma extensão de
instalador. Este produto oferece o pacote pacman e uma receita local equivalente.

## Instalação fácil

Entre no GitHub com uma conta autorizada ao repositório privado
`cliqueprojeto/GCP-Yt-Rebalance`. Na release `v0.3.0`, baixe o arquivo
`gcp-yt-rebalance-bin-0.3.0-1-x86_64.pkg.tar.zst` e seu SHA-256. Na pasta do download:

```bash
sha256sum -c gcp-yt-rebalance-bin-0.3.0-1-x86_64.pkg.tar.zst.sha256
sudo pacman -U ./gcp-yt-rebalance-bin-0.3.0-1-x86_64.pkg.tar.zst
```

Abra GCP Yt Rebalance pelo menu ou execute `gcp-yt-rebalance`. Use uma sessão
gráfica X11; em Wayland, é necessário XWayland. Escolha uma pasta de saída existente.
O motor CPU, pesos, Python embarcado, FFmpeg/ffprobe, yt-dlp e Node estão incluídos.
O pacman resolve bibliotecas sistêmicas; nenhuma instalação manual de Python ou
FFmpeg é necessária. A primeira instalação pode precisar de internet para essas
bibliotecas; separação e conversão locais não precisam após a instalação.

Para remover: `sudo pacman -R gcp-yt-rebalance-bin`. Preferências e arquivos
exportados na pasta do usuário permanecem fora do pacote.

## Reconstrução local

Baixe a receita `GCP-Yt-Rebalance-0.3.0-Arch-PKGBUILD.zip` e o DEB
`gcp-yt-rebalance_0.3.0_amd64.deb` da mesma release privada. Extraia a receita e
coloque o DEB ao lado de `PKGBUILD`. Com `base-devel` instalado, como usuário comum:

```bash
makepkg -si
```

A receita usa arquivos locais e hashes fixados. Ela não lê tokens, não contém
credenciais e não faz chamadas autenticadas ao GitHub. A opção `!strip` é
necessária para preservar os executáveis PyInstaller e o payload validado.

## Validação

O workflow `arch-private.yml` constrói com makepkg sem root, instala com pacman,
confere os hashes dos arquivos originais, testa interface via Xvfb, conversões
WAV/PCM/FLAC/MP3, quatro stems e remoção. O resultado real e o digest da imagem
Arch são registrados em `artifacts/arch/`. Só um job aprovado permite declarar o
pacote testado. Container X11 não certifica uma sessão Wayland ou máquina física.

Não há publicação pública ou concessão de licença pública dos binários/modelos.
A licença definitiva e a redistribuição pública continuam pendentes.
