# ADR 0001 — Não consolidar motor antes de evidência

Data: 19/10/2026. Estado: aceito para investigação; escolha de runtime pendente.

A camada de separação terá contrato substituível. Testar primeiro ONNX; preservar PyTorch como referência candidata e Open-Unmix como comparação. Não empacotar modelo convertido como funcional sem validar pré/pós-processamento, duração, segmentação, inferência e licença. Não implementar a UI extensa antes do resultado.

Consequência: separar geração de ícone, pesquisa e scripts de experimento do código de produto. Mudança definitiva de motor ou outra decisão difícil de reverter exige revisão com o solicitante, conforme o prompt mestre.
