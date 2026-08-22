# Auditoria da migração antecipada `0002_ingredient_catalog`

Data: 2026-08-22. Somente leitura do código e do PostgreSQL local `panne`.  
MySQL legado **não** foi consultado nesta auditoria.

## Condições para reorganizar

| Condição | Evidência |
|---|---|
| Somente local | Arquivo não rastreado pelo git (`git ls-files` vazio) |
| Não compartilhada | Nenhum commit em `panne/` |
| Sem dados | `n_live_tup = 0` em todas as tabelas de negócio |
| Sem outros consumidores | Sem commit/push/deploy |
| Reversão só no `panne` | Alembic head era `0002_ingredient_catalog` só nesse banco |

**Decisão:** reverter no PostgreSQL local vazio e substituir por `0002_organization_foundation` + `0003_ingredient_catalog`. Preservar `0001_foundation`.

## Divergências (antes da correção)

| Tema | `0002` antecipada | Requisito CURSOR-003 |
|---|---|---|
| Sequência | Catálogo sem fundação de organização | Precisa `organization` antes |
| `organization_id` | UUID sem FK | FK real para `organization` |
| Isolamento | Sem unique/FK compostas | FKs compostas mesma organização |
| `ingredient_type` | Ausente (`is_additive` só) | `simple` / `composite` / `preparation` |
| Status | `situation` `active`/`cancelled` | `status` explícito |
| Versão | `version_no`, `superseded` | `version_number`, `retired` |
| `current_version_id` | Já omitida | Continua omitida |
| Base nutricional | Só no nutriente (`basis`) | Tipo + quantidade 100 + unidade de massa na **versão** |
| Nutriente | Unique (versão, nutriente, basis) | Unique (versão, nutriente); base herdada |
| Composição | Sem `organization_id` | Org + versões + `sequence` + ciclo |
| Alergênico | `absent`/`unknown`, override | `contains` / `may_contain` / `not_declared` + evidência |
| Fornecedor | `supplier_party_id` órfão | Agregado `supplier` da organização |
| Preço | Tinha `updated_at` | Append-only, sem update |
| Catálogos globais | Sem `status`; `data_source` com org | Sem dado de organização; `status` e versão da fonte |
| Conversão | Sem checagem de dimensão | Só dimensão compatível; sem massa↔volume |
| Multiempresa | Sem `organization`/`app_user` | Fundação completa |
| Auditoria | Colunas `created_by` soltas | `audit_event` append-only |
| Imutabilidade | Só índice `published` | Camada normal + trigger |
| Testes | 4 testes de metadados/health | Invariantes em PostgreSQL real |
| ON DELETE | Default | `RESTRICT` explícito |

Nenhuma dessas divergências foi “corrigida no lugar”: a migração antecipada foi revertida e substituída.
