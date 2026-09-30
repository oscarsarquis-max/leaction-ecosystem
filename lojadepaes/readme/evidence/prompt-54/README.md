# Prompt 54 — evidência isolada

Jornada Playwright em `:5085` com API/banco de teste. Não é produção. Nenhum pedido de teste foi criado no site publicado.

| Arquivo | O que mostra |
|---|---|
| `shelf-1440.png` / `768` / `390` / `320` | Vitrine com resumo comercial preservado e um único bloco de ingredientes expandido |
| `detail-1440.png` / `768` / `390` / `320` | Detalhe do pão com a lista de ingredientes uma vez |
| `review-1440.png` / `768` / `390` / `320` | Revisão `/pedido/novo`: quantidade 2, stepper, calendário, identificação e ações com margem |
| `order-1440.png` / `768` / `390` / `320` | Pedido persistido no ambiente isolado: `1 un.`, sem campo de quantidade, total inalterado após mutar o carrinho local |

Na revisão isolada: 1→2→1, digitação direta, recálculo com atraso, falha de cotação mantém dados, crédito de uma unidade em linha de 2, recarga mantém quantidade 2 e adaptação. Pedido persistido não virou carrinho editável.

Produção publicada: `lojadepaes:prod-20260929k`, bundle `/assets/index-CawDosg6.js`. Rollback de app: `prod-20260929j`. Alembic permanece `b3f7a1c82e09`. Sessão isolada no site, sem apagar o carrinho do proprietário, sem enviar pedido, Pix ou e-mail.

| Arquivo | Site publicado |
|---|---|
| `prod-shelf-1440.png` / `768` / `390` / `320` | Pão de Café com um único bloco de ingredientes expandido |
| `prod-detail-1440.png` / `768` / `390` / `320` | Detalhe do mesmo pão, lista única |
| `prod-review-1440.png` / `768` / `390` / `320` | Revisão desta sessão: quantidade 2, R$ 140,00, stepper e formulário com margem; envio não clicado |

## Causas

1. **Ingredientes duas vezes:** o `<details>` expandido mantinha o preview no summary e a lista completa no corpo. Não era duplicação de API nem texto cadastrado em dobro.
2. **Margens da revisão:** `main.checkout-page` herdava `main { padding: 0 40px }` e depois `.checkout-page { padding: 32px 0 }`, zerando as laterais e estreitando em 720 px.
3. **Quantidade “não editável”:** havia um input numérico estreito que forçava vazio para 1 (`|| 1`), sem stepper acessível e sem recálculo com sequência de cotação.
