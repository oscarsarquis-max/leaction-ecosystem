# SPIDER-PROMPT-004 — Multi-step Sequencial, Attempts e Retry

## Modelo linear

- Rotas com 1..`spider.canonical.route.max-steps` (default **8**) steps.
- Exatamente um entry (sem dependência); demais com exatamente uma dependência.
- Sem branch, join, ciclo ou DAG genérico.
- Target da rota = capability/operation do **step de entrada**.
- Steps não executados após falha terminal → `SKIPPED`.

## Mappings fechados

| Ref | Semântica |
|---|---|
| `mapping:ROOT_REQUEST_CANONICAL_DATA@1.0` | canonicalData do request |
| `mapping:PREVIOUS_STEP_CANONICAL_DATA@1.0` | output do predecessor |
| `mapping:MERGE_ROOT_AND_PREVIOUS_CANONICAL_DATA@1.0` | merge raso; conflito de chave → rejeição |

Sem SpEL/script/reflection.

## Retry

- `RetrySafety`: SAFE / SAFE_WITH_IDEMPOTENCY_KEY / UNSAFE
- Policy publicada via `RetryPolicyCatalogPort` (vazio por default; fixtures em teste)
- Critérios: error.retryable ∧ category/code da policy ∧ safety ∧ budget ∧ maxAttempts
- Nunca retry: AUTH/AUTHZ/VALIDATION/IDEMPOTENCY/BUSINESS_OUTCOME; async; unknown; business success técnico
- Backoff exponencial limitado; **sem jitter** neste incremento
- Uma chamada Adapter por attempt; attempts append-only

## Persistência

| Tabela | Papel |
|---|---|
| `tb_execution_step` | estado por step + state_version |
| `tb_step_attempt` | attempts imutáveis após terminal |

Migration: `database/migrations/V20260821b__tb_execution_step_attempt.sql`

Adapters memory (default) e JPA (`mode=jpa`). Outputs intermediários: `IntermediateStepOutputStore` (memória técnica).

## Budget

`ExecutionDeadline` absoluto (`spider.canonical.execution.budget`, default PT60S).  
Backoff/attempt não ultrapassam deadline.

## Async / unknown

Step e execution → `WAITING_EXTERNAL`; steps posteriores não executam; sem retomada neste prompt.

## Testes JPA

H2 adicionado (test scope). Cobertura JPA real mínima via stores em memória com mesmo contrato das portas + migration SQL documentada. Diferenças PG: `timestamptz` / constraints equivalentes em H2 quando `mode=PostgreSQL`.

```powershell
cd C:\Projetos\spider\backend
..\.tools\apache-maven-3.9.16\bin\mvn.cmd test
```

## Endpoint legado

`POST /v1/products/orchestrate` permanece no baseline. Sem Engine no path HTTP.

## Adiado (PROMPT-005+)

- Paralelismo / fork-join / conditions
- Retomada de WAITING_EXTERNAL
- Compensation
- Jitter no backoff
- HMAC / criptografia
- Testcontainers PG completo
- Endpoint canônico público
