# Changelog — inove4us

Todas as mudanças notáveis deste produto. Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

Versão por app (`inove4us/vX.Y.Z`). Não usar versão única do monorepo.

## [Unreleased]

### Added
- (preencher antes do próximo release)

## [2.0.0] - 2026-07-23

### Added
- Vetor **Dia a Dia**: planejamento de aula em ciclo rápido (~50 min)
- API `/api/daily/*` (CRUD + sugerir dinâmicas) com proteção `schema_pending` (503)
- UI: dashboard, planner com form + Kanban (4 estações) e modal obrigatório na migração
- Vínculo automático com a Agenda executiva (`tipo=aula_dia`, cards verdes)
- Cache local de dinâmicas sem designações autorais proibidas

### Changed
- Agenda: cores por vetor (Desafio âmbar × Dia a Dia verde)
- Mesa: atalho **Dia a Dia** ao lado de **+ Desafio**

## [1.0.0] - 2026-07-20

### Added
- Baseline de versionamento de go-live: `VERSION`, `CHANGELOG.md`, `DEPLOY_LOG.md`
- `/api/health` passa a expor `version` e `git_sha`
