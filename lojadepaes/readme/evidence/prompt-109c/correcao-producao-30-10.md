# Correção dos registros de 30/10 em produção (seção E)

Feita em 02/11/2026, depois do deploy de `lojadepaes:prod-20261102a` (Alembic `e7b3c9a41d06`), com `scripts/p109c-correct-oct30.py` rodando dentro do contêiner da API. O script abre uma sessão administrativa curta, chama as rotas `reschedule` e `void-duplicate` e apaga a sessão. Nenhum SQL de escrita. A saída mostra só referências, status, datas e contagens.

## Antes (somente leitura)

| Item | LP331354282E | LP398E6E6AC4 |
| --- | --- | --- |
| Status | completed | completed |
| Data solicitada | 2026-11-01 | 2026-10-30 |
| Data operacional | 2026-11-01 | 2026-10-30 |
| Ocupa vaga | sim | sim |
| Pagamento local | paid | pending |
| Caixa de saída | order_accepted 1, order_auto_accepted_admin 1, payment_approved 1 | acceptance_update_admin 1, order_accepted 1 |

Sexta 30/10: 1 pão ocupado. Domingo 01/11: 1 pão ocupado. Caixa de saída: 70 linhas, 0 `order_date_changed`. Lente de possível duplicidade: os dois pedidos. Par LP063F5ED6C6 / LPACD780ADB3: completed / cancelled, fora da lente.

## Ações

```text
reschedule LP331354282E 200
void-duplicate LP398E6E6AC4 200 ok
```

1. `reschedule` de LP331354282E para 2026-10-30, origem `customer`, sem aviso, motivo “Antecipação combinada com o cliente pelo WhatsApp; produzido e entregue na sexta”. Pedido concluído: correção de registro, sem checar capacidade e sem e-mail.
2. `void-duplicate` de LP398E6E6AC4 com original LP331354282E, motivo “Criado pelo aceite da solicitação de data; a encomenda real é LP331354282E, paga e entregue”.

## Depois (somente leitura)

| Item | LP331354282E | LP398E6E6AC4 |
| --- | --- | --- |
| Status persistido | completed | completed |
| Data solicitada | 2026-11-01 (intacta) | 2026-10-30 |
| Data operacional | 2026-10-30 | 2026-10-30 |
| Marca de exceção | Antecipada a pedido do cliente | — |
| Ocupa vaga | sim | não |
| Pagamento local | paid | cancelled |
| Etapa visível | Aceito | — (anulado) |
| Faixa de anulação | não | sim |
| Vínculo | lista LP398E6E6AC4 como anulado deste | — |

- Sexta 30/10: 1 pão ocupado (o LP331). Domingo 01/11: 0.
- Lente Anulados por duplicidade: só LP398E6E6AC4. Lente Entregues entre os dois: só LP331354282E. Lente de possível duplicidade: vazia.
- Caixa de saída: 70 linhas antes e depois; 0 `order_date_changed`; nenhum aviso novo em nenhum dos dois pedidos.
- Par LP063F5ED6C6 / LPACD780ADB3: não corrigido. Segue completed / cancelled e fora da lente de possível duplicidade. O cartão pago do cancelado, sem estorno no registro local, depende de conferir o Mercado Pago, o que fica com o proprietário.
