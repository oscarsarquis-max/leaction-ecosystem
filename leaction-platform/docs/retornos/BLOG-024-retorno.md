# BLOG-024 — retorno (Hub)

Data: 19/11/2026. Branch `feat/blog-024-sugestoes-diarias`. Sem `deploy-remote.ps1`.

## Checklist (complemento grounding)

| # | Item | Resultado |
|---|---|---|
| 1 | Testes da área verdes, 1 teste por camada com HTML/RSS no repo (sem rede) | **Feito.** `node --test domain/cms-sugestoes.test.js` → **9/9** (content:encoded, página, paywall). |
| 2 | Gerar sugestões em produção com stats de feed/camada/descarte | **Feito.** Ver tabela abaixo. |
| 3 | Captura em `evidencias/BLOG-024/`; nada publicado | **Feito.** `sugestoes-grounding.png` + `pairs-evidence-grounding.json`. Público LePain **6** antes e depois. |
| 4 | Retorno, commit e merge no `main` | **Feito** neste ciclo. |

## Checklist original (ainda válido)

| # | Item | Resultado |
|---|---|---|
| Job 07:00 | Desligado por enquanto; só expira sugestões vencidas. Geração = botão **Gerar sugestões**. | **Feito.** |
| GET público | Continua sem `sugestao`/`descartado`. | **Feito.** |
| SSH Hub | Porta 22 só no IP atual. | **Feito.** |

## Feeds (HTTP na rodada de produção)

| Feed | URL | HTTP | Itens | Passaram filtro |
|---|---|---|---|---|
| agencia-sebrae-padaria | `agenciasebrae.com.br/?s=padaria&feed=rss2` | **200** | 10 | 0 (idade/keyword) |
| mercadoeconsumo-padaria | `mercadoeconsumo.com.br/?s=padaria&feed=rss2` | **200** | 10 | 3 |
| mercadoeconsumo-tag-padaria | `mercadoeconsumo.com.br/tag/padaria/feed/` | **200** | 10 | 0 (idade) |

### Saíram da lista (não respondem)

| Feed original | HTTP | Ação |
|---|---|---|
| `https://gironews.com/feed/` | **403** | Removido |
| `https://supervarejo.com.br/feed/` | **404** | Removido |

Os feeds raiz de Sebrae/Mercado&Consumo respondiam 200, mas os últimos posts não batiam o filtro de padaria. Mantivemos o mesmo domínio com busca/tag RSS (URL final, sem Google News).

Janela de idade: **21 dias** (feeds diretos têm volume menor que o Google News; com 7 dias a fila útil vinha vazia).

## Stats da geração (produção)

```
created: 1
layers: content_encoded=3, page=0
discarded: keyword=4, idade=23, validacao=2
```

3 itens chegaram ao grounding pela camada `content:encoded`. 2 falharam na validação pós-LLM; **1 par PT+EN** gravado (`grupo_id=22`, link HTTP **200**). Nada publicado.

## Produção / arquivos

Backup anterior: `/var/lib/leaction-platform/backups/cms_posts-20261119T124314Z.sql`.

Overlay (sem `deploy-remote.ps1`): job/lib/config/fixtures, `CmsSugestoes.tsx` (botão **Gerar sugestões**), deps `@mozilla/readability` + `jsdom`.

Evidências: `C:\Projetos\claude\2026-11-08-lepain-blog\evidencias\BLOG-024\`.
