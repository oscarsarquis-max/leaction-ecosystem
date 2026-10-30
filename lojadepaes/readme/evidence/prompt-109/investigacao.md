# Investigação — 109

Feita antes de alterar a fila. O plano do prompt se mantém, com os ajustes abaixo.

## 1. O que a fila faz hoje

Arquivos: `frontend/src/admin/OrdersList.tsx`, `AdminApp.tsx`, `AttendanceSummary.tsx`, `ProductionAgenda.tsx`.

O estado fica no `AdminApp`: `filters`, `applied`, `page`, `list`, `listLoading`, `listError`. Voltar do detalhe não zera isso, porque o componente não desmonta o estado ao trocar a rota interna.

Controles e comportamentos de `OrdersList`:

- Busca (`filters.reference`, até 80 caracteres). No envio, referência ou situação limpam `lens`, a página volta para 1 e só então `applied` muda.
- Situação: Fila operacional (vazio), Todos (`all`), Solicitações de data (`date_pending`), e as lentes `stage:open`, `stage:accepted`, `stage:paid`, `stage:in_production`, `stage:ready_legacy`, `stage:delivered`, `stage:finalized`, `stage:cancelled`, `stage:rejected`. Valor com prefixo `stage:` vai para `lens`; os outros vão para `status` e zeram `lens`.
- Recebimento (`modality`): Todas, Retirada (histórico) `pickup`, Entrega `delivery`.
- Criado de / até (`created_from`, `created_to`). Com um dos dois preenchidos, a tela avisa que o recorte é a data de criação, não a fornada.
- Filtrar envia o formulário. Atualizar chama `onRefresh` (`loadList`). Não há botão “Limpar” ao lado do formulário; “Limpar filtro” só aparece na frase do `filter_label`, e “Limpar filtros” no vazio filtrado.
- Paginação de 20 (`page_size` fixo no `loadList`). Anterior / Seguinte. Texto “Página X de Y”.
- Abertura: botão da referência e o botão de ação chamam `onOpen`. Solicitação vai para `/admin/pedidos/solicitacao/{id}`; pedido para `/admin/pedidos/{id}`.
- Ação da linha: solicitação `pending`, `alternative_proposed` ou `awaiting_details` mostra “Avaliar e responder”; o resto mostra “Abrir”. Os dois só navegam.
- Vazio: `emptyHint === "none"` → “Nenhum pedido nesta fila de atendimento.” `filtered` → “Nenhum pedido com esses filtros.” mais Limpar filtros. Erro de rede ou carga parcial não mostra o vazio.
- Erro de rede: `role="alert"` com a mensagem e “Tentar de novo”.
- Carga parcial: `orders_error` e `date_requests_error` na mesma faixa, e a outra fonte continua na tabela.
- `filter_label`: “Filtro do resumo: {rótulo}. {total} registro(s).” mais aviso se a busca está dentro do filtro, mais `state_counts` quando existem.
- Sem `filter_label`, `search_scope` explica histórico completo, todos os estados ou fila operacional, também com `state_counts`.
- Carregando: texto “Carregando pedidos…”.

`AttendanceSummary` (Ciclo dos pedidos) chama `onSelectLens` com a lente da etapa. O `AdminApp` zera os filtros, aplica só essa lente, página 1, e navega para `/admin/pedidos`. O painel de histórico faz o mesmo.

`ProductionAgenda` abre pedido ou solicitação pelo `href` da entrada. Não filtra a fila.

Hoje `/admin` e `/admin/pedidos` montam os dois painéis (`ordersHome`). O prompt pede a agenda e o ciclo só em `/admin`, e `/admin/pedidos` só com a fila. O teste `OrdersScope` que procura os dois títulos em `/admin/pedidos` muda de lugar: passa a procurá-los em `/admin`, com a mesma exigência, e `/admin/pedidos` fica sem eles. O resumo continua sendo carregado em `/admin/pedidos` porque as contagens das lentes vêm dele.

## 2. Como o servidor monta a lista

`list_attendance` (`attendance.py`):

