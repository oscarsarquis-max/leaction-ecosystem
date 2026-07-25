# Etapa 2/4 — Cursos e Disciplinas

Parte da versão ampliada **2.1.0** (Estruturação Pedagógica).

## Confirmações da Etapa 1 (reaplicadas)

| Item | Padrão |
|------|--------|
| Auth período | JOIN `inove_periodos_letivos` → `inove_instituicoes.id_clie` (sem `id_clie` na tabela de período) |
| Cursos/disciplinas | Mesmo JOIN até `id_clie` |
| Sem sessão | **401** |
| Não encontrado / outro professor | **404** (não 403) |
| Migration | `009_inove_cursos_disciplinas.sql` |

## Soft delete

- Curso: bloqueia se houver disciplina `ativo = true` (`409` + `code: disciplina_ativa`).
- Disciplina: soft delete livre nesta etapa (trava com aulas entra na Etapa 3).

## Freemium

Nada de curso/disciplina é obrigatório para aula avulsa.
