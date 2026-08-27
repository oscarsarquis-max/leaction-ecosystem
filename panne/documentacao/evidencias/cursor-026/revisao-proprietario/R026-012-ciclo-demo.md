# R026-012 — Ciclo start/stop da demo

## Estado

**Corrigida e revalidada** — ciclo técnico completo (Cursor) + confirmação Cortex da instância final.

## Incidentes

R026-003, R026-008, R026-011: API antiga em `:5080` com `/health` ok.

## Causa

Reuso por health; PID de launcher ≠ listener; stop incompleto; colisão `$ApiHealth`/`$apiHealth` (PS case-insensitive).

## Correcao

- `demo-lifecycle.ps1` — identidade, sanitizacao, stop seguro
- `start-demo.ps1` — ciclo limpo obrigatorio; `-ReuseExisting` opt-in; `instance_id` via env
- `stop-demo.ps1` — arvore + orfaos Panne; desconhecido nao morto
- `/health` demo: `instance_id`, `logical_database`, `demo_anchor_date`, `process_id`

## Validacao

### Ciclo tecnico (Cursor)

stop → livre → start → replace → stop → stop → start final OK.

### Cortex (estado final)

Confirmou `/health` 200, `/ready` 200, `/entrar` 200, ambiente demo, `panne_demo`, ancora `2026-08-24`.
Identificador efemero da execucao (nao permanente): `3c0df0d52c934eedba2358adbdbd0072`.
O Cortex nao repetiu o harness automatizado; validou o estado final.

## Testes

Harness 14 passed; backend health 7 passed. Sem segredo em `instance.json`.

## Restricoes

CURSOR-027 nao iniciado. Sem force/merge/deploy neste registro.
