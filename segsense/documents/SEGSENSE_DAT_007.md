# SEGSENSE_DAT_007 — Snapshots de URL, hashes, contribuições e integridade

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_DAT_007 |
| Versão | 1.1 |
| Data | 15/09/2026 |
| Prompt | SEGSENSE_PRM_020_COR_001 |

`SEGSENSE_DAT_006` permanece a persistência V12 de DemonstrationStory. Este documento cobre **V17**.

## Migration

Arquivo: `database/migrations/V17__demo_url_capture.sql`. V1–V16 intactas.

## `demo_url_capture`

Uma linha por tentativa de captura. Sem UPDATE do conteúdo. Sem HTML bruto.

Colunas mínimas: `id`, `requested_url`, `final_url`, `final_host`, `captured_at`, `http_status`, `content_type`, `title`, `detected_language`, `excerpt`, `normalized_text`, `bytes_sha256`, `text_sha256`, `extractor_version`, `result_code`, `extracted_elements_json`, `correlation_id`, `created_at`.

`result_code` restrito aos valores de `SEGSENSE_URL_001`.

## `demo_url_capture_confirmation`

Append-only. FK `capture_id` **sem CASCADE**. Correções em `corrections_json`; elementos confirmados em `confirmed_elements_json`. Não apaga a captura original.

## Jornada

`demo_protection_journey.status` passa a aceitar `NO_COMPATIBLE_CAPABILITY`. Fingerprint da jornada (coluna já existente) inclui no canônico v4: `captureId`, `confirmationId`, `textSha256`.

## Integridade semântica

- Contribuição Spider 1.2 `URL_EXTRACTED` referencia `sourceId = SEGSENSE_URL_` + prefixo do `text_sha256` do **conteúdo principal**.
- `bytes_sha256` cobre o documento integral recebido; `text_sha256` cobre só o texto principal normalizado.
- `extracted_elements_json` inclui `selectionStrategy`, `extractorRuleSet=LOCAL_WINDOW_V1`, e por elemento: regra, offsets, `windowKind=PARAGRAPH`, trecho.
- Elementos estruturados só entram confirmados se tiverem evidência local no snapshot **ou** forem declaração da pessoa. Cultura/região/período distantes **não** são materializados.
- `scenarioKey` não armazena artigo, hash completo nem URL.

## Retenção

URLs podem conter identificadores. MVP: retenção documental de 7 dias; sem job de purge nesta fatia.
