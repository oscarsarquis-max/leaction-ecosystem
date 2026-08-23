# Acessibilidade — direção aprovada

Herdado do laboratório UX-001 e confirmado na combinação:

- contraste AA do par bege/grafite (≈ 10:1);
- `:focus-visible` 3 px `--foco`;
- skip link “Ir para o conteúdo”;
- teclado: Tab, Enter, Escape fecha menu e gaveta;
- `aria-expanded`, `aria-current`, `role="dialog"`, `role="status"`, `role="alert"`, `caption`;
- estado em texto e ponto do badge, não só cor;
- alvos ≥ 40 px;
- `prefers-reduced-motion`;
- menus por clique, nunca só hover;
- leitor de tela: título da gaveta, etapa `aria-current="step"`, progresso com `aria-valuenow`.

Validação: inspeção manual da direção aprovada e capturas UX-002. Sem suíte nova no frontend produtivo.
