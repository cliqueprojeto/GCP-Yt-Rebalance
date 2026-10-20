# ADR 0004 — preservar o downloader universal no bundle macOS

Estado: aplicado no build Intel `dcc59d58e623e33fe0d84c091e59d1b308b4174d`; testes do aplicativo e da instalação do DMG aprovados na execução 39411413799.

O primeiro build Intel abriu a interface e converteu áudio, mas `yt-dlp --version` falhou depois da coleta como `BINARY` pelo PyInstaller. O executável oficial macOS é universal e contém seu próprio arquivo PKG anexado. A coleta para um alvo específico usa redução de arquitetura, conforme a [documentação do PyInstaller](https://pyinstaller.org/en/v6.12.0/feature-notes.html#trimming-fat-binaries-for-single-arch-targets).

O experimento nativo `scripts/macos_downloader_probe.py` comparou três casos no Intel:

| Caso | Resultado |
|---|---|
| Original oficial com checksum fixado | Código 0, versão 2026.08.19 |
| Cópia reduzida por `lipo -thin x86_64` e reassinada | Código 255: arquivo PKG interno não encontrado |
| Cópia universal preservada e reassinada | Código 0, versão 2026.08.19 |

Decisão: no macOS, excluir esse sidecar da coleta que reduz arquiteturas, copiá-lo integralmente após `BUNDLE` para `Contents/Frameworks/vendor/download/yt-dlp` e reassinar o bundle com identidade ad hoc. FFmpeg, ffprobe e Node continuam na coleta normal. O contrato exige que o sidecar contenha a arquitetura do alvo e o manifesto registra o hash efetivamente empacotado.

A verificação `codesign --verify --deep --strict`, os testes reais do downloader e a cópia instalada do DMG passaram no Intel corrigido. O DMG ARM64 anterior também passou, com seu commit e hash próprios; não foi reconstruído sem necessidade. Builds futuros ARM64 usarão o caminho universal preservado e deverão repetir toda a suíte. A assinatura ad hoc não substitui Developer ID ou notarização.

O self-test também passou a registrar código de saída e stderr de `--version`, evitando erro vazio quando uma ferramenta embarcada falhar. Esses comandos usam argumentos constantes e não incluem URLs ou credenciais.
