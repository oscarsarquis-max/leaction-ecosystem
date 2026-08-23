# CURSOR-017 — Retorno

Ciclo executado em 2026-08-23. Base `c64737f9e7cc12a598b8cddfdd8d12a77ee9208b` (`main` / `origin/main`). Sem commit, push ou deploy. **CURSOR-018 não iniciado.** Receitas não avançaram.

## 1. Isolamento e base

Somente `panne/`. Sem MySQL, FTP, apps irmãs, AWS/Bedrock/Cognito reais. Artefatos untracked de outras pastas permaneceram de lado.

## 2. Auditoria

Ver [AUDITORIA-017-INGREDIENTES.md](../arquitetura/AUDITORIA-017-INGREDIENTES.md). Alembic de partida: `0013_legacy_role_label`. Baseline: backend 201/2, frontend 29, `pip-audit` limpo.

## 3. Banco e migração

Revisão `0014_ingredient_http`: `row_version`, `ingredient_command` + RLS, trigger de aposentadoria, seed de permissões, GRANT a `panne_runtime`. Sem renumerar.

## 4–25

Detalhados no retorno obrigatório da conversa. Testes finais: backend **203 aprovados / 2 ignorados**, frontend **38 aprovados**, typecheck, lint (0 erros), build, `pip-audit` sem vulnerabilidades. Python do venv: 3.11.15 (3.12 ausente nesta máquina).
