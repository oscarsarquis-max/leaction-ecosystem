# Deploy log — Action Hub (produção)

Registro operacional de deploys. Uma linha por promoção a produção.

| Data (UTC-3) | Versão | Tag Git | SHA | Ambiente | Resumo | Quem |
|--------------|--------|---------|-----|----------|--------|------|
| 2026-07-20 | 1.0.0 | actionhub/v1.0.0 | — | prod | Baseline versionamento go-live | — |

Ao promover: atualize esta tabela **e** confira:
- Gateway: `https://actionhub.com.br` via API interna `/health` (ou proxy) — `version` + `git_sha`
- Frontend: `https://actionhub.com.br/api/health`
