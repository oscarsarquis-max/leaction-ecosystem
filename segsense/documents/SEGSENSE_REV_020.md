# SEGSENSE_REV_020 — Revisão de aderência do PRM_020

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_REV_020 |
| Versão | 1.1 |
| Data | 15/09/2026 |
| Situação | Corretivo único `SEGSENSE_PRM_020_COR_001` executado nesta etapa; **não autoaprovado** |

## Decisão pedida ao auditor

Não autoaprovar. Não iniciar `SEGSENSE_PRM_021`. Este já é o único corretivo permitido do PRM_020. Não emitir segundo corretivo.

## Comparação factual (auditoria visual do PRM_020 vs COR_001)

| | Antes (PRM_020 / `URL_EXTRACTOR_V1`) | Depois (COR_001 / `URL_EXTRACTOR_V2` + `LOCAL_WINDOW_V1`) |
|---|---|---|
| Tema / evento | `quebra de safra`, trecho com a expressão | Mantido quando o parágrafo local contém a expressão |
| Cultura | `milho` por ocorrência no índice/listagem | Omitido sem relação local com o evento |
| Região | `Rio Grande do Sul` por história institucional em Pelotas | Omitido sem relação local com o evento |
| Texto da fonte | Começava com navegação, menu, login e sumário | Conteúdo principal (`main` / equivalentes); chrome excluído |
| Payload Spider | Podia levar `crop`/`region` globais | Só elementos confirmados e sustentados no snapshot |
| Mock | Caminhos gerais sem R$ | Igual; perguntas explícitas de cultura, região, período e situação |

## Execução observada do corretivo (15/09/2026)

Stack isolada `:15178/:19088/:19080/:19095` + Postgres `:15437` (volume `segsense_pgdata_isolated_cor016`). Reunião `:5178/:8095` intacta.

URL pública `https://pt.wikipedia.org/wiki/Agricultura_no_Brasil` (13:10 UTC) → `FETCHED` (`URL_EXTRACTOR_V2`, `MAIN_ELEMENT`, HTTP 200). Trecho começa pelo artigo, não por menu/login. Elementos: tema/evento/situação/restrição de quebra de safra. **Sem** `crop=milho` e **sem** `region=Rio Grande do Sul`. Confirmação `65aabef9-…`. Jornada `001693a9-…` `PRE_PROPOSAL_AVAILABLE`, Satellite **1.2**, capability `DISCOVER_SYNTHETIC_CROP_PROTECTION_PATHS`, mock `crp-9872472d-…` **sem R$**, perguntas explícitas de cultura/região/período/situação. Payload `URL_EXTRACTED` só com tema/evento/situação/constraint. Mesma URL + residencial → `AMBIGUOUS`. Cotação governada permanece `R$ 540,00` (`qte-786484d1-…`).

Evidências: `documents/evidencias/SEGSENSE_PRM_020_COR_001/` (`http-proof.json`, `browser-proof.json`, `corpus-matrix.md`, PNGs). A fixture de teste **não** é o artigo integral nem prova da URL ao vivo (hashes distintos: bytes ao vivo `22e67d502e2f…` / texto principal `ff039b4f7a3e…`).

## Identificadores

| Pedido no prompt | Decisão |
|---|---|
| `SEGSENSE_DAT_006` para snapshots | **Não sobrescrito.** Snapshots = `SEGSENSE_DAT_007`. |
| `SEGSENSE_SEC_004` para SSRF | **Não sobrescrito.** Ingestão de URL = `SEGSENSE_SEC_005`. |
| Nova migration | **Não.** V17 permanece; metadados de extração cabem em `extracted_elements_json`. |

## O que permanece demonstrativo

Caminhos agrícolas sem produto, prêmio, seguradora ou Icatu. Cotação residencial `NON_BINDING_DEMO`. Extração determinística por janela local; não afirma que a pessoa sofreu a perda.
