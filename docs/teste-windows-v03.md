# GCP Yt Rebalance 0.3.0 — teste Windows x64

Desenvolvido por Bruno Albertini — Gestão Cultural Pro. Data: 19/10/2026.

Instalador completo: `dist/GCP Yt Rebalance Setup 0.3.0.exe`, **365.234.749 bytes**, aproximadamente 365 MB ou 348,31 MiB. Payload: **995.386.243 bytes**, aproximadamente 949,27 MiB, além do desinstalador e espaço dos trabalhos. Inclui Python, CPU/PyTorch, modelo, FFmpeg/ffprobe, downloader e Node. Não é necessário instalar esses componentes separadamente.

SHA-256: `c21cb9ff715834ff64847bbe0143402fcdf7c6d1508d38d81b1b9c8ca3fb5eb9`. Arquivo separado: `dist/GCP Yt Rebalance Setup 0.3.0.exe.sha256`.

## Mudanças solicitadas

- Logo lateral igual ao ícone do programa/atalho: utiliza a mesma arte de seta e onda em PNG/ICO/ICNS. O arquivo original fornecido continua preservado entre os ativos de origem.
- Padrão de fábrica: WAV PCM **16 bits**, 44.100 Hz. Configurações antigas sem qualidade salva migram para esse padrão.
- Downloads: botão **Carregar opções de legendas**, pesquisa por nome/código de idioma e seleção múltipla, com identificação de legendas publicadas ou automáticas. Apenas as opções informadas pela fonte são oferecidas. Limite de 20 idiomas por tarefa.
- Legendas selecionadas acompanham vídeo, áudio, instrumental ou stems como arquivos `.srt` separados. Exemplos: `Título_Legenda_pt.srt`, `Título_Legenda_en_automatica.srt`. Não são queimadas na imagem. Se a fonte recusar uma legenda, a tarefa apresenta erro compreensível e pode ser repetida sem esse idioma; não publica resultado parcial como concluído.
- Configurações salvam formato, profundidade, taxa de amostragem, bitrate MP3, threads CPU, resolução preferida, pasta e animações. Alterações temporárias na tela de conversão não substituem os padrões salvos; use **Salvar preferências** para isso.
- **Restaurar padrões de fábrica** exige confirmação e redefine as configurações. Preserva histórico, resultados e tarefas já criadas. A resolução preferida é um teto quando aplicável; a disponibilidade continua dependente da fonte.

Para legendas, cole o link, clique em Carregar opções, escolha os idiomas e adicione o download à fila. Opções automáticas pertencem à plataforma; o aplicativo não envia áudio a serviços de transcrição nem produz traduções em nuvem.

## Testado nesta sessão

Host: Windows 11 AMD64. Instalador sem assinatura Authenticode, destinado a teste local. Não houve publicação externa.

- **16 testes unitários aprovados**, incluindo validação de preferências, idiomas, separação entre legendas publicadas/automáticas, bloqueio de opções inválidas e anexos sem traversal.
- Executável final com PATH limitado a System32: sete páginas em quatro tamanhos, conversão real pela fila, histórico, diálogos de erro, gravação/releitura de qualidade, reset preservando histórico e interface de seleção de idiomas.
- Arquivo convertido pelo padrão da interface confirmado por ffprobe como `pcm_s16le`, 44.100 Hz, estéreo, 16 bits.
- WAV, PCM24/48k, FLAC24, MP3/192k, vídeo local para WAV, quatro stems, cancelamento do processo supervisionado e descendente. Sinal sintético próprio de 0,4 s; não é teste de qualidade musical.
- **Downloader real com duas legendas próprias pt/en**: vídeo + dois SRT e áudio + dois SRT, conferindo texto UTF-8 e timecodes após conversão de VTT. Teste executado primeiro no código-fonte e depois no executável final. O caminho automático foi validado em teste de comando, sem alegar download real de legenda automática nesta sessão.
- Consulta real ao vídeo aberto Big Buck Bunny no YouTube: a fonte retornou zero legendas; essa ausência foi tratada corretamente. Vídeo e áudio reais do YouTube já haviam passado na versão 0.2; a evidência anterior foi preservada. Não foi alegado teste de legenda inexistente.
- **Instalador real aprovado**: instalação isolada, comparação SHA-256 dos 2.899 arquivos do payload, interface instalada com conversão e preferências, e desinstalação. Test mode omite atalhos/registro do fluxo normal.
- Conjunto mínimo de dependências do pipeline instalado offline em `.venv-ci-check`, separado do laboratório: interface, preferências, quatro conversões, vídeo local, inferência de quatro stems e cancelamento passaram. Isso valida esse conjunto no Windows; não substitui a execução dos runners Mac/Linux.

