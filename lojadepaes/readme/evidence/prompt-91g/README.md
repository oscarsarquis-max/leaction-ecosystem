# Adendo 91G — evidência

Publicado em 08/10/2026. Sem assinatura, compra, cancelamento, e-mail ou cobrança reais de teste.

## Produção

| Item | Evidência |
|---|---|
| Loja | https://lojadepaes.com.br/ — `lojadepaes:prod-20261008f` |
| Bundle | `/assets/index-B-aP-XuE.js` + `index-pwEhWLTn.css` |
| Backup Loja | `/opt/lojadepaes/backups/lojadepaes-20261008T182428Z.sql.gz` |
| Alembic | `b5c8d3e02f16` (sem migração nova) |
| Regras | `91` |
| Hub | gateway + frontend ActionHub; `/loja` e `/loja/contratar` 200 |
| Backup Hub | `leaction_hub_20261008T181319Z` + rollback files `p91g-20261008T181319Z` |
| Contratos/pedidos Hub da Loja | 0 no momento da conversão do SKU |

## Produtos no catálogo oficial

Página: https://actionhub.com.br/loja (retorno `return_origin` / `return_to` para a Loja).

| SKU | ID | Tipo | Modalidade | Preço |
|---|---|---|---|---|
| `LOJADEPAES_BIBLIOTECA_MENSAL` | `00bf4a0c-e598-414d-96cb-88cd47278e44` | `plan` | `subscription` / recorrente | R$ 19 / mês · 20 consultas + 10% |
| `LOJADEPAES_BIBLIOTECA_CREDITOS` | `cd4df3ce-6e67-45ab-ac5f-7bd876549129` | `credit_pack` | `hub_brick` / avulso | R$ 10 por compra · 10 consultas |

O SKU de créditos foi convertido no mesmo ID (zero clientes). A oferta antiga recorrente saiu de novas contratações. Histórico vazio; nada cancelado nem cobrado.

## Provas ao vivo (sem direito pago)

- Visitante: `GET /api/v1/conta/situacao` → Assinatura **Sem assinatura**, Consultas de IA vazias, Fidelidade / créditos de pão separados; `identified=false`.
- Biblioteca: `plans_href` = `https://actionhub.com.br/loja?...`; pacote `period=avulso`; textos sem R$ 10/mês.
- Cotação Pão de Frutas R$ 70 (`7000` cents), sem identidade: `subscriber_discount_cents=0`, preço de catálogo intacto.
- Cotação personalizada R$ 70: `origin=custom`, `subscriber_discount_cents=0`, sem crédito de pão (`fidelity_qualifies=false`).
- Calculadora `1720 g` e calendário `/api/v1/schedule/calendar` intactos; cotação não exige assinatura nem endereço novo.
- Bundle da Loja: sem `R$ 10,00/mês`.

Desconto 10% com direito vigente: R$ 70 → R$ 7 e R$ 90 → R$ 9 no servidor (`test_prompt91g`). Pacote isolado não recebe 10%.

## Domínios

Rótulos: **Assinatura**, **Consultas de IA**, **Fidelidade / créditos de pão**. Identidade (CPF/código) autentica a pessoa e envia ao e-mail cadastrado; não é licença da Biblioteca.

## Decisões ainda do proprietário

1. **Validade dos créditos avulsos** — confirmados preço, quantidade e natureza avulsa, não uma nova validade. Créditos entram após pagamento confirmado; não foi inventada expiração nem acúmulo ilimitado.
2. **Acumulação 10% + crédito de pão** — conflito concreto: se os dois caberiam no mesmo pedido, o crédito de fidelidade segue a regra atual e o 10% **não** é aplicado (`promo_conflict`).
3. Elegibilidade do pacote fora de assinatura: consultas de IA podem ser usadas (1 crédito = 1 consulta); **não** há desconto de assinante.

## O que não foi feito

Cobrança, e-mail, assinatura ou cancelamento reais. Pedidos históricos não foram alterados. Ofertas Mercado Livre/Amazon continuam sem desconto da Loja.
