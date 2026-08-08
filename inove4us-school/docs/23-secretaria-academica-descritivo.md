# Secretaria Acadêmica — Descritivo pós-reformulação (v2 híbrido + drill-down)

**Rota:** `/secretaria` · zona `operacional` · `SecretariaOperacional.jsx`  
**API única:** `backend/secretaria_routes.py` → `/api/secretaria/*`  
**Inventário prévio:** `docs/21-secretaria-academica-descritivo.md`  
**Calendário UI:** `frontend/src/components/MonthAgendaCalendar.jsx` (compartilhado com Radar Agenda)

## Decisões de produto

1. **Híbrido** — `curso_id` opcional em disciplina e em turma.  
2. **Hierarquia real** Período → Curso → Turma/Disciplina, navegada por expansão numa única seção **Estrutura Acadêmica** (não abas separadas).  
3. Turmas e Alunos nesta mesma página.  
4. Superfície única: removidos `secretaria_api.py`, `comunicacoes_api.py`, `Secretaria.jsx`.  
5. Calendário = grade mensal (mesmo componente do Radar). Mural = quadro de cards.

## Abas (6)

Unidades · Estrutura Acadêmica · Alunos · Calendário · Mural/Comunicações · Planejamento Escolar

### Estrutura Acadêmica

- Chips de períodos + “+ Novo período”
- Cards de cursos do período (contador turmas/disciplinas) → expansão
- Dentro do curso: Turmas | Disciplinas (2 colunas) + alocação docente ao expandir turma
- Seção **Sem curso** no período (fluxo flat)

## Schema relevante

| Tabela | Notas |
|--------|--------|
| `school_unidades` | campus |
| `school_periodos_letivos` | período |
| `school_cursos` | sob período (015); instituição via join no período |
| `school_disciplinas` | `curso_id` nullable + `instituicao_id` (019) |
| `school_turmas` | `unidade_id` (008); `periodo_letivo_id` NOT NULL + `curso_id` nullable (029); `ano_letivo` mantido |
| `school_alunos` | `turma_id` nullable |
| `school_calendario_letivo` | delete físico na API |
| `school_alocacoes_docentes` | `turma_id` opcional (028) → `TEACHER_ALLOCATED` |
| `school_comunicacoes_eventos` | mural; PATCH cancelar |
| `school_planejamento_escolar` | push esqueleto aula/evento → B2C (031) |

## Integrações

- `TEACHER_ALLOCATED` — inclui `turma_id`/`turma_nome` quando alocação tem turma.  
- Mural → `push_comunicado_to_b2c` (inalterado).  
- Planejamento → `POST /api/integracoes/school/planejamento` (`push_planejamento_to_b2c`); depende do endpoint B2C (`inove4us-21`).  
- Avisos Mesa (Radar) permanece canal irmão.

## Fora / próxima etapa

Endpoint B2C do planejamento (prompt companheiro); PEI com Turmas/Alunos reais; filtro mural por unidade via turma; gravação do `id_clie` real no aceite de convite.
