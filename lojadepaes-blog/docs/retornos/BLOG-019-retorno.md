# BLOG-019 — retorno

Data: 16/11/2026.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | `git apply` limpo e os 23 testes | **Feito.** |
| 2 | Capturas de `/pt` em 1280 e 390, só do destaque, sem cache e sem faixa branca | **Feito.** |
| 3 | Só o `lepain` com `StartedAt` novo; Loja e Gestão em 200; SSH fechado | **Feito.** |
| 4 | Commit, push e merge no `main` | **Feito** neste commit. |

## O que mudou

Em `.hero-panel img.cover`, a foto passa a `object-position: center top`, `transform-origin: 50% 0` e `transform: scale(1.07)`. Ela cresce a partir do topo, e a faixa clara que vinha no rodapé da própria imagem fica fora da caixa.

## Testes

`pytest tests/test_blog.py`: 23 passaram. O patch não acrescentou teste.

## Produção

Imagem `lojadepaes-blog:blog019-20261116` (`sha256:a948285144e82332b0ea58ce0d7e8f5545b98ddeb9f524cbfe2fa9af2c79469f`). Assets com `?v=d728c41a`. O CSS público traz `scale(1.07)` e `transform-origin: 50% 0`. `remote-deploy.sh` recriou só o `lepain`. A imagem anterior é `lojadepaes-blog:blog018-20261116`.

| Contêiner | StartedAt |
|---|---|
| lepain | 2026-11-16T13:52:08.38705674Z |
| infra-caddy-1 | 2026-11-08T20:34:12.590952489Z |
| infra-api-1 | 2026-11-13T18:16:32.346323845Z |
| gestao-api | 2026-11-12T13:35:32.633165352Z |
| infra-db-1 | 2026-09-20T18:14:08.677061212Z |

LePain (`/pt`), Loja e Gestão responderam 200. A porta 22 ficou fechada. 80 e 443 seguem abertas. Nenhum `.tar` local.

O destaque em produção mostra "Guerra e… Pão". A foto cobre a caixa arredondada até o rodapé, em 1280 e em 390 px. A faixa clara não aparece.

Capturas em `C:\Projetos\claude\2026-11-08-lepain-blog\evidencias\BLOG-019\`: `destaque-pt-1280.png`, `destaque-pt-390.png`.

Para voltar só o blog: em `/opt/lojadepaes-blog/deploy`, gravar `LEPAIN_IMAGE=lojadepaes-blog:blog018-20261116` no `.env` e `docker compose -f docker-compose.prod.yml --env-file .env up -d --force-recreate lepain`.
