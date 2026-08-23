# CHECKPOINT-GIT-002 — Retorno

Checkpoint operacional de Git do CURSOR-016. Sem projeto visual, redesign, CURSOR-017, deploy, PR, tag, release ou push forçado.

## Branch e remoto

- Branch: `main`
- Upstream: `origin/main`
- Remoto: `https://github.com/oscarsarquis-max/leaction-ecosystem.git`
- Base anterior: `e6d54f9d15de0019bd846d6faea71f7e6e4ee9af`

## Primeiro commit

- Hash: `1f45eb54f4e0703e75094fbeded6a6e3cadc1420`
- Mensagem: `feat(panne): add production operator mode`
- Push: `e6d54f9..1f45eb5  HEAD -> main`, sem força

## Escopo incluído

Somente `panne/`: backend (ficha v2, catálogo, projeção `/execution`), frontend do modo operacional, testes, documentação do CURSOR-016, evidências visuais locais, prompt deste checkpoint e índice.

## Validações reais

- Python **3.12.14**
- Backend: **201 passed, 2 skipped**
- `pip-audit`: limpo (o pacote local `panne 0.1.0` não existe no PyPI e foi ignorado pelo scanner)
- Alembic: `0013_legacy_role_label (head)`
- Frontend: typecheck, lint, **29 testes**, build de produção
- `/health` e `/ready` em `127.0.0.1:5080`: `ok`

## Skips

1. `tests/test_ai_bedrock_live.py`: Bedrock vivo desabilitado (`BEDROCK_LIVE_TEST != 1`). Não chama AWS.
2. `tests/test_runtime_url.py::test_unconfigured_runtime_session_is_unavailable`: a sessão de runtime **está** configurada nesta estação. O teste cobre o caso sem URL e por isso é ignorado. Os demais testes do arquivo (sem fallback administrativo) e os testes de RLS rodaram e passaram. O skip não esconde regressão de RLS nem uso da sessão administrativa.

## Arquivos excluídos

- `panne/.env`
- `node_modules`, `dist`, caches, `.venv`
- `apps/diario-obra-api/diario-start.err`
- `infra/deps-install-log.txt`
- `leaction-platform/services/gateway-api/mp-log-20260719-1015.txt`
- `phanton/database/_lan-sync/`

## Segurança

Nenhum `.env`, token, chave AWS, senha ou URL autenticada no staging. `git diff --cached --check` limpo. Evidências PNG entre 37 e 44 KB, sem Git LFS.

## Confirmações

- Sem deploy, PR, tag, release ou push forçado
- Projeto visual não iniciado
- CURSOR-017 não iniciado
