# BLOG-022 — retorno (blog)

Data: 16/11/2026. Branch `feat/blog-022-right-now-v2`.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Testes novos do cookie, do hash e do `.ics` | **Feito.** |
| 2 | `quero` duas vezes, enquete nula e `.ics` de um evento de teste, depois apagado | **Feito.** |
| 3 | Só o `lepain` com `StartedAt` novo; Loja e Gestão em 200; SSH da Loja fechado | **Feito.** |
| 4 | Este retorno, commit, push e merge | **Feito** neste commit. |

## Testes

`pytest tests/test_rn.py tests/test_blog.py`: 26 passaram. Os 23 de `test_blog.py` continuam. Os novos:

- A primeira chamada cria o cookie `lp_vid` (HttpOnly, SameSite=Lax, um ano). O `visitante` enviado ao Hub é `sha256(lp_vid + segredo)`.
- A segunda chamada, com o mesmo cookie, manda o mesmo hash.
- Sem enquete aberta, `GET /api/rn/enquete` devolve `null`.
- O `.ics` de um evento traz `BEGIN:VCALENDAR`, a data, o título e o link. Promoção responde 404.

## Produção

Imagem `lojadepaes-blog:blog022-20261116` (`sha256:035193b7cbfc6c59eb3b932927c292ee37639e8c493f086f7705db7a10c57092`). Assets com `?v=58cc6b07`. `remote-deploy.sh` recriou só o `lepain`. A imagem anterior é `lojadepaes-blog:blog021-20261116`.

| Contêiner | StartedAt |
|---|---|
| lepain | 2026-11-16T18:01:52.946469684Z |
| infra-caddy-1 | 2026-11-08T20:34:12.590952489Z |
| infra-api-1 | 2026-11-16T15:30:40.808666811Z |
| gestao-api | 2026-11-12T13:35:32.633165352Z |
| infra-db-1 | 2026-09-20T18:14:08.677061212Z |

LePain, Loja e Gestão responderam 200. A porta 22 da Loja ficou fechada. 80 e 443 seguem abertas. Nenhum `.tar` local.

Com o cache desligado no pedido:

- `GET /api/rn/enquete?idioma=pt` respondeu `null` e criou o cookie.
- `POST /api/rn/quero` duas vezes, com o mesmo cookie, devolveu `voted: true` e a mesma contagem (`1`).
- `GET /pt/right-now/blog022-evento-teste.ics` veio `text/calendar`, com a data, o título e o link do item.
- O evento de teste foi apagado em seguida. O mesmo `.ics` passou a responder 404.

Os itens do Right Now passam a trazer `link_url`, `fonte`, `quero_count`, `origem` e o tipo, inclusive `curiosidade` e `parceiro`.

Para voltar só o blog: em `/opt/lojadepaes-blog/deploy`, gravar `LEPAIN_IMAGE=lojadepaes-blog:blog021-20261116` no `.env` e `docker compose -f docker-compose.prod.yml --env-file .env up -d --force-recreate lepain`.
