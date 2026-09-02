# Changelog — Action Hub (leaction-platform)

Todas as mudanças notáveis deste produto. Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

Versão por app (`actionhub/vX.Y.Z`). Não usar versão única do monorepo.

## [Unreleased]

### Changed
- **Catálogo inove4us HVLT:** Profissional R$24,90 · Mentor R$49,90 · Pacote 3 desafios R$14,90
  (+ anuais R$249 / R$499); desativa SKUs de penny test; destaque “Recomendado” no Profissional

### Added
- Página pública `/panne` no Action Hub: apresentação comercial estática da Panne, jornada da operação e assistente comercial local (canal WhatsApp já usado no Hub). Sem CMS, Gigio, Demo ou autenticação.

## [1.0.0] - 2026-07-20

### Added
- Baseline de versionamento de go-live: `VERSION`, `CHANGELOG.md`, `DEPLOY_LOG.md`
- Gateway `GET /health` e Next.js `GET /api/health` com `version` e `git_sha`
