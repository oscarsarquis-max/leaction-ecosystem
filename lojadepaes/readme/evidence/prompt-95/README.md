# Prompt 95 — lacunas de prontidão (09/10/2026)

Prioridade: restaurar `/loja` e Ver planos. Sem cobrança, assinatura, cancelamento ou e-mail reais. Pay de pão, marketplace e Spider não foram tocados. Loja permanece `prod-20261008g`.

## Causa da tela “This page couldn’t load”

Não foi crash do Chrome, falha de headless, query string nem indisponibilidade do servidor.

1. HTML de `/loja` e da URL com `return_origin` / `return_to` já respondia 200.
2. O JS da página chamava `resolveClientBrand('lojadepaes')` e lia `brand.colors`.
3. Em produção o módulo de branding publicado pelo 91G **não** continha `LOJADEPAES_BRAND`. O resolver devolvia `null`.
4. Erro de execução: `Cannot read properties of null (reading 'colors')`.
5. O Chrome (visível e automatizado) caía na UI genérica. Home do Hub e `/ecossistema` renderizavam.

Pré-correção: `diagnose-loja.json` + `captures/diag-loja-bare.png` / `diag-loja-params.png`. Mesma falha nas duas URLs.

## Correção publicada (Hub FE apenas)

`lojaBrand()` usa o brand canônico se o resolver vier vazio. `return_origin` passou a allowlist (`https://lojadepaes.com.br` e localhost de dev); origem estranha cai no default, sem redirecionamento aberto. Middleware e `SiteHeader` isentam `/loja`. Pack avulso deixa de herdar rótulo “/mês”.

- BUILD_ID servido: `ODrRI9FZL2AwRMNrQtqEx`
- Backup Hub: `leaction_hub_20261009T102421Z` + arquivos `p95-20261009T102421Z`
- Gateway, marketplace e imagem Loja: inalterados
- Teste de retorno: `loja-return.test.mjs` — 2 passaram

## Jornada pública após o deploy

Chrome (canal real) desktop 1440 e celular 390. Sem spinner permanente, sem crash UI, sem erro de página.

| Passo | URL | Resultado |
|---|---|---|
| Home Loja | https://lojadepaes.com.br/ | Visitante vê Identifique-se |
| Biblioteca | https://lojadepaes.com.br/biblioteca/o-comeco | Artigo aberto; Ver planos aponta para a URL exata do proprietário |
| Ver planos | `https://actionhub.com.br/loja?return_origin=https%3A%2F%2Flojadepaes.com.br&return_to=%2F%23biblioteca` | Assinatura R$ 19,00/mês e pacote R$ 10,00 avulso |
| `/loja` sem parâmetros | https://actionhub.com.br/loja | Mesmos dois cartões |
| Celular | mesma URL com parâmetros | Mesmos dois cartões |
| Próximo passo mensal | `/loja/contratar?sku=LOJADEPAES_BIBLIOTECA_MENSAL&…` | E-mail + Contratar assinatura mensal. Sem submit |
| Próximo passo avulso | `/loja/contratar?sku=LOJADEPAES_BIBLIOTECA_CREDITOS&…` | E-mail + Comprar pacote avulso. Sem submit |

Capturas: `captures/prod-home-1440.png`, `prod-article-1440.png`, `prod-hub-loja-from-ver-planos-1440.png`, `prod-hub-loja-params-1440.png`, `prod-hub-loja-bare-1440.png`, `prod-hub-loja-params-390.png`, `prod-hub-contratar-assinatura-1440.png`, `prod-hub-contratar-avulso-1440.png`. Relatórios: `verify-journey.json`, `verify-contratar.json`.

A webfont às vezes cola letras na foto; o DOM e as APIs têm espaços. Catálogo ao vivo: mensal `plan` R$ 19 / 20 créditos / 10%; pack `credit_pack` R$ 10 / 10 créditos, sem desconto.

## Fronteira financeira — não verificada no provedor

Documentação oficial do Mercado Pago (2026): teste de checkout/assinatura exige credenciais de **Testing → Test credentials** (`TEST-…`) e contas/cartões de teste. Token `APP_USR` não é sandbox.

| Ambiente | Modo observado | O que isso implica |
|---|---|---|
| Produção `GET /hub-api/config/payments` | `sandbox_mode=false`, `allow_payment_simulation=false`, par `APP_USR` | Qualquer checkout aqui cobra de verdade |
| Gateway local `.env` | mesmo par `APP_USR` | Não é modo de teste oficial |
| FE local `.env.local` | só public key `TEST-` | Sem Access Token `TEST-` correspondente |

Não há Access Token `TEST-` disponível nesta estação. Não foi usado `fulfillOrderPayment` como substituto desta fronteira. Não foi criado checkout, tokenização, autorização, assinatura no provedor, renovação nem webhook do MP.

A cadeia interna 94A (Hub local `:5433`, contrato do Hub) continua válida só para ledger/outbox/créditos. UI interceptada 94A continua válida só para apresentação de estados.

## Versões

| Peça | Versão |
|---|---|
| Loja | `lojadepaes:prod-20261008g` — sem republicação |
| Alembic Loja | `c6d9e4f13a27` |
| Hub FE | BUILD_ID `ODrRI9FZL2AwRMNrQtqEx` |
| Hub / gateway health | 200, `git_sha` `49b2a83` |
| Spider | sandbox, intocado |
| Pay físico | intocado |

## Pendências reais

1. **Mercado Pago oficial não exercitado.** Falta par `TEST-` + conta/cartão de teste para checkout de assinatura e compra avulsa sem dinheiro real. Enquanto isso, tokenização, autorização, evento do provedor, concessão a partir do pagamento confirmado e débito pós-consulta **não** estão comprovados ponta a ponta.
2. Logo `/brands/lojadepaes.png` — corrigido no Adendo 95A (`RcbKeSmRZ78ehM6EjRi82`).
3. Não pronto como entrega financeira completa. A página e o caminho Ver planos voltaram a funcionar hoje.

## O que não foi feito

Cobrança, contratação, cancelamento, concessão manual ou e-mail em produção. Sem dump. Sem mudança de infraestrutura global. Sem reabrir arquitetura.
