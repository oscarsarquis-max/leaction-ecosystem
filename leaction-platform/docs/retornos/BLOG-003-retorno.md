# BLOG-003 — retorno

Data: 08/11/2026. Branch `feat/blog-003-cms-lepain`, base `origin/main` (`49b2a839`), worktree `C:\Projetos\_blog-003`.

O blog deve ler o gateway público **`https://api.actionhub.com.br`**.

- Lista: `GET /api/cms/posts?sistema_destino=lepain&secao=&idioma=&limit=&offset=`
- Um post publicado: `GET /api/cms/posts/{slug}`
- As duas respostas levam `Cache-Control: public, max-age=60`

## Checklist

### 1. Testes — feito

`node --test domain/cms-posts.test.js domain/cms-lepain-patch.test.js` no gateway: 9 testes, 0 falhas.

- O patch rodou duas vezes num banco descartável (`cms_lepain_patch_<pid>` em `localhost:5433`) e a linha antiga ficou `paneldx` / `publicado`, com `secao` e `atualizado_em` nulos. O banco foi apagado no fim.
- LePain sem seção, sem idioma ou sem sentidos responde 400. Uma segunda EN no mesmo grupo responde 409 e não chega a inserir.
- `secao` em `paneldx` responde 400.
- `?sistema_destino=paneldx` continua com `sistema_destino = $1 OR sistema_destino = 'todos'`, sem filtrar seção nem idioma.
- `secao`, `idioma`, `offset` e `GET` por slug (só publicado) passam. O `PUT` grava `atualizado_em = now()`.

### 2. Capturas, sem gravar — feito

Formulário local em `http://localhost:4023`, sessão só no navegador, API interceptada. Nenhum `POST`/`PUT` em `/api/cms/posts`. Nada foi salvo em produção.

- `docs/retornos/evidence/blog-003/novo-insights-pt.png` — Insights, português, sentidos Olhar e Sabor, contador do Instagram, dica de vídeo/áudio.
- `docs/retornos/evidence/blog-003/novo-en-ligada.png` — English, Tradução de “A crosta que escuta”.
- `docs/retornos/evidence/blog-003/novo-right-now.png` — Right Now, tipo Evento, data e válido até.
- `docs/retornos/evidence/blog-003/novo-right-now-mobile.png` — a mesma tela em 390 px.
- `docs/retornos/evidence/blog-003/lista.png` — PT sem par com “sem EN” e “Criar versão EN”; par com “PT ↔ EN”; `paneldx` sem selo de idioma.

“Criar versão EN” abre `/dashboard/cms/novo?grupo_id={id}&secao=...` e só aparece no PT que ainda não tem EN.

### 3. Backup, patch e contagens — feito

Backup, antes do patch:

- Servidor: `/var/lib/leaction-platform/backups/cms_posts-20261108T160451Z.sql`
- Cópia local: `C:\Users\Oscar Sarquis\AppData\Local\cms-backups\cms_posts-20261108T160451Z.sql`
- Tamanho dos dois: **3536 bytes**

A tabela estava vazia (`SELECT count(*) FROM cms_posts` = 0). O arquivo é o esquema.

O patch rodou duas vezes em produção (`ON_ERROR_STOP`). A segunda execução só avisou que coluna e índice já existiam. `\d cms_posts` mostra `secao`, `idioma`, `grupo_id`, `sentidos`, `resumo_instagram`, `right_now_tipo`, `data_evento`, `valido_ate`, `atualizado_em` com default `now()`, o índice único `(grupo_id, idioma) WHERE grupo_id IS NOT NULL`, a FK `ON DELETE SET NULL` e `lepain` no `chk_cms_posts_destino`. `atualizado_em` entrou sem default na mesma sentença do `ADD COLUMN`, para `now()` não preencher linha antiga; em seguida o default passou a valer para insert novo. Nesta tabela não havia linha para preservar. Depois do patch, `count(*)` continuou 0.

`GET` público, antes e depois (os dois momentos iguais):

| `sistema_destino` | HTTP | `count` |
|---|---|---|
| paneldx | 200 | 0 |
| inove4us | 200 | 0 |
| actionhub | 200 | 0 |
| lepain | 200 | 0 (`{"posts":[],"count":0}`) |

Nenhum post de teste foi criado.

### 4. Deploy e gateway — feito, sem o script que troca a árvore inteira

`https://api.actionhub.com.br/health` responde 200, `git_sha` `49b2a83`. O `server.js` dessa máquina, porém, tem rotas de checkout por valor, créditos, assinatura de catálogo e Spider Pay que não estão no `origin/main`. `scripts/deploy/deploy-remote.ps1` apaga `/var/www/leaction-platform` e sobe o zip do git. Isso tiraria essas rotas. O deploy deste ciclo foi só o CMS, em cima da árvore que já estava no ar:

- `services/gateway-api/domain/cms-posts.js`
- formulário, lista, `novo/page.tsx` e `admin-api.ts`
- `shared/database/patch_cms_lepain.sql` (o SQL já tinha sido aplicado)

`admin-api.ts` no servidor já tinha `charged_amount_cents` e campos vizinhos, ausentes no `origin/main`. O arquivo publicado conserva esses campos e ganha os tipos do LePain. O arquivo no git é o de `origin/main` mais os tipos do CMS.

`pm2 restart gateway-api`. Health local depois: gateway `:4001` 200, marketplace `:4012` 200, frontend `:4000` 200. O marketplace não foi reiniciado (uptime segue o de antes).

Leitura pública depois do código novo:

- os quatro destinos continuam `count` 0
- `Cache-Control: public, max-age=60` na lista
- `GET /api/cms/posts/nao-existe-blog-003` → 404
- `?secao=nope` → 400

O frontend foi reconstruído no servidor (`npm run build`, TypeScript ok) com cópia de `.next` para voltar atrás se o build falhasse. `pm2 restart action-hub`. O bundle de produção contém o texto “Criar versão EN”.

### 5. Commit, push e merge

O commit, o push e o merge ficam registrados no final deste arquivo quando o git terminar.

## Comportamento que o blog pode contar

No destino `lepain`, a API exige `secao`, `idioma` e ao menos um sentido. Em `right_now`, exige `right_now_tipo`. No PT, `grupo_id` vira o próprio `id` depois do insert. Na EN, `grupo_id` é o id de um post LePain em PT, e só cabe uma EN por grupo. Nos outros destinos, campo novo preenchido é recusado. `atualizado_em` muda em todo `PUT`.

O filtro `todos` de `paneldx`, `inove4us` e `actionhub` permanece. A lista pública agora também devolve as colunas novas (nulas nos posts antigos) e o `Cache-Control`.
