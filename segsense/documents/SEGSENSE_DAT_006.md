# SEGSENSE_DAT_006 — Persistência V12 de DemonstrationStory

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_DAT_006 |
| Versão | 1.0 |
| Data | 12/09/2026 |

Arquivo: `database/migrations/V12__create_demonstration_story.sql`. V1–V11 intactas.

Tabelas: `demonstration_source`, `demonstration_story`, `demonstration_revision`, `demonstration_block`, `demonstration_claim`, `demonstration_decision`.

Invariantes: revisão congelada imutável; INSERT de bloco/alegação em revisão frozen rejeitado; decisão append-only; `LIVE` exige decisão `APPROVED` da revisão publicada; fonte de alegação verificada.

Sem tabelas de produto, cotação, apólice ou integração.
