# Prompt 107 — inventário e contrato

29/10/2026. Nada de `backend/app/`, `frontend/src` de produção, `database/` ou `infra/` foi alterado. Sem migração, imagem, SSH ou escrita em produção.

## 1. Resumo

O comportamento atual de pedidos, solicitações de data, pagamento e avisos ficou descrito em quatro documentos e travado na suíte `backend/tests/contract` (32 testes) mais `frontend/src/admin/stageContract.test.ts`. O inventário funcional lista 44 capacidades `T-*` do backoffice. As capturas “antes” são 28 PNGs locais, em 1280×800 e 390×844. Ficou de fora o Prompt 108 e qualquer redesenho. Diálogos de detalhe, cancelamento e fechamento de agenda não foram fotografados: o banco de teste não tinha esses estados abertos. Playwright não está nas dependências do frontend; o script usa puppeteer-core e o Chrome local, só em `127.0.0.1:5175`.

## 2. Números

| Item | Contagem |
|---|---|
| Comandos no grafo | 18 linhas em `grafo-estados-atual.md` |
| Kinds de notificação | 24 linhas em `matriz-notificacoes.md` (inclui três fatos CRM, que não têm outbox) |
| Capacidades `T-*` | 44 |
| Capturas | 28 PNG |
| Contrato | 32 passed em 32,22 s (`pytest tests/contract`) |
| Suítes nomeadas | 143 passed, 2 failed, 171,47 s |
| Frontend | 208 passed em 33,53 s (`npm test`, 48 arquivos) |

As duas falhas já existiam contra o código atual e não foram afrouxadas: `test_date_requests.py:109` e `test_adaptations.py:347`.

## 3. Divergências e suspeitas

Nada foi corrigido.

- A hipótese `in_production → completed` não está em `ALLOWED_TRANSITIONS` (`enums.py` 34–36). O salto é `confirm_delivery` (`orders.py` 383), que também grava `delivery_confirmed_at`. `POST .../complete` a partir de `ready` conclui sem esse carimbo, e a etapa visível fica `finalized`, não `delivered` (`order_board.py` 190–193).
- `ready → in_production` só existe em `correct_ready_to_in_production` (`orders.py` 418). Não há rota HTTP.
- `draft` continua na tabela de transições, e `submit_order` não cria rascunho (`storefront_orders.py` 615).
- `date_request_available` tem template (`email_outbox.py` 74) e entra no CHECK, e `apply_date_request_action` não o enfileira.
- `payment_available` é booleano da visão pública (`storefront_orders.py` 883), não kind de e-mail.
- Nome de produto padrão vai para `dough_name_snapshot`; a apresentação vai para `shape_name_snapshot` (`storefront_orders.py` 697–698).
- `GET /api/v1/admin/products` preenche a vitrine (`admin/products.py` 63) e a sessão da request dá commit (`db/session.py` 41). A captura de Produtos deixou 10 posições vazias em `lojadepaes_test`.
- A etapa visível é recalculada em `admin_orders.py` 474, `attendance.py` 139, `production_agenda.py` 54, e a interface ainda tem rótulos próprios em `format.ts` 4 e `OrdersList.tsx` 19. A vitrine repete texto em `OrderStatusPage.tsx` 63.
- O CSS quebra em 720 px e 390 px (`admin.css` 146), não em 768. A classe `.admin-ops-tests` (`admin.css` 79) não aparece em TSX.
- Não há componente `OrdersScope` nem rota HTTP para `exclude_subject` (`managerial_exclusion.py` 63).
- No autoaceite com pagamentos ligados, `submit_order` só engole `ConfirmationError` (`storefront_orders.py` 764–768). `HubUnavailableError` sobe e o envio inteiro falha.
- `test_date_requests.py` 104–109 propõe a mesma data desejada e espera 200. O domínio recusa (`date_requests.py` 199–202).
- `test_adaptations.py` 342–347 pede checkout de um pedido com adaptação, ainda `submitted`, e espera 200. O domínio recusa até o aceite (`storefront_orders.py` 1075–1076).
- `readme/current-state.md`, antes desta entrada, ainda citava a imagem `prod-20261027b` e o Alembic `c4d8e1f07a22`. A base informada desta etapa é `prod-20261028c` e `d5e9f2a18b33`. Este prompt não conferiu produção.

## 4. Lacunas

