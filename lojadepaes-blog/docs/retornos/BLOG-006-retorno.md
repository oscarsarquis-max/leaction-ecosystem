# BLOG-006 — Retorno

Data: 08/11/2026. Branch `feat/blog-006-acabamento`, a partir de `27db5f4f` (`feat/blog-004-publicacao`). O visual ficou congelado: as caixas, os raios e as alturas são os mesmos. Mudou o conteúdo. Nada foi alterado na Loja, na Gestão, no Caddy nem no Hub. O redeploy recriou só o contêiner `lepain`.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Testes novos | **Feito.** `12 passed` em 0,93 s. Os três novos estão abaixo. |
| 2 | Capturas em 1280 e 390: Home PT e post PT/EN, foto do levain, "Editor LePain", "Nº 01" | **Feito.** Pasta `docs/retornos/blog-006/`. |
| 3 | Cards PT e EN com "Nº 01" | **Feito.** `card-pt.png` e `card-en.png`. |
| 4 | Loja e Gestão em 200, `StartedAt` dos outros contêineres igual, porta 22 fechada | **Feito.** |
| 5 | Este retorno, commit e push | **Feito** neste commit. |

## 1. Testes

```
12 passed, 1 warning in 0.93s
```

O aviso é a depreciação do Starlette sobre `httpx` no `TestClient`. Não é falha. Os nove testes anteriores continuam passando.

Os testes novos, com o Hub simulado:

- `test_en_inherits_pt_issue_number` — a EN do grupo publicado primeiro mostra "Nº 01", mesmo com data posterior; a PT seguinte mostra "Nº 02". O card repete o número.
- `test_cover_present_and_absent` — com `imagem_capa`, o hero usa `img.cover` e some o pão desenhado e o rótulo; a figura do post recebe a foto uma vez. Sem capa, o hero volta a mostrar o pão e o rótulo, e o post não ganha figura.
- `test_hub_html_has_no_placeholder` — a Home e o post não contêm `[PLACEHOLDER]`. A frase do Instagram permanece e o botão "Seguir @" não aparece quando `LEPAIN_INSTAGRAM` está ausente.

## 2. O que mudou no conteúdo

- A `imagem_capa` preenche o painel do hero (`min-height` 440 px, raio `40px 40px 40px 4px`) e a figura `.wide` do post (altura 280 px, raio `4px 40px 40px 40px`), com `object-fit: cover`. O pão desenhado e o rótulo só entram no hero quando o post não tem capa.
- Autor: "Editor LePain" em PT e "LePain Editor" em EN, na linha do post, no meta da Home e no bloco "quem escreve" / "who writes". A segunda linha é "LePain · Bread & Sense".
- O número segue a ordem de `publicado_em` das PT de Insights. A EN usa o número da PT do mesmo `grupo_id`. O card usa o mesmo texto: "Insights · Nº 01".
- O botão do Instagram só é renderizado se `LEPAIN_INSTAGRAM` for um identificador. Em produção a variável não está definida (`instagram_set 0`). A frase da faixa continua.

## 3. Capturas

Produção, depois do redeploy:

| Arquivo | O que mostra |
|---|---|
| `home-pt-1280.png`, `home-pt-390.png` | Foto do levain no hero, "Editor LePain", faixa do Instagram sem o botão |
| `post-pt-1280.png`, `post-pt-390.png` | "INSIGHTS · Nº 01", "por Editor LePain", foto no lugar do bloco verde, "Editor LePain" / "LePain · Bread & Sense" |
| `post-en-1280.png`, `post-en-390.png` | "INSIGHTS · Nº 01", "by LePain Editor", a mesma foto, "LePain Editor" / "LePain · Bread & Sense" |
| `card-pt.png` (184 133 bytes) | "Insights · Nº 01" |
| `card-en.png` (177 545 bytes) | "Insights · Nº 01" |

O HTML público de `/pt`, do post PT e do post EN não contém `[PLACEHOLDER]` nem "Seguir @". A capa é `1794158075108-levain-biblioteca.png`.

## 4. Redeploy e o que não se mexeu

Imagem `lojadepaes-blog:blog006-20261108`, a partir de `lojadepaes-blog:blog004-20261108`. `remote-deploy.sh` recriou só o `lepain`. Saúde em `/api/v1/health` ok.

Antes e depois, a Loja e a Gestão responderam 200. O LePain também.

| Contêiner | `StartedAt` |
|---|---|
| `infra-caddy-1` | `2026-11-08T17:46:46.938554147Z` (igual) |
| `infra-api-1` | `2026-11-04T16:05:11.35453791Z` (igual) |
| `infra-db-1` | `2026-09-20T18:14:08.677061212Z` (igual) |
| `gestao-api` | `2026-11-07T15:12:10.777531884Z` (igual) |
| `lepain` | `2026-11-08T18:23:39.711083477Z` (só este mudou; antes `2026-11-08T17:17:43.118284911Z`) |

A porta 22 foi aberta só para o IP desta sessão e fechada ao final. `get-instance-port-states` ficou com 80 e 443 abertos, sem regra na 22. Depois do fechamento, Loja, Gestão e LePain continuaram em 200.

Os scripts do Caddy no servidor não foram substituídos.
