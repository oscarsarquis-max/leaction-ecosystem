# CHECKPOINT-GIT-007 — Versionar CURSOR-021

Pedido recebido em 2026-08-23. CURSOR-021 implementado localmente sobre `72cf2402e9c46ee7bb9fe7bcab32b809d281a0c4`. Sem CURSOR-022, deploy, PR, tag, release ou push forçado.

## Base esperada

- Branch: `main`
- Upstream: `origin/main`
- HEAD: `72cf2402e9c46ee7bb9fe7bcab32b809d281a0c4`
- Working tree contendo somente o CURSOR-021 em `panne/`

## Resultados aprovados neste checkpoint

- Backend Python 3.12.14: 230 passed, 1 skipped
- Frontend: 70 passed, typecheck, lint, build
- Alembic head `0018_costing_pricing`
- `pip-audit` limpo nas dependências da Panne
- `/health` e `/ready` em `127.0.0.1:5080`

## Objetivo

Validar, versionar e enviar exclusivamente o incremento de Custos de Produção e Formação de Preços.

## Condições que bloqueiam o commit

- divergência incompatível com `origin/main`
- trabalho misturado de outra aplicação no staging
- segredo, `.env`, cache, build, `.venv`, `node_modules` ou `dist`
- inclusão de `panne/.tmp-chrome-017/`

## Escopo do versionamento

Migração `0018`, motor e HTTP de custeio/preços, permissões, RLS, UI Gestão → Custos e preços, testes, documentação e evidências do CURSOR-021. Sem leftovers de outras apps e sem iniciar o CURSOR-022.
