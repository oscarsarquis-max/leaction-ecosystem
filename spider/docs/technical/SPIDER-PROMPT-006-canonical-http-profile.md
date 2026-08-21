# SPIDER-PROMPT-006 — Perfil REST/HTTP Canônico

## Escopo

REST/HTTP é **Adapter inbound opcional**. Engine, stores e Porta Universal não dependem de HTTP.

## Feature flags (default `false`)

```yaml
spider.canonical.http.enabled: false
spider.canonical.http.status-query-enabled: false
spider.canonical.signal-http.enabled: false
```

Gates técnicos transitórios — não são Control Plane.

## Endpoints (somente com flags)

| Método | Path | Flag |
|---|---|---|
| POST | `/v1/canonical/executions` | `http.enabled` |
| GET | `/v1/canonical/executions/{id}` | `http.enabled` + `status-query-enabled` |
| POST | `/v1/canonical/signals` | `signal-http.enabled` |

`POST /v1/products/orchestrate` permanece no legacy baseline.

## Auth / Authz

- `CanonicalIngressAuthenticationPort` → default **DenyAll**
- `CanonicalExecutionAuthorizationPort` → default **DenyAll**
- `ExternalSignalIngressAuthenticationPort` → default **DenyAll**
- Authenticator permissivo **somente em testes** (`@Primary` em `@TestConfiguration`)
- Body **não** é autoridade de identidade; `originatorId`/`channel` devem bater com o autenticado

## Ownership

Campo aditivo `owner_principal_ref` em `tb_execution_control` / `ExecutionControlRecord`.  
Preenchido nas submissões HTTP; query exige match de ownership (sem enumeração).

## Trace / Idempotency-Key

Header `Idempotency-Key` reconciliado com body (iguais ou body omitido).  
`traceparent` reconciliado quando ambos presentes.

## Sinal HTTP

DTO `ExternalSignalHttpRequest` **sem** Security Context do cliente.  
Controller autentica peer e constrói `SignalSecurityContext` internamente; chama só `ExternalSignalApplicationPort`.

## Status mapping

`CanonicalHttpStatusMapper`: 200 terminal success, 202 waiting/running, 401/403/409/422/5xx conforme categoria canônica.

## JPA Wait / Inbox

Adapters dedicados: `JpaExecutionWaitStoreAdapter`, `JpaInboxStoreAdapter` (`mode=jpa`).  
Teste H2: `JpaWaitInboxPersistenceIT`.

## Limites

`max-request-bytes`, `max-canonical-data-bytes`, `request-timeout` — defaults conservadores.

## Como testar

```powershell
cd C:\Projetos\spider\backend
..\.tools\apache-maven-3.9.16\bin\mvn.cmd test
```

## Adiado (PROMPT-007+)

IdP/OAuth real, outbound callback, HMAC, Control Plane, migração do legado, scheduler distribuído.
