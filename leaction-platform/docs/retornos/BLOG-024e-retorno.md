# BLOG-024e — retorno

**Branch:** `feat/blog-024e`  
**Base:** `main` (`a2c451a4`)  
**Imagem Hub FE:** `dS-oniR_4j7dmtbZSoi2_`

## Acabamentos
1. Resumo da rodada: objetos `{motivo, rotulo, total}` viram uma linha legível (ex.: `1 sugestão nova · 7 descartadas: 4 antigas, 2 fora do tema (nota < 7), 1 sem texto`), com detalhe no `title` (hover).
2. Fonte: `shortenFonteNome` corta no primeiro ` - ` / ` | ` / ` — ` e limita a 40 — "Acorda Cidade - Portal…" → "Acorda Cidade".
3. Wikipédia: card mostra **Verbete da Wikipédia** no lugar de "Matéria de DD/MM".

## Passo 4 (pendente 024c/d)

### Causa do erro 26/11 ~08:28 (Oscar)
No nginx do Hub (`11:27 UTC` = `08:27 BRT`):

```
26/Nov/2026:11:27:22 +0000  POST /hub-api/api/cms/sugestoes/gerar  → 499
26/Nov/2026:11:27:47 +0000  POST /hub-api/api/cms/sugestoes/gerar  → 499
```

**HTTP 499** = cliente/proxy fechou antes da resposta. A geração era síncrona (feeds + páginas + Bedrock) e passou do tempo do proxy. Correção já em 024d: `POST …/gerar` → **202** + poll da rodada.

### Job 07:00 de 27/11
Ainda **não executou** no momento deste retorno (hoje é **26/11** BRT). A última automática registrada:

- `rodada automática 2026-11-26 (#1)` — catch-up pós-deploy ~11:04 BRT  
- **criadas:** 3 (Correio Braziliense + 2 verbetes Wikipédia: Panetone, Trigo)  
- **fontes com itens mantidos:** Sebrae, Bing (várias queries)  
- **nota editorial média (aprovadas):** ≈ **7,9** (scores 8,8,8,8,8,7,7 nas 7 aprovadas; 4 rejeitadas)

Quando rodar em **27/11 07:00**, completar aqui com o log `rodada automática 2026-11-27 (#N)` (criadas / fontes / média).

## Checklist
| Item | Resultado |
|---|---|
| Testes gateway `cms-sugestoes` | **36 pass** |
| Captura | `evidencias/BLOG-024e/sugestoes-resumo-wiki.png` (resumo legível + Verbete da Wikipédia + fonte curta) |
| Deploy sem queda | overlay (sem `deploy-remote.ps1`); `HEALTH_NON_200=0`; gw/fe/mkt 200 |
| SSH | Hub SG aberto no IP atual no passo 0; fechado no fim (todos os /32 de :22) |

## Observação
Gateway `↺` 100→101 e action-hub `↺` 29→30 por `pm2 reload` (esperado). Build FE em pasta no mesmo FS com hardlinks de `node_modules` (tmpfs `/tmp` estoura cota).
