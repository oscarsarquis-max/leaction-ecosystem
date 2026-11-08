# BLOG-008 — retorno (blog)

Data: 08/11/2026. Branch `feat/blog-008-instagram-blog`, base `feat/blog-006-acabamento` (`f3c8baec`), worktree `C:\Projetos\_blog-008-blog`.

O nome pedido era `feat/blog-008-instagram` nos dois. Esse nome já é a branch do Hub, que parte do `main` (`0b9fdda5`). O blog não está nesse histórico, então esta branch leva o sufixo `-blog`. O visual não mudou: o mesmo lugar do "Ver o card" passou a ser o link do post, e o botão da faixa só ganhou o endereço com `www` e a barra final.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Testes novos do link e do botão | **Feito.** 14 testes, 0 falhas. |
| 2 | `LEPAIN_INSTAGRAM=loja.de.paes` e redeploy só do `lepain` | **Feito.** |
| 3 | Capturas da faixa e do post, com e sem o link | **Feito.** O exemplo foi removido. |
| 4 | Loja, Gestão e LePain em 200; porta 22 fechada | **Feito.** Só 80 e 443 continuam abertas. |
| 5 | Este retorno, commit e push | **Feito** neste commit. |

## 1. Testes

`pytest tests/test_blog.py` :

```
14 passed
```

Os novos:

- `test_follow_button_uses_instagram_handle` — com `LEPAIN_INSTAGRAM=loja.de.paes`, a home PT tem `https://www.instagram.com/loja.de.paes/` e "Seguir @loja.de.paes"; a home EN tem "Follow @loja.de.paes".
- `test_post_instagram_link_only_when_the_url_is_set` — com `instagram_url`, o post mostra "Ver no Instagram ↗" (e "See on Instagram ↗" no EN) apontando para o post; sem o campo, o link não aparece. A página do ensaio não tem mais `/card/`.

O teste que exige a faixa sem o botão quando a variável não está definida continua passando. A rota `/{lang}/card/{slug}` não foi alterada.

## 2. Produção

`LEPAIN_INSTAGRAM=loja.de.paes` em `/opt/lojadepaes-blog/secrets/app.env`. Dentro do contêiner, a variável lê `loja.de.paes`.

Imagem `lojadepaes-blog:blog008-20261108`. `remote-deploy.sh` recriou só o `lepain`. Saúde em `/api/v1/health` ok. Dois `docker restart lepain` depois disso só esvaziaram a memória do blog, para a captura do exemplo e para tirá-lo do ar. Os outros contêineres não foram recriados.

| Contêiner | `StartedAt` |
|---|---|
| `infra-caddy-1` | `2026-11-08T17:46:46.938554147Z` (igual) |
| `infra-api-1` | `2026-11-04T16:05:11.35453791Z` (igual) |
| `infra-db-1` | `2026-09-20T18:14:08.677061212Z` (igual) |
| `gestao-api` | `2026-11-07T15:12:10.777531884Z` (igual) |
| `lepain` | `2026-11-08T19:37:34.548763844Z` (só este mudou; antes `2026-11-08T18:23:39.711083477Z`) |

A porta 22 foi aberta só para o IP desta sessão e fechada ao final. `get-instance-port-states` ficou com 80 e 443, sem regra na 22. Depois do fechamento, Loja, Gestão e LePain continuaram em 200.

Os scripts do Caddy no servidor não foram substituídos.

## 3. Capturas

- `docs/retornos/evidence/blog-008/seguir.png` — a faixa em produção com "Seguir @loja.de.paes".
- `docs/retornos/evidence/blog-008/post-sem-link.png` — "em uma mordida" no post de teste, sem link.
- `docs/retornos/evidence/blog-008/post-com-link.png` — o mesmo bloco com "Ver no Instagram ↗", depois de gravar o exemplo só no post PT (id 1).

O exemplo era `https://www.instagram.com/p/blog008-exemplo/`. Foi removido em seguida. O `GET` público dos dois posts voltou com `instagram_url` nulo, e a página do ensaio PT deixou de mostrar "Ver no Instagram". A faixa "Seguir @loja.de.paes" permaneceu. A rota do card responde 200 e segue com `noindex`.

## Comportamento

O botão da home só aparece com `LEPAIN_INSTAGRAM` e leva a `https://www.instagram.com/loja.de.paes/`. No ensaio, "Ver no Instagram ↗" / "See on Instagram ↗" só aparece quando o post tem `instagram_url`. "Ver o card" saiu da página pública. O card continua em `/{lang}/card/{slug}`.
