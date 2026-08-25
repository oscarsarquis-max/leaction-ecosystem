# SPIDER-PROMPT-016 — Telemetria Canônica e Operational Events

## Baseline

- Produto: **0.16.0** · boundary **MOCK_ONLY**
- Predecessor: SPIDER-PROMPT-015 VERIFIED (`1d63740`)
- Flag: `spider.telemetry.enabled` (default **false**)
- Persistência: `tb_operational_event` (`V20260825`) + memory store no modo `memory`

## Conceito

**Operational Event** é um fato observacional com semântica estável sobre uma execução.
Telemetria **observa** a execução; **não controla** a engine, wait/resume, callback ou segurança.

Não é event sourcing. O estado durável da engine permanece a fonte de verdade funcional.
Não há broker (Kafka/Rabbit). OpenTelemetry distribuído completo e SLOs ficam para 017+.

## Contrato

`OperationalEvent` (`schemaVersion = 1`):

| Campo | Notas |
|-------|--------|
| `eventId` | identidade própria |
| `eventType` / `category` | enums fechados |
| `occurredAt` | instante do fato |
| `executionId` | correlação obrigatória |
| `interactionId` / `correlationId` | opcionais |
| `source` | componente emissor |
| `outcome` | SUCCESS / FAILURE / WAITING / REJECTED / INFO (opcional) |
| `durationMs` | quando mensurável |
| `metadata` | allowlist + redaction 015 |

## Emissão

- Porta: `OperationalEventPublisher` → `SafeOperationalEventPublisher` (fail-open)
- Falha de telemetria: log `event=telemetry_publish_failed`; **não** gera OE recursivo; **não** altera resultado de negócio
- Instrumentação real: engine (start/success/fail/wait/reject), resume, signal ingress (incl. rejeições de segurança), callback outbox

## Consulta / Console

- `GET /v1/console/executions/{id}/events` (ação `VIEW_OPERATIONAL_EVENTS`, DenyAll default)
- UI: seção **Operational Timeline** (read-only), distinta da timeline projetada do estado persistido (015)

## Logs × Operational Events

| Logs | Operational Events |
|------|--------------------|
| Diagnóstico técnico da aplicação | Acontecimentos canônicos da execução |
| Livres / estruturados ad hoc | Catálogo tipado, correlacionável |

## Relação com 017 / 018

- **017** consome estes eventos (e outros sinais) para SLIs/SLOs — não implementado aqui
- **018** Failure Lab usa evidências/jornadas — não implementado aqui

## Referências

- ARCH-010 §9 (Operational Events) e decisões 016
- ARCH-013 (console / visualização)
- Manifesto CAP-016
