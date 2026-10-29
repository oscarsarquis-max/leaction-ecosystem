# Inventário funcional do backoffice

Lista que a interface nova tem de cumprir item por item. Rotas confirmadas em `AdminApp.tsx` 136 e 562–668 e `Root.tsx`. Não existe componente `OrdersScope`: o arquivo `OrdersScope.test.tsx` exercita `AdminApp`, `ProductsList` e `WeekRecipesList`. A classe CSS `.admin-ops-tests` (`admin.css` 79) não é referenciada em TSX.

Abaixo de 768 px o CSS que existe quebra em `max-width:720px` e `390px` (`admin.css` 146 e 190), não em 768.

Confirmação destrutiva encontrada: cancelar pedido pede motivo e desabilita o envio com texto vazio (`OrderDetail.tsx` 357–367). Fechar solicitação pede justificativa no domínio. Não há `window.confirm` genérico nesses fluxos.

Estado vazio: listas mostram texto e botão de atualizar (`OrdersList.tsx` 186–206, `ProductsList`). Erro de ação vai para `detailError` via `errorMessage` (`AdminApp.tsx` 530–532).

Leitura com efeito: abrir Produtos chama `GET /api/v1/admin/products`, que preenche slots vazios da vitrine (`admin/products.py` 63).

Capturas em `antes/`. Onde o estado não foi fotografado, a coluna Captura diz por quê.

## Acesso

| ID | Capacidade | Onde | Condição | Confirmação | Retorno | Teste | Captura |
|---|---|---|---|---|---|---|---|
| T-acesso-01 | entrar pelo acesso do cabeçalho | `HeaderAccount.tsx` 150 `POST /api/v1/admin/local-login` ou login com senha | loopback e `admin_local_passwordless`, ou conta com senha | não | sessão com `csrf_token`; sem sessão a API devolve 401 | `HeaderAccount.test.tsx` | T-acesso-01 |
| T-acesso-02 | redirecionar sessão ausente | `AdminApp.tsx` 330 e 546–551 | `session` nulo depois de `GET /admin/session` | não | “Redirecionando ao acesso do cabeçalho…” | `AdminApp.test.tsx` | T-acesso-02 |
| T-acesso-03 | abrir notificações neste aparelho | `AdminApp.tsx` 577–590, `PushNotices.tsx` | sessão presente | não | painel; ativar, desativar, testar, revogar aparelho | `PushNotices` coberto em testes de admin | T-acesso-03 |
| T-acesso-04 | ativar push neste aparelho | `PushNotices.tsx` 162 `activate` | permissão do navegador e VAPID no servidor | não | nota de sucesso ou falha; teste não prova que o celular mostrou | nenhum de contrato de VAPID | T-acesso-03; o servidor da captura não tem VAPID, então o painel mostra indisponível |
| T-acesso-05 | sair da conta | `HeaderAccount` | sessão | não | volta ao acesso | `HeaderAccount.test.tsx` | T-acesso-05-menu e T-acesso-05-sair |

Ativação de senha por link (`AdminActivationToken`) não tem tela no `AdminApp`. Estado não reproduzível no fluxo local sem token de ativação.

## Pedidos

