# Etapa 4/4 — Importação de arquivo geral de aulas/eventos

Parte da versão ampliada **2.1.0**. Fecha o ciclo da Estruturação Pedagógica.

## Passo 0 — caminho de escrita

### O que existe hoje

| Fluxo | Escrita | Espelho |
|-------|---------|---------|
| Dia a Dia `POST /api/daily/planejar` | `inove_aulas_simples` (`draft`) | `_sync_agenda_evento` → `inove_agenda_eventos` (`planejado`, `tipo=aula_dia`) |
| Wizard `registrar-aulas` | só `inove_agenda_eventos` | sem `aulas_simples` |
| Compromisso manual | só `inove_agenda_eventos` | — |

- Grafo / `id_evento_pai` vive **apenas** em `inove_agenda_eventos`.
- Calendário da Mesa lê **apenas** `inove_agenda_eventos`.
- Não há coluna `id_externo` antes desta etapa (só metadados em `meta_json`).

### Decisão

A importação **não** chama `planejar` (força prefixo de título e `meta.origem=dia_a_dia`).

Usa um serviço único `importacoes_service.upsert_registro_importado`:

1. **Sempre** upsert em `inove_agenda_eventos` (requisito mínimo: aparecer no calendário + grafo).
2. Se `tipo=aula`: também upsert em `inove_aulas_simples` (`status=draft`) e mantém o espelho via `id_evento_agenda` / `meta_json.aula_simples_id` — mesmo vínculo do Dia a Dia, sem passar pelo Wizard.
3. Se `tipo=evento`: só agenda (`tipo=geral`).
4. `origem='importacao'` nas duas tabelas; idempotência `(id_clie, id_externo_importacao)`.
5. Passada 2: `vinculo_pai_id_externo` → `id_evento_pai` (só dentro do lote).

Status “aguardando planejamento”: `draft` (Dia a Dia) / `planejado` sem `plan_data` (Agenda).

## Migration

- Up: `011_inove_importacoes_lote.sql`
- Down: `011_inove_importacoes_lote.down.sql`

## API

| Método | Rota |
|--------|------|
| POST | `/api/importacoes/aulas-eventos` |
| GET | `/api/importacoes` |
| GET | `/api/importacoes/:id` |

## Frontend

- `/importacoes` — upload + resumo + relatório + histórico
- Atalho **Importar** na Mesa
- Agenda: badge “Importado · aguarda planejamento”; filtro `?origem=importacao`

## Exemplo

`inove4us_docs/exemplos/importacao-aulas-exemplo.json`
