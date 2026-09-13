# SEGSENSE_API_005 — APIs de link contextual e resolução pública

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_API_005 |
| Título | Contratos administrativos e resolução pública do link |
| Categoria | API |
| Versão | 1.2 |
| Status | Vigente nesta etapa |
| Data | 11/09/2026 |
| Dependências | SEGSENSE_API_001; SEGSENSE_LNK_001; SEGSENSE_SEC_002; SEGSENSE_PRM_008 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 11/09/2026 | Emissão, listagem, consulta, revogação, eventos e GET público. |
| 1.1 | 11/09/2026 | HTTPS fail-closed; só `local`/`test` explícitos relaxam HTTP. |
| 1.2 | 11/09/2026 | Página React `/c/{token}` consome o GET público sem alterar o contrato. |

## 1. Base administrativa

```text
/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments/{environmentId}/opportunities/{opportunityId}/links
```

| Método | Caminho | Authority | Notas |
|---|---|---|---|
| POST | `/links` | `segsense.link.manage` | 201; `token` e `publicUrl` uma vez |
| GET | `/links` | `segsense.link.read` | Cursor opaco; sem token/URL |
| GET | `/links/{linkId}` | `segsense.link.read` | Metadados, bindings, efetividade |
| POST | `/links/{linkId}/revoke` | `segsense.link.manage` | `expectedVersion` + justificativa |
| GET | `/links/{linkId}/events` | `segsense.link.read` | ISSUED/REVOKED |

Matchers de link são avaliados **antes** dos matchers genéricos de oportunidade. PUT/PATCH/DELETE, reativação e recuperação de token são proibidos. Cross-scope: 404. Sem IdP: 401.

`publisherContext` é **lista tipada** `[{ "fieldKey", "value" }]`, não objeto livre. Valores NUMBER/BOOLEAN são JSON nativos. Duplicatas, null, objeto, array e chave desconhecida: `INVALID_PUBLISHER_CONTEXT`.

Headers de emissão: `Cache-Control: no-store`, `Pragma: no-cache`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`.

## 2. Resolução pública

```text
GET /api/v1/public/context-links/{opaqueToken}
```

PermitAll somente nesta rota GET. Sem sessão, sem mutação. Envelope: `applicationId=SEGSENSE`, `resolutionId` (UUID de correlação da resolução, não persistido como usuário), título, CTA, `contextMode`, resumo com `template` + `publisherValues`, bindings não pessoais, campos USER/EITHER unbound só como definição, validade efetiva, flags `quotationPerformed`, `eligibilityEvaluated`, `recommendationPerformed` = false.

Não devolve IDs internos, `objectiveTemplate`, digest, hint, token, autores ou metadados Spider/Icatu. A página React `/c/{token}` (PRM_008) é a única consumidora de apresentação; o contrato HTTP não foi ampliado.

| Estado | HTTP | Código |
|---|---|---|
| Token ausente/malformado | 404 | `CONTEXT_LINK_NOT_FOUND` |
| Revogado | 410 | `CONTEXT_LINK_REVOKED` |
| Link ou oportunidade expirada | 410 | `CONTEXT_LINK_EXPIRED` |
| Pausada / hierarquia / janela | 503 | `CONTEXT_LINK_TEMPORARILY_UNAVAILABLE` + `Retry-After: 60` |
| Terminal (ex.: oportunidade REVOKED) | 410 | `CONTEXT_LINK_UNAVAILABLE` |

## 3. URL pública

Construída só de `SEGSENSE_PUBLIC_BASE_URL` (local padrão `http://127.0.0.1:5178`). Nunca de `Host`/`Forwarded`. HTTPS obrigatório salvo profiles ativos exclusivamente `local` e/ou `test`; HTTP só em loopback. Sem profile, `default`, `prod` ou combinação incompatível exigem HTTPS.

## 4. Erros novos

`OPPORTUNITY_NOT_PUBLISHED` 422, `APPROVED_REVISION_MISMATCH` 409, `LINK_PLACEMENT_CONFLICT` 409, `LINK_EXPIRY_INVALID` 422, `INVALID_PUBLISHER_CONTEXT` 400, `REQUIRED_PUBLISHER_CONTEXT_MISSING` 422, mais os códigos públicos acima. Envelope e `X-Correlation-ID` preservados. Erros não incluem token.

## 5. CORS e rate limit

CORS administrativo permanece origem única (`SEGSENSE_FRONTEND_ORIGIN`). Não há `*`. Navegação por link não exige CORS público amplo. Rate limiting distribuído **não** existe neste stack; é requisito obrigatório de gateway/hardening (PRM_017), sem simulação local.
