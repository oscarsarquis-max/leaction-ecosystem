# CURSOR-018 — Retorno

Receitas e fichas técnicas no produto, sobre `FormulationVersion`. Sem commit, push, deploy ou ciclo de IA.

## 1. Preservação do CURSOR-017

HEAD de partida `3d14c01145547a45ba403f55aac2450762235a38`. Nenhuma restauração, descarte ou sobrescrita do 017. `0014`, ingredientes, Produção e logos mestres permanecem.

## 2. Python 3.12

Provas oficiais do CHECKPOINT-GIT-004 (container `python:3.12-slim-bookworm`, **3.12.14**): 204 passed, 1 skipped (`test_ai_bedrock_live`). Não repetidas como gate de abertura. Neste ciclo, HTTP e migração 0015 foram executados no venv local 3.11.15 contra o Postgres `panne`.

## 3. Migrações

`0015_formulation_http` sobre `0014`. Reversível no `test_migrations`: `0014↔0015` e `0001→head`. Head atual: `0015_formulation_http`. `alembic check` mantém o ruído histórico UniqueConstraint vs índice único; 0015 não abre classe nova de autogenerate.

## 4–22. Entrega

Permissões `recipe.*`, RLS, criação atômica, versionamento, componentes, percentual do padeiro, processo, rendimento, escala, trials, aprovação, referências, nutrição técnica, ficha derivada, completude, shell Receitas, assistente e badges. Detalhes nos documentos indexados.

## 23–24. Testes

Backend: `test_recipe_http` 3 passed; `test_migrations` inclui 0015; `pip-audit` limpo. Frontend: **45 passed** (38 de regressão + 7 de receitas), typecheck, lint, build. Sem chamada externa.

## 25–29

Evidências em `documentacao/evidencias/cursor-018/`. Sem commit, push ou deploy. Ciclo de IA para receitas **não iniciado**.
