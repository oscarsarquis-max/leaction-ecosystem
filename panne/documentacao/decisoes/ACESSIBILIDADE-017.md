# Acessibilidade — CURSOR-017

Validado nos testes de UI e no shell:

- foco visível, teclado nas linhas da tabela e nos submenus
- labels nos filtros e formulários; erros em `role="alert"`
- marca no link do cabeçalho (`aria-label="Panne"`); imagens decorativas com `alt` vazio
- estado além da cor (texto do badge + tom)
- alvos de toque no cromado; menu compacto em largura reduzida
- `prefers-reduced-motion` já no CSS de tokens
- nenhuma ação exclusiva por hover
- contraste AA bege/grafite ≈ 10:1 na marca aprovada
- desktop, notebook, tablet horizontal e vertical via tokens e evidências de login
