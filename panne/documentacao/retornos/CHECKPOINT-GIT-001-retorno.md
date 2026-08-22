# CHECKPOINT-GIT-001 — Retorno

Checkpoint operacional de Git após o CURSOR-015. Sem deploy. Sem CURSOR-016.

## Branch e remoto

- Branch: `main`
- Remoto: `origin`
- Upstream: `origin/main`
- Situação antes do primeiro commit: alinhada ao remoto (`0` ahead / `0` behind após `git fetch`)
- HEAD anterior: `1d63740edf326a8908932cf77956a2a65bbcc821`

## Primeiro commit

- Hash: `42175d57fb8ad11fe69b695af6a972a19023002a`
- Mensagem: `feat(panne): establish production planning platform`
- Arquivos: 354 (`+51320`)

## Escopo versionado

1. Conteúdo aprovado de `panne/` até o CURSOR-015 (backend, frontend, migrações `0001`–`0013`, testes, documentação e evidências visuais em `documentacao/evidencias/cursor-015/`).
2. Trechos da Panne em `infra/ecosystem-databases.sql` (`CREATE DATABASE panne`) e `leaction-ecosystem.code-workspace` (pasta `Panne`).
3. Prompt `prompts/CHECKPOINT-GIT-001-commit-push.md` e `INDICE.md` com o checkpoint em execução.

## Validações desta execução

| Verificação | Resultado |
|---|---|
| Testes backend no Python 3.12.14 (Docker) | **199 passed, 1 skipped** |
| `pip-audit` | limpo (Pacote `panne` local não publicado no PyPI) |
| Typecheck do frontend | ok |
| Lint do frontend | ok |
| Vitest | **18 passed** |
| Build de produção do frontend | ok |
| Alembic | `0013_legacy_role_label (head)` |
| `GET /health` (API local) | **200** `{"status":"ok","service":"panne","versao":"0.1.0","ambiente":"local"}` |
| `GET /ready` (API local) | **200** `{"status":"ok","service":"panne"}` |

A subida local da interface pelo usuário foi só visualização, não deploy.

`git diff --cached --check` apontou whitespace residual em markdown antigo da Panne. Não há hook ativo de pre-commit; o conteúdo não foi reescrito para não alterar documentação já aprovada.

## Head do Alembic

`0013_legacy_role_label` (head)

## Resultado do primeiro push

Aceito. `origin/main`: `1d63740` → `42175d5`. Sem force.

## Arquivos deliberadamente excluídos

- `panne/.env` (local, gitignored)
- `.venv`, `node_modules`, caches, cobertura e builds
- `apps/diario-obra-api/diario-start.err`
- `infra/deps-install-log.txt`
- `leaction-platform/services/gateway-api/mp-log-20260719-1015.txt`
- `phanton/database/_lan-sync/`
- Qualquer trabalho do CURSOR-016 (inexistente)

## Estado restante do Git após o primeiro push

`main` alinhada a `origin/main`. Permaneceram não rastreados os artefatos preexistentes listados acima.

## Alterações preexistentes mantidas fora

Logs, dumps e sync LAN das aplicações irmãs. Nenhuma alteração funcional de outra app.

## Segredos

Nenhum `.env` real versionado. Exemplos só com placeholders (`<configure-…>`). Sem tokens, chaves AWS, chaves privadas ou URLs autenticadas no conteúdo commitado. O `.env` local permanece só nesta máquina.

## Deploy, PR, tag e release

Não houve deploy, PR, tag, release, pull, merge, rebase nem push forçado.

## CURSOR-016

**Não iniciado.**
