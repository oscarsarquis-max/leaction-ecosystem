# Acessibilidade, responsividade e desempenho — CURSOR-024

## Acessibilidade

Contraste AA nos pares oficiais. Foco visível. Gaveta com `role="dialog"`, Escape fecha quando não há comando pendente, foco inicial no fechar. Badges com texto. Tabelas equivalentes às visões do quadro. Alvos de toque em `--panne-alvo`. `prefers-reduced-motion`. Zoom 200% sem perda do centro do login. axe sem violações críticas nos testes de login e quadro.

## Responsividade

Login em três colunas no desktop, centro primeiro no estreito. Shell horizontal sem barra lateral permanente.

## Desempenho

Login interativo não espera editorial. Provider estático sem rede. Imagens de teste são logos oficiais já no repositório. Gaveta do assistente só monta quando aberta. Quadro reutiliza `GET /board` existente; o catálogo de contexto é leitura mínima. Polling existente permanece subordinado a aba visível, formulário limpo e ausência de comando pendente.
