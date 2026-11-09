# BLOG-014 — retorno

Data: 09/11/2026.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Quatro PNGs baixados pelo botão, depois de recarregar sem cache | **Feito.** |
| 2 | Só o `lepain` com `StartedAt` novo; os três sites em 200; SSH fechado | **Feito.** |
| 3 | Este retorno, commit e push | **Feito** neste commit. |

## O que mudou

No tipográfico o pão tem 600 px, à direita (`right: -130px`) e com a base 150 px acima do fim do quadro. Na cópia do PNG o `bottom` sozinho deixava o desenho em cima do título, então o mesmo lugar também está em `top: 600px` (1350 − 600 − 150). O resumo ficou com `max-width: 600px`. O título não mudou. No PNG o texto termina antes do traço do pão.

A faixa branca da foto está no arquivo da capa: 11 px à direita, cerca de 2% da largura. A imagem cobre a caixa (`width` e `height` 100%, `object-fit: cover`, `display: block`) e o corte usa `object-position: left center` com `scale(1.02)` a partir da esquerda, para levar embora essa borda. No PNG novo não há coluna branca.

As etiquetas não quebram linha. Se não couberem, a fonte desce de 16 até 13 px, depois o espaçamento vai a 0,12 em e o padding horizontal a 14 px. PT e EN, com os quatro sentidos, saem numa linha só.

## Produção

Imagem `lojadepaes-blog:blog014-20261109`. Os assets vão com `?v=681183b9`.

| Contêiner | StartedAt |
|---|---|
| lepain | 2026-11-09T13:15:31.328478928Z |
| infra-caddy-1 | 2026-11-08T20:34:12.590952489Z |
| gestao-api | 2026-11-07T15:12:10.777531884Z |
| infra-api-1 | 2026-11-04T16:05:11.35453791Z |
| infra-db-1 | 2026-09-20T18:14:08.677061212Z |

LePain, Loja e Gestão responderam 200. A porta 22 da Loja ficou fechada. 80 e 443 seguem abertas.

Os quatro PNGs estão em `C:\Projetos\claude\2026-11-08-lepain-blog\evidencias\BLOG-014\`, todos em 1080×1350.
