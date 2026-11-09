# BLOG-012 — retorno

Data: 09/11/2026.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Testes novos | **Feito.** 19 passaram, entre eles os quatro deste ciclo. |
| 2 | PNGs A e B, PT e EN, em 1080×1350, ao lado dos quadros 06A e 06B | **Feito.** |
| 3 | Painel do CMS com os quatro links | **Feito.** |
| 4 | Só o `lepain` com `StartedAt` novo; Hub em 200; SSH da Loja fechado; regra do Hub no IP atual | **Feito.** |
| 5 | Este retorno, commit e push | **Feito** neste commit. |

## Card

`/{l}/card/{slug}` segue o desenho em pixels. Sem `modelo`, ou com um valor desconhecido, cai em `tipografico`. `foto` sem capa responde 302 para o modelo A.

O PNG sai do próprio DOM, com `html-to-image` 1.11.13 (MIT, servido em `/static/html-to-image.js`), em 1080×1350 e `pixelRatio` 1, depois das fontes e da imagem. A capa entra por `/media/capa/{slug}`, que só busca o bucket do CMS. Outro domínio responde 400, antes de qualquer download.

O título reduz de 6 em 6 px até 80 no A e 72 no B. O resumo cabe em 4 linhas no A e 3 no B.

## Testes

`tests/test_blog.py`, suíte completa: 19 passaram.

- `test_card_modelo_defaults_to_tipografico`
- `test_foto_without_cover_redirects_to_tipografico`
- `test_media_capa_refuses_a_host_outside_the_bucket`
- `test_long_title_shrinks_to_the_floor`

## Evidência

Pasta `docs/retornos/evidence/blog-012/`. Os quatro cards e os dois quadros de referência estão em 1080×1350.

| Arquivo | O que é |
|---|---|
| `pt-tipografico.png` `en-tipografico.png` | Modelo A dos posts 3 e 4 |
| `pt-foto.png` `en-foto.png` | Modelo B dos posts 3 e 4 |
| `06A.png` `06B.png` | Quadros do desenho, com o logo do LePain |
| `painel-instagram.png` | Card PT · Tipográfico, Card PT · Com foto, Card EN · Tipográfico, Card EN · Com foto |

## Deploy

Imagem `lojadepaes-blog:blog012-20261109`. O script recriou só o `lepain`.

| Contêiner | StartedAt |
|---|---|
| lepain | 2026-11-09T12:17:57.548158342Z |
| infra-caddy-1 | 2026-11-08T20:34:12.590952489Z |
| gestao-api | 2026-11-07T15:12:10.777531884Z |
| infra-api-1 | 2026-11-04T16:05:11.35453791Z |
| infra-db-1 | 2026-09-20T18:14:08.677061212Z |

No Hub, só `CmsPostForm.tsx`. Build do frontend e restart do `action-hub`. Gateway, marketplace e frontend responderam 200. Os outros processos do PM2 não foram reiniciados.

A porta 22 da Loja ficou fechada. Continuam abertas 80 e 443. No Hub, a porta 22 ficou só no /32 desta máquina (`world=0`, `mine=1`, `other=0`). 80 e 443 seguem abertas para a internet.
