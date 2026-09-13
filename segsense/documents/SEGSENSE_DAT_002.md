# SEGSENSE_DAT_002 — Persistência V3/V4 da oportunidade e do escopo de catálogo

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_DAT_002 |
| Título | Flyway V3 (escopo de ambiente) e V4 (oportunidade versionada) |
| Categoria | DAT — dados |
| Versão | 1.0 |
| Status | Vigente nesta etapa |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_DAT_001 v1.1; SEGSENSE_DOM_002; Flyway V1–V4 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Correção relacional V3 e tabelas de oportunidade/revisão/campo V4. |

## 1. Imutabilidade das migrations

V1, V2 e V3, depois de aplicadas, não são editadas. JPA permanece `ddl-auto=none`. Nenhuma exclusão em cascata.

## 2. V3 — escopo do ambiente

Arquivo: `database/migrations/V3__enforce_environment_catalog_scope.sql`.

1. Conta ambientes cujo `publisher_id` difere do publisher do canal.
2. Se `inconsistent_count > 0`, `RAISE EXCEPTION` — aborta sem alterar ou apagar dados.
3. `UNIQUE (id, publisher_id)` em `channel`, nome `channel_id_publisher_unique`.
4. Índice `environment_channel_publisher_idx` em `(channel_id, publisher_id)`.
5. FK composta `environment_channel_scope_fk`: `(channel_id, publisher_id) → channel(id, publisher_id)`, `NO ACTION`.
6. Remove a FK simples `environment_channel_fk`.
7. Mantém a FK direta do publisher.

Prova SQL: inserção coerente aceita; Publisher A + Channel B rejeitada pelo banco.

## 3. V4 — oportunidade

Arquivo: `database/migrations/V4__create_contextual_opportunity_tables.sql`.

Alvo extra para FK: `UNIQUE (id, channel_id, publisher_id)` em `contextual_environment` (`environment_id_scope_unique`).

### contextual_opportunity

Identidade, hierarquia, `key`, `status` (`DRAFT`), `current_revision`, `version`, timestamps e autoria.

- Única `(environment_id, key)`.
- FKs: publisher; composta canal `(channel_id, publisher_id)`; composta ambiente `(environment_id, channel_id, publisher_id)`.
- CHECKs de formato da key, status, revisão positiva e `version >= 0`.
- Índices: listagem por ambiente `(environment_id, created_at, id)` e `(environment_id, status)`.

### contextual_opportunity_revision

PK UUID. Única `(opportunity_id, revision_number)`. Snapshot completo do conteúdo. FK para oportunidade sem cascade. CHECK de comprimentos, modo e `valid_until > valid_from` quando ambos existem. Índice `(opportunity_id, revision_number)`.

### contextual_opportunity_revision_field

PK UUID. Única `(opportunity_revision_id, field_key)` e `(opportunity_revision_id, position)`. `allowed_values TEXT[]` somente para ENUM. Classification CHECK `NON_PERSONAL`. Posição 0–19.

## 4. Reversibilidade conceitual

Rollback manual, nunca automático:

1. `DROP TABLE segsense.contextual_opportunity_revision_field;`
2. `DROP TABLE segsense.contextual_opportunity_revision;`
3. `DROP TABLE segsense.contextual_opportunity;`
4. Remover `environment_id_scope_unique`.
5. A V3 não é revertida automaticamente; reverter o escopo exigiria recriar a FK simples, o que **não** é feito por esta etapa.

## 5. O que não é persistido

Valores dinâmicos de runtime, PII, tokens, produto, preço, cobertura, intent, route, adapter, Execution Plan, payloads Spider/Icatu.
