# Fase 0 — diagnóstico em 19/10/2026

Diretório auditado: `Ícone`. Antes do trabalho havia somente `Ícone_Sistema` (1.533.415 bytes), sem Git ou código. Repositório Git inicializado neste diretório, sem alterar pastas externas.

Ambiente observado: Windows 11 AMD64, 12 processadores lógicos. Git, Node 25.6.1 e npm 11.9.0 disponíveis. Rust/Cargo, FFmpeg e ffprobe ausentes do PATH. Python 3.12.14 do runtime de desenvolvimento disponível; Torch, Demucs, ONNX Runtime e ONNX inicialmente ausentes. Consulta CIM de RAM/CPU recusada; não inferir RAM disponível. Não há runners nativos macOS/Linux nem certificados configurados.

`venv` criou o ambiente mas falhou em `ensurepip`; a instalação isolada pode ser feita pelo pip externo com `--python`. A primeira tentativa de instalar pip falhou na resolução. Download explícito pelo índice oficial, com acesso de rede autorizado pelo sandbox, funcionou. Não modificar Python global.

## Milestones e critérios de saída

| Fase | Entrega | Critério de saída |
|---|---|---|
| 0 | Inventário, marca, arquitetura, protocolo | Evidências salvas, lacunas explícitas |
| 1 | Comparação A/B/C e relatório do motor | Três casos autorizados, pesos identificados, métricas reais, decisão registrada |
| 2 | Desktop local Tauri | Importar, separar, converter, cancelar; sem rede |
| 3 | Download autorizado | Quatro modos YouTube com formatos reais; restrições respeitadas |
| 4 | Fila, A/B, histórico e preferências | Responsividade, teclado e recuperação validados |
| 5 | Instaladores completos por arquitetura | Artefatos reais e teste em máquinas limpas |
| 6 | Release candidata | E2E, SBOM, avisos, hashes, assinatura disponível; publicação autorizada |

Fases 2–6 ainda não executadas. O alvo mínimo de SO, licença própria, uso comercial, sites suportados, atualização e assinatura ficam pendentes antes da distribuição. Nenhuma despesa ou publicação autorizada por inferência.

## Pressupostos e riscos

- CPU primeiro; uma tarefa pesada por vez. Limites definitivos dependem das medições.
- Não usar pasta do projeto como histórico de mídia pessoal. Áudios de teste e pesos ficam ignorados no Git.
- Não habilitar GPU, piano ou guitarra sem validação individual.
- Node presente serve ao desenvolvimento; é preciso escolher uma versão LTS validada para CI.
- GCPShot não foi fornecido como captura. Seguir inicialmente apenas o guia textual navy/violeta; não afirmar correspondência visual com captura inexistente.
- Distribuição multiplataforma exige runners, teste nativo, licenças e binários completos; scripts não equivalem a instaladores.

Comandos e resultados estruturados: `docs/evidence/environment.json`, `docs/evidence/` e relatório final desta etapa. Arte original preservada e checksums em `assets/branding/manifest.json`.
