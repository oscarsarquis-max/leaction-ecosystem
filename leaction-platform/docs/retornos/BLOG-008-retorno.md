# BLOG-008 — retorno (Hub)

Data: 08/11/2026. Branch `feat/blog-008-instagram`, base `origin/main` (`0b9fdda5`), worktree `C:\Projetos\_blog-008`. Sem `deploy-remote.ps1`.

O blog não cabe nesta branch: `feat/blog-006-acabamento` (`f3c8baec`) não é ancestral do `main`. O blog está em `feat/blog-008-instagram-blog`, no outro worktree.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Testes novos do CMS e do patch | **Feito.** 15 testes, 0 falhas. |
| 2 | Patch em produção, backup e `\d cms_posts` | **Feito.** Contagens públicas iguais. |
| 3 | Captura do painel Instagram | **Feito.** API interceptada; nenhuma escrita saiu do navegador. |
| 4 | Loja, Gestão e LePain em 200; porta 22 fechada | **Feito.** A porta 22 desta sessão foi fechada no host do blog. |
| 5 | Este retorno, commit e push | **Feito** neste commit. |

## 1. Testes

`node --test domain/cms-posts.test.js domain/cms-lepain-instagram-patch.test.js` no gateway:

```
pass 15
fail 0
```

Os novos:

- `aceita só no LePain e só no domínio do Instagram` — `https://www.instagram.com/...` e `https://instagram.com/...` passam; vazio vira `null`; `http`, host parecido e outro domínio falham; `instagram_url` em `paneldx` responde com a recusa de campo do LePain.
- `recusa o link fora do LePain e devolve o aceito no GET público` — `PUT` em `paneldx` e URL fora do Instagram respondem 400; o `PUT` aceito volta no `GET` público.
- `roda duas vezes e deixa a linha antiga sem link` — o SQL roda duas vezes num banco descartável; a coluna é `text` e nullable; a linha que já existia continua com `instagram_url` nulo.

Os testes anteriores do filtro `todos`, do LePain, do Right Now e de editar/despublicar/excluir continuam passando.

## 2. Produção

Backup antes do patch, 11342 bytes:

- Servidor: `/var/lib/leaction-platform/backups/cms_posts-20261108T192132Z.sql`
- Cópia local: `C:\Users\Oscar Sarquis\AppData\Local\cms-backups\cms_posts-20261108T192132Z.sql`

O patch rodou duas vezes (`ON_ERROR_STOP`). A segunda avisou que `instagram_url` já existia. `\d cms_posts` mostra `instagram_url | text`, nullable, sem default. As outras colunas ficaram como estavam.

Contagens, antes e depois, no banco e no `GET` público:

| `sistema_destino` | publicados |
|---|---|
| paneldx | 0 |
| inove4us | 0 |
| actionhub | 0 |
| lepain | 2 |

Depois do código, o `GET` público dos dois posts do LePain inclui `instagram_url`. Os dois estão `null` de novo, depois de remover o exemplo.

Arquivos publicados, em cima da árvore que já estava no ar:

- `services/gateway-api/domain/cms-posts.js`
- `CmsPostForm.tsx`
- `admin-api.ts`
- `shared/database/patch_cms_lepain_instagram.sql`

`admin-api.ts` no servidor já tinha `charged_amount_cents` e os campos vizinhos, ausentes no `origin/main`. O arquivo publicado conserva esses campos e ganha `instagram_url` nos dois tipos. O arquivo no git é o de `origin/main` mais `instagram_url`.

`pm2 restart gateway-api` e `pm2 restart action-hub`. O marketplace não foi reiniciado.

| Serviço | HTTP | `pm_uptime` |
|---|---|---|
| gateway `:4001` | 200 | mudou (reinício) |
| frontend `:4000` | 200 | mudou (reinício) |
| marketplace `:4012` | 200 | `1791409944012` (igual) |

`inove4us-school` não foi reiniciado (`1789741347472`).

## 3. Captura e o exemplo

`docs/retornos/evidence/blog-008/painel-instagram.png` — painel Instagram da edição, em `http://localhost:4023`, com o campo "Link do post no Instagram" e a legenda terminando em `@loja.de.paes`. A API em `/hub-api` foi interceptada. Nenhum `POST`, `PUT` ou `DELETE` saiu do navegador.

No post de teste PT (id 1) foi gravado `https://www.instagram.com/p/blog008-exemplo/` e, em seguida, removido. O `PUT` não mexeu no resumo (`estrutura..`). O post EN continuou com `instagram_url` nulo. O `GET` público do slug PT voltou a `null`. O post não foi excluído.

## Comportamento

A coluna aceita nulo. A API só grava o link no destino `lepain`, e só se o endereço for `https://www.instagram.com/...` ou `https://instagram.com/...`, com caminho. No painel da edição publicada, cada idioma tem o seu campo, porque cada idioma é um post. A legenda pronta termina com `@loja.de.paes`.
