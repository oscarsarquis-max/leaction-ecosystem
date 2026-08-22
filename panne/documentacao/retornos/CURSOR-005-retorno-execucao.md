# CURSOR-005 — Retorno da execução

Data: 2026-08-22. Sem commit, push, deploy ou CURSOR-006. Aguarda revisão do arquiteto.

## 1. MySQL legado

Não foi aberto, consultado nem modificado. Nenhuma credencial da origem foi usada.

## 2. PostgreSQL alvo (antes da `0004`)

- Mecanismo: PostgreSQL (container `leaction_db`, 18.4)
- Banco lógico: `panne`
- Ambiente: `local` / testes `test`
- Head inicial: `0003_ingredient_catalog`

## 3. Arquivos (somente `panne/`)

Criados: migração `0004_formulation_lab`, modelos e regras de `formula_lab`, motor `calculation_engine`, testes, `MODELO-DADOS-FORMULACOES.md`, prompt e retorno.

Alterados: `alembic/env.py`, `tests/helpers.py`, `tests/test_migrations.py`, `FRONTEIRAS-FUTURAS-FORMULA.md`, `MODELO-DADOS-INGREDIENTES.md`, `MODELO-CONCEITUAL-FORMULACOES.md`, `PROPOSTA-POSTGRESQL-FORMULACOES.md`.

Endpoints: só `/health` e `/ready`. Sem CRUD, frontend, nutrição, custo ou IA.

## 4. Tabelas

`technical_product`, `recipe_reference`, `formulation`, `formulation_recipe_reference`, `formulation_version`, `formulation_item`, `process_step`, `scale_calculation`, `scale_calculation_item`, `trial`, `trial_measurement`, `approval`.

UUID, `timestamptz`, `numeric` explícito, FKs compostas, checks, uniques, índices parciais. Exclusão física bloqueada nas identidades/versões/cálculos/approvals.

## 5. Versionamento

Sem `current_version_id`. Unique `(formulation_id, version_number)`. Uma `published` por formulação (índice parcial). Publicada imutável; única mutação: `published` → `retired`. Publicar exige aprovação mais recente `approved`.

## 6. Líquido e fator

`net_quantity` > 0 (`numeric(14,6)`). `correction_factor` > 0 (`numeric(20,10)`), padrão 1.  
`gross_quantity = net × factor` (derivado; sem coluna fonte). Só unidade de massa.

## 7. Percentual do padeiro

Soma dos `net` com `is_flour_basis`. `bakers_percentage = net / total_flour × 100`. Sem farinha-base: válido, sem percentual. Não classifica pelo nome.

## 8. Escala

A: `factor = target_total / base_net`.  
B: `pre_bake = units × unit_weight / (1 − loss)`; `factor = pre_bake / base_net`.  
Itens: `scaled_net = base_net × factor`; `scaled_gross = scaled_net × factor_correção`.

## 9. Precisão

`Decimal`, `ROUND_HALF_UP`. Massas 6 casas; fatores 10. Apresentação configurável, sem mudar o interno.

## 10. Memória

`scale_calculation` + itens com versões, bases e resultados. Algoritmo `deterministic_scale` v1. Append-only. Reconstruível. Sem nutrição.

## 11. Trials

`planned` / `in_progress` / `completed` / `cancelled`. Medições: massa da massa, unidades, peso final, perda real, tempo, temperatura. Sensorial só em texto. Concluído preservado.

## 12. Aprovação

Append-only. Revogação insere evento novo. Sem endpoint. Papéis futuros.

## 13. Migração

Teste: `0001` → `0003` → `0004` → `0003` → `0004` → `0001` → `head`. Head final `0004_formulation_lab`.

## 14. Testes

63 passed (pytest, PostgreSQL `panne`). Inclui isolamento, publicação, escala, baker’s %, trials e approval.

## 15. Python 3.12

Container `python:3.12-slim-bookworm`, runtime **3.12.14**: 63 passed. Sem install global nesta estação.

## 16. Git

`git diff --check`: sem erro.

`git diff --stat` (rastreados; pré-existentes, não deste ciclo):

```
 infra/ecosystem-databases.sql     | 1 +
 leaction-ecosystem.code-workspace | 4 ++++
 2 files changed, 5 insertions(+)
```

`git status --short`: `M` nesses dois; `?? panne/`; lixo pré-existente intacto.

## 17. Preexistentes

`infra/ecosystem-databases.sql`, `.code-workspace` e untracked de outras apps não tocados.

## 18. Riscos

Sem RLS nem autenticação. Publicar a v2 exige aposentar a v1. Escala de rascunho permitida. Preparação-como-ingrediente e custo só documentados.

## 19–20.

Nenhuma credencial nos documentos. Sem commit, push ou deploy.
