# Adendo 91B — evidência

Publicado em 08/10/2026. Imagem `lojadepaes:prod-20261008e`. Backup `20261008T141759Z`. Regras `91`. Alembic `b5c8d3e02f16`.

A apresentação dos dois preços e o envio consciente (`Usar 1 crédito`) estão no ar. Monetização **não** está pronta: os planos ainda não existem no editor do ActionHub e a API de reserva ainda não foi publicada no Hub de produção.

## O que ficou ativo na Loja

- Painel da Biblioteca com Principal R$ 19,00/mês (20 créditos) e Complementar R$ 10,00/mês (10 créditos)
- Recorrência mensal explícita; complementar opcional; sem compra automática ao esgotar
- Gigio no modo aprofundamento: saldo + **Usar 1 crédito**; atendimento comercial continua livre
- Reserva/confirm/release no servidor contra o contrato do Hub; operação local só para reconciliação
- Calculadora 1720 g e artigos 87–90 preservados

## IDs (sandbox local, não produção)

| Plano | ID |
|---|---|
| Principal `LOJADEPAES_BIBLIOTECA_MENSAL` | `42f21bac-2648-42cb-bad1-f6f3e212a2dc` |
| Complementar `LOJADEPAES_BIBLIOTECA_CREDITOS` | `bddfcf1d-7182-41c5-b372-9f4a9a2ada2f` |

Catálogo público de produção (`https://actionhub.com.br/hub-api/v1/catalog/lojadepaes`) continua `plans: []`.

## Navegador (produção)

`scripts/p91b-browser-check.mjs` em `/biblioteca/o-comeco` e `/biblioteca/calculadora`: R$ 19/mês, R$ 10/mês, 20 créditos, complementar opcional, sem botão Assinar, calculadora aberta. Fotos em `readme/evidence/prompt-91b/`.

## O que ainda não está pronto

| Camada | Estado |
|---|---|
| Configuração dos planos | IDs no Hub **local**; produção sem plano publicado |
| Assinatura autorizada | `configured=false`, `checkout_ready=false` |
| Consumo no Hub de produção | rotas novas no repositório; **não publicadas** no gateway |
| Cobrança real | não feita e não deve ser usada para prova |

Ficha: `scripts/p91-hub-plan-sandbox.md`.

## Testes

- Hub (unit): franquia 20 substitui saldo; complementar +10 sem trocar plano/ciclo; pack Inove soma; reserva/confirm idempotentes; confirmado não libera
- Loja: envio sem `Usar 1 crédito` não chama modelo nem reserva; débito único + recuperação sem novo débito; falha libera; Pix na rota da Biblioteca não gasta crédito
- Frontend: R$ 19,00 / R$ 10,00; `Usar 1 crédito` envia `spend_credit` + `operation_id`
- Regressão 87 e 90: passou

Não houve compra, assinatura, e-mail nem cobrança real.

## Rollback

Imagem anterior `lojadepaes:prod-20261008d`. Alembic `b5c8d3e02f16` só cria `gigio_credit_operations`; downgrade remove essa tabela sem tocar pedidos.
