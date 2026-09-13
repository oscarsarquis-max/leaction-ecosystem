# SEGSENSE_API_002 — Contratos do catálogo administrativo

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_API_002 |
| Título | API administrativa de publicadores, canais e ambientes |
| Categoria | API |
| Versão | 1.0 |
| Status | Vigente nesta etapa |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_API_001 v1.2; SEGSENSE_DOM_001; SEGSENSE_SEC_001 v1.1 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Contratos reais do catálogo local. Sem IdP no runtime: chamadas anônimas recebem 401. |

## 1. Base e proteção

Base: `/api/v1/admin`

| Operação | Authority |
|---|---|
| GET | `segsense.catalog.read` |
| POST, PATCH | `segsense.catalog.write` |

Sem IdP, chamadas reais permanecem **401** `AUTHENTICATION_REQUIRED`. Sucesso autenticado é comprovado somente em testes com mock do Spring. Não há PUT completo, DELETE nem alteração de `key`.

Correlação: header e campo de erro `X-Correlation-ID` / `correlationId`, conforme `SEGSENSE_API_001`.

## 2. Recursos

| Método | Caminho |
|---|---|
| `POST` | `/api/v1/admin/publishers` |
| `GET` | `/api/v1/admin/publishers` |
| `GET` | `/api/v1/admin/publishers/{publisherId}` |
| `PATCH` | `/api/v1/admin/publishers/{publisherId}` |
| `POST` | `/api/v1/admin/publishers/{publisherId}/status` |
| `POST` | `/api/v1/admin/publishers/{publisherId}/channels` |
| `GET` | `/api/v1/admin/publishers/{publisherId}/channels` |
| `GET` | `/api/v1/admin/publishers/{publisherId}/channels/{channelId}` |
| `PATCH` | `/api/v1/admin/publishers/{publisherId}/channels/{channelId}` |
| `POST` | `/api/v1/admin/publishers/{publisherId}/channels/{channelId}/status` |
| `POST` | `/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments` |
| `GET` | `/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments` |
| `GET` | `/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments/{environmentId}` |
| `PATCH` | `/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments/{environmentId}` |
| `POST` | `/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments/{environmentId}/status` |

## 3. Paginação

Listagens usam cursor opaco:

- `page[size]`: 1 a 100; padrão 20
- `page[after]`: cursor da página anterior
- ordem: `createdAt,id` crescente

Resposta:

```json
{
  "items": [],
  "page": { "size": 20, "next": null }
}
```

## 4. Corpos

Criação de publicador: `{ "key", "name" }` → 201, status inicial `DRAFT`.

Criação de canal: `{ "key", "name", "type" }`.

Criação de ambiente: `{ "key", "name", "type", "canonicalUrl?" }`.

PATCH de nome: `{ "name", "version" }`. Campo `key` extra é ignorado e não altera a chave.

Transição: `{ "status", "version" }`.

Respostas incluem `effectivelyAvailable` calculado, sem alterar o status persistido dos filhos.

## 5. Erros

| HTTP | Código |
|---|---|
| 400 | `VALIDATION_ERROR` |
| 401 | `AUTHENTICATION_REQUIRED` |
| 403 | `ACCESS_DENIED` |
| 404 | `NOT_FOUND` (também cross-scope) |
| 409 | `CONCURRENT_MODIFICATION`, `PUBLISHER_KEY_CONFLICT`, `CHANNEL_KEY_CONFLICT`, `ENVIRONMENT_KEY_CONFLICT` |
| 422 | `INVALID_STATE_TRANSITION` |

Mensagens em português. Sem SQL, stack ou nome de constraint no corpo.

## 6. Honestidade operacional

A existência destes contratos **não** significa que a interface real consiga operá-los. Sem autenticação, o runtime nega. O frontend declara “Autenticação ainda não configurada” ao receber 401.
