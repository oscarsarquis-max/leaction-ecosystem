# Emenda documental 001 — implementação DDL v0

- Status: Aceito (emenda)
- Data: 2026-08-03
- Congelamento base: **`domain-docs-v0`** (não alterado)
- Escopo: divergências descobertas na implementação física do esquema

## 1. Regra

O pacote Aceito em `domain-docs-v0` permanece imutável. Esta emenda registra decisões de implementação que diferem do texto congelado, sem reescrever ADRs/modelos Aceitos.

## 2. Divergências

| # | Fonte congelada | Texto / expectativa | Implementação DDL v0 | Motivo |
|---|---|---|---|---|
| 1 | ADR-005 | Migrações SQL `NNN_*.sql` + `.down.sql` estilo inove | **Alembic** + SQL versionado em `qmind/backend/sql/` | Pedido explícito de produto para Alembic na entrega DDL v0 |
| 2 | ADR-005 | Porta host do `leaction_db` citada como 5434 | Ambiente vigente: **`leaction_db` em `localhost:5433`** (`paneldx_db` usa 5434) | Estado real do compose/runtime na data da implementação |
| 3 | ADR-005 | “base logicamente pertencentes ao QMind” | **Database** PostgreSQL `qmind` (lógica dedicada). **`leaction_db`** = serviço/cluster Postgres compartilhado do ecossistema — **não** é nome de schema nem base misturada com outras apps | Isolamento por *database* no cluster; coerente com ADR-005 |
| 4 | Dicionário | `Report`/`MaturityAssessment` etc. | Tabelas físicas criadas; seeds de catálogo **fora** da migração | Separação migração × seed exigida |

## 3. Artefatos físicos

| Artefato | Caminho |
|---|---|
| SQL DDL v0 | `../../backend/sql/0001_initial_schema_domain_docs_v0.sql` |
| Migração Alembic | `../../backend/alembic/versions/20260803_0001_initial_schema_domain_docs_v0.py` |
| Doc DDL | `../03_Database/003_DDL_v0.md` |
| Seeds | `../../backend/seeds/` |
| Testes isolamento | `../../backend/tests/test_tenant_isolation.py` |
| Provisionamento DB | `../../../infra/ecosystem-databases.sql` (+ `CREATE DATABASE qmind`) |

## 4. O que permanece fiel ao freeze

- UUIDs + `timestamptz`
- FKs compostas `(id, organization_id)` same-tenant
- `legal_hold` como flag (não estado)
- Estados / aplicabilidade / SoD em CHECK
- `platform_audit_events.actor_type` ∈ {user, service, system}
- Índices `(organization_id, …)`
- RLS FORCE + papel `qmind_app` como defesa adicional
- Catálogos globais sem `organization_id`

## 5. Próximas emendas

Qualquer mudança de semântica de domínio (novos estados, mudança de SoD, etc.) exige nova emenda ou novo marco (`domain-docs-v0.1` / `v1`), nunca edição silenciosa dos arquivos Aceitos em `domain-docs-v0`.
