<p align="center"><img src="assets/branding/icon-128.png" width="96" alt="GCP Yt Rebalance"></p>

<h1 align="center">GCP Yt Rebalance</h1>

<p align="center">Áudio • Vídeo • Karaokê — baixe, separe e converta com processamento 100% local.<br>
Desenvolvido por Bruno Albertini | <a href="https://gestaoculturalpro.com.br">Gestão Cultural Pro</a></p>

## Download

Baixe a versão mais recente em **[Releases](https://github.com/cliqueprojeto/GCP-Yt-Rebalance/releases/latest)**:

| Sistema | Arquivo | Instalação |
|---|---|---|
| Windows 10/11 (64 bits) | `…-Windows-x64-Setup.exe` | Dois cliques no instalador |
| macOS Apple Silicon (M1 ou superior) | `…-macOS-arm64.dmg` | Abra o DMG e arraste para Aplicativos |
| macOS Intel | `…-macOS-x86_64.dmg` | Abra o DMG e arraste para Aplicativos |
| Ubuntu, Debian, Mint, Pop!_OS | `…_amd64.deb` | Dois cliques (Central de Programas) ou `sudo apt install ./arquivo.deb` |
| Fedora, openSUSE, RHEL | `…x86_64.rpm` | Dois cliques ou `sudo dnf install ./arquivo.rpm` |
| Arch, Manjaro, EndeavourOS | `…pkg.tar.zst` | `sudo pacman -U ./arquivo.pkg.tar.zst` |

Tudo incluído no instalador: motor de separação, modelo, FFmpeg/ffprobe, downloader e runtime. Nada para baixar por fora.

## Recursos

- Downloads de áudio, vídeo e legendas (YouTube, Vimeo, SoundCloud, Archive.org e links diretos).
- Karaokê (remove vocais), acapella e separação em 4 stems na CPU.
- Conversão WAV, PCM, FLAC e MP3 com profundidade e taxa configuráveis.
- Fila, histórico local e estimativa de tempo.
- Tema claro, escuro ou do sistema.
- Interface em Português, English e Español.
- Atualizações direto no aplicativo, a partir das releases do GitHub, com verificação SHA-256.
- Sem conta, assinatura, anúncios ou envio de áudio.

## Apoie o projeto

O aplicativo é gratuito. Se ele ajuda no seu trabalho, apoie pelo app (tela **Apoie o projeto**) ou:

- **PIX:** QR Code dentro do aplicativo
- **Stripe (internacional):** [donate.stripe.com/fZu4gzeBSfhbd7451F6Ri00](https://donate.stripe.com/fZu4gzeBSfhbd7451F6Ri00)

## Desenvolvimento

```bash
python -m unittest discover -s tests -v
python apps/desktop/main.py
```

Releases: o workflow **Release — GCP Yt Rebalance** (`.github/workflows/desktop-installers.yml`) gera e testa todos os instaladores e publica a release. Ele roda ao enviar uma tag `vX.Y.Z` igual à versão em `apps/desktop/runtime.py`, ou manualmente pela aba Actions.

- [Arquitetura](docs/arquitetura.md) • [Build multiplataforma](docs/build-multiplataforma.md) • [Identidade visual](assets/branding/README.md) • [Arch Linux](packaging/arch/README.md)

Fonte Inter incluída sob a SIL Open Font License 1.1 (`assets/fonts/OFL.txt`). Componentes de terceiros mantêm suas licenças, incluídas no pacote em `vendor/notices`.

© Bruno Albertini — Gestão Cultural Pro. Todos os direitos reservados.
