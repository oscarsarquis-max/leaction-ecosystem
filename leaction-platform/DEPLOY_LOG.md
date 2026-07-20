# Deploy log — Action Hub (produção)

Registro operacional de deploys. Uma linha por promoção a produção.

| Data (UTC-3) | Versão | Tag Git | SHA | Ambiente | Resumo | Quem |
|--------------|--------|---------|-----|----------|--------|------|
| 2026-07-20 | 1.0.0 | actionhub/v1.0.0 | 967a268 | prod | Baseline versionamento go-live | — |
| 2026-07-20 | 1.0.0 | actionhub/v1.0.0 | 095a0b3+ | prod | Cutover MP APP_USR, gate simulação, catálogo R$1/2/3, webhook inove4us | — |

Ao promover: atualize esta tabela **e** confira:
- Gateway: `https://actionhub.com.br` via API interna `/health` (ou proxy) — `version` + `git_sha`
- Frontend: `https://actionhub.com.br/api/health`
