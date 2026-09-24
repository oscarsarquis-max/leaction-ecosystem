# Candidato isolado — insumo manual sobre `d0a3451`

**Não publicado.** Produção permanece em `d0a34515912805987fb5ae6522b92cdbf8da366d` / `panne-prod-api:15`. A autorização do SHA `7177805` continua sem efeito.

Ramo: `feat/panne-insumo-manual-on-prod` (worktree `_panne-insumo-on-prod`). Base: árvore produtiva. Sem cherry-pick cego dos seis commits do pacote.

## 1. Diff contra `d0a3451`

Só caminhos `panne/**`. Sem sujeira do monorepo.

### Preservados (identidade bit a bit com `d0a3451`)

- Dockerfile da API e do frontend
- Cognito / OIDC, `LoginPage`, editorial de `/entrar`
- `FirstAccess`, onboarding, `access_code`, `test_productive_onboarding` (código de produto)
- Revisão fiscal sem estoque (`0029`), `receiptOperation.ts`, `receiptReview.ts`, constantes fiscais
- Dashboard econômico, `CostingPages` por atacado, grafo de produto

### Arquivos produtivos tocados além das rotas novas — e por quê

| Arquivo | Motivo contratual |
|---|---|
| `costing_pricing/engine.py` | Pacote trazia `unknown_cost_cut`; **manteve** o bloco produtivo de rendimento vendável e só acrescentou o recorte incompleto. |
| `costing_pricing/valuation.py` | `select_price` não completa recorte com lote `unknown`. |
| `fiscal_http/router.py` + `fiscal_inbound/commands.py` | `create_ingredient` explícito; conteúdo de embalagem só depois do receive. Gravação da nota continua separada da entrada. |
| `inventory_procurement/services.py` | Abertura sem NF exige `confirmed`/`origin`/custo; `ensure_published_policy` só neste caminho. Receive produtivo (`recebimento-inicial`) intacto. |
| `inventory_http/router.py` + `serialize.py` | Campos de lote/pacote e abertura. |
| `ingredient_http/writes.py` + `ingredient_catalog/models.py` | API de consolidação e auditoria `ingredient_link_reassignment`. |
| `production_http/errors.py` | Códigos de embalagem **somados** às mensagens fiscais produtivas. |
| `App.tsx`, `Shell.tsx`, `FlowCoachPanel.tsx` | Rotas consolidar/abertura; Gigio montado e recolhido em formulário/visão geral. |
| `client.ts` / `types.ts` | Campos aditivos. `gaps` duplicado do pacote foi removido para o tipo produtivo de cálculo continuar compilando. |
| `FiscalDocumentPage.tsx`, `ReceiptSheet.tsx` | Destino explícito; `creating: false` + `create_ingredient`. |
| `CostingDecisionPage.tsx` | Aviso de custo desconhecido; UI econômica produtiva preservada. |
| `InventoryPages.tsx`, `IngredientsPage.tsx`, `RecipeEditorPage.tsx` | Visão geral aprovada; atalhos. |
| `language/fiscal.ts` | Só o texto de `save_review` / `confirm_stock`. Rótulos de match produtivos ficaram. |
| `language/inventory.ts` | Agrupamento da visão geral e aviso de embalagem. |
| `styles/app.css` | `.manual-path`, `.estoque-util`, `.flow-coach--form`, `html { overflow-x: clip }`. Chrome produtivo (`overflow-wrap: anywhere`) **não** foi apagado. |
| `vite.config.ts` | Proxy lê `PANNE_API_URL` e continua em `:5080` por omissão. |
| Testes fiscais / procurement / costing / isolation / R026-009 | Adaptados ao contrato produtivo (não à árvore `7177805`). |

### Decisões de conflito (contrato, não preferência de árvore)

1. **Política de estoque.** Pacote extraía bootstrap para toda confirmação. Produção usa política inline `recebimento-inicial`. Ficou a de produção; abertura sem NF chama `ensure_published_policy` (`estoque-inicial`).
2. **Custo × rendimento vendável.** Pacote removia o bloco de yield. O bloco produtivo ficou; unknown-cost é extra.
3. **Erros HTTP.** Pacote apagava mensagens de `sale_basis` / revisão. Ficaram; códigos de embalagem entram ao lado.
4. **Códigos de erro no FE.** `errorFromResponse` produtivo mapeia 422 → `regra_dominio`. A consolidação reconhece o recorte usado pela **mensagem** da API, sem alargar o enum.
5. **Colunas da visão geral.** Prévia aprovada: Físico / Reservado / Impedido / Disponível. Não se restaurou “Não reservado” / “Disponível para produção” do teste antigo do pacote.
6. **Gigio.** Produção: Recolher / Abrir. FAB: `Abrir Gigio`. Formulário e `/componentes/estoque` começam recolhidos.

