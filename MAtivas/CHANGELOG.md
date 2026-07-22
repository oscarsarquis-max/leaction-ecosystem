# Changelog — MAtivas

Todas as mudanças notáveis deste produto. Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

Versão por app (`mativas/vX.Y.Z`). Não usar versão única do monorepo.

## [Unreleased]

### Added
- (preencher antes do próximo release)

## [1.0.0] - 2026-07-22

### Added
- Baseline de versionamento: `VERSION`, `CHANGELOG.md`, `DEPLOY_LOG.md`
- `/health` passa a expor `version` e `git_sha`
- Biblioteca canônica completa de passos (Faça Fácil → `database/biblioteca_passos.json`)
- Curtida do roteiro (`POST /api/roteiro/<id>/curtir`) com coluna `curtido_em` (migração 007)
- Disclaimer de IA no roteiro/e-mail; capa do livro no e-mail

### Changed
- Resultado: lock-in no primeiro match da árvore (sem alternativas/fusão); botão obrigatório quando há campos de contexto
- Worker/prompts: títulos e descrições dos passos literais da biblioteca
- UI: logo centralizado, login admin em popover, título do documento, PDF do roteiro alinhado ao e-mail