Os resultados completos ficam em `docs/evidence/windows-v03/`. Os scripts de teste e empacotamento são:

```powershell
.venv-poc/Scripts/python.exe -m unittest discover -s tests -v
.venv-poc/Scripts/python.exe scripts/prepare_windows_package.py
.venv-poc/Scripts/python.exe -m PyInstaller --noconfirm --distpath dist/v0.3 --workpath build/v0.3 apps/desktop/windows.spec
.venv-poc/Scripts/python.exe scripts/smoke_windows.py --exe "dist/v0.3/GCP Yt Rebalance/GCP Yt Rebalance.exe" --separation --out artifacts/v03-final-offline
.venv-poc/Scripts/python.exe scripts/smoke_subtitles.py --exe "dist/v0.3/GCP Yt Rebalance/GCP Yt Rebalance.exe" --out artifacts/v03-final-subtitles
.tools/nsis-3.12/makensis.exe /V2 scripts/windows-installer.nsi
.venv-poc/Scripts/python.exe scripts/smoke_installer.py
.venv-poc/Scripts/python.exe scripts/hash_installers.py
```

Os diretórios de teste devem ser novos. Nesta sessão, executáveis GUI e NSIS foram testados no host fora do sandbox; não representam testes em VM limpa.

## Pendências

Os instaladores macOS Intel/Apple Silicon e Linux DEB **não foram gerados neste Windows**. O solicitante autorizou preparar o [pipeline nativo](build-multiplataforma.md). Faltam repositório/runners e execução efetiva; Linux Mint precisa ainda de VM/máquina de teste específica. Nenhuma compatibilidade dessas plataformas foi aprovada só pela configuração.

Permanecem pendentes: máquina limpa Windows; matriz de qualidade musical/benchmarks; versões mínimas dos sistemas; licença do aplicativo; auditoria de redistribuição dos pesos/componentes; assinatura e notarização; player A/B e recuperação persistente da fila. Sem release pública final.

## Revisão de empacotamento em 20/10/2026

O teste da instalação normal identificou a pasta do menu Iniciar gravada como `GestÃ£o Cultural Pro`. O script NSIS passou a usar UTF-8 com BOM e migra somente o atalho deste aplicativo no nome incorreto; diretórios de outros aplicativos são preservados. A marca Unicode agora é verificada também nos metadados reais do instalador.

O pacote foi recompilado como revisão de empacotamento 2, mantendo o executável e a versão 0.3.0 do aplicativo. O hash acima corresponde ao instalador corrigido; evidências da revisão anterior foram preservadas com data de 19/10/2026. O novo instalador passou em instalação, integridade, primeira execução e desinstalação isolada.

A instalação normal no usuário foi aprovada em 20/10/2026: registro da versão 0.3.0, atalhos na área de trabalho e em `Gestão Cultural Pro` no menu Iniciar, destino dos atalhos e remoção do atalho legado. A cópia instalada passou em conversões, separação, preferências, cancelamento, legendas próprias pt/en e download real de vídeo/áudio do YouTube aberto do Blender. O programa foi deixado instalado e aberto; os testes usaram um estado separado do histórico pessoal. Evidências com prefixo `user-` em `docs/evidence/windows-v03/`.
