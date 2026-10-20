# GCP Yt Rebalance — builds nativos e downloads

Estado revisto em 20/10/2026: o instalador Windows 0.3 foi instalado e testado. O repositório privado [cliqueprojeto/GCP-Yt-Rebalance](https://github.com/cliqueprojeto/GCP-Yt-Rebalance) foi criado com autorização do titular. O primeiro ciclo nativo é a [execução 39408624618](https://github.com/cliqueprojeto/GCP-Yt-Rebalance/actions/runs/39408624618). O DMG ARM64 foi gerado e passou nos testes do runner macOS 15.7.9 ARM64, incluindo montagem, cópia e primeira execução; Intel está em andamento. Linux apresentou ausência de `PIL._tkinter_finder` na primeira execução e exige novo build com esse módulo incluído. Não há WSL/Linux local nem Mac disponível nesta sessão.

## Ativação

1. Criar um repositório GitHub **privado** e colocar o projeto nele, incluindo `.github/workflows/desktop-installers.yml`. O pipeline atual exige repositório privado porque a redistribuição pública dos pesos e do produto ainda não foi aprovada. Isso segue os gates de distribuição do projeto, não uma necessidade técnica do GitHub.
2. Abrir Actions → **Instaladores internos — GCP Yt Rebalance** → Run workflow. O fluxo é somente manual; não agenda execuções nem publica GitHub Releases. A opção YouTube é desativada por padrão, para não confundir indisponibilidade da fonte com falha do build offline.
3. Acompanhar cada job. Só após sucesso, baixar o arquivo em **Artifacts**: `windows-x64`, `macos-intel`, `macos-apple-silicon` ou `linux-amd64`. Os artefatos ficam por sete dias. Cada pacote inclui checksum e evidências.
4. Qualquer falha impede marcar o respectivo instalador como validado. Analisar os diagnósticos, corrigir no SO correspondente e executar novamente. Não publicar os artefatos como release final sem os aceites abaixo.

Os minutos/runners são administrados na própria conta GitHub. O titular autorizou o envio privado e a execução dos builds, incluindo o consumo dos runners. Nenhum outro repositório foi alterado.

Por padrão o fluxo executa somente Mac Intel, Mac ARM64 e Linux; `target` permite repetir apenas um alvo corrigido e `include_windows` permite incluir o Windows se necessário. Consumo além da franquia pode ser cobrado, conforme a [documentação de cobrança do Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions). Nenhum valor ou limite de gastos foi alterado automaticamente.

A autorização do escopo `workflow` foi concluída pelo titular no fluxo normal do GitHub. Não fornecer senhas, tokens ou códigos de recuperação no chat. Referência: [escopos OAuth oficiais](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps).

Pacote revisável de fontes: `dist/GCP Yt Rebalance - Fontes para build Mac Linux.zip`, gerado por `scripts/export_build_sources.py`, com manifesto interno e checksum SHA-256. **É fonte para build, não é instalador.** Exclui arquivos de áudio, histórico, credenciais, caches e os pesos; estes últimos são obtidos e verificados explicitamente no build. O programa final inclui os pesos e não os baixa na primeira execução.

## Matriz configurada, ainda pendente de execução

| Alvo | Runner de build | Arquivo previsto | Teste configurado |
|---|---|---|---|
| Windows x64 | windows-2022 | `GCP Yt Rebalance Setup 0.3.0.exe` | Instalação em pasta isolada, hashes, primeira execução e desinstalação |
| macOS Intel | macos-15-intel | `GCP Yt Rebalance-0.3.0-macOS-x86_64.dmg` | Montagem do DMG, cópia do .app e primeira execução |
| macOS Apple Silicon | macos-15, Python arm64 | `GCP Yt Rebalance-0.3.0-macOS-arm64.dmg` | Build arm64 separado, montagem, cópia e primeira execução |
| Linux x86_64 | Ubuntu 22.04 | `gcp-yt-rebalance_0.3.0_amd64.deb` | Instalação/remoção no host e instalação em containers Ubuntu 22.04/24.04, Debian 12/13 |
| Linux Mint 21/22 | VM/máquina nativa ainda necessária | Mesmo DEB candidato | **Pendente; não há runner Mint configurado nem teste executado** |

Os nomes dos runners Intel/ARM seguem a [documentação oficial do GitHub](https://docs.github.com/en/actions/reference/runners/github-hosted-runners). A escolha de runner não comprova compatibilidade com todos os Macs nem define uma versão mínima de sistema já suportada. M1 exige validar também o aplicativo em hardware real; não se promete compatibilidade apenas pela arquitetura arm64.

## Componentes incluídos e integridade

O script `scripts/prepare_ci.py` é exclusivo de build. Adquire o modelo fixado por SHA-256, yt-dlp 2026.08.19 e Node 25.6.1 próprios de cada plataforma. URLs e hashes estão em `scripts/native-sources.lock.json`. O produto instalado usa caminhos internos e não executa esse script nem baixa modelos.

Windows utiliza o FFmpeg LGPL BtbN da release datada 19/10/2026, com checksum fixado, e NSIS 3.12. Nos runners Mac/Linux, FFmpeg 8.0.1 e LAME 3.100 são compilados nativamente de fontes com hashes fixados. A configuração desativa autodetecção de bibliotecas opcionais e produz ffmpeg/ffprobe com libmp3lame estática; fontes, licenças e comandos acompanham o pacote. O build efetivo deve confirmar codecs e licenças pela saída real das ferramentas, conforme as [orientações do FFmpeg](https://ffmpeg.org/legal.html).

PyTorch 2.2.2 CPU, NumPy 1.26.4 e demais dependências utilizadas têm versões explícitas em `requirements-desktop-native.txt`. Não se instala torchaudio/CUDA ou a CLI completa de treinamento do Demucs. A aplicação usa somente o caminho de inferência validado. A aquisição registra nomes, tamanhos e hashes dos wheels resolvidos por arquitetura e o ambiente Python em `artifacts/ci/`. As ações oficiais do workflow estão fixadas por SHA de commit.

Os builds de runner ainda podem variar com compilador, SDK e imagem do SO. O manifesto por build é evidência; não constitui promessa de reprodução bit a bit. Antes da release, arquivar também as ferramentas/imagens e validar repetição dos builds. A lista mínima real de bibliotecas sistêmicas do DEB depende do primeiro `ldd`/teste nativo; o `Depends` atual é candidato e será validado pelos jobs.

Na revisão de 20/10 foram acrescentadas validações dos cabeçalhos ELF/Mach-O para impedir troca de arquiteturas entre binários principais e sidecars. O pacote exige modelo com hash correto, ferramentas presentes/executáveis e symlinks internos. Um manifesto de todos os arquivos é comparado após a cópia do DMG e após instalação do DEB. Os containers conferem SHA-256 antes de executar. O diretório raiz do DEB usa permissão 0755. O cancelamento no teste POSIX considera processos zumbis como encerrados, sem aceitar um descendente ainda em execução.

Validação local desta preparação: 20 testes unitários aprovados, sintaxe Python e YAML conferidas. Os testes de cabeçalhos usam fixtures sintéticas, sem fingir execução Mac/Linux. A geração real de pacotes e as primeiras execuções nativas continuam pendentes.

## Verificações e limites

O fluxo executa sete páginas em quatro tamanhos, preferências, reset, erro customizado, conversões, separação CPU, cancelamento e legendas próprias pt/en via downloader real. Os containers Linux verificam abertura instalada, WAV/PCM/FLAC/MP3 e stems com sinal sintético, sem instalar Python, FFmpeg ou modelos à parte. Esses testes só passam a ser evidência após a execução bem-sucedida do workflow.

macOS recebe a assinatura ad hoc necessária ao bundle; não há certificado Developer ID ou notarização configurados. Windows não tem assinatura Authenticode. Não se desativa proteção do sistema. A instalação Mac por DMG é validada por cópia para diretório isolado, sem modificar `/Applications` do runner. Aceite visual no Finder/Dock, quarentena de download e instalação por usuário real continuam necessários.

Pendências antes da distribuição final: primeira execução de todos os jobs; testes em máquinas/VMs limpas, especialmente Linux Mint e Macs Intel/M1; versões mínimas exatas; qualidade/benchmark musical com as três faixas; redistribuição dos pesos; licença do aplicativo; auditoria de todos os componentes; assinaturas/notarização e autorização de publicação. Preparar o pipeline não conclui essas entregas.
