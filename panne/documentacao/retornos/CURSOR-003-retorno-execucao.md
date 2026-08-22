# CURSOR-003 — Retorno da execução

Data: 2026-08-22. Sem commit, push, deploy ou CURSOR-004.

## 1. MySQL legado

Não foi aberto, consultado nem modificado. Nenhuma URL, host ou credencial da origem foi gravada.

## 2. PostgreSQL alvo (antes das mutações)

- Mecanismo: PostgreSQL
- Banco lógico: `panne`
- Ambiente: local
- Tabelas de negócio da `0002` antecipada: 0 linhas
- Sem consumidores externos

## 3. Auditoria da antiga `0002`

Ver `arquitetura/AUDITORIA-0002-INGREDIENT-CATALOG.md`. Principais falhas: sem organização, UUID sem FK, sem isolamento composto, base nutricional só no nutriente, fornecedor órfão, alergênicos e status desalinhados, testes só de metadados.

## 4. Reorganização

Todas as condições de reescrita foram verdadeiras (arquivo local, sem commit, sem dados). Revertido no `panne` local e substituído por:

`0001_foundation` → `0002_organization_foundation` → `0003_ingredient_catalog`

## 5. Arquivos

Criados/alterados só em `panne/` (modelos, migrações, testes, `/ready`, documentação). `0002_ingredient_catalog.py` removida após downgrade.

## 6–11. Núcleo

Multiempresa: `organization`, `establishment`, `app_user`, `organization_membership`, `audit_event`.  
Catálogos globais com `status`. Ingrediente com FK e tipo. Versão com base `per_100g` explícita, published único e imutável. Composição com FK composta e ciclo na camada normal. Fornecedor + item + preço append-only.

## 12. Upgrade / downgrade / reaplicação

Comprovado no teste `test_upgrade_downgrade_reapply` e na operação local: head `0003_ingredient_catalog`.

## 13. Testes

29 passed (pytest no PostgreSQL `panne`).

## 14. Python 3.12

Container isolado `python:3.12-slim-bookworm` (ver execução anexa). Sem install global.

## 15. Endpoints

- `/health`: 200 sem banco; contrato inalterado.
- `/ready`: 200 se o Postgres da Panne responder; 503 `indisponivel` sem vazamento.

## 16–17. Git

Índices preexistentes do workspace intactos. `?? panne/` + lixo de outras apps preservado.

## 18. Riscos

Sem RLS. Ciclo N níveis só na camada Python. Identidade sem autenticação. Sem semente de unidades/nutrientes.

## 19–20.

Nenhuma credencial versionada. Sem commit, push ou deploy.
