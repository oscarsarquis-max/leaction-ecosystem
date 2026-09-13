# SEGSENSE_DOM_002 — Oportunidade contextual e versionamento

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_DOM_002 |
| Título | Oportunidade contextual, conteúdo e revisões imutáveis |
| Categoria | DOM — domínio |
| Versão | 1.2 |
| Status | Vigente nesta etapa |
| Data | 11/09/2026 |
| Dependências | SEGSENSE_DOM_001 v1.1; SEGSENSE_PRM_005; SEGSENSE_PRM_006; SEGSENSE_GOV_001 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Aggregate `ContextualOpportunity` em DRAFT, conteúdo versionado e contrato de campos não pessoais. |
| 1.1 | 04/09/2026 | Ciclo de vida editorial; PUBLISHED é autorização interna. Revisão nova somente em DRAFT. |
| 1.2 | 11/09/2026 | Referência ao aggregate de link (`SEGSENSE_LNK_001`); PUBLISHED continua autorização interna. |

## 1. Escopo

Uma oportunidade contextual pertence a exatamente um `ContextualEnvironment` e, por consequência, ao mesmo Channel e Publisher.

Nesta etapa a oportunidade é **conteúdo editorial local** com governança de autorização interna (`SEGSENSE_GOV_001`). O link contextual seguro passou a `SEGSENSE_LNK_001` / PRM_007: emissão administrativa e resolução pública mínima, ainda sem página de usuário, consentimento ou Spider/Icatu.

Textos são declarados por operador. Não são inferidos, classificados ou tratados como entendimento da Spider.

## 2. Identidade estável

| Campo | Regra |
|---|---|
| `id` | UUID |
| `publisherId`, `channelId`, `environmentId` | Hierarquia imutável após a criação |
| `key` | Minúscula, imutável, única no ambiente, `^[a-z][a-z0-9-]{2,49}$` |
| `status` | `DRAFT`, `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, `PAUSED`, `REVOKED`, `EXPIRED` |
| `currentRevision` | Inteiro positivo |
| `version` | Concorrência otimista do aggregate |
| timestamps e autoria | UTC e subject técnico |

Não existem nesta etapa: link público, `ContextInstance`, valores dinâmicos de runtime ou envio à Spider. Os estados de governança estão em `SEGSENSE_GOV_001`.

## 3. Conteúdo versionado

Snapshot de cada revisão:

- `title`: 5 a 140 caracteres;
- `contextMode`: `STATIC`, `DYNAMIC` ou `HYBRID`;
- `contextSummaryTemplate` e `objectiveTemplate`: 10 a 1.000 caracteres;
- `callToActionLabel`: 3 a 80 caracteres;
- `validFrom` / `validUntil`: opcionais, UTC; se ambos existirem, `validUntil` é posterior a `validFrom`.

Placeholders usam `{{fieldKey}}` e só referenciam campos declarados na mesma revisão.

Não incluem produto, seguradora, route, adapter, intent, execution plan, capability, preço, cobertura, elegibilidade, dados pessoais ou identificador de usuário final.

## 4. Campos de contexto

Coleção ordenada de 0 a 20 campos:

| Campo | Regra |
|---|---|
| `key` | `^[a-z][a-zA-Z0-9]{1,39}$` |
| `label` | 3 a 80 caracteres |
| `type` | `TEXT`, `NUMBER`, `BOOLEAN`, `DATE`, `ENUM` |
| `required` | boolean |
| `source` | `PUBLISHER`, `USER`, `EITHER` |
| `allowedValues` | obrigatório só para ENUM, 1 a 50 valores únicos |
| `classification` | somente `NON_PERSONAL` |

- `STATIC` exige zero campos;
- `DYNAMIC` exige ao menos um;
- `HYBRID` admite campos e texto estático;
- chave duplicada, placeholder desconhecido, HTML/script, JSON arbitrário e identificadores pessoais são rejeitados.

A definição integra o snapshot imutável. Esta etapa **não** recebe valores dinâmicos em runtime, não renderiza o template e não envia objetivo à Spider.

## 5. Versionamento

- Criar gera revisão 1.
- Editar conteúdo gera revisão N+1 **somente em `DRAFT`**. Revisões anteriores são imutáveis.
- Somente a revisão corrente pode originar a próxima.
- Edição exige `expectedVersion` do aggregate e `baseRevision` igual à corrente.
- Conteúdo idêntico ao vigente não cria revisão (`NO_CONTENT_CHANGE`).
- `key`, hierarquia e autoria histórica não mudam.

## 6. Disponibilidade efetiva

Criação exige Publisher, Channel e Environment existentes na mesma hierarquia, `ACTIVE` e `effectivelyAvailable=true`.

Após criada, a oportunidade continua consultável se um pai for suspenso; `effectivelyAvailable` torna-se falso. O status persistido **não** é alterado silenciosamente, inclusive em `PUBLISHED` (`effectivelyPublished=false`).

Consulta sempre escopada por `publisherId`, `channelId` e `environmentId`. Cross-scope é `NOT_FOUND`.
