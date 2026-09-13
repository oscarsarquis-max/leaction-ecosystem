# SEGSENSE_API_006 — Aviso de finalidade e instância contextual pública

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_API_006 |
| Título | Contratos do aviso administrativo e da instância pública |
| Categoria | API |
| Versão | 1.1 |
| Status | Vigente nesta etapa |
| Data | 12/09/2026 |

## 1. GET público (aditivo)

`GET /api/v1/public/context-links/{opaqueToken}` permanece. Envelope ganha `continuity`:

```json
"continuity": {
  "available": false
}
```

ou, com aviso aprovado:

```json
"continuity": {
  "available": true,
  "noticeVersion": 1,
  "purposeTitle": "...",
  "purposeDescription": "...",
  "transparencyText": "...",
  "noExternalSharingStatement": "..."
}
```

Sem UUID do aviso. Headers `no-store` / `Pragma` / `Referrer-Policy` / `nosniff` inalterados.

## 2. Instância pública

Base: `/api/v1/public/context-links/{opaqueToken}/context-instances`

| Método | Caminho | Notas |
|---|---|---|
| POST | `/` | Cria instância; `Idempotency-Key` obrigatória (16–128, alfabeto URL-safe, entropia mínima); `instanceCredential` somente nesta resposta 201 |
| GET | `/current` | Instância autenticada pelo header, não sessão de usuário |
| PUT | `/current/values` | Lista tipada `{ key, type, value }`; `expectedVersion` |
| POST | `/current/authorize` | `expectedVersion`, `noticeVersion`, `acknowledged: true` |
| POST | `/current/withdraw` | Idempotente se já retirada; permitido enquanto a sessão não expirou, mesmo se o aviso deixar de ser efetivo para novas mutações |

Header obrigatório nas mutações posteriores: `X-SegSense-Instance-Credential`. Nunca na query/URL.

`current` = instância da credencial, não usuário logado.

Valores: NUMBER/BOOLEAN nativos; DATE ISO sem fuso; ENUM em `allowedValues`. Rejeita desconhecido, PUBLISHER, EITHER já ligado, não NON_PERSONAL, tipo errado, duplicata, null, objeto, array.

## 3. Admin do aviso

```text
/api/v1/admin/.../opportunities/{opportunityId}/consent-notice
```

| Método | Caminho | Authority |
|---|---|---|
| GET | `/consent-notice` | `segsense.consent.read` |
| POST | `/consent-notice` | `segsense.consent.write` |
| POST | `/consent-notice/draft` | `segsense.consent.write` |
| POST | `/consent-notice/approve` | `segsense.consent.approve` |
| POST | `/consent-notice/retire` | `segsense.consent.write` + justificativa |

Matchers registrados **antes** dos genéricos de oportunidade. Sem IdP: 401.

## 4. Concorrência

`expectedVersion` é a única escolha de concorrência nas mutações. Não há ETag paralelo.

## 5. Erros públicos (mensagens humanas)

| Código | HTTP |
|---|---|
| `CONTINUITY_UNAVAILABLE` | 422 |
| `INSTANCE_CREDENTIAL_REQUIRED` | 401 |
| `CONTEXT_INSTANCE_NOT_FOUND` | 404 (também credencial inválida) |
| `CONTEXT_INSTANCE_EXPIRED` | 410 |
| `CONTEXT_INSTANCE_UNAUTHORIZED` | 422 |
| `INVALID_COLLECTED_VALUE` | 400 |
| `INSTANCE_CREDENTIAL_NOT_REPLAYABLE` | 409 |
| `IDEMPOTENCY_KEY_REQUIRED` | 400 |
| `IDEMPOTENCY_KEY_INVALID` | 400 |
| `JUSTIFICATION_REQUIRED` | 400 |

Replay da criação com a mesma chave **não** devolve a credencial. O cliente deve iniciar nova tentativa com **nova** chave.

Aprovação e retirada administrativas exigem justificativa persistida em `consent_notice_decision` (sem autoria na página pública).

Logs e erros nunca incluem token do link, segredo da instância nem valores submetidos.
