# BLOG-022 — retorno (Hub)

Data: 16/11/2026. Branch `feat/blog-022-right-now-v2`. Sem `deploy-remote.ps1`.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Testes novos do patch e da API | **Feito.** |
| 2 | Backup, patch duas vezes, `\d` e contagens públicas iguais | **Feito.** |
| 3 | Formulário do Right Now e a tela Enquetes no ar | **Feito.** |
| 4 | Gateway, marketplace e frontend em 200; a porta 22 do Hub ficou só no IP atual | **Feito.** |
| 5 | Este retorno, commit, push e merge | **Feito** neste commit. |

## Testes

`node --test domain/cms-posts.test.js domain/cms-right-now.test.js` no gateway: 18 testes, 0 falhas. Os 14 que já existiam continuam passando. Os novos:

- O patch roda duas vezes. A linha antiga fica `publicado`, `origem = manual`, sem link e sem fonte.
- `sugestao` e `descartado` não entram no GET público.
- Sem `X-LePain-Key` a rota privada responde 401. O mesmo visitante no `quero` não soma de novo (`novo: false`, contagem igual).
- O segundo voto responde 409. Enquete fechada responde 410.

## Produção

Backup de `cms_posts`, antes do patch, 26471 bytes:

- Servidor: `/var/lib/leaction-platform/backups/cms_posts-20261116T174326Z.sql`
- Cópia local: `C:\Users\Oscar Sarquis\AppData\Local\cms-backups\cms_posts-20261116T174326Z.sql`

O patch rodou duas vezes (`ON_ERROR_STOP`). A segunda avisou que coluna e tabela já existiam. `\d` mostra `link_url`, `fonte`, `origem` (padrão `manual`) e `sugestao_expira_em` em `cms_posts`, mais `cms_reacoes`, `cms_enquetes` e `cms_votos` com o único de visitante. O status aceita `sugestao` e `descartado`. O tipo aceita `curiosidade` e `parceiro`.

Contagens públicas, antes e depois:

| `sistema_destino` | HTTP | `count` |
|---|---|---|
| paneldx | 200 | 0 |
| inove4us | 200 | 0 |
| actionhub | 200 | 0 |
| lepain | 200 | 4 |

Depois do código, o GET do LePain inclui `link_url`, `fonte`, `origem` e `quero_count`.

Arquivos publicados, em cima da árvore que já estava no ar:

- `services/gateway-api/domain/cms-posts.js`
- `services/gateway-api/domain/cms-right-now.js`
- `shared/database/patch_cms_right_now_v2.sql`
- `admin-api.ts`, `CmsPostForm.tsx`, `CmsPostsList.tsx`
- `CmsEnquetes.tsx` e `dashboard/cms/enquetes/page.tsx`

`pm2 restart gateway-api` e, depois do `npm run build`, `pm2 restart action-hub`. Marketplace e escola não foram reiniciados.

| Serviço | HTTP | `pm_uptime` |
|---|---|---|
| gateway `:4001` | 200 | mudou |
| frontend `:4000` | 200 | mudou |
| marketplace `:4012` | 200 | `1791409944012` (igual) |

`inove4us-school` não foi reiniciado (`1789741347472`). A página de enquetes entrou no build. A regra de SSH do Hub ficou uma só, a do IP atual. A da Loja foi fechada no fim do ciclo.

## Comportamento

O GET público continua só com `publicado`. O `quero` e o voto exigem `X-LePain-Key` e param em 30 pedidos por minuto por IP; o blog manda o IP do visitante. O mesmo visitante não soma o `quero` duas vezes. O voto repetido é 409 e a enquete fechada é 410. O resultado da enquete só vem se a pessoa já votou ou se a enquete fechou. No painel, o Right Now ganha Curiosidade, Parceiro, Link e Fonte. A tela Enquetes grava de 2 a 4 opções em PT e EN e não publica uma segunda enquete no mesmo período.
