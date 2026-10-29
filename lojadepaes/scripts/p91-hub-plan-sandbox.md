# Planos da Biblioteca — ActionHub (Adendo 91B)

Não criar plano local na Loja. Configurar no editor existente: `/dashboard/admin/plans?app_id=lojadepaes`.
Não criar, assinar nem cobrar estes planos em produção para prova.

## Principal

| Campo | Valor |
|---|---|
| App | `lojadepaes` |
| SKU | `LOJADEPAES_BIBLIOTECA_MENSAL` |
| Tipo | Assinatura mensal (`plan`) |
| Preço | `19.00` BRL |
| Créditos do ciclo | `20` (`meta_json.creditos` / `direitos.creditos`) |
| Periodicidade | mensal (`meta_json.periodicidade=mensal`, `period_months=1`) |
| Direitos | `assinatura=true`, `biblioteca=true` |
| Trial / desconto / reajuste / acumulação | não |

## Complementar

| Campo | Valor |
|---|---|
| App | `lojadepaes` |
| SKU | `LOJADEPAES_BIBLIOTECA_CREDITOS` |
| Tipo | Assinatura mensal (`plan`) com `direitos.papel=complementar` |
| Preço | `10.00` BRL |
| Créditos | `10` adicionais no ciclo vigente |
| Periodicidade | mensal — não é aquisição avulsa |
| Opcional | sim; só entra se o cliente contratar |
| Vários pacotes simultâneos | não autorizados por este adendo |

Não usar `type=credit_pack` para o complementar se o objetivo é mensalidade: o pack legado **soma** créditos e, no checkout de catálogo, o Hub hoje abre Brick (pagamento único), não preapproval. Sem pró-rata, prazo reduzido nem sincronização de vencimento inventados.

## Contrato reutilizado

- Catálogo: `GET /v1/catalog/lojadepaes`
- Checkout: `POST /v1/checkout/catalog` com `subject_id` do e-mail **já verificado**
- Autorização: `GET /v1/entitlements?app_id=lojadepaes&subject_id=<email>`
- Consumo: `POST /v1/credits/reserve|confirm|release` (S2S, `operation_id` idempotente)
- Identidade: cadastro verificado da Loja
- Concessão: Contract Service. Principal **define** 20 no próprio ciclo. Complementar **define** 10 no próprio ciclo e **não** substitui o plano nem o `valid_until` do principal. Se ambos renovam, 20+10 novos, sem sobras. Com vencimentos distintos, cada saldo segue o próprio ciclo.

## Regras efetivas do Hub (inspecionadas)

| Tema | O que o Hub faz hoje |
|---|---|
| Ciclo | `valid_until` a partir de `periodicidade` / `period_months` no fulfill, não mês de calendário |
| Renovação | Novo pedido PAID; contrato por `order_id` é idempotente (evento duplicado não concede duas vezes) |
| Acumulação | Principal com tipo `plan` + créditos: saldo do ciclo anterior é substituído pela franquia |
| Complementar no meio do ciclo | Define 10 no bucket complementar; não inventamos pró-rata; vencimento do principal é preservado |
| Cancelamento / proporcional | Sem wipe imediato. O complementar vale até o próprio `cycle_ends_at`; depois não se gasta. Sem pró-rata. |
| Checkout de catálogo | Brick (`checkout_mode=hub_brick`). Voltar da tela não prova assinatura |
| Vários complementares | O Hub não bloqueia segunda compra sozinho; a Loja só oferece um se elegível |

## Sandbox local (leaction_hub :5433) — IDs reais, sem cobrança

Criados em 08/10/2026 no banco isolado. **Não estão no catálogo de produção** (`actionhub.com.br` continua `plans: []`).

| Plano | SKU | Preço | Créditos | ID sandbox |
|---|---|---:|---:|---|
| Principal | `LOJADEPAES_BIBLIOTECA_MENSAL` | 19.00 | 20 | `42f21bac-2648-42cb-bad1-f6f3e212a2dc` |
| Complementar | `LOJADEPAES_BIBLIOTECA_CREDITOS` | 10.00 | 10 | `bddfcf1d-7182-41c5-b372-9f4a9a2ada2f` |

Smoke: `leaction-platform/services/gateway-api/scripts/p91b-hub-sandbox-smoke.js` — concessão 20, complementar +10, consulta, concorrência, débito idempotente, falha+liberação, recuperação, expiração, renovação sem acumulação, evento duplicado. Sem cobrança.

## Produção (Adendo 91D — 08/10/2026)

Mecanismo efetivo: **Mercado Pago preapproval** (`POST /preapproval`, `status=authorized`, `auto_recurring` mensal). Créditos só após pagamento confirmado do ciclo (`subscription_authorized_payment` / `payment` approved). Autorizar a recorrência não concede saldo.

IDs preservados. `checkout_mode=subscription`, `recurring_ready=true`.

Dependência: complementar exige principal vigente no servidor. Cancelar o principal interrompe a renovação do complementar; o período já pago continua. Sem pró-rata.

Rotas novas: `GET /v1/subscriptions`, `POST /v1/subscriptions/cancel`.

## Produção (Adendo 91C — 08/10/2026)

Criados pelo `POST /admin/plans` no host, após `GET` vazio. **Não são os IDs do sandbox.**

| Plano | SKU | Preço | Créditos | ID de produção |
|---|---|---:|---:|---|
| Principal | `LOJADEPAES_BIBLIOTECA_MENSAL` | 19.00 | 20 | `00bf4a0c-e598-414d-96cb-88cd47278e44` |
| Complementar | `LOJADEPAES_BIBLIOTECA_CREDITOS` | 10.00 | 10 | `cd4df3ce-6e67-45ab-ac5f-7bd876549129` |

Rotas publicadas: `POST /v1/credits/reserve|confirm|release` (400 sem corpo; 401 sem secret). Catálogo público: `GET /v1/catalog/lojadepaes`. Checkout Brick existente; **não** houve inscrição do proprietário nem cobrança real de teste.

Rollback: dumps `leaction_hub_20261008T144247Z.dump` e `inove4us_school_20261008T144247Z.dump`; cópias em `/var/lib/leaction-platform/backups/p91c-20261008T144249Z`. Não restaurar dump antigo sobre transações novas.

Não assinar, cobrar nem cancelar em produção para prova.

## Cache na Loja

`LOJADEPAES_ACTIONHUB_ENTITLEMENT_CACHE_SECONDS` (padrão 120). Guarda a última autorização. Não vale como saldo. Falha do Hub ≠ esgotado ≠ cancelado.
