# ACTIONFINANCE_REV_MAPA_MENUS_006 — Mapa definitivo de menus

Versão 0.1 — 02/10/2026. Recorte de navegação. Aceite: **NÃO**. Não encerra PRM_009, prova Spider, canónica histórica, Pay, APPLY nem PRM_007.

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_MAPA_MENUS_006 |
| Prompt | [ACTIONFINANCE_PROMPT_MAPA_MENUS_006](../prompts/ACTIONFINANCE_PROMPT_MAPA_MENUS_006.md) |
| Histórico | PRM_003 / PRM_004 / PRM_005 e [PROMPT_NOVA_INTERFACE_001](../prompts/ACTIONFINANCE_PROMPT_NOVA_INTERFACE_001.md) permanecem como registro; não foram reescritos |
| Produto | ActionFinance apenas |
| Modelo físico | Sem mudança |

## Mapa final de rotas

| Menu | Submenu | Rota | Observação |
|---|---|---|---|
| Recebimentos | A receber | `/receivables` | Lista existente. Criação: **Nova conta a receber** na página |
| Recebimentos | Transações importadas | `/pay-receipts` | Visível se `receiptSyncEnabled` ou homolog. Título da página: Recebimentos ActionHub Pay (sistema integrado). Importação ≠ liquidação |
| Pagamentos | A pagar | `/payables` | Lista existente. Criação: **Nova conta a pagar** na página |
| Contas | Contas financeiras | `/financial-accounts` | Sem fluxo de caixa, transferência ou conciliação |
| Cadastros | Clientes e fornecedores | `/catalogs/counterparties` | Mesma página de cadastro; seção pela rota |
| Cadastros | Categorias | `/catalogs/categories` | Idem |
| Compatibilidade | — | `/catalogs` | Encaminha a `/catalogs/counterparties` |
| Folha | — | `/settlements/:id` | Sem área própria; barras principais permanecem |

Clicar o menu principal vai ao primeiro submenu da área. Deep link e recarga reconstroem os dois níveis pela rota. Sem Restaurar último destino.

Retirados da navegação global: Mais, Registrar recebível, Registrar pagável, barra inferior, overlay, drawer.

## Diagnóstico da tela azul

Causa identificada no recorte anterior: o destino **Mais** usava overlay `.nav-backdrop` navy semitransparente, painel fixo `.more-panel` com `inert`/focus trap e barra inferior `.bottom-nav` em `--brand-navy` cobrindo o conteúdo (`padding-bottom: 88px`). Se o painel ficasse aberto, o backdrop navy + chrome azul da marca ocupavam a viewport e o conteúdo ficava inacessível ou “azul”.

Correção: remoção completa desse mecanismo (estado `navOpen`, listeners de Escape/Tab, `inert`, backdrop, painel, barra inferior). Modais legítimos (`Modal`) e confirmação de formulário sujo permaneceram. Sem reload/catch vazio para esconder erro.

## Gates locais

| Gate | Resultado |
|---|---|
| `npm test` | 49/49 |
| `npm run lint` | ok |
| `npm run build` | `index-D4veh_k3.js` / `index-BM02UawR.css` |
| Capturas 360/768/1280 | `documents/reviews/screenshots/mapa-menus-006/` — API simulada no Playwright |

## Publicação

| Peça | Valor |
|---|---|
| Commit | `587e6da1` Organize ActionFinance navigation into two explicit menu bars |
| Worktree | `C:\Projetos\.wt-af-ui` detached no mesmo commit |
| JAR | sha256 `73b5e930a2609087df2abebd9a5122b4dd1fd5e9f8c4a39b42a46edf6719fffa` |
| Tag local | `actionfinance:mapa-menus-587e6da1` |
| Digest ECR | `sha256:32b0bdedc30c4f943a05c3fc4b870183c8be6ce7c6fc81f389588ba31e8e87f9` |
| Tarefa | `actionfinance-web:8` · desired=1 · running=1 · COMPLETED |
| Origin | `https://actionfinance.actionhub.com.br` readiness 200 |
| SPA | `/assets/index-D4veh_k3.js` · `/assets/index-BM02UawR.css` |
| Bundle público | Cadastros, Transações importadas, Clientes e fornecedores, Nova conta a receber; sem Mais / more-panel / bottom-nav |
| Rollback | `actionfinance-web:7` · `sha256:b69787a237f9b41947d7bf9283961304d769cb8b51c48e769e2f491b7803826b` |
| Cognito | Não alterado |

Navegação autenticada no origin ainda depende de sessão humana. Sem escrita financeira de teste em produção. Sem restart da Spider.

## Limitações

- Capturas locais usam API simulada; não são jornada financeira real nem sessão pública autenticada.
- Transações importadas só aparece quando a API de info habilita o sync.
- Hosted UI clássico e pendências da interface 001 / PRM_009 permanecem separados.
- Aceite com analista/proprietário.
