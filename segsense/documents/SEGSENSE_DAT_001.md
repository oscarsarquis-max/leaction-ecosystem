# SEGSENSE_DAT_001 — Modelo relacional do catálogo local

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_DAT_001 |
| Título | Persistência de publicadores, canais e ambientes |
| Categoria | DAT — dados |
| Versão | 1.1 |
| Status | Vigente nesta etapa |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_DOM_001; Flyway V2; Flyway V3 (integridade de escopo) |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Tabelas `publisher`, `channel` e `contextual_environment` no schema `segsense`. |
| 1.1 | 04/09/2026 | Ressalva do PRM_004: V3 impõe UNIQUE `(channel.id, publisher_id)` e FK composta do ambiente ao canal. |

## 1. Schema

Todas as tabelas deste incremento residem no schema `segsense`. A V1 (`runtime_marker`) permanece inalterada. `ddl-auto=none`. Autoria é identificador textual técnico, **sem** FK de usuário.

Chaves primárias: UUID. Timestamps: `TIMESTAMPTZ`. Optimistic locking: coluna `version BIGINT`.

Nenhuma exclusão em cascata (`ON DELETE NO ACTION`).

## 2. Tabelas

### publisher

Única em `key`. CHECK de formato da chave, comprimento do nome, status (`DRAFT|ACTIVE|SUSPENDED`) e `version >= 0`.

Índices: `status`; `(created_at, id)` para cursor.

### channel

FK `publisher_id → publisher(id)` sem cascade. Única em `(publisher_id, key)`. CHECK de tipo (`WEBSITE|WEB_APPLICATION|MOBILE_APPLICATION|PARTNER_PORTAL`) e status.

Índices: `(publisher_id, status)`; `(publisher_id, created_at, id)`.

### contextual_environment

FKs `publisher_id → publisher(id)` (mantida) e, a partir da V3, FK composta `(channel_id, publisher_id) → channel(id, publisher_id)` nomeada `environment_channel_scope_fk`, `ON DELETE/UPDATE NO ACTION`. A FK simples `environment_channel_fk` da V2 é removida pela V3, sem alterar o arquivo V2. Única em `(channel_id, key)`. CHECK de tipo (`ARTICLE|PAGE|APPLICATION_SCREEN|EMBEDDED_COMPONENT`), status e URL canônica (`NULL` ou `https://` sem `?` nem `#`).

A V3 aborta com `RAISE EXCEPTION` se algum ambiente existente tiver `publisher_id` diferente do publisher do canal; não altera nem apaga dados. Detalhe e modelo da oportunidade: `SEGSENSE_DAT_002`.

Índices: `(publisher_id, channel_id)`; `(channel_id, status)`; `(channel_id, created_at, id)`.

## 3. Reversibilidade conceitual

Rollback manual, nunca automático nem destrutivo na subida:

1. `DROP TABLE segsense.contextual_environment;`
2. `DROP TABLE segsense.channel;`
3. `DROP TABLE segsense.publisher;`

A V1 não é revertida por este incremento.

## 4. O que não é persistido

CNPJ, CPF, endereço, e-mail, telefone, contrato, conteúdo editorial, perfil de usuário, contexto inferido, tokens, credenciais de IdP, dados da Spider ou da Icatu.
