# BLOG-025 — retorno (Hub / leaction-platform)

## Checklist

| # | Item | Status |
|---|------|--------|
| 1 | Testes da área verdes | **Feito.** `node --test domain/cms-receitas.test.js domain/cms-enquete-ludica.test.js` → 5 passed |
| 2 | Receita de teste + revisão/EN + publicar + limpeza | **Feito** (crédito pendente de telefone Oscar). POST 201, `revisao` com EN + correções; publicar → posts PT/EN `secao=receita` + Right Now `receita`; apagado no fim |
| 3 | Sugerir outra (enquete lúdica) | **Feito.** Enquete `id=2` status `sugerida`, sem nome de produto na pergunta/opções |
| 4 | Contratos `/api/rn/enquete` e histórico | Evidências em `claude/.../evidencias/BLOG-025/` |
| 5 | Hub 200 no deploy; SSH | Gateway/FE/marketplace 200 no reload; SSH Hub permanece aberto até crédito |
| 6 | Commit / merge / este retorno | Commit na branch `feat/blog-025` |

## Deploy

- Overlay gateway + FE (`BUILD_ID=mw35y1hhrP4WkANHuX_qm`); SQL `patch_cms_receitas_enquete_025.sql` aplicado
- `LOJA_INTEGRACOES_SERVICE_KEY` gravada no `.env` do Hub (não versionada)
- Schedulers: `startEnqueteScheduler` + `startReceitasScheduler`

## Pendência

Crédito de ponto na Loja exige telefone de cliente de teste indicado pelo Oscar (checklist). Sem isso, não rodei crédito nem idempotência em produção.
