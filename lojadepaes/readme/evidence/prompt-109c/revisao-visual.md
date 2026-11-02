# Revisão visual — Prompt 109C

Banco de captura `lojadepaes_capture` (dados fictícios, e-mails `@example.test`), API em `127.0.0.1:5075`, Vite em `127.0.0.1:5175`, Hub apontado para uma porta fechada. Larguras 390 e 1440. Semente: `scripts/p109c-seed-capture.py`. Captura e medição: `scripts/p109c-check.mjs` (o `p109a-check.mjs` citado no prompt não existe; o equivalente publicado é `scripts/p109-check.mjs`).

## Critérios medidos

- Controles com no mínimo 44 px abaixo de 960 px e 40 px a partir de 960 px.
- Sem rolagem horizontal da página, sem controle fora da tela e sem dois controles sobrepostos.
- Fonte DM Sans em todo texto dos painéis e das faixas. O Arial que aparece nas linhas dos painéis vem só dos botões nativos de rádio e de caixa de seleção, que não desenham texto.
- Marca `antecipada`/`adiada` na fila com 11 px, peso 600 e a cor `--admin-stage-warn-ink`.

## Medidas

| Captura | Controles | Menor altura (px) | Fontes | Rolagem horizontal | Observação |
| --- | --- | --- | --- | --- | --- |
| reagendar-dia-normal-390.png | 4 | 44 | DM Sans, Arial | não | ok |
| reagendar-dia-fechado-390.png | 4 | 44 | DM Sans, Arial | não | ok |
| reagendar-capacidade-cheia-390.png | 4 | 44 | DM Sans, Arial | não | ok |
| reagendar-erro-390.png | 4 | 44 | DM Sans, Arial | não | ok |
| corrigir-data-registrada-390.png | 4 | 44 | DM Sans, Arial | não | ok |
| solicitacao-pedido-existente-390.png | 5 | 44 | DM Sans, Arial | não | ok |
| detalhe-possivel-duplicidade-390.png | 4 | 44 | DM Sans | não | ok |
| anular-por-duplicidade-390.png | 6 | 44 | DM Sans | não | ok |
| detalhe-anulado-390.png | 0 | — | DM Sans | não | ok |
| detalhe-original-390.png | 2 | 44 | DM Sans | não | ok |
| fila-possivel-duplicidade-390.png | 16 | 44 | DM Sans, ui-monospace | não | ok |
| fila-anulados-por-duplicidade-390.png | 15 | 44 | DM Sans, ui-monospace | não | ok |
| fila-entregues-com-marca-390.png | 17 | 44 | DM Sans, ui-monospace | não | ok |
| reagendar-dia-normal-1440.png | 4 | 44 | DM Sans, Arial | não | ok |
| reagendar-dia-fechado-1440.png | 4 | 44 | DM Sans, Arial | não | ok |
| reagendar-capacidade-cheia-1440.png | 4 | 44 | DM Sans, Arial | não | ok |
| reagendar-erro-1440.png | 4 | 44 | DM Sans, Arial | não | ok |
| corrigir-data-registrada-1440.png | 4 | 44 | DM Sans, Arial | não | ok |
| solicitacao-pedido-existente-1440.png | 5 | 44 | DM Sans, Arial | não | ok |
| detalhe-possivel-duplicidade-1440.png | 4 | 44 | DM Sans | não | ok |
| anular-por-duplicidade-1440.png | 6 | 44 | DM Sans | não | ok |
| detalhe-anulado-1440.png | 0 | — | DM Sans | não | ok |
| detalhe-original-1440.png | 2 | 44 | DM Sans | não | ok |
| fila-possivel-duplicidade-1440.png | 22 | 40 | DM Sans, ui-monospace | não | ok |
| fila-anulados-por-duplicidade-1440.png | 21 | 40 | DM Sans, ui-monospace | não | ok |
| fila-entregues-com-marca-1440.png | 22 | 40 | DM Sans, ui-monospace | não | ok |


## O que cada captura mostra

| Arquivo | Conteúdo |
| --- | --- |
| `reagendar-dia-normal` | Painel Mudar a data da fornada em dia de produção: data atual, ocupação “N de M pães”, origem, motivo, aviso por e-mail marcado. |
| `reagendar-dia-fechado` | Mesmo painel numa sexta (dia fechado): aparece a caixa “Reservar mesmo fora dos dias de produção” e o botão fica bloqueado até marcar. |
| `reagendar-capacidade-cheia` | Sábado com limite 1 já ocupado: a ocupação mostra “1 de 1 pães”. |
| `reagendar-erro` | Confirmação recusada por capacidade: a mensagem aparece dentro do painel, que continua aberto. |
| `corrigir-data-registrada` | Pedido concluído: rótulo “Corrigir a data registrada”, sem a opção de avisar o cliente. |
| `solicitacao-pedido-existente` | Caixa de atenção “Este cliente já tem o pedido …”, botão primário “Mover … para …” e o link “Criar pedido novo mesmo assim” com a confirmação. |
| `detalhe-possivel-duplicidade` | Detalhe com possível duplicidade e o botão “Anular por duplicidade…”. |
| `anular-por-duplicidade` | Painel com o pedido original pré-selecionado, motivo obrigatório e aviso do que acontece. |
| `detalhe-anulado` / `detalhe-original` | Faixa de registro anulado, sem ações; no original, a linha “O pedido … foi anulado como duplicado deste.” |
| `fila-possivel-duplicidade` | Lente Possível duplicidade com “Possível duplicado de …” e o botão “Ver duplicidade”. |
| `fila-anulados-por-duplicidade` | Lente de auditoria Anulados por duplicidade. |
| `fila-entregues-com-marca` | Pedido entregue com a marca “antecipada” ao lado da data operacional. |
| `reagendado-detalhe-1440` | Após confirmar a exceção: “Solicitado para … · Entrega em … — adiada pela loja”, com motivo e ator. |
| `solicitacao-movida-1440` | Solicitação convertida apontando para o pedido existente, sem pedido novo. |

## Defeitos achados na revisão e corrigidos

- A mensagem de capacidade aparecia duas vezes (na página e no painel). Agora aparece só no painel.
- Com um filtro ativo, o link “Limpar” apertava a barra de filtros e os campos de data passavam por baixo do botão Filtrar. Os campos agora encolhem (`min-width: 0`).
- O link “Limpar filtro” tinha 40 px no celular. Passou a 44 px.
- Uma segunda solicitação para um pedido já ligado a outra gerava erro 500 (`uq_date_requests_converted_order`). Passou a responder 409 com mensagem clara, com teste.