- Se há `lens`, `lens_fetch_status` troca o `status` da consulta. `stage:*` vira um status persistido (`stage:open` → `submitted`, `stage:rejected` → `date_closed`, etc.). `payment:*`, `pending:*`, `work:*` e `audit:tests` buscam `all`.
- Sem status e sem busca, a fila é a vigente: pedidos `submitted`, `confirmed`, `in_production`, `ready`, mais solicitações abertas (`pending`, `alternative_proposed`, `awaiting_details`).
- Busca sem status olha o histórico. `status=all` também. Referência que começa com LP ou SD restringe a consulta SQL; `_matches_search` ainda filtra por referência, nome e id.
- Recebimento, fornada (`production_batch_id`) e slot excluem solicitações.
- Testes marcados saem da fila, exceto na lente `audit:tests`. Solicitação `converted` não entra.
- A ordenação é `_rank`: solicitação vencida, solicitação aberta, adaptação, pago aguardando aceite, submetido, ativos do mais novo, resto.
- Página depois da ordenação. `filter_label` vem de `LENS_LABELS` depois de cruzar com os âncoras do `managerial_board`.

`OrderListItemOut` hoje: id, referência, criado, status, cliente, pães, modalidade, fornada (id e código), slot, total, `financial_kind`, adaptação, personalizado, origem, `row_key`, data desejada, `context_label`, horas pendentes, vencido, entrega pendente, `visible_stage`, `visible_label`, `payment_attention`.

`classify_payment` é a única classe financeira do pedido. `visible_stage_for_order` e `payment_attention_label` continuam como estão. A projeção nova só lê esses resultados.

## 3. Testes que mudam de lugar

Backend: nenhum teste existente é editado. Campos novos têm default, então os construtores atuais continuam válidos.

Frontend, mesma força, texto novo onde o prompt troca a frase:

- `AdminApp.test.tsx` “Nenhum pedido nesta fila de atendimento.” → “Nenhum pedido na fila agora.” O vazio filtrado e o alerta de erro permanecem.
- “Solicitação de data” / “Avaliar e responder” / “Limpar filtros” / “Tentar de novo” continuam. “Sem cobrança” no total da solicitação → “—” na coluna de total; “Sem cobrança” passa a ser o selo de pagamento vindo da API.
- Cartão `data-label="Estado"` com “Confirmado” → selo `visible_label` da API e as quatro trilhas da API. A referência continua abrindo a linha.
- “Adaptação: Aguardando avaliação” → o texto `attention` da API (“Adaptação pedida: …”). A lista não inventa a restrição.
- `AttendanceSummary.test.tsx`: opções “Aceito” e “Pago” saem do select e viram pílulas (`stage:accepted`, `stage:paid`). “Pronto — aguardando confirmação de entrega” continua no select. “Filtro do resumo” e “Limpar filtro” continuam.
- `OrdersScope.test.tsx`: títulos “Ciclo dos pedidos” e “Agenda de produção” em `/admin/pedidos` → os mesmos títulos em `/admin`. `/admin/pedidos` mostra “Pedidos” e não mostra esses dois.
- `stageContract.test.ts`: cores de `.admin-stage.is-*` em `admin.css` e o texto de `OrdersList.tsx` → valores dos tokens de tom em `tokens.css`, e `TrackChip` usa `label` e `tone` da API. `statusLabel` permanece.

## 4. Endpoint de fornadas

Não há endpoint de admin que liste fornadas com id, código e data. `GET /admin/schedule` devolve a rotina. `GET /admin/schedule/days/{data}` devolve um dia. A consulta da fila já aceita `production_batch_id`, mas sem lista não há o que colocar no select. O filtro “Fornada” fica fora deste prompt. Nenhum endpoint novo foi criado.

## Ajustes em relação ao texto do prompt

- `order_tracks` ganha dois argumentos opcionais, `adaptation_text` e `today`. Sem eles a função não tem a frase da cliente nem o dia da padaria, e a atenção não fecha. A assinatura obrigatória continua `order, bucket, *, unresolved_adaptation`.
- A lente `work:needs_action` já cairia em `lens_fetch_status` → `all` por causa do prefixo `work:`. Faltava a chave no quadro. Ela entra em `LENS_LABELS` e nos âncoras.
- As pílulas “Vigentes” e “Todos” usam as chaves `vigentes` e `all`. `vigentes` não filtra por âncora (é a fila sem lente). `all` equivale a `status=all`, também sem âncora. Assim a contagem de cada item de `queue_lenses` bate com `GET /admin/orders?lens=…`.
- Data vencida na atenção vale para pedido vigente (`submitted`, `confirmed`, `in_production`, `ready`) e para solicitação aberta, porque a regra cita a data desejada e o quadro já marca essas solicitações em `pending:overdue`.
- O corte de 60 caracteres inclui o “…” no limite.
