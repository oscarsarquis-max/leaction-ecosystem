# Prompt 70 — E-mail único de aceite, endereço que salva, formulário legível

## Causas (separadas)

1. **E-mail.** O aceite gravava `order_accepted` só em texto, sem logo, sem botão e sem explicar pagamento + endereço no mesmo recado. O aviso anterior `date_request_complete` mandava a cliente para `/solicitacao/…`, uma página de complemento, não o pedido protegido. `sent` no outbox não prova caixa.
2. **Gravação.** A página antiga da solicitação usava o token da solicitação e um formulário desalinhado. No pedido, `DeliveryAddressIn` recusava UF com mais de 2 caracteres (`CEARA`) antes da persistência; o cliente via falha genérica. CEP sem máscara e Estado livre agravavam o erro.
3. **Layout.** `DateRequestCompletePage` não usava `.checkout-form`. Os labels do endereço ficavam inline e os inputs, estreitos — exatamente a captura móvel.

## Correção

- Um e-mail de aceite (HTML + texto) com logo oficial `/images/lojadepaeslogo.png`, itens, total, data aceita, CTA **Pagar e acompanhar meu pedido** e aviso de entrega no mesmo corpo.
- Link antigo de solicitação convertida abre o pedido protegido, sem nova formalização.
- Formulário compartilhado do checkout: labels acima, 16px, UF por sigla, CEP com máscara, erros no campo. Salvar só após persistir; recarregar devolve o endereço.
- Pedido aceito paga sem endereço. Complemento não muda aceite, total nem reserva.

## Gravação (follow-up)

A imagem `d` ainda não persistia o que a cliente digitava:

1. O POST ia sem `Content-Type: application/json`; o FastAPI respondia 422 e a tela só mostrava «resposta-invalida».
2. Depois do aceite, a página `/solicitacao/` redirecionava sozinha para o pedido e escondia o formulário do link antigo.
3. No pedido em produção, o token às vezes ficava só no cabeçalho; pagamento também não abria em `in_production` não pago.

A imagem `e` manda JSON com tipo, aceita o token na query, mantém o formulário no link antigo até o endereço gravar, e deixa pagar/salvar com o pedido já em produção. Rua solta no complemento da solicitação **não** foi copiada para o pedido.

## Isolado

- API: `tests/test_prompt70.py` (e-mail único, pagamento antes do endereço, UF/CEP, link antigo, recuperação idempotente, pedido pago, checkout padrão).
- Navegador: `tests/test_prompt70_browser.py` — emulação Chromium 320/390/768/1440, não é aparelho físico. Sem SES real.
- Relato: `isolated.json`. HTML/texto do template em `order-accepted.html` / `order-accepted.txt`. Capturas neste diretório.

## Produção

| Item | Valor |
|---|---|
| Imagem | `lojadepaes:prod-20261006e` |
| Rollback de app | `prod-20261006d` |
| Bundle | `/assets/index-IdBO8t8r.js` |
| Alembic | `a7d3b8e02c41` (sem migrate) |
| Backup | `20261006T140336Z` |

Leitura de `LP42BF063F0C` **antes** da comunicação corretiva: `in_production`, reserva 06/10, R$ 90, pagamento pendente sem cobrança no provedor, entrega pendente. Um `order_accepted` antigo (`sent`, sem CTA novo). `date_request_complete` antigo preservado. Eventos de 05:08/05:09 preservados.

Correção pontual `prompt70`: um novo `order_accepted` `sent`, com CTA, aviso de entrega e link do pedido. Segunda execução reusou a mesma chave. Depois, o aceite antigo (`Data da fornada confirmada`) ainda era o recado que a cliente abria: tinha `/pedido/` mas o botão dizia só «Acompanhe». Foi enviado um aviso extra `prompt70pay` (`sent`, assunto «pague e acompanhe»), sem novo aceite, reserva ou cobrança. Pedido, reserva, total e pagamento **não** mudaram. Sem sessão administrativa no navegador de produção. SES `sent` **não** prova entrega ou leitura na caixa. Sem pagamento de teste.

O proprietário acompanha o envio no detalhe do pedido (avisos `order_accepted`). Não há token no relatório.
