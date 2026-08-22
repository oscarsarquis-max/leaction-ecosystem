# Máquinas de estados — execução (0011)

## Ordem

`released` → `in_weighing` (abrir sessão) → `ready` (`mark_order_ready`) → `in_progress` (iniciar etapa).

Pausa: `released` | `in_weighing` | `ready` | `in_progress` → `on_hold` → retoma `held_from_status`.

Término: `completed` (dentro da tolerância) ou `short_closed` (parcial/fora do alvo, autorizado).

`cancelled` só se não houver fatos de execução.

## Batelada

`pending` → `in_weighing` → `ready` → `in_progress` → `completed` | `short_closed`.

## Etapa (por batelada)

`pending` → `ready` → `in_progress` ⇄ `on_hold` → `completed`.

Pular: `pending`|`ready` → `skipped` (motivo). Cancelar etapa conforme encerramento permitido. Sequência: predecessor da mesma batelada precisa estar `completed` ou `skipped`.