| ID | Capacidade | Onde | Condição | Confirmação | Retorno | Teste | Captura |
|---|---|---|---|---|---|---|---|
| T-pedidos-01 | ver o resumo operacional | `AttendanceSummary.tsx`; `GET /api/v1/admin/ops/attendance-summary` (`AdminApp.tsx` 274) | só em `/admin` e `/admin/pedidos` | não | lentes com contagem; vazio é zero | `AttendanceSummary.test.tsx` | T-pedidos-01 |
| T-pedidos-02 | filtrar a lista por uma lente | clique na lente, `AttendanceSummary.tsx` 47+ | contagem pode ser zero | não | lista com `lens` | `AttendanceSummary.test.tsx` | T-pedidos-04-lente (estado Pago) |
| T-pedidos-03 | ver a agenda de produção e abrir o item | `ProductionAgenda.tsx` 90 | home de pedidos | não | navega ao href | testes de agenda se existirem | T-pedidos-03 |
| T-pedidos-04 | buscar e paginar pedidos | `OrdersList.tsx` 144 `GET /admin/orders` | sessão | não | vazio “nenhum” ou página | `test_admin_orders.py`, `contract/test_admin_order_api.py` | T-pedidos-04-lista (Todos) e T-pedidos-04-lente |
| T-pedidos-05 | abrir o detalhe | `OrdersList.tsx` 282; `GET /admin/orders/{id}` | linha de pedido | não | etapa visível, pagamento, itens | `AdminApp.test.tsx` | T-pedidos-05, um arquivo por etapa |
| T-pedidos-06 | aceitar a solicitação de encomenda | `OrderDetail.tsx` 314–318 `POST .../confirm` | some ou desabilita se houver adaptação sem resposta | não na UI | detalhe atualizado ou `detailError` | contract confirm | T-pedidos-06 |
| T-pedidos-07 | iniciar produção | `POST .../start-production` | `confirmed`; sem quitação a UI pede a exceção (`OrderDetail.tsx` 611–620) | motivo implícito na exceção, botão próprio | 409 com balde, ou Em produção | contract | T-pedidos-07 |
| T-pedidos-08 | marcar pronto | `POST .../mark-ready` | `in_production` | não | Pronto — aguardando confirmação de entrega | contract | T-pedidos-08 |
| T-pedidos-09 | concluir sem carimbo de entrega | `POST .../complete` | `ready` | não | Finalizado | contract | T-pedidos-09 |
| T-pedidos-10 | confirmar entrega | `POST .../confirm-delivery` | `in_production` ou `ready` | não | Entregue | contract | T-pedidos-10 |
| T-pedidos-11 | cancelar com motivo | `OrderDetail.tsx` 357–367 `POST .../cancel` | não concluído; botão desabilitado sem texto | texto obrigatório | Cancelado, ou 422 | contract | T-pedidos-11 |
| T-pedidos-12 | propor outra data de produção | `POST .../propose-date` | pedido ainda proponível | não | data atualizada ou erro | nenhum na suíte contract | T-pedidos-12 |
| T-pedidos-13 | resolver adaptação | `OrderDetail.tsx` 498 `POST .../adaptation` | status `submitted` na UI | texto de resposta conforme a decisão | detalhe; e-mail `adaptation_proposed` se propor | `test_adaptations.py` | T-pedidos-13 |
| T-pedidos-14 | gravar nota interna | `OrderDetail.tsx` 540 `POST .../notes` | texto não vazio | não | nota na lista | contract | T-pedidos-14 |
| T-pedidos-15 | reenviar um aviso da outbox | `AdminApp.tsx` 504 `POST /admin/ops/outbox/{id}/retry` | linha de aviso | não | erro ou atualização | `test_email_outbox.py` | T-pedidos-15 |
| T-pedidos-16 | ver solicitações de data | lista na home; detalhe `/admin/pedidos/solicitacao/:id` | sessão | não | pendentes ou vazio | `test_date_requests.py` | T-pedidos-16 |
| T-pedidos-17 | propor outra data da solicitação | `DateRequestDetail.tsx` `POST /admin/date-requests/{id}` action propose | não encerrada; data diferente | nota opcional | `alternative_proposed`; não reserva | contract | T-pedidos-17 |
| T-pedidos-18 | pedir complemento | action `request_completion` | e-mail válido | nota | `awaiting_details` | contract | T-pedidos-18 |
| T-pedidos-19 | encerrar com justificativa | action `close` | nota obrigatória | texto | `closed` / Rejeitado | contract | T-pedidos-19 |
| T-pedidos-20 | aceitar a solicitação e virar pedido | action `accept` + prévia `commercial-preview` (`AdminApp.tsx` 492) | linhas cotáveis | prévia não grava | pedido confirmado ou erro | `test_prompt102.py` | T-pedidos-20 |
| T-pedidos-21 | ver contagem de testes excluídos | número `excluded_tests` no resumo | exclusão já gravada | — | a etapa do pedido não muda; a linha sai da fila | contract `test_exclusion_hides_the_order` | sem botão na UI; ver lacuna |

