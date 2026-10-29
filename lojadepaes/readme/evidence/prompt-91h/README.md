# Adendo 91H — evidência

08/10/2026. Sem senhas, cobrança, e-mail ou operação financeira real.

## Diagnóstico

| Ambiente | Estado |
|---|---|
| Produção Loja `prod-20261008f` | 91G intacto: catálogo R$ 19/mês + pacote R$ 10 avulso; `plans_href` = https://actionhub.com.br/loja |
| Código local examinado | Loja chamava Hub em catálogo, direitos, assinatura, checkout de planos, cancelamento e créditos |
| Pay de pedidos de pão | fora de escopo; `actionhub_client.py` `/v1/checkout/amount` não foi alterado |

Rotas HTTP autenticadas não comprovam Spider. O corte local removeu o bypass deste fluxo.

## Capacidades criadas (contrato 1.5)

Satélite EXPERIENCE `lojadepaes` · provedor `actionhub-biblioteca` · propósito `LOJA_BIBLIOTECA` · fonte `LOJADEPAES_BIBLIOTECA_V1`.

| Objetivo (Loja) | Capacidade | Destino Hub |
|---|---|---|
| LIST_LOJA_PLANS | LIST_HUB_CATALOG | catálogo público |
| GET_LOJA_ENTITLEMENTS | GET_HUB_ENTITLEMENTS | snapshots de direito |
| LIST_LOJA_SUBSCRIPTIONS | LIST_HUB_SUBSCRIPTIONS | assinaturas |
| START_LOJA_CHECKOUT | START_HUB_CATALOG_CHECKOUT | checkout de catálogo (Hub/MP) |
| CANCEL_LOJA_SUBSCRIPTION | CANCEL_HUB_SUBSCRIPTION | cancelar renovação |
| RESERVE_LOJA_CREDITS | RESERVE_HUB_CREDITS | reserva |
| CONFIRM_LOJA_CREDITS | CONFIRM_HUB_CREDITS | confirmação |
| RELEASE_LOJA_CREDITS | RELEASE_HUB_CREDITS | liberação |

Cadeia: Loja `POST {spider}/v1/satellites/interactions` → Spider `DemoSliceRules` → `POST {hub}/v1/provider/capabilities/{id}/executions`. Recusa entre aplicativos: `appId` só `lojadepaes`; Action Finance recebe 403 neste propósito.

## Provas isoladas

- Spider `LojaBibliotecaSatelliteInteractionHttpTest`: catálogo READY + `LIST_HUB_CATALOG`; app estrangeiro 400; Action Finance 403.
- Hub `spider-biblioteca.test.js`: credencial obrigatória; catálogo pela capacidade.
- Loja `test_prompt91h.py`: `httpx` só contra `/v1/satellites/interactions`; timeout recuperável.
- 10% + resgate: subtotal R$ 140 + crédito de pão R$ 70 + 10% R$ 14 → total R$ 56; linhas separadas. Pacote isolado sem 10%.
- Visitante: rótulo **Identifique-se**, não Sem assinatura.
- Header + Biblioteca frontend: 6 testes.

## Caminhos diretos removidos (código local)

`access.py` e `credits.py` não montam mais `/v1/catalog`, `/v1/entitlements`, `/v1/subscriptions`, `/v1/checkout/catalog` nem `/v1/credits/*`. `plans_href` continua navegação de browser para a página oficial do Hub.

## Produção

A imagem publicada da Loja **ainda é 91G**. Publicar o consumidor novo sem engine Spider + provedor Hub + segredos de satélite derrubaria o catálogo ao vivo. O incremento de produção precisa ser coordenado: Hub (rotas de capacidade) → Spider (1.5 + registro) → Loja `prod-20261008g` com `spider_base_url` e credencial de satélite. Sem fallback Loja–Hub.

## Ainda do proprietário

Validade dos créditos avulsos: sem expiração inventada e sem duração ilimitada anunciada. Base do 10% é o subtotal de catálogo, inclusive linha resgatada; não foi inventado “10% só do restante”.
