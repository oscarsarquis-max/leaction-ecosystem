# BLOG-023 — retorno

Data: 16/11/2026. Branch `feat/blog-023-right-now-v2`. Base `4e825bdd`.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | `git apply` limpo e 28 testes | **Feito.** O `--check` passou e o `git apply` entrou. `pytest tests/test_blog.py tests/test_rn.py`: 28 passaram. |
| 2 | Enquete, curiosidade, voto, Quero!, WhatsApp e `.ics` em produção | **Feito.** Os três itens de teste foram apagados. |
| 3 | Capturas com o cache do navegador desligado | **Feito.** Em `evidencias/BLOG-023/`. |
| 4 | Só o `lepain` com `StartedAt` novo; Loja e Gestão em 200; SSH da Loja fechado | **Feito.** |
| 5 | Este retorno, commit, push e merge | **Feito** neste commit. |

## Testes

Os 26 de hoje continuam. Os dois novos, em `tests/test_blog.py`:

- O botão muda com o tipo: promoção abre a Loja com UTM, evento aponta para o `.ics` e diz "termina amanhã", notícia e parceiro usam o `link_url` (um `javascript:` cai em "Ver detalhes"), curiosidade compartilha no WhatsApp. O selo NOVO vale por 48 horas.
- A página `/pt/right-now` vem com a classe `ember`, a enquete, o Quero!, o WhatsApp e os filtros de curiosidade e parceiro. A home não recebe a classe `ember` no `body`.

## Produção

Imagem `lojadepaes-blog:blog023-20261116` (`sha256:50d664807c18f9cfd4efe078344db5acb67cdb532645446d1159ddf5849144df`). Assets com `?v=6ad51b4d`. `remote-deploy.sh` recriou só o `lepain`. A imagem anterior é `lojadepaes-blog:blog022-20261116`. A chave do Hub já estava no `secrets/app.env` e não foi trocada.

| Contêiner | StartedAt |
|---|---|
| lepain | 2026-11-16T18:20:30.527718607Z |
| infra-caddy-1 | 2026-11-08T20:34:12.590952489Z |
| infra-api-1 | 2026-11-16T15:30:40.808666811Z |
| gestao-api | 2026-11-12T13:35:32.633165352Z |
| infra-db-1 | 2026-09-20T18:14:08.677061212Z |

LePain, Loja e Gestão responderam 200. A porta 22 da Loja ficou fechada (`loja_22` 0). 80 e 443 seguem abertas. Nenhum `.tar` local.

Não havia evento publicado. Foram criados, em PT, a curiosidade `blog023-curiosidade-teste` (fonte "Forno da casa"), a enquete "Qual pão você quer ver na próxima fornada de teste?" e o evento `blog023-evento-teste`. Com o cache do navegador desligado:

- O voto mostrou as porcentagens (Focaccia 100%, Brioche 0%).
- O Quero! saiu de 0 para 1, continuou marcado depois de recarregar e, passado o cache da lista, o número seguiu 1.
- O WhatsApp abriu em `wa.me` com o título e o link do item.
- "Salvar na agenda" baixou um `.ics` (`text/calendar`, com `BEGIN:VCALENDAR` e o título).

A faixa da home ficou vermelha (`rgb(142, 27, 16)`). Capturas: `right-now-desktop.png`, `right-now-mobile-390.png`, `enquete-depois-do-voto.png` e `home-faixa-vermelha.png`.

Os três itens de teste foram apagados. A lista pública do LePain voltou a 4. A enquete passou a responder `null`. O `.ics` do evento de teste passou a responder 404. A página levou cerca de cinco minutos para soltar a cópia em memória.

Para voltar só o blog: em `/opt/lojadepaes-blog/deploy`, gravar `LEPAIN_IMAGE=lojadepaes-blog:blog022-20261116` no `.env` e `docker compose -f docker-compose.prod.yml --env-file .env up -d --force-recreate lepain`.