Não há rota administrativa para `exclude_subject`. O operador não marca teste por esta interface.

## Produtos

| ID | Capacidade | Onde | Condição | Confirmação | Retorno | Teste | Captura |
|---|---|---|---|---|---|---|---|
| T-produtos-01 | listar produtos | `ProductsList.tsx` `GET /admin/products` | sessão | não | tabela nome, estado, vitrine, preço; o GET preenche a vitrine | `ProductsList.test.tsx` | T-produtos-01 |
| T-produtos-02 | criar produto | `/admin/produtos/novo` `ProductEditor.tsx` `POST /admin/products` | sessão | não | volta ao id salvo (`AdminApp.tsx` 651) | `ProductEditor.test.tsx` | T-produtos-02 |
| T-produtos-03 | editar nome, texto, disponibilidade, fidelidade, variantes e ingredientes | `ProductEditor.tsx` | rascunho ou publicado | remover variante pede o controle do editor | erro de validação no formulário | `ProductEditor.test.tsx` | T-produtos-03 |
| T-produtos-04 | publicar, arquivar, apagar | ações do editor | conforme estado editorial | apagar volta à lista (`onDeleted`) | lista atualizada | testes de produto | T-produtos-04 |
| T-produtos-05 | ordenar a vitrine | `ShowcasePanel.tsx` se montado no editor/lista | slots | não | ordem gravada; GET já pode ter preenchido vazio | testes de showcase | T-produtos-05 |
| T-produtos-06 | listar receitas da semana | `WeekRecipesList.tsx` `/admin/produtos/receitas` | sessão | não | tabela ou vazio | `OrdersScope.test.tsx` | T-produtos-06 |
| T-produtos-07 | publicar, arquivar ou excluir receita da semana | botões da lista `WeekRecipesList.tsx` 83–113 `POST /admin/week-recipes/{id}/{action}` | estado editorial | a ação de excluir é o botão da grade | lista recarregada | teste da lista | T-produtos-07 |
| T-produtos-08 | editar receita da semana | `/admin/produtos/receitas/:id` | sessão | não | salva e permanece no id | editor | T-produtos-08 |
| T-produtos-09 | configurar pão sob encomenda | `CustomLoafPanel.tsx` | flag/painel presente na área de produtos | não | preço e peso | `OrdersScope.test.tsx` lê o payload | T-produtos-09 |
| T-produtos-10 | editar notas do Gigio | `GigioNotes.tsx` `/admin/produtos/gigio` | sessão | não | nota salva | testes gigio | T-produtos-10 |
| T-produtos-11 | editar harmonizações | `PairingRefs.tsx` | sessão | não | lista | testes de pairing | T-produtos-11 |
| T-produtos-12 | editar complementos espelhados do Hub | `AccompanimentsAdmin.tsx` | sessão; Hub falso na suíte | não | oferta com `hub_source` | testes de accompaniment | T-produtos-12 |

## Agenda

| ID | Capacidade | Onde | Condição | Confirmação | Retorno | Teste | Captura |
|---|---|---|---|---|---|---|---|
| T-agenda-01 | ver e trocar dias de produção | `SchedulePage.tsx` `WeekdayPicker.tsx` | sessão | não | semana gravada | `test_schedule.py` | T-agenda-01 |
| T-agenda-02 | gravar teto do dia e bases elegíveis | `SchedulePage.tsx` 689–806 | prévia antes de gravar | não | erro de capacidade ou dia salvo | `test_schedule.py` | T-agenda-02 |
| T-agenda-03 | programar fechamento | `ClosurePanel.tsx` 209–212 | intervalo e primeiro dia elegível | não | compromisso na lista | testes de closure | T-agenda-03 |
| T-agenda-04 | cancelar ou reabrir fechamento | `ClosurePanel.tsx` 231 e 240 | item existente | `setConfirmCancel` pede confirmação na UI | lista atualizada | testes de closure | T-agenda-04 |

## Fidelidade

