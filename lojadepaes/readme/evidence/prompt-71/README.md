# Prompt 71 — Ação de pagamento no link do e-mail

## Causa

O CTA do aceite abre `/pedido/{ref}?token=…` (`OrderStatusPage`). A API já marcava `payment_available` para pedido aceito e não pago. A tela escondia **Pagar com Pix** e **Pagar com cartão** quando `/api/v1/operations` falhava ou ainda não tinha respondido, e o fallback antigo só liberava `submitted` não confirmado. Pedido em produção (`LP42BF063F0C`) caía nessa trava: título «Pagamento», item e «Voltar à vitrine», sem ação. O formulário de endereço vinha antes e ocupava a dobra.

## Correção

- A ação de pagamento depende só de `payment_available` do pedido, sem segundo fetch.
- Pix e cartão ficam no topo da seção Pagamento, antes do endereço.
- Pedido pago, cancelado, total zero ou pagamentos desligados mostram razão, nunca seção vazia.
- Link antigo `/solicitacao/` convertido aponta para o mesmo pedido com as duas ações.

## Isolado

`tests/test_prompt71.py` e `tests/test_prompt71_browser.py`. O navegador abre o **href extraído do HTML do e-mail**, sessão limpa, sem login admin. Pix e cartão visíveis sem endereço; clique em Pix gera cobrança simulada idempotente. 320/390/1440. Sem SES real.

## Produção

| Item | Resultado |
|---|---|
| Imagem | `lojadepaes:prod-20261006f` |
| Bundle | `/assets/index-XQ7UfZt_.js` |
| Pedido | `LP42BF063F0C` `in_production`, R$90, não pago, `payment_available` |
| Endereço | ainda pendente; não bloqueia pagamento |
| Link | `/pedido/LP42BF063F0C` — mesmo destino do e-mail já enviado |
| Leitura 390 | **Pagar com Pix** e **Pagar com cartão** visíveis e habilitados, acima do endereço |
| Provedor | não clicado |

Sem novo e-mail. Rollback `prod-20261006e`. Backup `20261006T143731Z`.