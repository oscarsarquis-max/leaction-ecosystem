# SEGSENSE_API_007 — APIs editoriais de demonstração (SegSense)

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_API_007 |
| Versão | 1.0 |
| Data | 12/09/2026 |

Este documento **não** é o Satellite Contract.

## Público

`GET /api/v1/public/demonstrations/{key}` — somente snapshot `LIVE`. `Cache-Control: no-store`. Sem IDs internos, autores ou PII. Ausência: `404 DEMONSTRATION_NOT_PUBLISHED`.

## Admin (deny-by-default)

`/api/v1/admin/demonstrations`

Autoridades: `segsense.demonstration.read|write|approve|publish`.

Anônimo: **401**. Fixture sem autoridade: **403**.

Mutações: create, `/draft`, `/submit`, `/return`, `/approve`, `/publish`, `/pause`, `/resume`, `/retire`, `/revisions`.

Respostas admin trazem `administrativePreview: true`.
