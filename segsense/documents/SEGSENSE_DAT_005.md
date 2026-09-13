# SEGSENSE_DAT_005 — Persistência V9 de aviso, instância e evidência

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_DAT_005 |
| Título | Persistência V9–V11 de ConsentNotice e ContextInstance |
| Categoria | DAT |
| Versão | 1.2 |
| Status | Vigente nesta etapa |
| Data | 12/09/2026 |
| Dependências | SEGSENSE_DAT_004; V1–V10 intactas |

## 1. Migration

Arquivo canônico: `database/migrations/V9__create_consent_notice_and_context_instance.sql`.
Endurecimento: `database/migrations/V10__harden_consent_relational_integrity.sql`.
Congelamento do conjunto de campos: `database/migrations/V11__freeze_approved_notice_field_set.sql`.

Pré-validação fail-fast (V10 e V11): aborta se existir campo com classificação distinta de `NON_PERSONAL`. Sem `down -v`. Sem CASCADE. Sem reparo de dados.

Rollback conceitual da V11: dropar triggers/funções `reject_consent_notice_field_insert`, `reject_consent_notice_snapshot_insert` e `reject_effective_notice_identity_mutation`. V1–V10 permanecem.

Rollback conceitual da V10: dropar triggers/funções novas, `consent_notice_decision`, FKs compostas e colunas incrementais; V9 permanece.

V11 não reescreve V1–V10. Impede INSERT de `consent_notice_field` em snapshot já commitado ou em notice `APPROVED`/`RETIRED`; impede INSERT de snapshot extra em notice efetiva; congela identidade (`current_version`, `approved_version`, revisão) quando APPROVED/RETIRED, permitindo apenas `APPROVED` → `RETIRED`. Campos de um novo snapshot DRAFT só entram na mesma transação do INSERT do snapshot (`age(xmin) = 0`).

## 2. Tabelas

| Tabela | Função |
|---|---|
| `consent_notice` | Agregado por `opportunity_revision_id` (único). FK de escopo e revisão aprovada. |
| `consent_notice_snapshot` | Versão imutável de textos + `content_hash` SHA-256. |
| `consent_notice_field` | Campos USER/EITHER NON_PERSONAL cobertos, FK da definição imutável da revisão. |
| `context_instance` | Sessão; `credential_digest` único; `idempotency_key_digest` SHA-256 **obrigatório** (NOT NULL). |
| `context_instance_value` | Valores tipados (text/number/boolean/date); CHECK de tipo. |
| `consent_decision` | Ledger de AUTHORIZED/WITHDRAWN; UPDATE/DELETE rejeitados por trigger. |
| `consent_notice_decision` | Ledger administrativo APPROVED/RETIRED com justificativa, ator, versão, hash e timestamp UTC. |

Índice único parcial: um `APPROVED` por revisão. Um `AUTHORIZED` por instância.

## 3. Chaves candidatas novas em V8/V4

- `opportunity_revision_field_full_definition_unique` `(opportunity_revision_id, field_key, type, source, classification)`
- `published_context_link_identity_unique` identidade completa do link para FK da instância

V1–V10 não foram reescritas. V10 adiciona FKs compostas (snapshot/revisão da instância e do campo), ledger administrativo `consent_notice_decision`, imutabilidade de snapshot/campo/decisão administrativa e digest de idempotência obrigatório. V11 fecha o INSERT SQL direto no conjunto efetivo de um aviso aprovado ou retirado, sem impedir versionar um aviso ainda DRAFT.
