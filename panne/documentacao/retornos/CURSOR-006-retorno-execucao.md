# CURSOR-006 — Retorno da execução

Data: 2026-08-22. Sem commit, push, deploy ou CURSOR-007. Aguarda revisão do arquiteto.

## 1. MySQL legado

Não foi aberto, consultado nem modificado.

## 2. PostgreSQL alvo (antes da `0005`)

- Mecanismo: PostgreSQL
- Banco lógico: `panne`
- Ambiente: local / test
- Head inicial: `0004_formulation_lab`
- Head atual: `0005_nutrition_calculation`

## 3. Arquivos (somente `panne/`)

Criados: `0005_nutrition_calculation.py`, `nutrition_calculation` (modelos + acesso), `calculation_engine/nutrition.py`, `tests/test_nutrition.py`, `MODELO-DADOS-NUTRICAO-TECNICA.md`, prompt e retorno.

Alterados: `alembic/env.py`, `tests/helpers.py`, `tests/test_migrations.py`, docs de fronteira/proposta/modelo.

HTTP: só `/health` e `/ready`. Sem CRUD, frontend, rótulo, PDF, IA ou %VD.

## 4. Tabelas

`nutrition_calculation`, `nutrition_calculation_item`, `calculation_evidence`.  
FK composta por organização; checks de status/base/completude; unique (cálculo, nutriente); append-only; exclusão física bloqueada. Invalidação só altera `status`.

## 5. Fórmulas

`contribuição = massa_líquida_g × valor_per_100g ÷ 100`  
`total = soma das contribuições conhecidas`  
`por_100g = total ÷ massa_final × 100`  
`porção = por_100g × porção_técnica ÷ 100`

## 6. Massa final

`massa_final = massa_líquida × (1 − perda)` quando a taxa é válida.  
Perda não reduz totais; só concentra. Sem retenção inventada. Sem massa final: totais ok, 100 g vazio.

## 7. Ausências

Ausência ≠ zero. Zero conhecido é completo. Faltante: `missing_value` + `incomplete`. Sem IA e sem outra versão.

## 8. Compostos e preparações

Só o dossiê da `IngredientVersion` apontada. Sem recursão. Preparação sem dados: incompleto.

## 9. Unidades

Massa→g via `si_factor`. Massa↔volume recusado.

## 10. Precisão

`Decimal`, quantize técnico 14,6, `ROUND_HALF_UP`. Sem arredondamento regulatório.

## 11. Evidências

Sete tipos; rastreio de versão/fonte; reconstrução pela soma das contribuições.

## 12. Imutabilidade

Snapshots congelados. Invalidação preserva linhas. Novo cálculo = nova linha. Rascunho = simulação.

## 13. Migração

`0004` → `0005` → `0004` → `0005` e `0001` → `head`. Reversível.

## 14–15. Testes

80 passed no PostgreSQL `panne`.  
Python **3.12.14** no container oficial: 80 passed.

## 16. Sem regras regulatórias

Sem %VD, lupa, alegação, glúten/lactose automáticos, “rótulo aprovado” ou “conforme Anvisa” no domínio.

## 17. Git

`git diff --check`: sem erro.

`git diff --stat` (rastreados; pré-existentes):

```
 infra/ecosystem-databases.sql     | 1 +
 leaction-ecosystem.code-workspace | 4 ++++
 2 files changed, 5 insertions(+)
```

`git status --short`: `M` nesses dois; `?? panne/`; lixo pré-existente intacto.

## 18. Riscos

Sem RLS/autenticação. Nutrientes nunca declarados no dossiê não entram na união. LOQ sem campo na fonte. Formulação-como-ingrediente fora.

## 19–20.

Nenhuma credencial nos documentos. Sem commit, push ou deploy.
