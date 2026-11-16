# BLOG-018 — retorno

Data: 16/11/2026.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | `git apply` limpo e os 23 testes | **Feito.** |
| 2 | Capturas de `/pt` e `/en`, em 1280 e 390, sem cache | **Feito.** |
| 3 | Só o `lepain` com `StartedAt` novo; Loja e Gestão em 200; SSH fechado | **Feito.** |
| 4 | Commit, push e merge no `main` | **Feito** neste commit. |

## O que mudou

O cartão abaixo do destaque ganhou o título "Insights anteriores" / "Earlier insights". O bloco colorido mostra os quatro primeiros versos do poema, com "do poema" / "from the poem". O botão passou a "Ler o ensaio →" / "Read the essay →", e o tipo de mídia foi para a linha do sentido. Com um post anterior, o cartão fica horizontal a partir de 760 px. A foto de capa do destaque cobre a caixa (`scale(1.03)`). O cartão é o partial `_story_card.html`, na Home e em `/insights`.

## Testes

`pytest tests/test_blog.py`: 23 passaram. Os dois novos são `test_earlier_card_shows_the_poem_and_reads_as_earlier` e `test_poem_lines_needs_two_consecutive_short_verses`.

## Produção

Imagem `lojadepaes-blog:blog018-20261116` (`sha256:44d93068365bb6e6b5771c8f1d17cc0e0c1f4e2f0dca0bc34d0170130d541c8a`). Assets com `?v=574e73d4`. `remote-deploy.sh` recriou só o `lepain`. A imagem anterior é `lojadepaes-blog:blog015-20261109`.

| Contêiner | StartedAt |
|---|---|
| lepain | 2026-11-16T13:33:38.568075201Z |
| infra-caddy-1 | 2026-11-08T20:34:12.590952489Z |
| infra-api-1 | 2026-11-13T18:16:32.346323845Z |
| gestao-api | 2026-11-12T13:35:32.633165352Z |
| infra-db-1 | 2026-09-20T18:14:08.677061212Z |

LePain (`/pt` e `/en`), Loja e Gestão responderam 200. A porta 22 ficou fechada. 80 e 443 seguem abertas. Nenhum `.tar` local.

A home em produção mostra "Guerra e… Pão" no destaque, com a foto cobrindo a caixa, e abaixo "Insights anteriores" com o cartão de "O pão que guarda uma casa" e os versos. Em inglês, "Earlier insights" e "The Bread That Holds a Home".

Capturas em `C:\Projetos\claude\2026-11-08-lepain-blog\evidencias\BLOG-018\`: `home-pt-1280.png`, `home-pt-390.png`, `home-en-1280.png`, `home-en-390.png`.

Para voltar só o blog: em `/opt/lojadepaes-blog/deploy`, gravar `LEPAIN_IMAGE=lojadepaes-blog:blog015-20261109` no `.env` e `docker compose -f docker-compose.prod.yml --env-file .env up -d --force-recreate lepain`.
