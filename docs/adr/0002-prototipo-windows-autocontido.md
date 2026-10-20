# ADR 0002 — Executável experimental Windows para teste local

Data: 19/10/2026. Estado: escolha provisória e reversível, autorizada pela solicitação de um .exe para testar e pela instrução para prosseguir.

A primeira POC já registrou falha da exportação ONNX direta e execução CPU com pesos oficiais; os testes musicais permanecem incompletos. Rust e toolchain nativo não estavam disponíveis. Para produzir um executável funcional de teste sem consolidar arquitetura final, implementar uma interface nativa Python/Tk, empacotada com PyInstaller, Python, Torch CPU, modelo e FFmpeg/ffprobe LGPL compartilhados.

Este protótipo não aprova qualidade musical, redistribuição pública do modelo ou compatibilidade com máquinas limpas. Não substitui o plano Tauri multiplataforma. Não incorpora DRM, paywall ou fonte Spotify. Downloads online, player A/B e fila múltipla ainda não fazem parte desta build.

Tarefas são executadas em processo filho, sob Job Object Windows com kill-on-close. Progresso deriva de FFmpeg e segmentos realmente concluídos do modelo. Stems usam ganho conjunto explícito para evitar clipping. Saídas são verificadas com ffprobe e publicadas numa subpasta única após conclusão; temporários são removidos em sucesso, erro ou cancelamento supervisionado.

Avaliar o resultado do teste antes de migrar esta UI, adotar Qt ou integrar o motor ao Tauri. Nenhuma assinatura, publicação, cobrança ou instalação de ferramentas de sistema foi realizada.
