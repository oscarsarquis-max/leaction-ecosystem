# BLOG-004 — Retorno

Data: 08/11/2026. Branch `feat/blog-004-publicacao`, a partir de `0531fd8b` (`feat/blog-002-esqueleto`). Nada foi alterado na Loja, na Gestão nem no código do Hub. Sem `deploy-remote.ps1`. O visual do blog não mudou: o estado vazio usa a classe `.hand` que já existia (Caveat Brush).

O LePain está em `https://lepain.lojadepaes.com.br`, lendo o Hub em `https://api.actionhub.com.br` com `LEPAIN_CMS_SOURCE=hub`.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Testes novos | **Feito.** `9 passed` em 1,31 s (`.venv` do worktree). |
| 2 | Portão | **Feito.** Memória disponível 941 MB; disco livre 20 GB. |
| 3 | `/pt` e `/en` em HTTPS 200, post do levain, seletor, capturas | **Feito.** |
| 4 | `hreflang`, Open Graph, `sitemap.xml`, PNG do card | **Feito.** |
| 5 | Loja e Gestão em 200, tempo de início dos contêineres igual, SSH fechado | **Feito**, com o incidente do Caddy anotado abaixo. |
| 6 | Ids do teste, este retorno, commit e push | **Feito** neste commit. |

## 1. Testes

```
9 passed, 1 warning in 1.31s
```

O aviso é o depreciação do Starlette sobre `httpx` no `TestClient`. Não é falha.

Os testes novos, com o Hub simulado:

- `test_hub_list_url_filters_and_slug` — lista com `sistema_destino=lepain`, `secao`, `idioma` e `offset`; post em `GET /api/cms/posts/{slug}`.
- `test_hub_sibling_by_grupo_and_discards_todos` — irmão pelo `grupo_id`; `todos` não aparece; `hreflang` aponta para o outro idioma.
- `test_hub_empty_section` — seção sem posts mostra "primeiro texto a caminho" ou "first story on its way".
- `test_hub_keeps_last_good_copy` — falha do Hub devolve a última cópia boa (cache de 5 min).

As fixtures continuam só para os testes. Em produção a fonte é o Hub.

## 2. Portão, antes de criar o `lepain`

No host `lojadepaes-app` (`52.15.107.86`), antes do contêiner:

```
               total        used        free      shared  buff/cache   available
Mem:            1906         964         305          28         870         941
/dev/root        58G   38G   20G  66% /
```

941 MB disponíveis (acima de 500 MB) e 20 GB livres (acima de 3 GB).

Antes:

| URL | HTTP |
|---|---|
| `https://lojadepaes.com.br/` | 200 |
| `https://gestao.lojadepaes.com.br/` | 200 |

| Contêiner | `StartedAt` |
|---|---|
| `infra-caddy-1` | `2026-09-20T18:14:25.281181575Z` |
| `infra-api-1` | `2026-11-04T16:05:11.35453791Z` |
| `infra-db-1` | `2026-09-20T18:14:08.677061212Z` |
| `gestao-api` | `2026-11-07T15:12:10.777531884Z` |

## 3 e 4. Publicação

Imagem `lojadepaes-blog:blog004-20261108`. Contêiner `lepain` no projeto `lojadepaes-blog`, rede `infra_default`, `expose` 8091, 256 MB, 0,5 CPU, sistema de arquivos só leitura. Saúde em `/api/v1/health` ok. `StartedAt` do `lepain`: `2026-11-08T17:17:43.118284911Z`.

DNS: `A lepain.lojadepaes.com.br` → `52.15.107.86`, TTL 300, zona `Z04478628VQ84VS1J0YU`, change `C05864152UF2R7SW3T3MF`.

Certificado Let's Encrypt, `CN = lepain.lojadepaes.com.br`, emissor `CN = YE2`.

Depois, da máquina local:

| URL | HTTP |
|---|---|
| `https://lepain.lojadepaes.com.br/pt` | 200 |
| `https://lepain.lojadepaes.com.br/en` | 200 |
| `https://lojadepaes.com.br/` | 200 |
| `https://gestao.lojadepaes.com.br/` | 200 |

O seletor do post em PT (`Read in English →`) foi para `/en/insights/levain-and-bakers-percentage`. O de EN (`Ler em português →`) voltou para `/pt/insights/levain-e-a-porcentagem-de-padeiro`.

`hreflang` do post: `pt`, `en` e `x-default` (o `x-default` é o PT). Open Graph do post usa o título, o resumo e a capa enviada ao Hub. `sitemap.xml` em 200, com os dois slugs e `xhtml:link` `hreflang` (24 ocorrências no arquivo).

Cards gerados no navegador, em produção, 1080×1350:

- `docs/retornos/blog-004/card-pt.png` (190 597 bytes)
- `docs/retornos/blog-004/card-en.png` (183 993 bytes)

Capturas: `home-pt/en` e `post-pt` em 1280 e 390, `post-en` em 390 e `post-en-via-selector-1280.png`. O `meta.txt` e o `sitemap.xml` estão na mesma pasta.

## 5. Caddy e SSH

O arquivo no host (`/opt/lojadepaes/app/infra/Caddyfile`, inode 329139) não é o inode montado em `infra-caddy-1` (inode 302681, `nlink` 0, só leitura, data de 20/09). O `caddy reload` desse arquivo montado carregou só a Loja. A Gestão respondeu 000 nesse intervalo. O contêiner do Caddy não foi reiniciado.

A configuração completa (Loja, Gestão e LePain) foi recarregada a partir de `/tmp/Caddyfile.full` dentro do contêiner. O autosave passou a citar `gestao.lojadepaes.com.br` e `lepain.lojadepaes.com.br`. A Gestão voltou a 200. O `StartedAt` dos quatro contêineres da Loja e da Gestão ficou o mesmo da medição inicial.

`caddy-add.sh` e `caddy-remove.sh` agora recarregam essa cópia em `/tmp` e recusam o reload se o bloco da Gestão sumir. Um `docker restart` de `infra-caddy-1` ainda leria o inode velho e tiraria a Gestão e o LePain do ar. Isso não foi feito.

SSH: a regra `189.14.180.206/32` na porta 22 foi aberta para esta sessão e fechada no fim (`close-instance-public-ports`, status Succeeded). As outras 29 regras `/32` que já estavam na instância continuam. A regra desta sessão não está mais na lista.

## 6. Posts de teste — apagar depois

Texto copiado da Biblioteca do Padeiro, artigo público `o-comeco` (`GET /api/v1/biblioteca/artigos/o-comeco`), sem mudar as frases. Corpo convertido para `p`, `h2`, `a`, `figure` e `img`. A foto `/images/internal levain 1 bread.png` foi enviada pelo upload do CMS e é a capa.

| | id | slug | grupo_id |
|---|---|---|---|
| PT | 1 | `levain-e-a-porcentagem-de-padeiro` | 1 |
| EN | 2 | `levain-and-bakers-percentage` | 1 |

Capa: `https://paneldx-cms-assets-2026.s3.us-east-2.amazonaws.com/cms/1794158075108-levain-biblioteca.png`

Destino `lepain`, seção `insights`, sentidos `aroma`, `sabor`, `toque`, status `publicado`. É só teste.
