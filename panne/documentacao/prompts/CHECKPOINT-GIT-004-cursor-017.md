# CHECKPOINT-GIT-004 — Validar e versionar o CURSOR-017

Pedido recebido em 2026-08-23. CURSOR-017 aceito condicionalmente. Sem CURSOR-018, Receitas, deploy, PR, tag, release ou push forçado.

## Base esperada

- Branch: `main`
- Upstream: `origin/main`
- HEAD: `c64737f9e7cc12a598b8cddfdd8d12a77ee9208b`
- Working tree contendo somente o CURSOR-017 em `panne/`

## Objetivo

Validar no ambiente oficial (Python 3.12 isolado + ciclo da `0014`) e versionar o shell Oficina + Atelier e Componentes → Ingredientes somente se todas as condições forem aprovadas.

## Condições que bloqueiam o commit

- falha da suíte no Python 3.12
- skip novo sem causa explícita
- falha de reversão/reaplicação da `0014`
- regressão de RLS
- lacuna crítica de cobertura no frontend
- segredo, `.env`, cache, build ou app irmã no staging

## Escopo do versionamento

Somente implementação, testes, migração, documentação, evidências, prompt, retorno, este checkpoint e índice. Sem `.env`, `node_modules`, `dist`, `.venv`, `.tmp-chrome-017` ou leftovers de outras apps.
