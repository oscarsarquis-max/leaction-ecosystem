# SPIDER-PROMPT-002 — Engine Canônica Mínima

## Packages e responsabilidades

| Package | Papel |
|---|---|
| `execution.route` | `RouteDefinition`, step único, catálogo em memória, validação, resolver determinístico |
| `execution.plan` | `ExecutionPlan` imutável + `DeterministicExecutionPlanMaterializer` |
| `execution.runtime` | Estado transitório, recorder em memória, máquina de estados mínima |
| `execution.engine` | `CanonicalExecutionEngine` / `DefaultCanonicalExecutionEngine` + mapping Adapter→estado |
| `execution.support` | `IdentifierGenerator`, `SpiderClock`, `IntegrityDigestPort` |
| `integration.binding` | `AdapterBindingResolverPort` / `ConfiguredAdapterBindingResolver` |
| `config.CanonicalEngineConfig` | Beans técnicos; catálogo vazio por default |

## Fluxo da vertical slice

```text
CanonicalExecutionRequest
  → RECEIVED
  → validação estrutural (QUERY)
  → VALIDATED | REJECTED
  → RouteResolver (catálogo PUBLISHED)
  → RESOLVED | REJECTED
  → ExecutionPlan materializado (versões + digest)
  → PLANNED
  → check idempotency REQUIRED
  → resolve adapterBindingRef
  → RUNNING
  → UniversalAdapterPort (Mock em teste/dev)
  → map disposition → SUCCEEDED | FAILED | TIMED_OUT | WAITING_EXTERNAL
  → CanonicalExecutionResult
```

## Modelo de rota e plano

- Rota: exatamente **um** step linear neste incremento.
- Somente `RouteStatus.PUBLISHED` é elegível.
- Resolver ordena por `priority` explícita; empate na maior prioridade → `ROUTE_AMBIGUOUS`.
- Plano fixa `routeCode@version`, contracts, binding e policies por referência.
- Integridade: SHA-256 da representação canônica estável (`IntegrityDigestPort`).

## Configurar rota + Mock em teste

```java
RouteCatalogPort catalog = new InMemoryRouteCatalog(
    List.of(CanonicalRouteFixtures.publishedSingleStep("demo", 1)));
AdapterBindingResolverPort bindings = new ConfiguredAdapterBindingResolver(
    Map.of(ConfiguredAdapterBindingResolver.DEFAULT_MOCK_BINDING,
           new MockUniversalAdapter(objectMapper)));
```

Cenários Mock via `payload.canonicalData.mockScenario`:
`SUCCESS`, `TECHNICAL_FAILURE`, `BUSINESS_NEGATIVE`, `TIMEOUT`, `INVALID_RESPONSE`, `UNKNOWN`, `ACCEPTED_ASYNC`.

Binding default: `binding:mock-universal@1.0` (`spider.adapter.bindings.mock-ref`).

## Testes

```powershell
cd C:\Projetos\spider\backend
..\.tools\apache-maven-3.9.16\bin\mvn.cmd test
```

## Endpoint atual

`POST /v1/products/orchestrate` **não** foi migrado. Continua em
`OrchestrationCompatibilityService` → `OrchestrationService` (legacy baseline).
A Engine canônica é interna e exercitada por testes; sem endpoint público novo.
Shadow mode **não** foi introduzido (evitar efeito externo duplicado).

## Limitações / adiados (PROMPT-003+)

- Um step apenas; sem fork/join, compensation, retomada de `WAITING_EXTERNAL`
- Sem persistência JPA de plan/state/transitions
- Sem idempotency store / retry real
- Catálogo em memória (não é Control Plane)
- Sem endpoint público canônico
- Sem Adapter real / legado
