# SEGSENSE_API_004 — Governança e autorização de publicação

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_API_004 |
| Título | Comandos, consultas, authorities e erros de governança |
| Categoria | API |
| Versão | 1.0 |
| Status | Vigente nesta etapa |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_API_001 v1.3; SEGSENSE_API_003; SEGSENSE_GOV_001; SEGSENSE_SEC_001 v1.3 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | POST de governança/publicação e GET de estado/eventos. |

## 1. Base

Todos os recursos permanecem sob:

```text
/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments/{environmentId}/opportunities/{opportunityId}
```

Escopo completo obrigatório. Cross-scope: `404 NOT_FOUND` sem revelar existência. Não há endpoint público nesta etapa. Envelope de erro e `X-Correlation-ID` inalterados.

O GET da oportunidade ganhou campos aditivos: `submittedRevision`, `approvedRevision`, `effectivelyPublishable`, `effectivelyPublished`.

## 2. Consultas

| Método | Caminho | Authority |
|---|---|---|
| GET | `/governance` | `segsense.opportunity.read` |
| GET | `/governance/events` | `segsense.opportunity.read` |

`GET /governance` devolve status, revisões corrente/submetida/aprovada, decisão mais recente, janela, disponibilidade efetiva, `publishedMeans=INTERNAL_AUTHORIZATION_ONLY` e `availableActions`.

`availableActions` é calculado por estado, datas UTC e pais. Não é autorização final.

`GET /governance/events` pagina com cursor opaco ligado à oportunidade (`opportunityId|occurredAt|id`), ordem `occurred_at ASC, id ASC`. Cursor de outra oportunidade é inválido (`VALIDATION_ERROR`).

## 3. Comandos

Todo comando POST recebe `expectedVersion`. Comandos de avaliação recebem `revisionNumber` igual à revisão da submissão aberta.

| Caminho | Authority | Corpo extra |
|---|---|---|
| `/governance/submit` | `segsense.opportunity.submit` | — |
| `/governance/return-for-changes` | `segsense.opportunity.review` | `revisionNumber`, `justification` |
| `/governance/approve` | `segsense.opportunity.review` | `revisionNumber` |
| `/governance/reject` | `segsense.opportunity.review` | `revisionNumber`, `justification` |
| `/publication/activate` | `segsense.publication.manage` | — |
| `/publication/pause` | `segsense.publication.manage` | — |
| `/publication/resume` | `segsense.publication.manage` | — |
| `/publication/expire` | `segsense.publication.manage` | — |
| `/publication/revoke` | `segsense.publication.manage` | `justification` |

Matchers específicos vêm **antes** do POST genérico de oportunidades (`segsense.opportunity.write`). PUT/PATCH/DELETE continuam `denyAll`.

Resposta de comando aceito: o mesmo schema de `GET /governance`.

## 4. Erros

| Código | HTTP | Uso |
|---|---|---|
| `INVALID_GOVERNANCE_TRANSITION` | 422 | transição incompatível com o estado |
| `REVISION_NOT_CURRENT` | 409 | revisão/submissão informada não é a corrente |
| `SUBMISSION_ALREADY_OPEN` | 409 | segunda submissão aberta |
| `CONCURRENT_MODIFICATION` | 409 | versão do aggregate divergente (padrão único; não há `STALE_GOVERNANCE_VERSION`) |
| `SEGREGATION_OF_DUTIES_VIOLATION` | 403 | mesmo `subjectId` em papéis incompatíveis |
| `JUSTIFICATION_REQUIRED` | 400 | justificativa ausente |
| `NOT_EFFECTIVELY_PUBLISHABLE` | 422 | hierarquia indisponível |
| `PUBLICATION_WINDOW_NOT_OPEN` | 422 | `validFrom` futuro ou `validUntil` já atingido |
| `PUBLICATION_NOT_EXPIRED` | 422 | `expire` antes de `validUntil` |
| `VALIDATION_ERROR` | 400 | tamanho, HTML/script, cursor, versão ausente |
| `AUTHENTICATION_REQUIRED` | 401 | sem autenticação real |
| `ACCESS_DENIED` | 403 | authority insuficiente |
| `NOT_FOUND` | 404 | hierarquia/oportunidade inexistente ou cross-scope |

Não se devolve stack, SQL, nome de constraint, credencial ou existência cross-scope.

## 5. Matriz de exposição

| Recurso | Anônimo | Autenticado sem authority | Authority correta |
|---|---|---|---|
| GET governança/eventos | 401 | 403 | 200 se no escopo |
| POST submit | 401 | 403 | 200 ou erro de domínio |
| POST review | 401 | 403 | 200, 403 SOD, ou erro de domínio |
| POST publication | 401 | 403 | 200, 403 SOD, ou erro de domínio |
| PUT/PATCH/DELETE | 401/403 | 403 | 403 |
| GET `/api/v1/system/info` | 200 | 200 | 200 |

Sucessos autenticados existem somente em teste Spring Security. Runtime real sem IdP permanece 401.
