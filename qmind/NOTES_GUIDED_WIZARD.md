# Assessment Wizard — decisões e débitos (2026-08-06)

## Decisões
- Catálogo file-backed `catalog_iso9001_c4c10_v1.json` (cláusulas 4–10); perguntas próprias em pt-BR.
- Versão: `iso9001-2015-c4c10-v1` (sucede `iso9001-2015-c4c5-v1`).
- Sessão 1:1 com avaliação (`guided_sessions` + `guided_answers`), RLS por `organization_id`.
- Entrada draft/planned → `/assessments/:id/guided`; painel legado em `/advanced` ou status posteriores.
- OpenAPI e `@qmind/api-client` incluem operações guided; o web ainda usa `client.raw` em `guidedApi.ts`.
- `show_when` avaliado (backend e frontend) com regras `{ "answer": "qid", "in": [...] }`.
- Contagem de perguntas = apenas perguntas **visíveis** dadas as respostas atuais.
- Revisão entrega leitura narrativa por cláusula (não checklist cru).

## Débitos
- Migrar `guidedApi.ts` para SDK tipado gerado.
- Evidência anexada no Wizard ainda não cria `evidence_links` tipados para a pergunta guided (só IDs na resposta).
- IA fora do escopo desta entrega.
- Sessões antigas com `catalog_version` c4c5 continuam válidas; novas sessões gravam c4c10.

## Ops
- Publish deve ler sessão/respostas **antes** de `conn.commit()` (GUC `app.organization_id` é local à transação).
- Regenerar catálogo: `python app/modules/guided/_build_c4c10_catalog.py` (a partir do c4c5 + bloco 6–10).
