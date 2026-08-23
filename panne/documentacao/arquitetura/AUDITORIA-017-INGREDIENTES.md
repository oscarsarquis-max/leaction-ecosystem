# Auditoria CURSOR-017 — ingredientes

## Base

- Git: `c64737f9e7cc12a598b8cddfdd8d12a77ee9208b` em `main` = `origin/main`
- Alembic head ao iniciar: `0013_legacy_role_label`
- Baseline: backend 201/2, frontend 29

## O que já existia

Schema 0003/0006: identidade, versões, composição, nutrição com LOQ, alergênicos, fornecedores, preços append-only, catálogos globais, RLS organizacional, um publicado por ingrediente, versão publicada congelada. Sem `current_version_id`. Sem API, permissões ou UI.

## Incompatibilidades corrigidas neste ciclo

1. **Aposentadoria bloqueada pelo trigger** `panne_forbid_published_version_mutation`: qualquer UPDATE em `published` era recusado. A revisão `0014` permite somente `published → retired`, sem editar o dossiê.
2. **Ciclo de composição global** em `assert_acyclic_composition`: passou a filtrar pela organização.
3. **Sem `row_version`**: acrescentado em identidade, versão, fornecedor e item para `If-Match`.
4. **Sem permissões** `ingredient.*` / `supplier.*`: criadas e atribuídas por papel (padeiro só lê; publicação explícita).
5. **Sem log de comando**: tabela `ingredient_command` para idempotência organizacional.

## O que não foi mudado

Logos mestres, tabelas de nutrição/fornecedor existentes, rotas de Produção, eventos de produção, catálogos globais (continuam só leitura).
