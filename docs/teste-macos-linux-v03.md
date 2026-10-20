# GCP Yt Rebalance 0.3.0 — testes de instaladores Mac/Linux

Desenvolvido por Bruno Albertini — [Gestão Cultural Pro](https://gestaoculturalpro.com.br).

Execuções privadas autorizadas em 20/10/2026:

- [Primeiro ciclo Mac Intel, ARM64 e Linux](https://github.com/cliqueprojeto/GCP-Yt-Rebalance/actions/runs/39408624618), commit `6e4efd8dfe1fa1a49787c9309e2b5fe2010f91fd`.
- [Repetição Linux corrigido](https://github.com/cliqueprojeto/GCP-Yt-Rebalance/actions/runs/39410186466), commit `9d7c58babfc0ef271bff788b0a710bbc24acbf74`.

## Resultados em andamento

| Plataforma | Estado |
|---|---|
| macOS ARM64 | DMG gerado, instalado por cópia e primeira execução aprovada no runner macOS 15.7.9 ARM64 |
| macOS Intel | Build em andamento |
| Linux amd64 | Primeiro teste de abertura falhou por ausência de `PIL._tkinter_finder`; inclusão corrigida e novo build iniciado |

DMG ARM64: `dist/GCP Yt Rebalance-0.3.0-macOS-arm64.dmg`, 334.337.237 bytes. Payload medido: 643.465.089 bytes. SHA-256: `d5532a97c5101c08aea3d16e3c3c1650fbe00df2117348bb1b128ac6ebb5730f`. O arquivo baixado do Actions foi verificado novamente pelo hash antes da cópia para `dist/`.

Os testes ARM64 passaram para sete páginas em quatro tamanhos, conversões WAV/PCM/FLAC/MP3, vídeo local para WAV, geração de quatro stems, encerramento de worker e descendente, preferências, restauração de fábrica, opções de legendas, histórico e erros de entrada. O downloader real passou nos quatro modos com mídia sintética própria em servidor HTTP efêmero da suíte e legendas próprias pt/en. O teste YouTube público ficou desativado neste ciclo.

O DMG foi montado somente para leitura, o aplicativo foi copiado por `ditto`, o manifesto completo foi comparado por SHA-256 e symlinks, a assinatura ad hoc foi conferida e a cópia instalada passou no self-test. Cabeçalhos Mach-O e hash do modelo também foram validados.

As fixtures têm 0,4 segundo de sinal sintético próprio. Estes resultados verificam funcionamento e formatos, sem comprovar qualidade musical ou velocidade em músicas completas. No runner ARM64, o caso local de quatro stems levou 13,35 s, incluindo início do worker. Não extrapolar para uma música de 3–5 minutos.

## Limites da entrega de teste

O app inclui motor CPU, modelo, FFmpeg, ffprobe, yt-dlp, Node e dependências Python; o usuário final não instala essas ferramentas separadamente. Bibliotecas essenciais do sistema continuam sendo necessárias no Linux.

Não há certificado Developer ID nem notarização Apple. A assinatura ad hoc verifica integridade do bundle e não equivale à assinatura de distribuição. Hardware M1 físico, interação Finder/Dock, quarentena de download, máquinas/VMs limpas e Linux Mint ainda precisam de validação. A versão testada do macOS não estabelece uma versão mínima já certificada.

O repositório e os artefatos no Actions permanecem privados. Não foi criada release pública. Licença do aplicativo, redistribuição pública dos pesos, validação musical e demais gates da release continuam pendentes.
