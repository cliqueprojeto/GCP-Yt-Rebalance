# GCP Yt Rebalance 0.3.0 — teste privado

Desenvolvido por Bruno Albertini — [Gestão Cultural Pro](https://gestaoculturalpro.com.br).

Pré-lançamento privado com motor CPU, modelo, FFmpeg/ffprobe, downloader e runtime
incluídos. O usuário não instala Python, FFmpeg ou pesos separadamente.

## Downloads

| Plataforma | Arquivo |
|---|---|
| Windows x64 | `GCP-Yt-Rebalance-0.3.0-Windows-x64-Setup.exe` |
| macOS Intel | `GCP-Yt-Rebalance-0.3.0-macOS-x86_64.dmg` |
| macOS Apple Silicon ARM64 | `GCP-Yt-Rebalance-0.3.0-macOS-arm64.dmg` |
| Ubuntu/Debian amd64 | `gcp-yt-rebalance_0.3.0_amd64.deb` |
| Arch Linux x86_64 | Pacote em preparação; o resultado real será registrado antes da publicação |

Os anexos possuem SHA-256 individual e manifesto `SHA256SUMS-0.3.0.txt`.

## Arch Linux privado

O titular decidiu manter o produto privado em 02/11/2026. O pacote Arch é
instalável localmente com `pacman -U`; o PKGBUILD é fornecido para reconstrução.
Nada foi publicado no AUR oficial. Não use `yay -S` para este pacote privado.
As instruções finais serão completadas após o teste real de instalação.

## Validação e limites

Os pacotes anteriores de Windows, macOS Intel/ARM64 e DEB passaram pelos testes
documentados em `docs/teste-windows-v03.md` e `docs/teste-macos-linux-v03.md`.
Ubuntu 22.04/24.04 e Debian 12/13 tiveram testes de container aprovados.

macOS não possui certificado Developer ID nem notarização. Assinatura ad hoc de
integridade não equivale a assinatura de distribuição Apple. Windows não possui
assinatura Authenticode. M1 físico, Linux Mint, sessões gráficas reais e qualidade
musical da matriz de três faixas continuam pendentes. Testes sintéticos de
formato e processamento não comprovam qualidade musical.

Os arquivos são para avaliação privada autorizada. A licença definitiva do app e
a redistribuição pública dos modelos/binários continuam pendentes. O repositório
permanece privado; os demais projetos da conta não são alterados.
