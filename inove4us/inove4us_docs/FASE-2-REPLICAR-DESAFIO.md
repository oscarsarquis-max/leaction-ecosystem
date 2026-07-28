# Fase 2/3 — Replicar desafio para múltiplas turmas

## Passo 0 — auditoria (antes da implementação)

| Pergunta | Achado |
|----------|--------|
| Tabela `desafio`? | **Não existia.** Desafio era emergente: `plano_session` + cadeia `id_evento_pai` + conteúdo em `plan_data` / `meta_json` / `kanban_state` de `inove_agenda_eventos`. |
| `hipotese` / `hipotese_teste` | Wizard → `plan_data.hipotese` (+ espelho `meta_json.hipotese`). Fallback FE: `plan_data.hipotese_teste`. |
| `causas` | Só no React do Wizard (`causas_raiz`). **Não persistiam** até esta fase. |
| `tema` | Coluna `tema` + `meta_json.tema` (import). Wizard `registrar-aulas` não preenchia. |
| Turma | Execução: `inove_agenda_eventos.turma` + `turno`. Cadastro Etapa 2: `inove_cursos.turma_turno` (rótulo do curso — entidade distinta). |
| Fase 1 Kanban | Escopo = `plano_session` ∪ cadeia `id_evento_pai` — **não** mistura execuções se cada réplica ganha `plano_session` novo. |

## Decisão de modelo (Fase 2)

1. Tabela **`inove_desafios`**: fonte da verdade de hipótese, causas, tema, `plan_data` template.
2. Coluna **`inove_agenda_eventos.desafio_id`** (UUID, nullable legado).
3. Cada **execução** = um `plano_session` distinto + cadeia própria de aulas, todas com o mesmo `desafio_id`.
4. **Replicar não chama IA** — só copia do registro `inove_desafios` / aula fonte.
5. Grafo multi-turma simultâneo: **fora de escopo** (possibilidade futura).

Migration: `014_inove_desafios.sql`.
