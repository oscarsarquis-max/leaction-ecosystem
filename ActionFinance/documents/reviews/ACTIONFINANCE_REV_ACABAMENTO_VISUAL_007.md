# ACTIONFINANCE_REV_ACABAMENTO_VISUAL_007 — Acabamento das telas operacionais

Versão 0.1 — 02/10/2026. Recorte de acabamento. Aceite visual: **NÃO**. Menu publicado e teste verde não equivalem a interface bem acabada.

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_ACABAMENTO_VISUAL_007 |
| Prompt | [ACTIONFINANCE_PROMPT_ACABAMENTO_VISUAL_007](../prompts/ACTIONFINANCE_PROMPT_ACABAMENTO_VISUAL_007.md) |
| Evidência do defeito | [antes-proprietario.png](screenshots/acabamento-visual-007/antes-proprietario.png) — captura do proprietário (clipboard 02/10/2026) |
| Produto | ActionFinance apenas |
| Modelo | Sem mudança |

## Causa

1. `.top` usava coluna `1fr` para a empresa; o `select` com `max-width: 100%` esticava por quase toda a faixa.
2. `input, select` genéricos aplicavam `min-height: 44px` também ao checkbox.
3. `.searchable` era um cartão com borda e dois controles empilhados no meio da linha de filtros.
4. `.filters` em flex, com `align-items: center`, alinhava o botão ao bloco inteiro do label (rótulo + campo), não à caixa.
5. A busca era item flex sem crescimento; o placeholder longo era cortado.
6. No desktop, a segunda faixa de filtros ficava sempre aberta (`innerWidth > 1023`), independente do botão Filtros.
7. A contagem auxiliar do resumo ia para uma linha abaixo do valor.

## Componentes afetados

`app.css` (controles, cabeçalho, `filter-toolbar`, `filter-grid`, `combo`, `.check`), `AppShell` (só CSS do topo), `TitleListPage`, `PayReceiptsPage`, período do extrato, `FinancialSummary`, `SearchableSelect` extraído para combobox de um campo. Sem mudança de menu, Cognito, banco, Hub, Pay, Panne ou Spider.

## Comparação inspecionada pelo executor

Imagens efetivamente abertas nesta revisão (não só listadas):

| Arquivo | Leitura |
|---|---|
| `antes-proprietario.png` | Busca estreita; categoria em cartão duplo; checkbox de campo de texto; empresa esticada; intervalo morto |
| `1848-receber-filtros.png` | Empresa ~320 px; busca larga com placeholder inteiro; uma linha de filtros; checkbox 18 px junto do rótulo; Limpar secundário |
| `1848-receber-categoria.png` | Combobox da mesma altura; lista Todas / Insumos |
| `1280-receber-filtros.png` | Uma linha de filtros com Limpar; checkbox 18 px |
| `768-receber-filtros.png` | Grade quebra em duas linhas; busca + Ocultar filtros alinhados à caixa |
| `360-receber-filtros.png` | Empilhamento em ordem de leitura; checkbox proporcional; Sair visível |

Não redimensionei as imagens para esconder desalinhamento. Medidas em `evidence/acabamento-visual-007/medidas.json` (360/768/1280/1848, checkbox 18 px, empresa 159–320 px, sem overflow da página).

## Gates

`npm test` 51/51, `npm run lint`, `npm run build` (`index-Y5CEdRz0.js` no preview local; o hash público será o do JAR publicado). `npm audit --omit=dev` 0.

## Publicação

| Peça | Valor |
|---|---|
| Commit | `2c6c4c7b` |
| Digest | `sha256:fec29234a5b003e1fddbe57efaa480f65ee8fe4bbfa36e7897b74c55043cfe49` |
| Tarefa | `actionfinance-web:9` · running=1 · COMPLETED |
| SPA pública | `index-DtMFC6jP.js` / `index-4KjDmnSk.css` |
| Rollback | `actionfinance-web:8` · `sha256:32b0bded…` |
| Cognito / Spider | Não alterados |

Consulta autenticada no origin ainda depende de sessão humana. Sem escrita financeira de teste.

## Limitações

Capturas com API simulada; sem escrita financeira em produção. Nome longo no cabeçalho usa reticências, com `title` nativo do select e Sair sempre acessível. Aceite visual permanece com analista/proprietário.
