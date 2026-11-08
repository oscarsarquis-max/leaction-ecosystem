# BLOG-007 — retorno

Data: 08/11/2026. Branch `feat/blog-007-cms-editar`, base `origin/main` (`50c72cdb`), worktree `C:\Projetos\_blog-007`. Sem migração. Sem `deploy-remote.ps1`.

Não havia rota de edição. O `PUT /api/cms/posts/:id` já existia e a lista não apontava para ele. A lista agora abre `/dashboard/cms/{id}`, o mesmo formulário do Novo Post. A leitura que faltava é só `GET /api/cms/posts/admin/:id`, inclusive rascunho.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Testes do CMS | **Feito.** 12 testes, 0 falhas. |
| 2 | Capturas locais, API interceptada | **Feito.** Nenhum `POST`, `PUT` ou `DELETE` saiu do navegador. |
| 3 | Deploy só dos arquivos do CMS; 3 serviços em 200; contagens iguais | **Feito.** |
| 4 | Edição do post de teste PT (id 1) em produção, sem excluir | **Feito.** |
| 5 | Este retorno, commit, push e fast-forward do `main` | **Feito.** O `main` estava em `50c72cdb` e avançou para este commit. |

## 1. Testes

`node --test domain/cms-posts.test.js` no gateway:

```
pass 12
fail 0
```

Os novos:

- `GET admin por id devolve rascunho` — `GET /api/cms/posts/admin/9` devolve o rascunho; o `GET` público do mesmo slug responde 404.
- `PUT grava campos LePain e a validação de antes continua` — sentidos e `resumo_instagram` gravam; sentidos vazios respondem 400 e não atualizam; `secao` em `paneldx` responde 400.
- `despublicar some do GET público` — `PUT` com `status: rascunho` tira o post da lista e do slug públicos; o admin por id ainda o devolve.
- `excluir uma PT com EN apaga as duas e deixa os outros destinos` — apaga os ids 1 e 2; o `paneldx` continua; excluir o `paneldx` apaga só ele.

Os testes anteriores do filtro `todos`, do LePain e do Right Now continuam passando.

## 2. Capturas

Sessão só no navegador, em `http://localhost:4023`. A API em `/hub-api` foi interceptada. Nada foi gravado por essa tela.

- `docs/retornos/evidence/blog-007/lista-menu.png` — a linha do levain com ⋯: Editar, Despublicar, Ver no blog, Excluir. Selos LePain, PT, PT ↔ EN. “Outro ensaio” com sem EN e Criar versão EN. `paneldx` sem selo de idioma.
- `docs/retornos/evidence/blog-007/editar-instagram.png` — Editar post, Salvar, Salvar e publicar, painel Instagram com Card PT, Card EN, a legenda e Copiar.
- `docs/retornos/evidence/blog-007/aviso-slug.png` — “O endereço no blog muda”, com Cancelar e Continuar.
- `docs/retornos/evidence/blog-007/excluir-duas-versoes.png` — o título do post e o único botão “Excluir as duas versões”.

## 3. Deploy

Arquivos publicados, em cima da árvore que já estava no ar:

- `services/gateway-api/domain/cms-posts.js`
- `CmsPostForm.tsx`, `CmsPostsList.tsx` e a página nova `dashboard/cms/[id]/page.tsx`
- `admin-api.ts`

`admin-api.ts` no servidor já tinha `charged_amount_cents` e os campos vizinhos, ausentes no `origin/main`. O arquivo publicado conserva esses campos e ganha `fetchCmsPostAdmin` e `deleteCmsPost`. O arquivo no git é o de `origin/main` mais essas duas funções.

`pm2 restart gateway-api` e `pm2 restart action-hub`. O marketplace não foi reiniciado.

| Serviço | HTTP | `pm_uptime` |
|---|---|---|
| gateway `:4001` | 200 | mudou (reinício) |
| frontend `:4000` | 200 | mudou (reinício) |
| marketplace `:4012` | 200 | `1791409944012` (igual) |

Contagens públicas, antes e depois:

| `sistema_destino` | `count` |
|---|---|
| paneldx | 0 |
| inove4us | 0 |
| actionhub | 0 |
| lepain | 2 |

## 4. Post de teste

`PUT /api/cms/posts/1` acrescentou um ponto ao resumo. O post não foi excluído. O par em inglês permanece.

- Admin por id: 200, publicado, slug `levain-e-a-porcentagem-de-padeiro`.
- `GET` público do slug: 200, o resumo passa a terminar em `estrutura..`.
- O blog em `https://lepain.lojadepaes.com.br/pt/insights/levain-e-a-porcentagem-de-padeiro` já mostrava `estrutura..` na mesma leitura, dentro dos 5 minutos.

## Comportamento

A linha da lista é um link para a edição. O ⋯ publica ou despublica pelo `PUT` que já existia. “Ver no blog” só aparece em LePain publicado. Excluir uma PT com EN apaga as duas; nos outros destinos, e numa EN sozinha, apaga uma. Não há exclusão em massa. Mudar o slug de um post publicado pede confirmação. Sair com alteração não salva também pede. Depois de salvar, a edição mostra “Salvo. No blog, aparece em até 5 minutos.”
