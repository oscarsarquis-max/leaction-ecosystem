# BLOG-020 — retorno

Data: 16/11/2026.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | `git apply` limpo e os 23 testes | **Feito.** |
| 2 | PNGs baixados pelo botão do card com foto, sem faixa clara | **Feito.** |
| 3 | Só o `lepain` com `StartedAt` novo; Loja e Gestão em 200; SSH fechado | **Feito.** |
| 4 | Commit, push e merge no `main` | **Feito** neste commit. |

## O que mudou

Em `.sheet-b .photo img`, a foto passa a `object-position: center`, `transform-origin: center` e `transform: scale(1.09)`. O corte fica igual nas quatro bordas, cerca de 4,5% em cada uma. Somem a faixa clara de baixo e a faixa clara da direita que vinham na própria capa.

## Testes

`pytest tests/test_blog.py`: 23 passaram. O patch não acrescentou teste.

## Produção

Imagem `lojadepaes-blog:blog020-20261116` (`sha256:d0c845577156f9f32fdb097edca7d55ec224b091ab3e15d77e6ca6159ec3f766`). Assets com `?v=3e21b6ca`. O HTML do card traz `scale(1.09)` e `object-position: center`. `remote-deploy.sh` recriou só o `lepain`. A imagem anterior é `lojadepaes-blog:blog019-20261116`.

| Contêiner | StartedAt |
|---|---|
| lepain | 2026-11-16T14:17:29.334683309Z |
| infra-caddy-1 | 2026-11-08T20:34:12.590952489Z |
| infra-api-1 | 2026-11-13T18:16:32.346323845Z |
| gestao-api | 2026-11-12T13:35:32.633165352Z |
| infra-db-1 | 2026-09-20T18:14:08.677061212Z |

LePain, Loja e Gestão responderam 200. A porta 22 ficou fechada. 80 e 443 seguem abertas. Nenhum `.tar` local.

Os PNGs saíram do botão "Baixar PNG" / "Download PNG", com o cache desligado. O Nº 02 mostra "Guerra e… Pão" e "War and... Bread": o menino entra inteiro e a mesa chega ao canto, sem faixa branca. O Nº 01, "O pão que guarda uma casa", leva a cozinha até a borda direita, sem faixa clara.

Capturas em `C:\Projetos\claude\2026-11-08-lepain-blog\evidencias\BLOG-020\`: `lepain-guerra-e-pao-pt-foto.png`, `lepain-war-and-bread-en-foto.png`, `lepain-o-pao-que-guarda-uma-casa-pt-foto.png`.

Para voltar só o blog: em `/opt/lojadepaes-blog/deploy`, gravar `LEPAIN_IMAGE=lojadepaes-blog:blog019-20261116` no `.env` e `docker compose -f docker-compose.prod.yml --env-file .env up -d --force-recreate lepain`.
