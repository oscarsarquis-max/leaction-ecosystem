# Loop de feedback da curadoria + dossiê PEI

## 1. Fechamento do loop (metodologia)

Resolução real hoje:

- `POST /api/pedagogico/curadoria/<id>/incorporar` → `incorporado` (aprovada)
- `POST /api/pedagogico/curadoria/<id>/adaptar` → mesma incorporação, aviso “adaptada”
- `POST /api/pedagogico/curadoria/<id>/rejeitar` → `mantido_apenas_na_aula` (não incorporada agora)

Toda ação exige `retorno_docente`. Sem texto, HTTP 400 `RETORNO_DOCENTE_OBRIGATORIO`.

Aviso em `school_avisos_mesa`: `tipo = resposta_proposta_metodologica`, `professor_b2c_id` = `id_clie` de quem enviou a sugestão (via `sugestao_professor_json` ou `plano_espelhado_id` → vínculo). Turma e disciplina ficam NULL.

Na Mesa: tag lilás `[Resposta à Proposta Metodológica]`. Unidirecional.

## 2. Dossiê de execução do PEI

`school_pei_alunos` não tinha período. Migration `041`: `periodo_letivo_id` → `school_periodos_letivos` + `intervencoes_previstas` (JSONB).

Linkagem aluno↔aula (mais direta): `mesa.pei_aluno_id` (= PEI) e `school_pei_alunos.aluno_id` (Secretaria). Fallback: `aluno_nome` normalizado. Recorte = datas do período declarado naquele PEI.

`GET /api/pei/alunos/<id>/relatorio-execucao` devolve PDF (`reportlab`). Quatro seções: matriz AEE vigente, aulas do período, adaptações (`pei_override_versao_aplicada` + texto/cards PEI), diário de bordo. Sem aula no período: PDF claro, sem dado de outro aluno.
