# Prompt 68 — Aceite efetivo sem endereço

## Causa

O aceite da solicitação gravava `awaiting_details` e enviava `date_request_complete` quando faltava endereço, **sem criar pedido nem reserva**. Dois cliques geravam dois eventos “Aceite autorizado; faltam dados” e nenhum pedido operacional.

## Correção

- Aceite com pães e preço resolvidos formaliza um único pedido confirmado, reserva a data e libera pagamento, mesmo sem endereço.
- Endereço ausente vira o indicador independente “Dados de entrega pendentes”.
- E-mail de aceite traz link protegido de pagamento e aviso para completar a entrega.
- A página protegida permite pagar sem preencher endereço primeiro; o complemento não recria pedido, não muda preço e não duplica reserva.
- Clique repetido e recuperação do estado legado reutilizam o mesmo pedido, a mesma reserva e o mesmo aviso `order_accepted`.

## Isolado

- API: `tests/test_prompt68.py` (aceite sem endereço, pagamento, complemento, concorrência, legado, outbox, data excepcional, capacidade, data passada, pedido pago, checkout padrão, encerramento).
- API anterior: `tests/test_prompt67.py` (fila, justificativa, 66A).
- Navegador: `tests/test_prompt68_browser.py` — aceite sem endereço → pedido na fila/detalhe → página protegida paga Pix simulado e completa endereço. Desktop 1440 e celular 390. Sem SES real.
- Relato: `isolated.json`. Capturas neste diretório.

## Produção

| Item | Valor |
|---|---|
| Imagem | `lojadepaes:prod-20261006c` |
| Rollback de app | `prod-20261006b` |
| Bundle | `/assets/index-kFC1iNLj.js` |
| Alembic | `a7d3b8e02c41` (sem migrate) |
| Backup | `20261006T085825Z` |

Recuperação individual autorizada de `SD15BD4592` pelo serviço corrigido (`admin:prompt68-recovery`):

| Item | Valor |
|---|---|
| Pedido | `LP42BF063F0C` (único; `source_date_request` vinculado) |
| Estado | confirmado; reserva da data 06/10/2026 (`holds_capacity`) |
| Total | R$ 90,00 |
| Pagamento | pendente; sem cobrança no provedor; sem `external_reference` |
| Entrega | pendente (indicador independente; endereço incompleto) |
| Aviso corretivo | um `order_accepted` enfileirado e `sent`, com link de pagamento e texto de dados faltantes |
| Eventos originais | os dois `awaiting_details` de 05:08/05:09 (UTC 08:08/08:09) foram preservados |
| Recuperação | um evento `converted` com origem “recuperação do aceite já autorizado” |
| Fila | só o pedido `LP42BF063F0C`; `SD15BD4592` não reaparece como atendimento paralelo |
| `SD51A91EFF` | encerrado, sem pedido, intocado |
| Segunda execução | `ALREADY_CONVERTED`; sem segundo pedido, reserva ou outbox |

Health/ready ok. Sem sessão administrativa no navegador de produção — a prova da fila real é leitura de API/banco no container, não captura visual. SES `sent` no outbox **não** prova entrega ou leitura na caixa. Sem pagamento de teste, seed, reset ou reenvio dos avisos anteriores `date_request_complete`.
