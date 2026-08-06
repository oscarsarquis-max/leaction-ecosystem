# Assessment Wizard — decisões e débitos (2026-08-06)

## Decisões
- Catálogos file-backed versionados:
  - `catalog_iso9001_c4c5_v1.json` → `iso9001-2015-c4c5-v1` (15 perguntas, cláusulas 4–5) — preservado.
  - `catalog_iso9001_c4c10_v1.json` → `iso9001-2015-c4c10-v1` (padrão; cláusulas 4–10).
- Loader por `catalog_version`; API `GET /guided/catalog?version=…`.
- `show_when`: `answer` / `context` + `equals` | `not_equals` | `in` | `not_empty`, `all` / `any`.
- **Método consultivo:** abertura (antes da 1ª pergunta) + fechamento narrativo (após a última) por cláusula 4–10; revisão final consolidada. Sem julgamento automático de conformidade.
- Contagem = perguntas **aplicáveis** (visíveis). Respostas ocultas preservadas.
- Migração segura: só `draft` + sessão sem respostas + legado c4c5 → c4c10.

## Débitos
- Evidência tipada (`evidence_links`) a partir do Wizard.
- Ação “Adicionar evidência” na revisão final ainda redireciona ao roteiro (não abre upload dedicado).
- Sessões `planned`/`in_progress` com respostas em c4c5 não migram automaticamente.

## Ops
- Regenerar c4c10: `python app/modules/guided/_build_c4c10_catalog.py`
- OpenAPI: `python scripts/export_openapi.py` → `npm run generate:api-client`
