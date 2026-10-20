# Fase 1 — protocolo de viabilidade

Estado: investigação em andamento. Não há recomendação final de runtime nem validação de qualidade musical. A sonda de exportação usa arquitetura padrão HTDemucs e pesos aleatórios, sem rede; seu sucesso não comprovaria qualidade nem paridade com pesos treinados.

## Matriz de decisão inicial

| Critério | A: HTDemucs + ONNX Runtime CPU | B: Demucs/PyTorch CPU autocontido | C: Open-Unmix/umxhq local |
|---|---|---|---|
| Fidelidade, bleed e artefatos | Não medidos | Referência candidata, não medida | Baseline alternativo, não medido |
| RAM e tempo de música 3–5 min | Não medidos | Não medidos | Não medidos |
| Intel/AMD Windows | Validar exportador + kernels | Validar wheel e distribuição | Validar runtime e pesos |
| Apple Silicon | Runner ARM64 pendente | Runner ARM64 pendente | Runner ARM64 pendente |
| macOS Intel | Validar ORT e opset no alvo | PyTorch <2.3 segundo upstream; ambiente específico | Verificar combinação antiga compatível |
| Linux | glibc, WebKit e kernels pendentes | Dependências nativas pendentes | Dependências nativas pendentes |
| Instalação e manutenção | Sem Python no produto se paridade aprovada; conversão própria a manter | Empacotar Python, bibliotecas e pesos; maior superfície de dependências | Runtime Python e reconstrução espectral próprios |
| Licenças | Runtime/modelo/exportação auditados separadamente | Código MIT; registrar evidência específica dos pesos | Código MIT; `umxl` tem pesos NC e fica fora da seleção comercial |
| Tamanho comprimido/instalado | Não medido | Não medido | Não medido |
| Resultado desta etapa | Exportação direta legacy falhou em STFT complexo | Executou sinal sintético com pesos oficiais; qualidade não aprovada | Não executado |

Não transportar métricas publicadas pelos autores para este hardware. A meta de 400–600 MB é hipótese. O tamanho do cache de desenvolvimento também não representa um instalador.

## Experimento e tolerâncias propostas

1. Fixar versões e hashes. Primeiro ambiente diagnóstico: Python 3.12, Demucs 4.1.0, Torch 2.2.2 CPU, NumPy 1.26.4, ONNX 1.17.0, ORT 1.20.1. Torch antigo é baseline exploratório com possibilidade de macOS Intel; não é decisão final de produção. Se falhar, testar exportador atual em ambiente separado e documentar a diferença.
2. Sonda do `forward` sem pesos treinados: entrada estéreo com duração do segmento do modelo, exportação opset 17, checker ONNX, inferência exclusivamente CPU. Falha deve salvar exceção/etapa, não concluir inviabilidade de toda a abordagem ONNX.
3. Adquirir pesos oficiais explicitamente; registrar origem, revisão, SHA-256, licença e tamanho. Preferir safetensors. Não abrir checkpoint pickle arbitrário; a procedência deve ser verificada antes da desserialização.
4. Comparar referências usando o mesmo resampling, normalização, padding, ordem de fontes, segmento, overlap e shifts fixados. Testar silêncio, impulso, varredura, mono convertido para estéreo, último segmento incompleto e fronteiras. Validar STFT/iSTFT com teste de ida/volta antes de uma reimplementação.
5. Pré/pós-processamento: erro máximo <=1e-5 e SNR >=80 dB onde a energia permitir. Saídas completas: mesmo número de amostras, canais e sample rate; valores finitos; sem ganho/atraso oculto. Proposta de paridade: SNR >=60 dB por stem e degradação de SI-SDR <=0,1 dB versus referência, somente se houver stems de verdade. Silêncio usa erro absoluto. Tolerâncias precisam de revisão após dados reais.
6. Música: três perfis previstos pelo solicitante. Selecionar fontes CC BY quando possível; registrar atribuição e alterações. Metadados sugerem perfis, mas confirmar mixagem e reverberação por audição. Sem stems de verdade não alegar SDR de separação: comparar implementações e revisar A/B por trechos. Sem áudio 3–5 minutos não extrapolar benchmark de 7 segundos.
7. Medir tempo de parede, tempo CPU, pico de memória da árvore, versão/hardware/threads, duração real, pico/clipping, hashes e tamanho de cada saída. Execução fria e três quentes, arquivo completo e passagem por vários segmentos. Aplicar timeout e cancelamento supervisionado.
8. Exportar voz e soma bateria+baixo+outros, sem normalizar stems individualmente; validar WAV/PCM/FLAC/MP3 com ffprobe e redecodificação. Descrever qualquer redução conjunta de ganho para evitar clipping. PCM bruto deve ter parâmetros externos explícitos.

## Fontes oficiais consultadas em 19/10/2026

- [Demucs mantido pelo autor](https://github.com/adefossez/demucs): v4.1.0, arquitetura híbrida, quatro fontes e limite de segmentação; suporte Intel Mac exige versões antigas de Torch.
- [Dependências e restrições por plataforma](https://github.com/adefossez/demucs/blob/main/pyproject.toml).
- [Licença do código Demucs](https://github.com/adefossez/demucs/blob/main/LICENSE): MIT. Não substituir auditoria do artefato de pesos por licença de um arquivo de código.
- [Esquemas de operadores ONNX](https://github.com/onnx/onnx/blob/main/docs/Operators.md) e [kernels ORT](https://github.com/microsoft/onnxruntime/blob/main/docs/OperatorKernels.md): conferir operador, opset, tipo e provider do grafo produzido, não apenas existência de STFT na especificação.
- [Open-Unmix](https://sigsep.github.io/open-unmix/): implementação de referência local; licença de código e pesos não se confundem. Pesos `umxl` são CC BY-NC-SA 4.0.
- [FFmpeg](https://ffmpeg.org/legal.html): termos variam com componentes e build; guardar configure flags, fonte correspondente e avisos.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp): conferir licença do executável, dependências e suporte EJS/JavaScript; empacotamento não pode supor apenas um binário isolado.
- [Distribuição Tauri](https://v2.tauri.app/distribute/): formatos nativos e assinatura/notarização.

## Gate da próxima fase

Sem fechar recomendação do motor com evidências musicais e licença de pesos, não iniciar integração extensa do desktop. Se exportação direta falhar, avaliar STFT/iSTFT externos ou exportação espectral com paridade do pipeline completo; alternativa é B, condicionada ao tamanho/empacotamento. C só é fallback aprovado após experimentar, nunca substituir qualidade por presunção.