## 2. Testes locais (não homologar o resto)

### Backend (Docker `python:3.12-slim` → Postgres local `panne` `:5434`)

- `python -m compileall app` ok
- 57 passed / 1 deselected (`test_owner_without_bypass_can_issue_and_keeps_force` — exige dono de `access_credential`; o papel Docker não é dono). Código de onboarding **não** mudou.
- Inclui: consolidação, concorrência/replay, preservação nota/lote/saldo/custo/movimento, abertura sem NF, custo desconhecido, isolamento entre clientes, fiscal review sem estoque, receive HTTP com `create_ingredient`, inventory procurement, onboarding/access/productive (exceto o CLI de dono), **`test_0030_from_productive_head_does_not_mutate_existing_rows`**.

`0030` foi aplicada numa base **descartável** criada em `0029_fiscal_review_without_stock` com três farinhas distintas (tipo 1 Globo, tipo 00 Caputo, tipo 1 Anaconda). Depois do upgrade: mesmos nomes, mesmo lote/saldo/hash; `package_content_*` nulo; `cost_status=known` só por default de coluna; `ingredient_link_reassignment` vazio.

Não repetir `test_migrations` full downgrade contra o `panne` compartilhado.

### Frontend

- Build `tsc --noEmit && vite build` ok (OIDC de produção no modo `production` sem `VITE_AUTH_PROVIDER=fake`).
- Vitest dirigido: 59 passed no delta (estoque-visão, uso, 390, first-access, R026-009, isolamento).
- `login-editorial` 6/7: o caso “ajuda pública” espera heading `Ajuda para entrar`; a gaveta produtiva titula `Gigio`. Página de login **não** foi alterada.

## 3. Capturas React autenticadas

Vite isolado `:5183` + API isolada `:5083` (não a árvore produtiva em `:5080/:5182`). `VITE_API_BASE` vazio — sem `api.panne.ia.br`. Org `Ensaio insumo (descartável)`.

Arquivos em `capturas/` e tabela em `COMPARAR-PREVIA.md`.

Conferência visual:

- Estoque 1440: kicker Posição atual, colunas da prévia, Ver lotes, aviso de embalagem, Em trânsito sem zero inventado.
- Estoque 390: cartões, ação final visível, sem overflow horizontal do conteúdo.
- Gigio recolhido na visão geral; abre só no acionador; Ver lotes não abre o coach.
- Consolidar 1440/390/960: destino, compras, conteúdo, Confirmar vínculos visível.
- Abertura: erro vazio, custo desconhecido explícito, confirmação.
- Revisão fiscal 1440/390: nota gravada, entrada à parte.

## 4. Cliente que já tem ingredientes, notas, lotes e movimentos

A migração **não** consolida, **não** abre saldo, **não** recategoriza farinha e **não** atualiza estoque. Só adiciona colunas anuláveis/default e a tabela de auditoria vazia.

Tipo 1, tipo 0 e tipo 00 continuam cadastros distintos. Globo Superiore e Anaconda Premium, se existirem como tipo 1 de marcas diferentes, **não** são fundidos por nome, marca ou GTIN. A consolidação só ocorre por escolha explícita na API/UI, com confirmação.

Receive futuro exige `create_ingredient` ou ingrediente escolhido — sem criar silencioso.

## Riscos residuais

- `test_owner_without_bypass_can_issue_and_keeps_force` não rodou no papel Docker (privilégio). Contrato de onboarding inalterado.
- Abertura agora exige `confirmed`/`origin`/custo; seed Demo antigo que chame o endpoint antigo quebraria — Demo fora de escopo.
- `html { overflow-x: clip }` é global; chrome produtivo de login/custos não foi reaberto além do teste editorial já residual.
- Worktree local usou `.env` copiado (gitignored) e `node_modules` do frontend principal por junction.

Depois do parecer do Cortex, a publicação (foto pré/pós, `alembic upgrade`, ECS) é **outra ordem**.