- Kinds com linha de outbox na suíte: os da matriz, exceto `acceptance_update` (é kind de push; sem VAPID `enqueue_event_pushes` devolve 0 e não há aparelho na suíte) e os três fatos CRM, que não gravam linha.
- Sem captura: detalhe e diálogos de pedido, solicitação de data, logout, editor de produto existente, pão sob encomenda, fechamento de agenda, ajuste de fidelidade. Lista na seção final de `inventario-funcional.md`.
- T-pedidos-12 (propor data no pedido) e T-pedidos-21 (marcar teste) não têm caso de contrato próprio. A exclusão está em `test_order_visible_stage.py`; a proposta de data da solicitação está em `test_date_request_flow.py`.

## 5. Como reexecutar

Contrato, na pasta `backend`, com Postgres `lojadepaes_test` em `127.0.0.1:5438`:

```powershell
cd C:\Projetos\lojadepaes\backend
.\.venv\Scripts\python.exe -m pytest tests/contract -q
```

Suítes nomeadas:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_orders.py tests/test_admin_orders.py tests/test_date_requests.py tests/test_email_outbox.py tests/test_payments.py tests/test_adaptations.py tests/test_concurrency.py tests/test_prompt100.py tests/test_prompt101.py tests/test_prompt101b.py tests/test_prompt101c.py tests/test_prompt102.py tests/test_prompt102b.py tests/test_prompt104b.py tests/test_prompt104c.py tests/test_prompt104d.py tests/test_prompt105a_journeys.py tests/test_prompt105a_payments.py tests/test_prompt105a_followup.py tests/test_prompt105a_reference_recovery.py -q
```

Frontend:

```powershell
cd C:\Projetos\lojadepaes\frontend
npm test
```

Capturas, com a API em `127.0.0.1:5075` apontando para `lojadepaes_test`, acesso local sem senha, e o Vite em `127.0.0.1:5175`. O script recusa qualquer outra origem. `puppeteer-core` não está no `package.json`; o script resolve o módulo por `P77_PUPPETEER`.

```powershell
cd C:\Projetos\lojadepaes
$env:P77_PUPPETEER = Join-Path $env:TEMP "p107-puppeteer\package.json"
node scripts/p107-capture-backoffice.mjs
```

## 6. Commit

`2192fb2ba5c442abbe6dd0991c4e73989df5470f` no repositório `C:\Projetos` (`github.com/oscarsarquis-max/leaction-ecosystem`), ramo `feat/actionfinance-extrato-032`. Sem deploy.

## Adendo 107A

29/10/2026. Fecha as quatro ressalvas do 107. Não altera `backend/app/`, `frontend/src` fora de testes, `database/migrations/` nem `infra/`. Não publica e não inicia o 107B.

O histórico da Loja estava em `243ffc44`, não em `main`. O ramo `feat/lojadepaes-backoffice` nasce aí, com cherry-pick dos dois commits do 107 (`3c44df79` e `810d335b`) e o commit `24977d4e` da árvore até `prod-20261028c`. Em `feat/actionfinance-extrato-032` os dois commits foram revertidos num commit novo, `809c40e1`, já enviado. Ninguém mais tinha commitado depois de `66485af`.

Os testes `test_admin_propose_does_not_occupy_capacity` e `test_hub_checkout_description_omits_restriction` passam a esperar a recusa do domínio. O contrato cobre propor data, o silêncio operacional, o push com VAPID fictício e cada rota de `admin/orders.py`. A exclusão gerencial também afirma que o status não muda.

As capturas novas usam `lojadepaes_capture`. `scripts/p107a-seed-capture.py` recusa URL que não seja local com esse nome de banco. `T-pedidos-04-lista` tem hash diferente de `T-pedidos-01-home`.

Reexecutar:

```powershell
cd C:\Projetos\lojadepaes
.\backend\.venv\Scripts\python.exe scripts\p107a-seed-capture.py --prove-refusal
.\backend\.venv\Scripts\python.exe scripts\p107a-seed-capture.py
cd backend
.\.venv\Scripts\python.exe -m pytest tests/contract tests/test_date_requests.py::test_admin_propose_does_not_occupy_capacity tests/test_adaptations.py::test_hub_checkout_description_omits_restriction -q
cd ..\frontend
npm test
```

A captura continua `node scripts/p107-capture-backoffice.mjs`, com a API em `:5075` na base `lojadepaes_capture` e o Vite em `:5175`.
