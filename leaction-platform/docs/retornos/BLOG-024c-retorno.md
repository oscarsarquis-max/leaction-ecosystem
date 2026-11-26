# BLOG-024c — retorno

**Branch:** `feat/blog-024-sugestoes-diarias`  
**Base:** `c1323877`

## Marketplace
Health local do `marketplace-api` em `:4012` = **200** antes e depois (BLOG-024 não afetou). Endpoint público `/api/marketplace/health` via FE devolve 404 (rota inexistente no Next); o processo PM2 segue online.

## Fontes
A rodada BLOG-024 original usava feeds diretos (Sebrae / Mercado & Consumo), não Google News com resolução de link final. Por isso o **Bing News RSS** entrou junto (`url=` decodificado), mantendo os feeds atuais. Wikipédia (até 2 curiosidades/rodada) e filtro editorial Bedrock (≥7) também.

## Testes
`node --test domain/cms-sugestoes.test.js` → **34 pass / 0 fail** (Bing `url=`, editorial simulado, agrupamento, rodada async, admin filter, purge notify, job 07:00).

## Produção
- Overlay Hub + reload; FE build `hmLIAWa0yCkuU7YnfXpS8`
- Evidência: `evidencias/BLOG-024c/tela-real-cms-sugestoes.png` (tela real do CMS, campos PT/EN, trecho_base, Publicar/Descartar)
- Nada publicado neste ciclo além do que o job automático já criou como `sugestao`

## Job 07:00
Ligado (`dailyEnabled: true`). Catch-up no start: após o deploy, rodada automática `#1` em 26/11 ~11:04 BRT.
