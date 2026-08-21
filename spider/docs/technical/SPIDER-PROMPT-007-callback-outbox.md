# SPIDER-PROMPT-007 — Callback Governado, Outbox e Reconciliação

## Escopo

Entrega persistente e governada de callback de resultado para originadores. Sem HTTP/mensageria real — somente Mock Callback Adapter.

## Modelos

- `CallbackDefinition` + catálogo (vazio por default)
- `CallbackDeliveryPolicy` + catálogo
- Projeções fechadas: `MINIMAL_STATUS_V1`, `CANONICAL_RESULT_V1`
- `ExecutionCallbackContext` (fixado antecipadamente)
- `CallbackOutboxRecord` / `CallbackDeliveryAttempt`
- `CallbackDeliveryPort` (neutra a transporte)

## Fluxo

1. Submit HTTP com `callbackRef` → resolve definição PUBLISHED, autoriza, fixa contexto
2. Terminalização (Engine/resume) → `persistTerminalResult` cria Outbox `PENDING` atomicamente
3. `CallbackOutboxProcessor` (invocável) → claim → attempt → Mock Adapter → delivered/retry/unknown/dead-letter/expired
4. Query autorizada → `CallbackDeliverySummary` seguro
5. `RequeueCallbackDeliveryUseCase` → deny-by-default

## Schema

Migration `V20260821e__tb_callback_outbox.sql`:

- `tb_execution_callback_context`
- `tb_callback_outbox`
- `tb_callback_delivery_attempt`

## Invariantes

- Sem URL/host/credencial em definition ou request
- Falha de callback **não** altera `technicalStatus` / outcome
- `UNKNOWN` sem retry automático
- Idempotent reuse / duplicate signal → uma Outbox lógica
- JPA fora da event loop (`BlockingPersistenceSupport`)

## Como testar

```powershell
cd C:\Projetos\spider\backend
..\.tools\apache-maven-3.9.16\bin\mvn.cmd test
```

## Adiado (PROMPT-008+)

Callback HTTP real; consulta de status no destino; scheduler distribuído; HMAC; Control Plane; IdP real.
