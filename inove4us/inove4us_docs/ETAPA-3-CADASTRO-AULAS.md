# Etapa 3/4 — Cadastro de Aulas (auditoria + extensão)

Parte da versão ampliada **2.1.0**.  
**Passo 0 obrigatório** — descobertas antes da migration.

## 1. Onde vivem aula/evento hoje

| Entidade | Tabela | Uso |
|----------|--------|-----|
| Dia a Dia | `inove_aulas_simples` | Planejamento ~50 min (`/dia-a-dia/*`) |
| Agenda / Desafio | `inove_agenda_eventos` | Calendário, EduScrum, espelho Dia a Dia, grafo |
| Wizard IA | *(sem tabela própria)* | Estado no React; persiste só via `POST /api/agenda-eventos/registrar-aulas` |

Não há `disciplina_id` / `origem` como coluna antes desta etapa.

## 2. Status (ciclo de vida)

### `inove_aulas_simples`
`draft` → `planejado` → `realizado`  
Create sempre `draft`; FE promove no save; delete só `draft`|`planejado`.

### `inove_agenda_eventos`
`planejado` → `em_execucao` → `concluido`  
Desafio inicia em `em_execucao`; `concluir-aula` → `concluido`.

**Os conjuntos de status não são iguais** — não unificar nesta etapa.

## 3. Grafo / vínculo entre aulas

- Coluna: `inove_agenda_eventos.id_evento_pai` (self-FK)
- API: `GET /api/agenda-eventos/grafo`
- UI: `MapaRealizacoes.jsx` (Mesa)
- **Não alterar** nesta etapa.

## 4. Conteúdo IA (Bedrock)

- `POST /api/wizard/estruturar` / `selecionar-caminho`: resposta JSON, sem write de aula.
- Persistência: `registrar-aulas` → `plan_data`, `kanban_state`, `meta_json`, `plano_session` em `inove_agenda_eventos`.

## 5. Origem hoje

- Sem coluna `origem` / `source` / `created_via`.
- Dia a Dia já grava `meta_json.origem = "dia_a_dia"` no espelho da agenda (metadado JSON, não coluna).

## 6. Decisões desta etapa

| Campo | `inove_aulas_simples` | `inove_agenda_eventos` |
|-------|----------------------|------------------------|
| `disciplina_id` | FK nullable → `inove_disciplinas` | FK nullable (mesma) |
| `tipo_registro` | `aula` \| `evento` (default `aula`) | **não criar** — já existe `tipo` (`geral` \| `aula_eduscrum` \| `aula_dia`) |
| `origem` | `manual` \| `wizard_ia` \| `importacao` (default `manual`) | idem |

- Seletor UI: **DailyPlanner** (Dia a Dia) — principal dono da entidade aula.
- Agenda: aceita `disciplina_id`/`origem` nos endpoints existentes; Desafio pode enviar depois sem mudança visual obrigatória nesta etapa.
- Soft-delete disciplina: passa a bloquear se houver aula (`inove_aulas_simples`) ou evento (`inove_agenda_eventos`) ativo com aquele `disciplina_id`.

## 7. Migration

- Up: `010_inove_aulas_vinculo_pedagogico.sql`
- Down: `010_inove_aulas_vinculo_pedagogico.down.sql`

Pré-requisito local: `007_inove_aulas_simples.sql` (a tabela Dia a Dia pode ainda não existir se o vetor só usava `ensure_*`).

## 8. API (estendida, sem rota paralela)

| Rota | Campos novos |
|------|----------------|
| `POST/PUT /api/daily/*` | aceita/expõe `disciplina_id`, `tipo_registro`, `origem` |
| `GET /api/daily/` | filtros opcionais `disciplina_id`, `curso_id`, `periodo_letivo_id`, `origem` |
| `POST /api/agenda-eventos` | `disciplina_id`, `origem` (valida ownership da disciplina) |
| `GET /api/agenda-eventos` | mesmos filtros via join |
| `POST …/registrar-aulas` | grava `origem='wizard_ia'` |
| Soft-delete disciplina | `409` se houver linhas em aulas_simples ou agenda com aquele `disciplina_id` |

## 9. Frontend

- `VinculoPedagogicoSelector` no `DailyPlanner` (oculto se não houver caminho completo Instituição→…→Disciplina).
- Agenda / grafo / Wizard IA: sem mudança visual nesta etapa.
