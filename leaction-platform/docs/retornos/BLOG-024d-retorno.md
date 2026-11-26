# BLOG-024d — retorno

**Branch:** `feat/blog-024-sugestoes-diarias`  
**Imagens:** Hub FE `hmLIAWa0yCkuU7YnfXpS8` · Blog `lojadepaes-blog:blog024d-20261126` (retorno `blog023b-20261117`)

## Causa do erro 26/11 ~08:28 (Oscar)
No nginx do Hub:

```
26/Nov/2026:11:27:22 +0000  POST /hub-api/api/cms/sugestoes/gerar  → 499
26/Nov/2026:11:27:47 +0000  POST /hub-api/api/cms/sugestoes/gerar  → 499
```

**HTTP 499** = o cliente/proxy fechou a conexão antes da resposta. A geração era **síncrona** (feeds + páginas + Bedrock no mesmo pedido) e passou do tempo do proxy — alinhado à suspeita. Não há stack Bedrock nesse horário; o pedido simplesmente não chegou a terminar.

Correção: `POST /api/cms/sugestoes/gerar` → **202 `{rodada_id}`** + polling `GET .../rodadas/:id` a cada 3 s, com progresso e erros legíveis.

## Checklist
| Item | Resultado |
|---|---|
| Testes gateway | 34 pass |
| Purge + TTL 60 | Blog `TTL 60`; appear **715 ms**, disappear **188 ms** em `/pt/right-now` (meta < 5 s) |
| Lista sem sugestão/descartado | Admin SQL filtra; badge `Sugestões (N)` só de hoje |
| Datas / grupos | Sugerida em / Matéria de / expira em N h · Hoje/Ontem |
| Job 07:00 | Ligado + catch-up; log: `rodada automática 2026-11-26 (#1)` pós-deploy |
| Deploy sem queda | Hub: arquivos + `pm2 reload`; monitor HEALTH_NON_200=0 no reload; Blog: imagem pronta antes do recreate |
| SSH | Hub SG IP atual; Loja aberta no passo 0 e fechada no fim |

## Evidências
`C:\Projetos\claude\2026-11-08-lepain-blog\evidencias\BLOG-024d\`
- `sugestoes-datas-grupos.png` / `rodada-em-andamento.png` / `rodada-resumo-final.png`
- `lista-principal-sem-sugestoes.png` (botão **Sugestões (4)**)

## Observação
Gateway `↺` 99→100 por `pm2 reload` (esperado). Marketplace local 200 durante o deploy.
