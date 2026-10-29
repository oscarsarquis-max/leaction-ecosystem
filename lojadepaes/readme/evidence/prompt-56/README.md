# Prompt 56 / 56B — evidência do Gigio

## Local (gateway fake)

Roteiro Playwright em `:5086` com SPA de `frontend/dist`. Não é o site publicado.

| Arquivo | O que mostra |
|---|---|
| `fechado-1440/768/390/320.png` | Acionador «Conversar com Gigio» |
| `aberto-1440/768/390/320.png` | Painel com avatar, título Gigio e subtítulo |
| `checkout-390.png` | Acionador na revisão sem cobrir o rodapé |

## Bedrock real

`live-bedrock.md` — duas chamadas `invoke_model` no contrato do Chamelleon (região `us-east-1`, inference profile Sonnet 4). Sem dados de cliente, SES, pedido ou Pix.

## Produção

Publicado `lojadepaes:prod-20261001a`, bundle `/assets/index-ZkR9G8Kr.js`. Rollback de app: `prod-20260929k`. Alembic `c8e2f1a90b64`.

| Arquivo | O que mostra |
|---|---|
| `prod-home-1440-fechado.png` / `aberto.png` | Vitrine desktop com acionador e painel |
| `prod-home-390-fechado.png` / `aberto.png` | Celular |
| `prod-checkout-390.png` | Revisão com pão na seleção; «Enviar pedido» visível, sem sobreposição |

O avatar entra no bundle (`dist/assets/avatar_gigio-*.png`). A pasta `frontend/images/logos` não é publicada inteira.
