# CHECKPOINT-GIT-006 — Versionar CURSOR-020

Pedido recebido em 2026-08-23. CURSOR-020 implementado localmente sobre `2b478e2d5f12ce89a9e812f36414a37697075c67`. Sem CURSOR-021, deploy, PR, tag, release ou push forçado.

## Base esperada

- Branch: `main`
- Upstream: `origin/main`
- HEAD: `2b478e2d5f12ce89a9e812f36414a37697075c67`
- Working tree contendo somente o CURSOR-020 em `panne/`

## Resultados aprovados neste checkpoint

- Backend Python 3.12.14: 223 passed, 1 skipped
- Frontend: 64 passed, typecheck, lint, build
- Alembic head `0017_labeling_compliance`
- `pip-audit` limpo nas dependências da Panne
- `/health` e `/ready` em `127.0.0.1:5080`

## Objetivo

Validar, versionar e enviar exclusivamente o incremento de Conformidade e Rotulagem.

## Condições que bloqueiam o commit

- divergência incompatível com `origin/main`
- trabalho misturado de outra aplicação no staging
- segredo, `.env`, cache, build, `.venv`, `node_modules` ou `dist`
- inclusão de `panne/.tmp-chrome-017/`

## Escopo do versionamento

Migração `0017`, motor e HTTP de rotulagem, permissões, RLS, UI Conformidade, testes, documentação e evidências do CURSOR-020. Sem leftovers de outras apps e sem iniciar o CURSOR-021.