| ID | Capacidade | Onde | Condição | Confirmação | Retorno | Teste | Captura |
|---|---|---|---|---|---|---|---|
| T-fidelidade-01 | ver participantes e ciclos | `FidelityParticipants.tsx` `/admin/fidelidade` | sessão | não | tabela ou vazio | `test_house_fidelity.py` | T-fidelidade-01 |
| T-fidelidade-02 | ajustar crédito | ação do painel, se o botão estiver habilitado para a conta única | admin único, sem papel extra (`admin_auth.py` só username) | texto do ajuste se o formulário exigir | saldo novo ou erro | testes de ledger | T-fidelidade-02-ajuste |

## Capturas do adendo 107A

Banco `lojadepaes_capture` em `127.0.0.1:5438`, origem só `http://127.0.0.1:5175`. Nomes “Cliente Exemplo” e e-mails `@example.test`. `T-pedidos-04-lista` não é mais cópia de `T-pedidos-01-home`: a home é a fila operacional e a lista é o filtro “Todos”.

| Arquivo | Cobre |
|---|---|
| `T-pedidos-04-lista-*` | lista com as etapas semeadas |
| `T-pedidos-04-lente-*` | a mesma lista na lente Pago |
| `T-pedidos-05-<etapa>-*` | detalhe: aberto, aceito, pago, em-producao, excecao, pronto, entregue, finalizado, cancelado, endereco-pendente, verificacao, varias-linhas |
| `T-pedidos-07-excecao-*` | diálogo de produção sem quitação, antes de confirmar |
| `T-pedidos-11-sem-motivo-*`, `com-motivo-*`, `resultado-*` | cancelamento vazio, com motivo e depois de confirmar |
| `T-pedidos-12-proposta-*` | data alternativa já gravada no detalhe |
| `T-pedidos-13-adaptacao-*` e `T-pedidos-14-notas-*` | a mesma tela do pedido aberto: a adaptação e a nota estão nessa página |
| `T-pedidos-16-*` a `T-pedidos-20-*` | lista e cada estado da solicitação. `T-pedidos-20-previa` é a mesma tela de `T-pedidos-16-pendente` (`DateRequestDetail.tsx` 277). `T-pedidos-20-resultado` é a mesma tela de `T-pedidos-16-convertida` |
| `T-produtos-03-editor-*` | produto publicado, variantes peso e pacote |
| `T-produtos-04-acoes-*` | rascunho, com Publicar e Apagar. Arquivar fica no publicado |
| `T-agenda-03-fechamento-*`, `T-agenda-04-confirmacao-*`, `T-agenda-04-resultado-*` | fechamento, confirmação e reabertura |
| `T-fidelidade-02-ajuste-*` | carimbo do mês e ajuste manual já gravado |
| `T-acesso-05-menu-*`, `T-acesso-05-sair-*` | menu e saída |

Ainda sem quadro próprio, com o motivo:

- Pedido aberto sem data de produção: `submit_order` grava `production_local_date` a partir da data cotada (`storefront_orders.py`, por volta da linha 644).
- T-pedidos-12 não tem formulário. `OrderDetail.tsx` 254–255 só mostra a data que a API já gravou.
- T-pedidos-06, 08, 09 e 10 não abrem diálogo. O botão de aceite está no detalhe aberto e fica desabilitado enquanto a adaptação pende (`OrderDetail.tsx` 318). Pronto, finalizado e entregue estão nos detalhes `T-pedidos-05-pronto`, `finalizado` e `entregue`.
- T-pedidos-15: as linhas de aviso aparecem no detalhe; o reenvio não foi clicado porque chamaria o transporte.
- T-pedidos-21: não há botão (`inventário` já registrava).
- T-acesso-04: a captura não configura VAPID; o painel em `T-acesso-03` mostra a indisponibilidade.
- T-produtos-05: a vitrine está na lista `T-produtos-01` (`ProductsList.tsx` 123).
- T-produtos-07: os botões da receita estão na lista `T-produtos-06`; excluir não foi clicado.
- T-produtos-09 e T-agenda-02: o pão sob encomenda e o teto do dia estão em `SchedulePage.tsx` (828 e 689–806), na captura `T-agenda-01`.
- T-produtos-04 não mostra Apagar e Arquivar juntos: Apagar só existe em rascunho ou arquivado (`ProductEditor.tsx` 804).

