# Deploy log — Action Hub (produção)

Registro operacional de deploys. Uma linha por promoção a produção.

| Data (UTC-3) | Versão | Tag Git | SHA | Ambiente | Resumo | Quem |
|--------------|--------|---------|-----|----------|--------|------|
| 2026-07-20 | 1.0.0 | actionhub/v1.0.0 | 967a268 | prod | Baseline versionamento go-live | — |
| 2026-07-20 | 1.0.0 | actionhub/v1.0.0 | 095a0b3+ | prod | Cutover MP APP_USR, gate simulação, catálogo R$1/2/3, webhook inove4us | — |

Ao promover: atualize esta tabela **e** confira:
- Gateway: `https://actionhub.com.br` via API interna `/health` (ou proxy) — `version` + `git_sha`
- Frontend: `https://actionhub.com.br/api/health`

### Go-live comunidade (obrigatório)

> **Antes de abrir o público:** eliminar dados transacionais de homologação e **iniciar do zero**.
> Preservar: schema, `app_registry`, `catalog_plans` (SKUs reais ativos), admins seed, configs/secrets.
> Limpar: checkouts/pagamentos de teste, contratos/entitlements de smoke, outbox webhook,
> tracking CRM de teste, posts CMS de rascunho se não forem oficiais — base limpa para a comunidade.

Ordem sugerida: migrate patches → wipe transacional → deploy → smoke pagamento mínimo → unlock gatekeeper (Hub e/ou inove4us).
