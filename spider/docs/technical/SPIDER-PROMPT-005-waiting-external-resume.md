# SPIDER-PROMPT-005 — WAITING_EXTERNAL, Inbox, Sinais e Retomada

## Modelo

| Conceito | Papel |
|---|---|
| `WaitPolicyDefinition` | Policy publicada (type, sources, contract, maxWait, expiryAction) |
| `ExecutionWaitRecord` | Wait ativa por execution/step/attempt |
| `InboxRecord` | Reserva/dedup de sinal externo |
| `ExternalSignalEnvelope` | Contrato **interno** (sem HTTP público) |

Wait types: `ASYNC_COMPLETION`, `UNKNOWN_OUTCOME_RECONCILIATION`.  
Expiry: `TIME_OUT_EXECUTION` | `FAIL_EXECUTION` | `OPEN_RECONCILIATION`.

## Persistência

Migration aditiva: `database/migrations/V20260821c__tb_execution_wait_inbox.sql`  
Tabelas: `tb_execution_wait`, `tb_inbox_message`.  
Adapters: memory (default) + entidades JPA a evoluir; ports `ExecutionWaitStorePort` / `InboxStorePort`.

## Fluxos

1. **ACCEPTED_ASYNC** → valida continuation + Wait Policy → cria wait → step/execution `WAITING_EXTERNAL` → idempotência `IN_PROGRESS`.
2. **UNKNOWN** → sem retry → wait reconciliation (sem continuation → `RECONCILIATION_REQUIRED`).
3. **Sinal** (`ExternalSignalApplicationPort.process`) → reserve Inbox → auth deny-by-default → validate → claim wait → complete attempt → resume steps restantes do **mesmo** plan.
4. **Expiry** (`WaitExpiryProcessor.expire`) — invocável/idempotente; sem scheduler distribuído.
5. **Late / Orphan** → `LATE_REJECTED` / `ORPHANED`; não reabre terminal.

## Segurança provisória

`ConfiguredExternalSignalAuthorization`: principals/sources cadastrados. Sem IdP, sem credential no envelope.

## Deduplicação

Fingerprint SHA-256 v1.0 (source, messageId, contract, execution, step, extOp, completion lógico).  
Mesmo messageId + mesmo fp → DUPLICATE; fp diferente → CONFLICT (não altera wait).

## Ausências deste incremento

- Endpoint HTTP público de callback
- Outbound callback / polling / consumer real
- Scheduler distribuído
- Reconciliação completa
- Paralelismo / compensation

## Próximos itens (PROMPT-006+)

Endpoint canônico de sinal, autenticação corporativa, jitter/HMAC, Testcontainers PG para wait/inbox, outbound callback.
