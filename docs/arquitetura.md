# Arquitetura proposta — ainda condicionada à Fase 1

Tauri 2 com React/TypeScript/Vite; domínio em Rust. Frontend envia pedidos tipados, não comandos livres. Rust valida seleção de origem/destino, concede acesso restrito, inicia subprocessos por executável absoluto e vetor de argumentos, e publica eventos reais de fase/progresso.

```text
apps/desktop/       UI pt-BR, i18n, Tauri e permissões
crates/core/        contratos, fila e estados
crates/media/       ffprobe, FFmpeg e exportação
crates/download/    URL, formatos disponíveis e yt-dlp
crates/separation/  adaptação de motor aprovado na POC
models/            manifestos de pesos e integridade
scripts/           POC, aquisição explícita, validação, build
tests/fixtures/    manifestos e mídias autorizadas ignoradas
assets/branding/   ícone oficial e derivados
docs/              evidências, ADRs, conformidade, manuais
```

Os diretórios de produto serão implementados após a decisão do motor; nenhum frontend demonstrativo substitui a funcionalidade. Evitar SQLite no início: preferências pequenas e diário de fila em JSON com gravação atômica, migrável por versão. Reavaliar SQLite se a recuperação da fila justificar.

## Fronteiras

Mídia: executáveis embarcados e verificados, protocolos de entrada limitados a arquivos locais; `-nostdin`, sem sobrescrita por padrão; PCM exige sample rate, canais, representação, bits e endianness explícitos, acompanhados de JSON. Vídeo MP4 somente quando codecs/formatos realmente permitirem. MP3 não recupera perdas de compressão.

Download: apenas HTTPS e adaptadores habilitados; rejeitar credenciais na URL e destinos privados/locais, inclusive redirecionamentos quando controláveis. Não oferecer extrator genérico irrestrito. `--ignore-config`, sem plugins externos, cookies ou execução de pós-processadores arbitrários. Spotify não é fonte de músicas integrais. Descobrir formatos antes de exibir resolução; playlist com seleção e limite. EJS/runtime JS precisam entrar no inventário se o suporte YouTube os exigir. Confirmar escopo de uso permitido antes da integração.

Separação: serviço local substituível, manifesto validado antes de iniciar. Nenhum download em tempo de execução. Inicialmente CPU; um trabalho pesado ativo. Cada tarefa usa diretório temporário exclusivo, orçamento de disco e timeout. Cancelamento deve encerrar a árvore: Job Object no Windows e grupo de processos no Unix. Publicar saídas somente após validação; manter resultado anterior e pedir confirmação para sobrescrever. Falhas não devem aparecer como 100% concluído.

Segurança: CSP sem scripts/remotos, ponte Tauri mínima, frontend sem permissão genérica de shell ou HTTP. Player lê apenas arquivos autorizados. Logs por identificador de tarefa, sem URLs completas, tokens ou mídia. Link da marca é constante HTTPS e usa opener nativo restrito. Atualizações assinadas e opt-in ficam para a distribuição.

## Identidade e acessibilidade

Produto: GCP Yt Rebalance. Fabricante: Bruno Albertini. Sidebar e Sobre exibem `Desenvolvido por Bruno Albertini` e link `Gestão Cultural Pro` para https://gestaoculturalpro.com.br, com nome acessível e indicador externo.

Tokens iniciais propostos: fundo #101322, painel #1B2033, texto #F2F3FA, secundário #B7BCCD, primário #7854DE, foco #C6B5FF, espaço base 4px, raio 10px, fonte de sistema. Medir contraste nas combinações efetivamente usadas e testar escalas DPI. Rodapé da sidebar deve continuar visível ao redimensionar.
