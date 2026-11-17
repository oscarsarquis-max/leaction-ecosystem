# BLOG-023b — retorno

Data: 17/11/2026. Branch `fix/blog-023b-curiosidade-link`. Base `bce43743`.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | `git apply` limpo e 29 testes | **Feito.** O `--check` passou e o `git apply` entrou. `pytest tests/test_blog.py tests/test_rn.py`: 29 passaram. |
| 2 | "Saber mais" no item do fubá, mesma aba, e "Read more" em inglês | **Feito.** O link em PT abre o ensaio Nº 02. O item em EN mostra "Read more", mas o endereço gravado tem uma barra a mais e responde 404. |
| 3 | Capturas com o cache do navegador desligado | **Feito.** Em `evidencias/BLOG-023b/`. |
| 4 | Só o `lepain` com `StartedAt` novo; Loja e Gestão em 200; SSH da Loja fechado | **Feito.** |
| 5 | Este retorno, commit, push e merge | **Feito** neste commit. |

## Testes

Os 28 de ontem continuam. O novo, `test_curiosity_keeps_its_link_as_read_more`:

- Curiosidade com link do próprio blog ganha `more_href` e não marca o link como externo. O botão principal continua sendo o WhatsApp.
- Link de fora fica externo.
- Notícia não ganha o "Saber mais".

## Produção

Imagem `lojadepaes-blog:blog023b-20261117` (`sha256:f5f6efdb6b0cb2cae664b5590ad85bad8553754d167c7d793b5fb941c90d9f53`). Assets com `?v=a45de532`. `remote-deploy.sh` recriou só o `lepain`. A imagem anterior é `lojadepaes-blog:blog023-20261116`.

| Contêiner | StartedAt |
|---|---|
| lepain | 2026-11-17T13:27:33.117806908Z |
| infra-caddy-1 | 2026-11-08T20:34:12.590952489Z |
| infra-api-1 | 2026-11-16T15:30:40.808666811Z |
| gestao-api | 2026-11-12T13:35:32.633165352Z |
| infra-db-1 | 2026-09-20T18:14:08.677061212Z |

LePain, Loja e Gestão responderam 200. A porta 22 da Loja ficou fechada (`loja_22` 0). 80 e 443 seguem abertas. Nenhum `.tar` local.

Com o cache do navegador desligado, em `/pt/right-now`, o item "Em 1932, o pão levou fubá" mostra "Saber mais →" à direita dos botões. O clique ficou na mesma aba e abriu `/pt/insights/guerra-e-pao`. No celular (390 px) o link desce para a linha de baixo. Capturas: `curiosidade-fuba-desktop.png` e `curiosidade-fuba-mobile-390.png`.

Em `/en/right-now`, o item mostra "Read more →" sem `target="_blank"`. O endereço gravado é `https://lepain.lojadepaes.com.br//en/insights/war-and-bread` (duas barras) e responde 404. Sem a barra extra, `/en/insights/war-and-bread` responde 200. O dado não foi alterado.

Para voltar só o blog: em `/opt/lojadepaes-blog/deploy`, gravar `LEPAIN_IMAGE=lojadepaes-blog:blog023-20261116` no `.env` e `docker compose -f docker-compose.prod.yml --env-file .env up -d --force-recreate lepain`.
