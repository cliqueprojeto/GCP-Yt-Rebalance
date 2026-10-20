# GCP Yt Rebalance 0.2.0 — Windows x64 para teste

Desenvolvido por Bruno Albertini  
[Gestão Cultural Pro](https://gestaoculturalpro.com.br)

Instalador completo: `dist/GCP Yt Rebalance Setup 0.2.0.exe`. Execute e escolha a pasta. Inclui motor CPU, pesos, Python, FFmpeg/ffprobe, yt-dlp e Node; não exige instalar esses componentes manualmente. Não baixa modelos na primeira execução. O pacote ainda não tem assinatura digital.

## Uso

1. Em Downloads, cole a URL e consulte as opções disponíveis. Escolha áudio, vídeo com áudio, remoção vocal ou quatro stems. Resoluções dependem da fonte. Contêiner de vídeo pode ser MKV quando os codecs disponíveis não permitem o MP4 escolhido.
2. Em Separar Áudio, selecione um ou mais arquivos locais, operação, formato e pasta. A fila executa uma tarefa por vez. Outros arquivos podem ser adicionados durante o processamento.
3. Progresso e tempo estimado ficam visíveis no rodapé. A estimativa aparece depois de haver amostras de progresso e se refere à etapa atual. Cancelar encerra também os subprocessos.
4. Em Histórico, clique no nome ou em **Abrir pasta do resultado**. Entradas antigas sem destino registrado mostram essa limitação. Se a pasta tiver sido removida, um diálogo informa o problema.

Para `Minha música.mp3`, os nomes são `Minha música_convertido.wav`, `Minha música_Voz.wav` e `Minha música_Instrumental.wav`, conforme a ação. Os demais stems usam `_Bateria`, `_Baixo` e `_Outros`. A extensão acompanha o formato escolhido. Pastas têm título e operação, com `(2)` etc. se já existirem. Caracteres inválidos no Windows são sanitizados. PCM bruto é inteiro com sinal, little-endian, estéreo; profundidade e taxa selecionadas constam do relatório JSON.

## Mudanças

Interface navy/violeta com bordas, botões com ícones, rolagem, barra de andamento fixa, animações discretas e opção para reduzi-las. Ícone pequeno de alto contraste derivado do conceito visual aprovado; a arte original permanece na barra lateral. Erros e confirmações usam diálogos do tema. Histórico e preferências ficam apenas em `%LOCALAPPDATA%/GestaoCulturalPro/GCPYtRebalance`.

## Validação reproduzível

Host: Windows 11 10.0.26300 AMD64. Executável com PATH limitado a System32 e sem variáveis Python. Isso verifica dependências embarcadas; não equivale a máquina limpa.

```powershell
.venv-poc/Scripts/python.exe -m unittest discover -s tests -v
.venv-poc/Scripts/python.exe -m PyInstaller --noconfirm --distpath dist/v0.2 --workpath build/v0.2 apps/desktop/windows.spec
.venv-poc/Scripts/python.exe scripts/smoke_windows.py --exe "dist/v0.2/GCP Yt Rebalance/GCP Yt Rebalance.exe" --separation --out artifacts/v02-final-offline
.venv-poc/Scripts/python.exe scripts/smoke_downloads.py --exe "dist/v0.2/GCP Yt Rebalance/GCP Yt Rebalance.exe" --youtube --out artifacts/v02-final-youtube
.tools/nsis-3.12/makensis.exe /V2 scripts/windows-installer.nsi
.venv-poc/Scripts/python.exe scripts/smoke_installer.py
```

Os diretórios de saída dos smoke tests devem ser novos em cada execução. Nesta sessão, ferramentas nativas de empacotamento e teste GUI precisaram rodar fora do sandbox: a tentativa de self-test GUI dentro dele excedeu 180 segundos; a execução no host passou. Não foi demonstrada causa exclusiva desse timeout. O ajuste de DPI foi validado separadamente pela geometria dos componentes.

Resultados já observados no binário final: 13 testes unitários; sete páginas em 880×600, 1024×640, 1180×780 e 1440×900; diálogo de erro para URL inválida; conversão real pela fila; roteamento do destino do histórico; WAV16, PCM24/48k, FLAC24, MP3/192k, vídeo local para WAV24/48k; quatro stems e cancelamento do worker e descendente. Estes testes de áudio usam sinal sintético de 0,4 s e não aprovam qualidade musical. O teste de abertura da pasta intercepta `os.startfile` e verifica o caminho encaminhado, sem automatizar o Explorer.

Download real do vídeo aberto **Big Buck Bunny** do canal oficial Blender: vídeo com áudio de 634,601 s e áudio WAV de 634,578 s, sem truncamento relevante. Fonte e atribuição: [Blender Foundation, CC BY 3.0](https://peach.blender.org/about/). O arquivo de teste não integra o instalador. Os quatro modos de download também passaram com mídia sintética própria servida por servidor local de teste explicitamente habilitado; separação musical completa do vídeo YouTube não foi medida.

O instalador real passou: instalação em pasta isolada, SHA-256 dos 2.898 arquivos extraídos, primeira execução instalada, conversão pela fila, roteamento do histórico e desinstalação. O modo de teste não valida atalhos e entradas de registro do fluxo normal. Evidências estruturadas em `docs/evidence/windows-v02/`.

Tamanho do instalador: **365.156.506 bytes (348,24 MiB)**. Soma dos arquivos do payload instalado: **995.300.813 bytes (949,19 MiB)**, sem contar alocação do sistema de arquivos, desinstalador, preferências e espaço dos trabalhos temporários.

SHA-256 do instalador: `5a7f1173e6ddc664ab2d8ad478c6239a289bac790d391012a470030a6031b3cd`. Também disponível em `dist/SHA256SUMS-0.2.0.txt`.

## Pendências de release

Não foram concluídos: qualidade musical com as três faixas autorizadas, benchmark musical de 3–5 minutos, máquina limpa/VM, outros Windows, macOS Intel/ARM64, Linux, player A/B, recuperação persistente da fila, assinatura de código e autorização de redistribuição pública de todos os pesos e componentes. Downloads dependem da disponibilidade e das regras da fonte; conteúdo restrito deve produzir erro. Esta entrega é para teste local, sem publicação final.
