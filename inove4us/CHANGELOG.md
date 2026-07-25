# Changelog — inove4us

Todas as mudanças notáveis deste produto. Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

Versão por app (`inove4us/vX.Y.Z`). Não usar versão única do monorepo.

## [Unreleased]

### Added
- **Estruturação Pedagógica (Etapa 1/4):** cadastro de Instituição + Período Letivo
  (`inove_instituicoes`, `inove_periodos_letivos`, API `/api/instituicoes*`, UI `/instituicoes`)
- **Estruturação Pedagógica (Etapa 2/4):** Cursos + Disciplinas
  (`inove_cursos`, `inove_disciplinas`, API `/api/periodos-letivos/:id/cursos`, `/api/cursos*`, `/api/disciplinas*`; drill-down na UI)
- **Estruturação Pedagógica (Etapa 3/4):** vínculo pedagógico opcional em aula/evento
  (`disciplina_id` / `origem` em `inove_aulas_simples` + `inove_agenda_eventos`; `tipo_registro` só no Dia a Dia;
  seletor discreto no DailyPlanner; filtros de listagem; Wizard marca `origem=wizard_ia`)
- **Estruturação Pedagógica (Etapa 4/4):** importação em lote JSON/CSV
  (`inove_importacoes_lote`, `id_externo_importacao`, API `/api/importacoes*`, UI `/importacoes`;
  agenda canônica + espelho Dia a Dia; idempotência; grafo via `vinculo_pai_id_externo`)
- **Grafo de planejamento (reformulação visual):** trilhas por disciplina × eixo de tempo,
  cápsulas de tema via `id_evento_pai`, seletor de período letivo, filtro na API `/grafo`;
  clique reutiliza o detalhe da Agenda
- Documentação técnica em `inove4us_docs/` (resumo + integração Action Hub + Etapas 1–4 + grafo)

## [2.0.0] - 2026-07-23

> Baseline congelada antes da Estruturação Pedagógica. Ver `inove4us_docs/VERSAO-2.0.0-BASELINE.md`.

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
