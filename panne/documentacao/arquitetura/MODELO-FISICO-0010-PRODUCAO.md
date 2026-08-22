# Modelo físico — `0010_production_planning`

Tabelas (todas organizacionais, ENABLE+FORCE RLS):

| Tabela | Papel |
|---|---|
| `production_code_counter` | numeração concorrente por org/tipo/período |
| `production_plan` | plano do recorte |
| `production_plan_item` | demanda no plano (não vira ordem sozinha) |
| `production_order` | ordem |
| `production_order_dependency` | predecessor → dependente, sem autorreferência |
| `production_batch` | partição da ordem |
| `production_order_material` | snapshot de materiais |
| `production_order_step` | snapshot de etapas |
| `production_batch_material` | alocação planejada por batelada |
| `production_event` | fatos append-only |

FKs compostas `(id, organization_id)` ligam produto, formulação, escala, estabelecimento e plano à mesma organização. Código público único por organização. Índice parcial: no máximo uma ordem não cancelada por item de plano.

Gatilhos: evento imutável; snapshot sem update/delete; código público imutável; ordem não exclui após sair de `draft`/`scheduled`; plano não exclui se houver ordem ou evento.

Revision Alembic: `0010_production_planning` (≤32 caracteres).
