# SEGSENSE_API_003 — Contratos de oportunidade contextual

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_API_003 |
| Título | API administrativa de oportunidades e revisões |
| Categoria | API |
| Versão | 1.0 |
| Status | Vigente nesta etapa |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_API_001 v1.3; SEGSENSE_DOM_002; SEGSENSE_SEC_001 v1.2 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Endpoints reais de rascunho versionado. Sem IdP: anônimo 401. Sem publicação. |

## 1. Base e proteção

```text
/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments/{environmentId}/opportunities
```

| Operação | Authority |
|---|---|
| GET (coleção, detalhe, histórico, revisão) | `segsense.opportunity.read` |
| POST (criar, nova revisão) | `segsense.opportunity.write` |

Matchers de oportunidade são avaliados **antes** dos matchers genéricos de catálogo. Sem IdP, chamadas reais permanecem **401**. Sucesso autenticado somente em testes Spring Security.

Não há PUT, PATCH destrutivo, DELETE, transição de status nem publicação.

## 2. Recursos

| Método | Caminho |
|---|---|
| `POST` | `/opportunities` |
| `GET` | `/opportunities` |
| `GET` | `/opportunities/{opportunityId}` |
| `POST` | `/opportunities/{opportunityId}/revisions` |
| `GET` | `/opportunities/{opportunityId}/revisions` |
| `GET` | `/opportunities/{opportunityId}/revisions/{revisionNumber}` |

Listagens: cursor opaco, `page[size]` 1–100, ordem determinística. O cursor de histórico incorpora o `opportunityId`; cursor de outra oportunidade é `VALIDATION_ERROR`.

## 3. Corpo de criação

`key`, `title`, `contextMode`, `contextSummaryTemplate`, `objectiveTemplate`, `callToActionLabel`, `validFrom`/`validUntil` opcionais (ISO-8601 UTC), `contextFields` opcional.

Nova revisão: os mesmos campos de conteúdo mais `expectedVersion` e `baseRevision`.

## 4. Resposta

A resposta distingue:

- identidade estável (`id`, hierarquia, `key`);
- metadados (`status`, `currentRevision`, `version`, timestamps, autoria);
- revisão corrente (`current`);
- snapshot de conteúdo e `contextFields`;
- `effectivelyAvailable` calculado.

## 5. Erros

Todos seguem `SEGSENSE_API_001`: `code`, `message` em português, `timestamp`, `correlationId`. Sem SQL, constraint, stack ou enumeração cross-scope.

| Código | HTTP |
|---|---|
| `OPPORTUNITY_KEY_CONFLICT` | 409 |
| `STALE_OPPORTUNITY_REVISION` | 409 |
| `CONCURRENT_MODIFICATION` | 409 |
| `INVALID_PARENT_STATE` | 422 |
| `NO_CONTENT_CHANGE` | 422 |
| `VALIDATION_ERROR` | 400 |
| `NOT_FOUND` | 404 |
| `AUTHENTICATION_REQUIRED` | 401 |
| `ACCESS_DENIED` | 403 |
