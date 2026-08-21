# SPIDER-PROMPT-003 — Persistência Técnica, Idempotência e Recuperação

## Tabelas (aditivas)

| Tabela | Finalidade |
|---|---|
| `tb_execution_control` | Estado corrente, `state_version`, rota/plano |
| `tb_execution_plan` | Plano imutável + representação canônica + integrity |
| `tb_execution_transition` | Histórico append-only `(execution_id, sequence_no)` |
| `tb_execution_result` | Resultado técnico reutilizável + digest + expires_at |
| `tb_idempotency_record` | Escopo+hash da chave (nunca em claro) + fingerprint |

Migration: `database/migrations/V20260821__tb_canonical_execution_persistence.sql`  
Também anexada a `database/init.sql` para volumes novos.  
**Não altera** `tb_product_routes` / `tb_audit_trace`.

Aplicar em volume existente:

```powershell
psql -h localhost -U spider_user -d spider_orchestrator -f database/migrations/V20260821__tb_canonical_execution_persistence.sql
```

## Portas e adapters

Portas (sem JPA): `execution.persistence.port.*`  
Coordenador bloqueante: `ExecutionPersistenceCoordinator`  
Facade reativa: `ReactiveExecutionPersistenceGateway` → `BlockingPersistenceSupport` (`subscribeOn(boundedElastic)`)

| `spider.canonical.persistence.mode` | Implementação |
|---|---|
| `memory` (default) | `infrastructure.persistence.memory.*` |
| `jpa` | `infrastructure.persistence.jpa.JpaCanonicalPersistenceAdapters` |

## Fingerprint v1.0

- Algoritmo: SHA-256 sobre JSON canônico com chaves ordenadas
- Inclui: contract major, originator, channel, capability/operation, context refs, canonicalData, callbackRef
- Exclui: executionId, timestamp, correlationId, traceparent/tracestate
- **Limitação:** sem HMAC/secret management (adiado)

## Idempotência

- Escopo: `originatorId|capability|operation|contractMajor` → `scopeHash`
- Chave: apenas `idempotencyKeyHash` (SHA-256); nunca coluna em claro
- `REQUIRED` exige chave; `OPTIONAL` usa se presente; `NOT_SUPPORTED` ignora chave (documentado)
- Corrida: insert do registro idempotente antes da execução + unique `(scope_hash, key_hash)`
- TTL default: `PT24H`

Reuse: in-progress / completed / failed / unknown **sem** Adapter.  
Conflict: `REJECTED` + `IDEMPOTENCY_CONFLICT` sem Adapter.

**Correlation no reuse:** resultado persistido preserva correlação original; projeção in-progress pode usar correlation do request atual apenas na view, sem alterar o controle histórico.

## Recovery consultiva

`ExecutionRecoveryService` — `findByExecutionId`, `findRecoverableExecutions`, `verifyPlanIntegrity`.  
Sem retomada automática, sem Adapter.

## Result persistido

Serializer versionado com digest e limite `spider.canonical.persistence.result.max-bytes` (65536).  
Proteção criptográfica do conteúdo: adiada.

## Isolamento WebFlux/JPA

Nenhuma chamada a repository na Engine. Toda persistência passa pelo gateway reativo.  
Sem `.block()` no fluxo de runtime.

## Testes

```powershell
cd C:\Projetos\spider\backend
..\.tools\apache-maven-3.9.16\bin\mvn.cmd test
```

Testes de persistência usam stores em memória (mesmo contrato das portas).  
H2/Testcontainers não foram adicionados; diferenças PG (jsonb legado vs text canônico) documentadas — tabelas canônicas usam `text`.

## Endpoint atual

`POST /v1/products/orchestrate` permanece no legacy baseline. Engine canônica não está no path HTTP.

## Adiado (PROMPT-004+)

- Retomada automática / reconciliation workflow
- HMAC do fingerprint e criptografia do result
- Retry, multi-step, callback real
- Evidence store definitivo
- Endpoint canônico público
- Migração do orchestrate HTTP
- Startup inspection (flag existe, default off)
