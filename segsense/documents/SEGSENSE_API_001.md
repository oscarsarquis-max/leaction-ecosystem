# SEGSENSE_API_001 — Convenções HTTP do Satellite BFF

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_API_001 |
| Título | Convenções HTTP do Satellite BFF |
| Categoria | ARQ / API |
| Versão | 1.4 |
| Status | Vigente nesta etapa |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_ARQ_002; SPIDER-ARCH-017 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Convenções da fundação BFF; somente endpoints existentes. |
| 1.1 | 04/09/2026 | 401/403 padronizados, política de exposição deny-by-default e no-enumeration. |
| 1.2 | 04/09/2026 | Paginação por cursor em uso; catálogo admin; CORS POST/PATCH; códigos 400/409/422. |
| 1.3 | 04/09/2026 | Códigos de oportunidade: `OPPORTUNITY_KEY_CONFLICT`, `STALE_OPPORTUNITY_REVISION`, `NO_CONTENT_CHANGE`, `INVALID_PARENT_STATE`. |
| 1.4 | 15/09/2026 | Recursos públicos de captura: `POST /api/v1/public/demo/url-captures` e `POST .../confirmations`. Contrato: `SEGSENSE_URL_001`. |

## 1. Convenções HTTP

- Representação: JSON em UTF-8 (`application/json`).
- Nomes de código, campos JSON e códigos de erro em inglês.
- Mensagens destinadas ao usuário em português.
- URLs de aplicação versionadas sob `/api/v1`.
- Health de infraestrutura permanece em `/actuator/health` e `/actuator/health/readiness` (Spring Boot), fora do contrato de domínio.

## 2. Versionamento

A versão da API de aplicação está no caminho (`/api/v1`). Mudanças incompatíveis exigirão `/api/v2`. Campos novos em respostas existentes serão aditivos quando possível. Este documento não cria recursos fictícios para justificar a versão.

## 3. Correlação

Requisições `/api/**` usam o header `X-Correlation-ID`.

- Valor aceito somente se for UUID válido.
- Ausência ou valor inválido: o BFF gera um UUID.
- O response devolve o identificador efetivamente utilizado.
- O mesmo valor aparece no MDC `correlationId` durante a requisição e no campo `correlationId` dos erros padronizados.
- O frontend envia um UUID novo por chamada técnica. Não armazena o identificador indefinidamente e não o usa para rastreamento de usuário.

Este valor é correlação **local** do satélite. Não é `requestId`, `decisionId`, `planId`, `executionId` nem `interactionId` da Spider. O mapeamento futuro desses IDs dependerá do Satellite Contract executável. Eles não serão colapsados em um único campo.

## 4. Erros

Corpo padronizado:

```json
{
  "code": "NOT_FOUND",
  "message": "O recurso solicitado não foi encontrado.",
  "timestamp": "2026-09-04T12:00:00Z",
  "correlationId": "22222222-2222-2222-2222-222222222222"
}
```

- `code` estável, inglês, `UPPER_SNAKE_CASE`.
- `message` em português, sem stack trace, nome de classe, SQL, roles esperadas ou segredo.
- `timestamp` em ISO-8601 UTC.
- Códigos atuais: `NOT_FOUND`, `INTERNAL_ERROR`, `AUTHENTICATION_REQUIRED`, `ACCESS_DENIED`, `VALIDATION_ERROR`, `CONCURRENT_MODIFICATION`, `INVALID_STATE_TRANSITION`, `PUBLISHER_KEY_CONFLICT`, `CHANNEL_KEY_CONFLICT`, `ENVIRONMENT_KEY_CONFLICT`. Contratos de recurso: `SEGSENSE_API_002`.

### 4.1 Autenticação e autorização

| HTTP | Código | Quando |
|---|---|---|
| 401 | `AUTHENTICATION_REQUIRED` | Não há autenticação válida. Mensagem: `Autenticação necessária.` |
| 403 | `ACCESS_DENIED` | Há ator autenticado sem autorização para a operação. Mensagem: `Acesso não autorizado para esta operação.` |

O header `X-Correlation-ID` e o campo `correlationId` do corpo usam o mesmo UUID. Respostas de segurança não incluem `WWW-Authenticate: Basic` nem página HTML de login.

Rotas `/api/**` sem política explícita são negadas por padrão. Para um chamador anônimo isso resulta em **401**, sem revelar se o recurso existiria (no-enumeration).

## 5. Datas

Datas e instantes usam ISO-8601 em UTC (exemplo: `2026-09-04T12:00:00Z`). O backend fixa timezone UTC na JVM, no Jackson e no Hibernate JDBC.

## 6. Identificadores

- Identificadores distribuídos gerados pelo satélite: UUID.
- Identidade do satélite: `applicationId` = `SEGSENSE` (configuração, não UUID).
- IDs futuros da Spider permanecerão campos distintos, com os nomes canônicos do SPIDER-ARCH-017.

## 7. CORS

- Origens explícitas (`segsense.cors.allowed-origin` / `SEGSENSE_FRONTEND_ORIGIN`, lista separada por vírgula). Sem curinga. No local, `http://127.0.0.1:5178` e `http://localhost:5178` são origens distintas e ambas precisam estar na lista.
- Métodos atuais: `GET`, `POST`, `PATCH`, `OPTIONS`.
- Headers permitidos: `Accept`, `Content-Type`, `X-Correlation-ID`.
- Header exposto: `X-Correlation-ID`.
- Sem cookies de credencial nesta etapa (`allowCredentials=false`).

## 8. Paginação

Coleções do catálogo administrativo usam cursor:

- `page[size]`: 1 a 100; padrão 20;
- `page[after]`: cursor opaco da página anterior;
- ordem determinística: `createdAt,id`.

Justificativa: deslocamento (`page`/`offset`) torna-se instável sob inserção concorrente. Detalhes dos recursos: `SEGSENSE_API_002`.

## 9. Idempotência futura

Mutações futuras exigirão idempotência. Este satélite **não** introduz header de idempotência agora, para não conflitar com o mecanismo que o Satellite Contract executável vier a definir. Quando o contrato existir, o BFF adotará o identificador ali especificado. Mutações puramente locais, se surgirem antes do contrato, reavaliarão o header neste documento em vez de copiar um nome potencialmente incompatível.

## 10. Compatibilidade

O frontend depende de `GET /api/v1/system/info` com `name`, `version`, `applicationId` e `operationalState`. Payload sem `applicationId` é rejeitado e apresentado como indisponibilidade, não como sucesso parcial.

## 11. Endpoints existentes e política de exposição

Somente recursos realmente implementados no runtime:

| Método | Caminho | Exposição |
|---|---|---|
| `GET` | `/api/v1/system/info` | Público |
| `GET` | `/actuator/health` | Público; detalhes ocultos |
| `GET` | `/actuator/health/readiness` | Público |
| `OPTIONS` | `/api/**` | Pré-voo CORS da origem configurada |
| `GET` | `/api/v1/admin/**` | Protegido: `segsense.catalog.read` (401 anônimo) |
| `POST`, `PATCH` | `/api/v1/admin/**` | Protegido: `segsense.catalog.write` (401 anônimo) |
| — | demais `/api/**` | Negado por padrão (401 anônimo / 403 autenticado sem política) |
| — | demais `/actuator/**` | Não expostos |

Exemplo de `GET /api/v1/system/info`:

```json
{
  "name": "SegSense",
  "version": "0.1.0",
  "applicationId": "SEGSENSE",
  "operationalState": "UP"
}
```

`operationalState` é `UP` ou `DEGRADED`. Não há endpoint de manifesto, de jornada, de intent nem de Icatu.
