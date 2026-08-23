# CHECKPOINT-GIT-007 — Retorno

Checkpoint operacional de Git do CURSOR-021. Sem deploy, PR, tag, release, merge, rebase ou push forçado. CURSOR-022 não iniciado.

## Branch e remoto

- Branch: `main`
- Upstream: `origin/main`
- Remoto: `https://github.com/oscarsarquis-max/leaction-ecosystem.git`
- Base anterior: `72cf2402e9c46ee7bb9fe7bcab32b809d281a0c4`
- Após `git fetch`, antes do commit: `0` ahead / `0` behind

## Primeiro commit

- Hash: `617f8823b5ee444ae780878ab26c850ce038958b`
- Mensagem: `feat(panne): add production costing and pricing`
- Push: `72cf240..617f882  HEAD -> main`, sem força

## Escopo incluído

Somente `panne/`: Custos de Produção e Formação de Preços (API, migração `0018`, política, cálculos previsto/padrão/realizado, simulações, preços praticados, testes, UI Gestão), documentação 021 e evidências. Sem publicação automática de preço.

## Validações

- Backend Python 3.12.14 (`python:3.12-slim-bookworm`): **230 passed**, **1 skipped** (`test_ai_bedrock_live`, `BEDROCK_LIVE_TEST != 1`)
- Migração: downgrade/reaplicação `0017 ↔ 0018` e `0001 → head` no `test_migrations`
- Alembic head: `0018_costing_pricing`
- Ruff nos arquivos do CURSOR-021: I001 e format check de estilo; não reformatados neste checkpoint
- `pip-audit`: nenhuma vulnerabilidade conhecida nas dependências da Panne; pacote local `panne 0.1.0` ignorado por não existir no PyPI; achados PYSEC do `pip 25.0.1` do container não entram no produto
- Frontend: typecheck, lint, **70 passed**, build
- `GET /health`: **200** `{"status":"ok","service":"panne","versao":"0.1.0","ambiente":"local"}`
- `GET /ready`: **200** `{"status":"ok","service":"panne"}`
- `git diff --cached --check`: limpo

## Segurança

Sem `.env`, tokens, chaves, senhas ou URLs autenticadas no staging. RLS com ENABLE+FORCE e default deny por organização. Runtime sem fallback administrativo. Publicação de preço exige permissão humana.

## Arquivos excluídos

`.env`, `.venv`, `node_modules`, `dist`, caches, `panne/.tmp-chrome-017/`, leftovers de `apps/`, `infra/`, `leaction-platform/` e `phanton/`.

## Segundo commit

Prompt deste checkpoint, retorno e atualização do `INDICE.md`. Mensagem: `docs(panne): record costing and pricing checkpoint`.
