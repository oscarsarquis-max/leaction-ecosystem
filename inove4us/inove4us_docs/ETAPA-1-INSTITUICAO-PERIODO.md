# Etapa 1/4 — Instituição + Período Letivo

Parte da versão ampliada **2.1.0** (Estruturação Pedagógica).

## Ajustes aplicados ao prompt original

| Prompt | Decisão no inove4us |
|--------|---------------------|
| `professor_id` | `id_clie` → `ctdi_clie` (mesmo de `/api/auth/me`) |
| Tabelas genéricas | Prefixo `inove_instituicoes`, `inove_periodos_letivos` |
| uuid/serial | `BIGSERIAL` (padrão das tabelas `inove_*`) |
| Soft delete só em instituição | `ativo` também em período letivo |
| 1 `em_curso` por instituição | Unique index parcial + endpoint `marcar-em-curso` |
| Migration | `008_inove_instituicoes_periodos_letivos.sql` (SQL puro) |

## Fora de escopo (mantido)

- Cursos/disciplinas/aulas/importação  
- Diretório compartilhado de instituições  
- Obrigatoriedade de vínculo em aulas freemium  

## Critério de pronto

- [x] Migration 008  
- [x] CRUD API com filtro por `id_clie`  
- [x] Regra 1 período em curso / instituição  
- [x] UI mínima em `/instituicoes`  
