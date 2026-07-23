# Deploy log — inove4us (produção)

Registro operacional de deploys. Uma linha por promoção a produção.

| Data (UTC-3) | Versão | Tag Git | SHA | Ambiente | Resumo | Quem |
|--------------|--------|---------|-----|----------|--------|------|
| 2026-07-23 | 2.0.0 | inove4us/v2.0.0 | (ver git) | prod | Dia a Dia + Kanban; público locked (homologação) | — |
| 2026-07-20 | 1.0.0 | inove4us/v1.0.0 | 967a268 | prod | Baseline versionamento go-live | — |

Ao promover: atualize esta tabela **e** confira `https://inove4us.com.br/api/health` (`version` + `git_sha`).

### Homologação (público bloqueado)

- Gatekeeper: `system_locked=true` (site em manutenção para o público)
- Bypass tester: `GET /gatekeeper/bypass?secret=<PRODUCTION_MASTER_KEY>`
- Status: `GET /gatekeeper/status` → `{ "locked": true }`
