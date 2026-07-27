# Deploy log — inove4us (produção)

Registro operacional de deploys. Uma linha por promoção a produção.

| Data (UTC-3) | Versão | Tag Git | SHA | Ambiente | Resumo | Quem |
|--------------|--------|---------|-----|----------|--------|------|
| 2026-07-27 | 2.1.0 | (main) | ebc3030 | prod | ECS task :18 · imagem ECR `v2.1.0` · health OK | Cursor |
| 2026-07-23 | 2.0.0 | inove4us/v2.0.0 | 5b706a5 | prod | Dia a Dia + Kanban; público locked (homologação) | — |
| 2026-07-20 | 1.0.0 | inove4us/v1.0.0 | 967a268 | prod | Baseline versionamento go-live | — |

Ao promover: atualize esta tabela **e** confira `https://inove4us.com.br/api/health` (`version` + `git_sha`).

### Go-live comunidade (obrigatório)

> **Antes de abrir o público:** eliminar dados transacionais de homologação e **iniciar do zero**.
> Manter schema (migrations aplicadas) + seeds mínimos (ex.: conta operador/admin se necessário).
> Limpar: clientes de teste, aulas/agenda/importações, instituições/cursos/disciplinas de smoke,
> créditos/notices de teste, sessões — não reaproveitar base “suja” de homologação.

Ordem sugerida: migrations `008`–`012` → wipe transacional → deploy imagem `2.1.0` → smoke → unlock gatekeeper.

### Limpeza local de smoke (grafo)

Script: `infra/scripts/wipe-smoke-local.sql` — remove clientes/eventos/importações de smoke,
normaliza período `2026` (ano todo, em curso) e mantém desafios EduScrum reais.
Rodar no DB `inove4us` (Docker `leaction_db`).

### Homologação (público bloqueado)

- Gatekeeper: `system_locked=true` (site em manutenção para o público)
- Bypass tester: `GET /gatekeeper/bypass?secret=<PRODUCTION_MASTER_KEY>`
- Status: `GET /gatekeeper/status` → `{ "locked": true }`
