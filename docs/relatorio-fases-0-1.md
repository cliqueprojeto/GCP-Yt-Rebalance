# Marco de 19/10/2026 — GCP Yt Rebalance

Desenvolvido por Bruno Albertini — [Gestão Cultural Pro](https://gestaoculturalpro.com.br).

**Fase 0 entregue. Fase 1 parcial, sem aprovação de motor. Fases 2–6 não iniciadas. Não há instalador nem aplicação desktop pronta.**

## Entregas e alterações

- Git inicializado no diretório fornecido. Original `Ícone_Sistema` preservado.
- `assets/branding/`: cópia PNG oficial, seis PNGs de 16–512 px, ICO e ICNS, prancha de inspeção e manifesto SHA-256. Dez arquivos de imagem no total, incluindo original e prancha. Conferidos hashes, dimensões e abertura dos contêineres. Inspeção da prancha feita; no tamanho 16 px detalhes internos ficam reduzidos. Aprovação visual nativa continua pendente.
- `docs/diagnostico.md`, `arquitetura.md`, `poc.md`, ADR 0001: requisitos, milestones, riscos, matriz A/B/C e gate para integração.
- `scripts/`: scripts executáveis de inventário, aquisição explícita, sonda ONNX, referência CPU offline, exportações, métricas, sinal reproduzível e lock de wheels.
- `tests/test_metrics.py`: quatro testes de paridade numérica, truncamento, valores inválidos e clipping.
- `models/manifest.json`: nenhum modelo aprovado para release; pesos locais ignorados pelo Git.
- `docs/evidence/`: relatórios JSON, hashes e traceback da exportação. `artifacts/`: arquivos efetivos gerados pelos experimentos, ignorados pelo Git.

## Resultados observados

| Experimento | Resultado | Limite da conclusão |
|---|---|---|
| HTDemucs padrão sem treinamento → PyTorch CPU | Forward executado, saída `[1,4,2,441000]` | Arquitetura padrão de 26.899.536 parâmetros; não usa configuração/pesos treinados |
| Mesmo forward → ONNX opset 17 | Falhou: `STFT does not currently support complex types`, SymbolicValueError, 28,37 s totais | Torch 2.2.2+cpu, exportador legacy; ORT não chegou a executar o grafo |
| Pesos oficiais HTDemucs | 84.025.440 bytes, SHA-256 conferido com LFS upstream | Card não declara licença explícita; redistribuição não aprovada |
| Modelo treinado CPU → sinal sintético de 22,05 s | 4 stems + instrumental WAV float, 972.405 frames por arquivo, sem NaN/Inf ou picos acima de full scale | Sem voz real; não mede qualidade, bleed, artefatos ou inteligibilidade |
| Tempo e memória dessa execução | Inferência 104,84 s; total medido 105,84 s; CPU 179,92 s; pico RSS amostrado 1.239.080.960 bytes | 2 threads, segmento 7,8 s, overlap 0,25, shifts 0; uma execução; sem extrapolar para música de 3–5 min |
| Exportação original sintético + stem vocals + instrumental | 12 arquivos reais: WAV float, PCM16 LE com JSON, FLAC24, MP3 192 kbps solicitado | Releitura por libsndfile/NumPy; ffprobe indisponível; não valida todas as opções do futuro produto |
| Duração exportada | WAV, PCM e FLAC preservam frames; MP3 tem +2.187 frames (~49,59 ms) | Padding/atraso do codificador sem compensação gapless; requer tratamento posterior |
| Testes automatizados | 4/4 aprovados; `pip check` sem dependências quebradas; scripts compilam | Não são E2E do produto nem teste de instalador |

A configuração padrão do construtor testada na sonda ONNX difere da configuração dos pesos oficiais (`channels=48`, segmento 7,8 s). Logo, a sonda é evidência de falha do caminho direto exercitado, não prova de inviabilidade de toda exportação do modelo treinado. Relatórios completos: `onnx-probe-01.json`, `reference-synthetic-01.json`, `exports-*-01.json` em `docs/evidence`.

Cache de desenvolvimento: 41 wheels, 264.401.846 bytes comprimidos. Não representa tamanho de pacote do produto. Há um lock Windows x64 CPython 3.12 com SHA-256 de cada wheel. Torch 2.2.2 foi usado como baseline exploratório, sem consolidar versão de produção.

## Aquisição das músicas

O solicitante delegou a seleção. Foram escolhidas fontes que exibem CC BY 3.0: Somebody Help Me (CSoul, Down With Ben, Admiral Bob), Life Story (Numeron, myvanillaworld) e Up 2 Us (Aussens@iter, Mr. Yesterday). As páginas e a API estavam acessíveis, mas cada download retornou HTTP 403. Nenhum áudio dessas três faixas foi obtido. Detalhes em `audio-sources.json`. A classificação de mixagem/reverberação ainda precisa de audição; não é uma constatação do experimento.

Alternativa consultada: [Swansong — Josh Woodward, CC BY 3.0 US](https://commons.wikimedia.org/wiki/File:Josh_Woodward_-_Swansong.ogg). O download original também retornou 403. Não foram usados cookies, proxies ou tentativas de contornar restrições. Nenhum trecho dessas músicas entra nos artefatos entregues.

O sinal próprio gerado por `generate_signal.py` serve somente à validação técnica. As saídas denominadas `vocals` são a previsão do modelo para esse sinal sem voz, não acapellas musicais.

A reprodução do sinal gerou amostras idênticas, verificadas por releitura. A comparação inicial byte a byte falhou porque o WAV float gravado pela biblioteca inclui timestamp no chunk PEAK; por isso hashes identificam cada artefato e a reprodutibilidade de áudio é avaliada nas amostras decodificadas. Resultado em `signal-reproduction.json`.

## Comandos principais executados

```powershell
git init
# Inventário, marca e testes com Python de desenvolvimento do ambiente
python scripts/poc_environment.py
python scripts/branding.py
python -m unittest discover -s tests -v
# Ambiente .venv-poc com wheels adquiridos explicitamente de PyPI/PyTorch CPU
.venv-poc/Scripts/python.exe scripts/acquire_poc.py
.venv-poc/Scripts/python.exe scripts/lock_poc.py
.venv-poc/Scripts/python.exe scripts/poc_onnx.py --out artifacts/onnx-probe-01
.venv-poc/Scripts/python.exe scripts/poc_reference.py --weights models/weights/955717e8.safetensors --input tests/fixtures/audio/synthetic-no-voice.wav --out artifacts/reference-synthetic-01
.venv-poc/Scripts/python.exe scripts/poc_exports.py --input tests/fixtures/audio/synthetic-no-voice.wav --out artifacts/exports-synthetic-01
.venv-poc/Scripts/python.exe scripts/poc_exports.py --input artifacts/reference-synthetic-01/instrumental.wav --out artifacts/exports-instrumental-01
.venv-poc/Scripts/python.exe scripts/poc_exports.py --input artifacts/reference-synthetic-01/vocals.wav --out artifacts/exports-vocals-01
.venv-poc/Scripts/python.exe -m unittest discover -s tests -v
.venv-poc/Scripts/python.exe -m compileall -q scripts tests
```

`python` acima representa o Python de desenvolvimento fornecido pelo ambiente, pois o alias Windows do PATH não era um interpretador utilizável. Os caminhos reais e versões estão no inventário. As pastas de saída dos experimentos devem ser novas para impedir sobrescrita.

Para reproduzir o sinal em novo destino:

```powershell
.venv-poc/Scripts/python.exe scripts/generate_signal.py --out artifacts/new-signal.wav
```

Instalação offline a partir do cache adquirido (executar com um Python de desenvolvimento que tenha pip, sem instalar globalmente):

```powershell
python -m venv --without-pip .venv-poc-new
python -m pip --python .venv-poc-new/Scripts/python.exe install --no-index --find-links .cache/wheels --require-hashes -r scripts/requirements-poc-windows-x64.lock
```

## Pendências e próximo passo

1. Obter três áudios autorizados com acesso efetivo, validar os perfis por audição, comparar resultados e benchmarkar músicas de 3–5 minutos. Procurar outra fonte com licença verificável ou usar cópias locais autorizadas.
2. Investigar exportador ONNX atual em ambiente separado e variante com STFT/iSTFT externo; medir paridade de pipeline completo. Testar Open-Unmix como C; ainda não executado.
3. Instalar ferramentas de mídia de desenvolvimento em diretório isolado e validar com ffprobe as quatro exportações; corrigir padding/gapless de MP3 antes do aceite final.
4. Adicionar supervisão com timeout, cancelamento e limpeza da árvore aos experimentos antes de processar arquivos longos. Os scripts atuais são laboratório, não motor pronto para usuário final.
5. Confirmar licença de redistribuição dos pesos, produzir recomendação final de motor e solicitar revisão de decisão crítica. Só então iniciar Fase 2.
6. Runners e instaladores Windows/macOS Intel/macOS ARM64/Linux, licenças completas, assinatura, testes nativos, telemetria ausente e primeira execução offline seguem sem validação. Nenhuma publicação realizada.

Recomendação provisória: manter B como referência de comparação por já ter executado offline com pesos oficiais; não promovê-lo a motor de produção nem descartar A com base em uma única versão de exportador. A decisão definitiva depende das etapas acima.
