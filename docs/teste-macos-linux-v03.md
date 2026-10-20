# GCP Yt Rebalance 0.3.0 — testes de instaladores Mac/Linux

Desenvolvido por Bruno Albertini — [Gestão Cultural Pro](https://gestaoculturalpro.com.br).

Execuções privadas autorizadas em 20/10/2026:

- [Primeiro ciclo Mac Intel, ARM64 e Linux](https://github.com/cliqueprojeto/GCP-Yt-Rebalance/actions/runs/39408624618), commit `6e4efd8dfe1fa1a49787c9309e2b5fe2010f91fd`.
- [Repetição Linux corrigido](https://github.com/cliqueprojeto/GCP-Yt-Rebalance/actions/runs/39410186466), commit `9d7c58babfc0ef271bff788b0a710bbc24acbf74`.
- [Repetição Intel com downloader universal preservado](https://github.com/cliqueprojeto/GCP-Yt-Rebalance/actions/runs/39411413799), commit `dcc59d58e623e33fe0d84c091e59d1b308b4174d`.

## Resultados gerados e conferidos

| Plataforma | Estado |
|---|---|
| macOS ARM64 | DMG gerado, instalado por cópia e primeira execução aprovada no runner macOS 15.7.9 ARM64 |
| macOS Intel | DMG gerado, instalado por cópia e primeira execução aprovada no runner macOS 15.7.9 x86_64 após correção do downloader |
| Linux amd64 | DEB gerado, instalado e executado no runner Ubuntu 22.04; instalação, conversão e stems passaram também em containers Ubuntu 22.04/24.04 e Debian 12/13 |

DMG ARM64: `dist/GCP Yt Rebalance-0.3.0-macOS-arm64.dmg`, 334.337.237 bytes. Payload medido: 643.465.089 bytes. SHA-256: `d5532a97c5101c08aea3d16e3c3c1650fbe00df2117348bb1b128ac6ebb5730f`. O arquivo baixado do Actions foi verificado novamente pelo hash antes da cópia para `dist/`.

DMG Intel: `dist/GCP Yt Rebalance-0.3.0-macOS-x86_64.dmg`, 447.586.928 bytes. Payload medido: 995.254.538 bytes. SHA-256: `08c97bde35defe8102ac7319e245ce3a082f484b2f47e26755d926208cc36f20`. O arquivo baixado também passou na conferência local do hash. A mesma suíte funcional e de instalação passou. O experimento de empacotamento confirmou código 255 no downloader reduzido por `lipo` e código 0 no universal preservado; a correção e suas evidências estão na [ADR 0004](adr/0004-sidecar-universal-macos.md).

DEB amd64: `dist/gcp-yt-rebalance_0.3.0_amd64.deb`, 357.186.302 bytes. Payload medido: 1.133.969.170 bytes. SHA-256: `443518f3d56ff929f0cbe4d2d3b6402fce40f100bd94a0cf27cdd09a03d71dcc`. O manifesto instalado e o hash do instalador baixado passaram. O primeiro build Linux falhou ao abrir imagens por ausência de `PIL._tkinter_finder`; o módulo foi incluído explicitamente e toda a suíte do segundo build passou.

Os testes ARM64 passaram para sete páginas em quatro tamanhos, conversões WAV/PCM/FLAC/MP3, vídeo local para WAV, geração de quatro stems, encerramento de worker e descendente, preferências, restauração de fábrica, opções de legendas, histórico e erros de entrada. O downloader real passou nos quatro modos com mídia sintética própria em servidor HTTP efêmero da suíte e legendas próprias pt/en. O teste YouTube público ficou desativado neste ciclo.

O DMG foi montado somente para leitura, o aplicativo foi copiado por `ditto`, o manifesto completo foi comparado por SHA-256 e symlinks, a assinatura ad hoc foi conferida e a cópia instalada passou no self-test. Cabeçalhos Mach-O e hash do modelo também foram validados.

No Linux, a suíte equivalente passou para interface, preferências, histórico, quatro formatos, vídeo local, stems, cancelamento, quatro modos do downloader e legendas próprias. O DEB foi instalado e removido no host, com todos os hashes e symlinks comparados ao payload. Os quatro containers adicionais passaram em instalação, conferência de arquivos por SHA-256, abertura da interface, WAV/PCM/FLAC/MP3, stems e remoção. Containers não equivalem a teste visual em máquina/VM limpa, e não foi executado teste em Linux Mint.

As fixtures têm 0,4 segundo de sinal sintético próprio. Estes resultados verificam funcionamento e formatos, sem comprovar qualidade musical ou velocidade em músicas completas. O caso local de quatro stems levou 13,35 s no runner ARM64, 19,25 s no Intel e 11,48 s no Linux, incluindo início do worker. Não extrapolar para uma música de 3–5 minutos. Não foram medidos pico de RAM/CPU ou blocos reais ocupados em disco; os tamanhos de payload são somas dos bytes de arquivos, sem contar symlinks como cópias.

## Como testar os pacotes

No Mac, escolha o DMG ARM64 para Apple Silicon ou x86_64 para Intel. Abra o DMG, copie `GCP Yt Rebalance.app` para Aplicativos e abra a cópia. Os testes automatizados usam uma cópia isolada para conferir o mesmo conteúdo, sem instalar em `/Applications` do runner.

No Ubuntu/Debian com sessão gráfica, abra um terminal na pasta do DEB e execute:

```bash
sudo apt install ./gcp-yt-rebalance_0.3.0_amd64.deb
```

Abra GCP Yt Rebalance pelo menu de aplicativos. Selecione uma pasta de saída existente e um arquivo local autorizado para a primeira conversão. As bibliotecas sistêmicas declaradas pelo DEB podem ser resolvidas pelo gerenciador de pacotes; Python, motor, pesos, FFmpeg, ffprobe, Node e downloader já estão no produto.

## Limites da entrega de teste

O app inclui motor CPU, modelo, FFmpeg, ffprobe, yt-dlp, Node e dependências Python; o usuário final não instala essas ferramentas separadamente. Bibliotecas essenciais do sistema continuam sendo necessárias no Linux.

Não há certificado Developer ID nem notarização Apple. A assinatura ad hoc verifica integridade do bundle e não equivale à assinatura de distribuição. Hardware M1 físico, interação Finder/Dock, quarentena de download, máquinas/VMs limpas e Linux Mint ainda precisam de validação. A versão testada do macOS não estabelece uma versão mínima já certificada.

O repositório e os artefatos no Actions permanecem privados. Não foi criada release pública. Licença do aplicativo, redistribuição pública dos pesos, validação musical e demais gates da release continuam pendentes.
