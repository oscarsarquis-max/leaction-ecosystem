# CHECKPOINT-GIT-005 — Versionar CURSOR-018 e CURSOR-019

Pedido recebido em 2026-08-23. Receitas e o assistente de IA já aprovados. Sem deploy, PR, tag, release ou push forçado.

## Base esperada

- Branch: `main`
- Upstream: `origin/main`
- HEAD: `3d14c01145547a45ba403f55aac2450762235a38`
- Working tree contendo CURSOR-018 e CURSOR-019 em `panne/`

## Resultados aprovados

- Backend Python 3.12.14: 215 passed, 1 skipped
- Frontend: 55 passed
- Alembic até `0016`
- `pip-audit` limpo nas dependências da Panne

## Objetivo

Versionar e enviar imediatamente Receitas (`0015`) e o assistente de IA (`0016`) somente em `panne/`.

## Condições que bloqueiam o commit

- divergência com `origin/main`
- trabalho misturado de outra aplicação no staging
- segredo, `.env`, cache, build, `.venv`, `node_modules` ou `dist`
- alteração dos logos mestres

## Escopo do versionamento

Migrações `0015` e `0016`, backend, frontend, testes, documentação e evidências dos ciclos 018 e 019. Sem leftovers de outras apps e sem `.tmp-chrome-017`.
