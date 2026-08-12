# Deploy log — inove4us (produção)

Registro operacional de deploys. Uma linha por promoção a produção.

| Data (UTC-3) | Versão | Tag Git | SHA | Ambiente | Resumo | Quem |
|--------------|--------|---------|-----|----------|--------|------|
| 2026-08-12 | 2.2.0 | lancamento-2026-08-12 | 5c47834 | prod | ECR `v2.2.0` · ECS `:26` · N:N curso-disciplina (`033`) + chaves School na task; site trancado | Cursor |
| 2026-08-10 | 2.1.5 | (main) | 1732903 | prod | ECR `v2.1.5` · ECS `:25` · restaura Sonnet no wizard (reverte Haiku/SLA 30s) | Cursor |
| 2026-08-10 | 2.1.4 | (main) | fe303d3 | prod | ECR `v2.1.4` · ECS `:24` · pad wizard legível (sem colagem de fragmentos) | Cursor |
| 2026-08-10 | 2.1.3 | (main) | 4e7358b | prod | ECR `v2.1.3` · ECS `:23` · wizard SLA 30s (Haiku) + freemium Dia a Dia só navegação | Cursor |
| 2026-08-02 | 2.1.0 | (main) | fb703df | prod | ECR `v2.1.1` · ECS `:19` · RDS migrations `016`–`020` (PEI, Modo Aula, nina, feedback, colab card); health `git_sha=fb703df` | Cursor |
| 2026-07-28 | 2.1.0 | (main) | f23ccd0 | prod | RDS migrations `014`–`015` aplicadas (Fargate one-off); desafios + colaboradores OK | Cursor |
| 2026-07-28 | 2.1.0 | (main) | ebc3030 | prod | RDS migrations `008`–`013` aplicadas (Fargate one-off); schema pedagógico + `plan_tier` OK | Cursor |
| 2026-07-27 | 2.1.0 | (main) | ebc3030 | prod | ECS task :18 · imagem ECR `v2.1.0` · health OK | Cursor |
| 2026-07-23 | 2.0.0 | inove4us/v2.0.0 | 5b706a5 | prod | Dia a Dia + Kanban; público locked (homologação) | — |
| 2026-07-20 | 1.0.0 | inove4us/v1.0.0 | 967a268 | prod | Baseline versionamento go-live | — |

Ao promover: atualize esta tabela **e** confira `https://inove4us.com.br/api/health` (`version` + `git_sha`).

### Go-live comunidade (obrigatório)

> **Antes de abrir o público:** eliminar dados transacionais de homologação e **iniciar do zero**.
> Manter schema (migrations aplicadas) + seeds mínimos (ex.: conta operador/admin se necessário).
> Limpar: clientes de teste, aulas/agenda/importações, instituições/cursos/disciplinas de smoke,
> créditos/notices de teste, sessões — não reaproveitar base “suja” de homologação.

Ordem sugerida: migrations `008`–`012` ? wipe transacional ? deploy imagem `2.1.0` ? smoke ? unlock gatekeeper.

### Limpeza local de smoke (grafo)

Script: `infra/scripts/wipe-smoke-local.sql` — remove clientes/eventos/importações de smoke,
normaliza período `2026` (ano todo, em curso) e mantém desafios EduScrum reais.
Rodar no DB `inove4us` (Docker `leaction_db`).

### Homologação (público bloqueado)

- Gatekeeper: `system_locked=true` (site em manutenção para o público)
- Bypass tester: `GET /gatekeeper/bypass?secret=<PRODUCTION_MASTER_KEY>`
- Status: `GET /gatekeeper/status` ? `{ "locked": true }`
