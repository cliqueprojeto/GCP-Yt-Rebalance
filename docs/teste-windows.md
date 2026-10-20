# GCP Yt Rebalance — teste experimental no Windows

Desenvolvido por Bruno Albertini — [Gestão Cultural Pro](https://gestaoculturalpro.com.br).

Esta etapa entregou um executável portátil Windows x64, versão 0.1.0 experimental: 382.050.035 bytes (364,35 MiB). É um protótipo funcional para teste local; não é o instalador multiplataforma final do projeto. Os resultados do binário empacotado estão em `docs/evidence/windows-executable.json`.

SHA-256: `af0836641bcc14a11c858cb2a82df49510d5f8ca95c1ce662c3de14de76ae135`.

Teste do `.exe` real aprovado neste Windows com PATH restrito a System32 e sem PYTHONPATH/PYTHONHOME/VIRTUAL_ENV: construção das sete telas, integridade do modelo, importação das bibliotecas, FFmpeg/ffprobe embarcados, WAV16, PCM24 a 48 kHz, FLAC24, MP3 192 kbps, vídeo MP4 para WAV24 a 48 kHz, quatro stems WAV24 e cancelamento do worker. O Job Object também encerrou um pai e seu descendente em teste específico. Sete testes unitários passaram. Os sinais e o vídeo de teste foram gerados localmente e não contêm voz.

Na execução fria de cada worker independente do teste, os tempos totais incluíram extração/inicialização: conversões de sinal de 0,4s levaram aproximadamente 21–33s e a separação 58,84s. Não extrapolar para músicas completas. Uma medição durante inferência encontrou 851.332.182 bytes na pasta de componentes extraídos; isto é espaço temporário observado, não tamanho de instalação. Reserve espaço adicional para temporários e resultados de áudio.

Correções durante a verificação: os testes passaram a usar temporários dentro do workspace porque o TEMP do sandbox negava gravações; o teste de cancelamento passou a verificar encerramento e ausência de resultado, pois o fechamento de um Job Object pode encerrar o processo com código 0. Não se usa esse código como indicador de sucesso de cancelamento.

## Como testar

1. Abra `dist/windows/GCP Yt Rebalance.exe`. A primeira abertura extrai os componentes embarcados para uma pasta temporária e pode demorar.
2. Selecione um arquivo local de áudio ou vídeo e a pasta de saída.
3. Escolha remover vocais, isolar voz, voz + instrumental, quatro stems ou somente converter.
4. Escolha WAV, PCM, FLAC ou MP3. WAV/PCM oferecem inteiros de 16, 24 e 32 bits. FLAC permite 16/24 bits. PCM é estéreo, little-endian e inclui JSON com todos os parâmetros. MP3 usa o bitrate selecionado e tem perdas.
5. Clique em **Processar arquivo**. A separação usa CPU e pode levar mais tempo que a duração da faixa. O progresso da separação avança quando um segmento termina, sem estimar trabalho não realizado.
6. Ao concluir, use **Abrir resultado**. Cada execução cria uma subpasta própria e inclui `relatorio.json`, hashes, parâmetros e o ganho conjunto aplicado aos stems, quando necessário.
7. **Cancelar** encerra o processo de trabalho e seus descendentes; a interface remove temporários e resultados parciais. Resultados já concluídos são preservados.

Não é necessário instalar Python, PyTorch, modelo ou FFmpeg separadamente para este executável. O pacote usa os próprios componentes. Essa propriedade é verificada também com PATH isolado, mas isso não substitui testes em uma VM limpa.

Limites: uma tarefa por vez, até 10 GiB de entrada, até 30 minutos de duração, CPU com 1/2/4/8 threads, exportação estéreo a 44,1 ou 48 kHz. Os limites são guardas experimentais; memória e velocidade em músicas longas ainda precisam ser medidas. Comece com um trecho curto autorizado. Fonte inválida, modelo ausente e falta de disco produzem erro sem publicar uma saída parcial.

## O que ainda não está nesta build

Downloads por URL/YouTube, player A/B integrado, arrastar e soltar, fila de múltiplos arquivos, recuperação após queda de energia e seleção de stems individuais. A tela Downloads informa a indisponibilidade. Não há mecanismos de remoção de DRM, bypass de paywall ou extração de músicas protegidas do Spotify.

A qualidade musical do motor ainda não foi aprovada na matriz dos três perfis. Os testes automáticos usam sinal próprio, sem voz; comprovam execução e formatos, não qualidade de karaokê. macOS/Linux, GPU e versões mínimas de Windows ainda não estão certificados.

## Dados e rede

Processamento local. Não há telemetria, IA em nuvem, cadastro ou download de modelos durante o uso. O botão da marca abre apenas https://gestaoculturalpro.com.br no navegador padrão. Preferência de pasta e histórico com nome de arquivo, data e status ficam em `%LOCALAPPDATA%/GestaoCulturalPro/GCPYtRebalance`; o histórico pode ser apagado na interface.

## Reprodução do build

Executar no ambiente de desenvolvimento isolado com as dependências fixadas no lock Windows:

```powershell
.venv-poc/Scripts/python.exe scripts/prepare_windows_package.py
.venv-poc/Scripts/python.exe -m PyInstaller --noconfirm --distpath dist/windows --workpath build/windows apps/desktop/windows.spec
.venv-poc/Scripts/python.exe scripts/smoke_windows.py --exe 'dist/windows/GCP Yt Rebalance.exe' --separation --out artifacts/windows-exe-smoke
```

Os recursos externos de build incluem pesos safetensors oficiais e build FFmpeg/ffprobe BtbN LGPL. O pacote contém avisos e inventário em `vendor/notices`. SHA-256 dos pesos e do arquivo FFmpeg estão registrados. A release pública depende de auditoria completa das licenças, fontes correspondentes de FFmpeg/dependências, licença própria e autorização do titular.

O executável experimental não tem assinatura digital. Não confundir teste nesta máquina com certificação em máquinas limpas ou entrega de instaladores finais. Não houve publicação em loja, site ou repositório remoto.
