# SEGSENSE_DAT_004 — Persistência V7 dos links contextuais

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_DAT_004 |
| Título | Persistência V7–V8 de published_context_link |
| Categoria | DAT — dados |
| Versão | 1.1 |
| Status | Vigente nesta etapa |
| Data | 11/09/2026 |
| Dependências | SEGSENSE_DAT_003 v1.1; SEGSENSE_LNK_001; Flyway V1–V8 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 11/09/2026 | V7: chave candidata de escopo, aggregate, bindings tipados e eventos append-only. |
| 1.1 | 11/09/2026 | V8: FK da revisão aprovada, identidade técnica da revisão e FK dos bindings. |

## 1. Chave candidata

Antes das FKs compostas:

```sql
ALTER TABLE segsense.contextual_opportunity
    ADD CONSTRAINT opportunity_id_scope_unique
        UNIQUE (id, publisher_id, channel_id, environment_id);
```

Não altera V1–V6. `ddl-auto=none`. Sem CASCADE.

## 2. Tabelas

| Tabela | Papel |
|---|---|
| `published_context_link` | Aggregate: escopo, revisão, digest UNIQUE, placement único por oportunidade/revisão, status, validade, auditoria, version |
| `published_context_link_binding` | Insert-only; colunas tipadas (`text_value`, `number_value`, `boolean_value`, `date_value`) + `field_source` e `opportunity_revision_id` (V8) |
| `published_context_link_event` | Append-only `ISSUED` / `REVOKED`; sem token bruto |

FKs: escopo completo da oportunidade (`NO ACTION`) e `(opportunity_id, revision_number)` para a revisão existente. CHECKs de status, placement, digest de 32 bytes, hint, expiração posterior à emissão e consistência de revogação.

A V7 **não** garantia que a revisão do link fosse a `approved_revision`. SQL direto podia apontar para uma revisão histórica existente.

## 3. V8 — revisão aprovada e bindings

Pré-validação aborta sem mutação se houver link órfão, revisão divergente de `approved_revision`, revisão inexistente, escopo incoerente, binding de campo desconhecido/tipo divergente ou source `USER`.

Chaves e FKs novas (`NO ACTION`):

| Constraint | Papel |
|---|---|
| `opportunity_id_approved_revision_unique` | chave candidata `(id, approved_revision)` |
| `published_context_link_approved_revision_fk` | `(opportunity_id, revision_number) → contextual_opportunity(id, approved_revision)` |
| `opportunity_revision_id_natural_unique` | `(id, opportunity_id, revision_number)` |
| `published_context_link_revision_identity_fk` | identidade técnica da revisão no link |
| `published_context_link_id_revision_unique` | `(id, opportunity_revision_id)` para o binding |
| `opportunity_revision_field_definition_unique` | `(opportunity_revision_id, field_key, type, source)` |
| `published_context_link_binding_revision_fk` | binding no mesmo revision id do link |
| `published_context_link_binding_field_fk` | `field_key` + `field_type` + `field_source` iguais à definição |
| `published_context_link_binding_source_chk` | source persistido só `PUBLISHER` ou `EITHER` |

`opportunity_revision_id` no link e `field_source` no binding são evolução estrutural unívoca: preenchidos a partir da revisão `(opportunity_id, revision_number)` e da definição do campo. Sem correção de dado inconsistente.

`approved_revision` nullable não enfraquece a FK: `revision_number` do link é `NOT NULL`. Atualizar `approved_revision` com links existentes falha (`NO ACTION`); isso preserva o vínculo à revisão aprovada corrente.

Índices novos: os UNIQUE acima. FKs de escopo e de revisão da V7 permanecem. Índices herdados: digest (UNIQUE), listagem `(opportunity_id, issued_at DESC, id)`, expiração `(status, expires_at)`, eventos `(link_id, occurred_at, id)`.

## 4. Atomicidade

Emissão: insert do aggregate + bindings + evento `ISSUED` na mesma transação. Revogação: update do aggregate + insert `REVOKED`. Bindings e eventos não são atualizados.

## 5. Rollback conceitual

V8 (antes de V7):

1. Drop FKs/CHECKs de binding V8 e colunas `field_source`, `opportunity_revision_id` do binding
2. Drop FKs/UNIQUE de identidade no link e coluna `opportunity_revision_id`
3. Drop `published_context_link_approved_revision_fk` e `opportunity_id_approved_revision_unique`
4. Drop `opportunity_revision_field_definition_unique` e `opportunity_revision_id_natural_unique`

V7:

1. `DROP TABLE segsense.published_context_link_event`
2. `DROP TABLE segsense.published_context_link_binding`
3. `DROP TABLE segsense.published_context_link`
4. `ALTER TABLE segsense.contextual_opportunity DROP CONSTRAINT opportunity_id_scope_unique`

## 6. Aplicação

Banco vazio: Flyway V1–V8. Volume existente: V8 incremental sobre V1–V7. Testcontainers aplica o histórico completo. V1–V7 intactas.
