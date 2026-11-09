# BLOG-011 — retorno

Data: 09/11/2026.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Ids, slugs e `GET` público | **Feito.** |
| 2 | Capturas da Home e dos posts, em 1280 e 390 | **Feito.** |
| 3 | Cards com o resumo curto e o Nº | **Feito.** |
| 4 | Teste novo, só o `lepain` recriado, Loja e Gestão em 200, SSH fechado | **Feito.** |
| 5 | Posts de teste excluídos | **Feito.** |
| 6 | Este retorno, commit e push | **Feito** neste commit. |

## Posts

A PT foi criada primeiro. A EN entrou no grupo dela. A capa é `avopaomemoria.png`, enviada pelo admin para o armazenamento do CMS. Não há `instagram_url`.

| | id | slug | grupo |
|---|---|---|---|
| PT | 3 | `o-pao-que-guarda-uma-casa` | 3 |
| EN | 4 | `the-bread-that-holds-a-home` | 3 |

`GET` público, os dois com status 200:

- `https://api.actionhub.com.br/api/cms/posts/o-pao-que-guarda-uma-casa`
- `https://api.actionhub.com.br/api/cms/posts/the-bread-that-holds-a-home`

Os dois estão `publicado`, `secao=insights`, sentidos `memoria`, `aroma`, `toque` e `sabor`.

Em 390 px o poema no `<blockquote>` saía a 28 px e quebrava no meio da linha. Troquei só o HTML, sem mexer no CSS: cada verso virou `<p><em>…</em></p>`. O texto do autor continua `Editor LePain`.

## Card

O card, o botão de baixar e a descrição da página passam a usar o `resumo`. O `resumo_instagram` continua gravado e não aparece no quadro. O teste `test_card_uses_short_summary_when_instagram_caption_is_long` cobre uma legenda longa. A suíte do blog: 15 passaram.

Com os dois ensaios no ar, o card marcava Nº 02. Depois da exclusão dos posts de teste, os dois cards marcam Nº 01.

## Conferência

A Home PT e EN mostravam o ensaio novo como Insight da semana, o seletor PT ↔ EN e os quatro sentidos. O filtro Memória (`/pt/insights?sentido=memoria`) listava só este ensaio. As capturas dessa conferência estão em `docs/retornos/evidence/blog-011/`. Foram feitas antes de excluir os posts de teste, por isso a Home ainda mostra o ensaio antigo logo abaixo.

Imagem `lojadepaes-blog:blog011-20261109`. O `remote-deploy.sh` recriou só o `lepain`. Dois `docker restart lepain` depois disso só esvaziaram a memória do blog, para o poema novo e para tirar os posts excluídos. Os outros contêineres não mudaram.

| Contêiner | `StartedAt` |
|---|---|
| `lepain` | `2026-11-09T11:52:59.586558488Z` |
| `infra-caddy-1` | `2026-11-08T20:34:12.590952489Z` |
| `infra-api-1` | `2026-11-04T16:05:11.35453791Z` |
| `infra-db-1` | `2026-09-20T18:14:08.677061212Z` |
| `gestao-api` | `2026-11-07T15:12:10.777531884Z` |

Loja, Gestão e LePain responderam 200. A porta 22 da Loja foi fechada. Ficaram abertas a 80 e a 443.

## Limpeza

`DELETE /api/cms/posts/1` apagou os ids 2 e 1. O `GET` da lista LePain devolve 2 itens: o 4 (`the-bread-that-holds-a-home`) e o 3 (`o-pao-que-guarda-uma-casa`). O slug antigo responde 404.
