# BLOG-013 — retorno

Data: 09/11/2026.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Diagnóstico em produção, antes da mudança | **Feito.** |
| 2 | Quatro PNGs baixados pelo botão e a captura da página | **Feito.** |
| 3 | Testes novos, só o `lepain` recriado, Loja e Gestão em 200, SSH fechado | **Feito.** |
| 4 | Este retorno, commit e push | **Feito** neste commit. |

## Causa

O contêiner já tinha o commit `f8850077`. O hash de `card.js`, `card-fit.js`, `html-to-image.js` e `site.css` dentro da imagem bate com esse commit. O contêiner é `read_only` e o `static/` vem da imagem, não de um volume.

A página `https://lepain.lojadepaes.com.br/pt/card/o-pao-que-guarda-uma-casa` apontava para os nomes novos, sem `?v=`:

| Pedido | Status | Tipo |
|---|---|---|
| `/static/site.css` | 200 | `text/css` |
| `/static/card.js` | 200 | `text/javascript` |
| `/static/card-fit.js` | 200 | `text/javascript` |
| `/static/html-to-image.js` | 200 | `text/javascript` |
| `/static/img/lepain-logo-creme.png` | 200 | `image/png` |
| as seis fontes woff2 e o `miolo.svg` | 200 | fonte em `application/octet-stream` |

Não há CSP. Não há `Cache-Control`. Há `ETag` e `Last-Modified`. Numa carga limpa o quadro já saía verde, com o título a 118 px. O único erro de console era o `favicon.ico` em 404.

O PNG `lepain-o-pao-que-guarda-uma-casa-undefined.png` é o script do canvas, o de antes do BLOG-012: o nome usa `data.lang`, que o HTML novo não envia, e o pão é desenhado em `translate(740, 280)`. Desse botão só restava `data-summary`, então o canvas pintou o fundo, o pão no alto e o resumo. A página sem CSS é o mesmo cache: a folha antiga não tem `.sheet`, e o HTML novo fica sem layout. O navegador guardou os dois arquivos porque o endereço não mudou.

## Correção

O CSS do card foi para o `<head>` da página. JS e CSS do blog saem com `?v=b523b329`. O script do card continua um só. O PNG espera as fontes, o `decode()` do logo e da capa e dois frames; embute as woff2 do próprio domínio; usa `cacheBust` e 1080×1350. Se faltar logo, título ou rodapé, o botão não baixa o arquivo. O nome é `lepain-{slug}-{pt|en}-{tipografico|foto}.png`. As fontes passaram a responder `font/woff2`, porque o `nosniff` recusava `application/octet-stream`.

## Testes

21 passaram. Novos: `test_card_page_inlines_css_and_versions_assets` e `test_card_filename_never_contains_undefined`.

## Produção

Imagem `lojadepaes-blog:blog013-20261109`. Só o `lepain` mudou.

| Contêiner | StartedAt |
|---|---|
| lepain | 2026-11-09T12:55:23.993252648Z |
| infra-caddy-1 | 2026-11-08T20:34:12.590952489Z |
| gestao-api | 2026-11-07T15:12:10.777531884Z |
| infra-api-1 | 2026-11-04T16:05:11.35453791Z |
| infra-db-1 | 2026-09-20T18:14:08.677061212Z |

LePain, Loja e Gestão responderam 200. A porta 22 da Loja ficou fechada. 80 e 443 seguem abertas.

Os quatro PNGs, baixados pelo botão, e a captura da página estão em `C:\Projetos\claude\2026-11-08-lepain-blog\evidencias\BLOG-013\`. Todos os PNGs em 1080×1350, com o nome `lepain-…-pt|en-tipografico|foto.png`.
