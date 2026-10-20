# 0003 — Interface e instalador Windows experimental

Data: 19/10/2026. Escopo: versão 0.2 para teste local.

Evoluir o protótipo Python já funcional com CustomTkinter, mantendo os workers separados da interface. Não declarar isso como implementação Tauri nem consolidar a arquitetura multiplataforma. A migração definitiva permanece condicionada à POC musical e às plataformas alvo.

A interface usa componentes arredondados, ícones geométricos locais, conteúdo rolável e barra inferior fixa. O limite mínimo é 880×600 unidades lógicas do Windows; quebra de texto converte coordenadas físicas para unidades lógicas em telas com DPI ampliado. Animações podem ser desativadas. Créditos continuam fixos no rodapé lateral.

O instalador NSIS inclui o diretório autocontido do PyInstaller, com Python, CPU/PyTorch, modelo, FFmpeg/ffprobe, yt-dlp e Node. O formato onedir evita reextrair centenas de MB a cada abertura. Instalação por usuário, sem exigir administrador, com atalhos e desinstalador. O modo de teste isola a instalação e omite registro/atalhos para não alterar a instalação pessoal existente.

O pacote de teste usa zlib por arquivo. Uma tentativa LZMA solid foi interrompida após mais de oito minutos ainda sem terminar; seu arquivo parcial não é uma entrega nem uma medida de tamanho final. A troca prioriza tempo de iteração sem remover componentes. Tamanho efetivo e hashes são medidos apenas depois da compilação concluída.

Cada tarefa usa subprocesso inscrito em Windows Job Object antes do gate de início. Encerramento mata os descendentes. Sucesso exige evento de conclusão, não apenas código de saída. Exportação passa por diretório temporário exclusivo e rename para destino legível sem sobrescrita. A estimativa é calculada com progresso observado por fase; não é previsão garantida.

As saídas preservam o nome original sanitizado e recebem `_convertido`, `_Voz`, `_Instrumental`, `_Bateria`, `_Baixo` ou `_Outros`. A pasta usa título e operação; colisões recebem numeração. Histórico novo persiste o destino e permite abri-lo; registros antigos sem destino não são inferidos.

Não há publicação autorizada. Assinatura, redistribuição completa dos pesos/componentes, qualidade musical, máquinas limpas e demais sistemas continuam como gates de release.
