# BLOG-024 — retorno (Hub)

Data: 19/11/2026. Branch `feat/blog-024-sugestoes-diarias`. Sem `deploy-remote.ps1`.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Testes novos verdes (validação, dedupe, expiração, publicar PT+EN, batchexecute) | **Feito.** `node --test domain/cms-sugestoes.test.js` → 7/7. Regressão posts/right-now → 18/18. |
| 2 | Gerar agora em produção + captura com até 5 pares; link e HTTP por par | **Feito.** 5 pares. Evidência em `C:\Projetos\claude\2026-11-08-lepain-blog\evidencias\BLOG-024\` (`pairs-evidence.json`, `sugestoes-tela.png`). Todos os links em **200**. |
| 3 | Nada publicado; contagem pública LePain igual à de antes | **Feito.** Antes e depois: **6**. |
| 4 | Job às 07:00 America/Sao_Paulo + log de execução sem segredos | **Feito.** Scheduler em `cms-sugestoes.js` (`hour === 7 && minute === 0`) iniciado em `server.js`. Execução sob demanda gerou 5 pares (`GERAR_RESULT created:5`). GiroNews respondeu 403 (feed opcional). |
| 5 | Serviços Hub em 200; regra SSH só no IP atual | **Feito.** Gateway `:4001` 200; frontend `:4000` 200; marketplace não reiniciado. SG `sg-08a0721444e6176b3` porta 22 = IP atual `/32`. |
| 6 | Commit, push, merge no `main` e este retorno | **Feito** neste ciclo. |

## Produção

Backup de `cms_posts` antes do patch:

- Servidor: `/var/lib/leaction-platform/backups/cms_posts-20261119T124314Z.sql` (24591 bytes)

Patch `patch_cms_sugestoes_diarias.sql` rodou duas vezes (`ON_ERROR_STOP`). Colunas `trecho_base` e `data_materia` presentes.

Arquivos publicados em cima da árvore no ar (sem `deploy-remote.ps1`):

- `shared/database/patch_cms_sugestoes_diarias.sql`
- `services/gateway-api/config/cms-sugestoes-fontes.json`
- `services/gateway-api/domain/cms-sugestoes*.js` (+ test)
- `services/gateway-api/domain/cms-posts.js`, `server.js`, `package.json` / lock
- `frontend/action-hub` — `admin-api.ts`, `CmsPostsList.tsx`, `CmsSugestoes.tsx`, `dashboard/cms/sugestoes/page.tsx`

`pm2 restart gateway-api` e, após `npm run build`, `pm2 restart action-hub`. Marketplace e escola não reiniciados.

Contagem pública LePain: **6** antes e **6** depois. Nada foi publicado pelo job.

### Pares gerados (Gerar agora)

| grupo_id | HTTP | Fonte / link |
|---|---|---|
| 20 | 200 | itatiaia.com.br — pãozinho / custos |
| 18 | 200 | diariodocentrodomundo.com.br — fermentação natural |
| 16 | 200 | noticiasaominuto.com — Padaria Portuguesa |
| 14 | 200 | vivaacidadenews.com.br — Mundo Pão Olivier |
| 12 | 200 | g1.globo.com — item de padaria (revisão do Oscar) |

Correção crítica pós-deploy: o redirect do Google News (pós-2024) não segue HTTP; o job passou a resolver via `data-n-a-sg` / `data-n-a-ts` + `batchexecute` (`Fbv4je`).

## Comportamento

Sugestões entram com `status=sugestao`, `origem=auto`, `sugestao_expira_em` +48h, par PT/EN no mesmo `grupo_id`. O GET público continua só com `publicado`. A tela **Sugestões do dia** (ao lado de Enquetes) permite editar, publicar PT+EN num clique ou descartar. Teto de 5 pares/dia.
