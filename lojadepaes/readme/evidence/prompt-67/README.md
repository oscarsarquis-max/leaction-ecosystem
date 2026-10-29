# Prompt 67 — Pedidos é a fila única de atendimento

## Causa

O Prompt 66 só avisava “Há N solicitações… Abrir Agenda”. O proprietário precisa ver e responder as solicitações **na lista de Pedidos**. Encerrar sem justificativa e “Informar disponibilidade” sem formalizar o pedido estavam errados.

## Correção

- `/admin/pedidos` lista encomendas e `date_requests` na mesma fila (`order:{id}` / `date_request:{id}`).
- Pendentes primeiro, inclusive com mais de 24 h. Encerrados e convertidos só por filtro. Encerrado não conta como pendência.
- Cada solicitação tem “Avaliar e responder” no detalhe em Pedidos.
- Aceite formaliza pedido, reserva a data (exceção restrita à solicitação) e envia o link protegido de pagamento. Clique repetido reusa o mesmo pedido.
- Propor outra data: um único campo, só depois de escolher a ação. Silêncio do cliente não confirma.
- Encerrar exige justificativa enviada por e-mail. Sem “Encerrar sem enviar mensagem”, inclusive na API.
- Pedido padrão da vitrine, sem adaptação, em data convencional: aceite automático + pagamento (66A).
- Agenda fica com atalho para a fila. Resumo de pendências no layout administrativo após o login.
- Solicitação incompleta: lacunas visíveis, endereço no detalhe ou acesso protegido `/solicitacao/{id}`.

## Isolado

- API: `tests/test_prompt67.py` (fila mista, recusa de close_silent, justificativa, aceite→pedido, 66A, outbox, resumo).
- Navegador: `tests/test_prompt67_browser.py` — login → resumo → fila → detalhe → justificativa → outbox `date_request_declined`. Desktop 1440 e celular 390. Sem SES real.
- Relato: `isolated.json`. Capturas neste diretório.

## Produção

| Item | Valor |
|---|---|
| Imagem | `lojadepaes:prod-20261006b` |
| Rollback de app | `prod-20261006a` |
| Bundle | `/assets/index-GiTht6Yp.js` |
| Alembic | `a7d3b8e02c41` |
| Backup | `20261006T060336Z` |

Leitura no container, sem alterar estados:

- `SD15BD4592` (`15bd4592…`) **pending**, data 06/10, na fila de Pedidos e no resumo.
- `SD51A91EFF` (`51a91eff…`) **closed**, no filtro de encerradas; **não** conta como pendência.
- Fila operacional: 9 registros; 1 solicitação aguardando resposta; `unique_records=9`.

Health/ready ok. Sem sessão administrativa no navegador de produção — a prova visual do painel real não foi feita aqui. Nenhum aceite, cobrança ou e-mail a cliente.

Resumo operacional autorizado: outbox `ops_attendance_summary` / `ops:attendance_summary:prompt67` para oscar@oscarsarquis.com.br. SES aceitou (`sent`, message id presente). Isso **não** prova entrega ou leitura na caixa. Sem reenvio.
