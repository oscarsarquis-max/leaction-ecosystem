# BLOG-021 — retorno

Data: 16/11/2026.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | `git apply` limpo e os 23 testes | **Feito.** |
| 2 | PNGs baixados pelo botão do card com foto, sem linha clara na base nem nas laterais | **Feito.** |
| 3 | Só o `lepain` com `StartedAt` novo; Loja e Gestão em 200; SSH fechado | **Feito.** |
| 4 | Commit, push e merge no `main` | **Feito** neste commit. |

## O que mudou

Em `.sheet-b .photo img`, a foto passa a `object-position: center top` e `transform-origin: 50% 0`. O `transform: scale(1.09)` continua. O crescimento sai do topo: as laterais perdem cerca de 4,5% cada, a base chega a cerca de 9%, e o topo da foto permanece inteiro. Some a faixa clara de baixo da capa do Nº 02.

## Testes

`pytest tests/test_blog.py`: 23 passaram. O patch não acrescentou teste.

## Produção

Imagem `lojadepaes-blog:blog021-20261116` (`sha256:f050e173a1eda13e173d84b58f03b5c6afd1b6d26f628e5e136ad5583e94fca7`). Assets com `?v=b182a49e`. O HTML do card traz `object-position: center top`, `transform-origin: 50% 0` e `scale(1.09)`. `remote-deploy.sh` recriou só o `lepain`. A imagem anterior é `lojadepaes-blog:blog020-20261116`.

| Contêiner | StartedAt |
|---|---|
| lepain | 2026-11-16T17:06:10.814523811Z |
| infra-caddy-1 | 2026-11-08T20:34:12.590952489Z |
| infra-api-1 | 2026-11-16T15:30:40.808666811Z |
| gestao-api | 2026-11-12T13:35:32.633165352Z |
| infra-db-1 | 2026-09-20T18:14:08.677061212Z |

LePain, Loja e Gestão responderam 200. A porta 22 ficou fechada. 80 e 443 seguem abertas. Nenhum `.tar` local.

Os PNGs saíram do botão "Baixar PNG" / "Download PNG", com o cache desligado. O estilo calculado da foto foi `object-position: 50% 0%` e `transform-origin` no topo, com escala 1.09. O Nº 02 mostra "Guerra e… Pão" e "War and... Bread": a base é a mesa de madeira e as laterais ficam escuras, sem linha clara. O Nº 01, "O pão que guarda uma casa", leva a cozinha até as bordas; o claro da base é a bancada, não uma faixa.

Capturas em `C:\Projetos\claude\2026-11-08-lepain-blog\evidencias\BLOG-021\`: `lepain-guerra-e-pao-pt-foto.png`, `lepain-war-and-bread-en-foto.png`, `lepain-o-pao-que-guarda-uma-casa-pt-foto.png`.

Para voltar só o blog: em `/opt/lojadepaes-blog/deploy`, gravar `LEPAIN_IMAGE=lojadepaes-blog:blog020-20261116` no `.env` e `docker compose -f docker-compose.prod.yml --env-file .env up -d --force-recreate lepain`.
