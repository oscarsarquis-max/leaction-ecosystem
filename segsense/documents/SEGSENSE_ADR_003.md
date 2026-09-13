# SEGSENSE_ADR_003 — Bloqueio de implementação executável do Satellite Contract

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_ADR_003 |
| Título | Não implementar contrato Satellite até publicação externa da Spider |
| Categoria | ADR — decisão arquitetural |
| Versão | 1.0 |
| Status | Aceita |
| Data | 12/09/2026 |
| Dependências | SEGSENSE_INT_001; SEGSENSE_ARQ_003; SPIDER-ARCH-017 (leitura) |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 12/09/2026 | Ramo B do PRM_010. |

## Contexto

O PRM_010 exigiu um gate binário: implementar mapper somente se existisse contrato **público, versionado e executável**. A inspeção (INT_001) mostrou:

- ARCH-017 na Spider: ideal não implementado;
- Intent Contract e schemas canônicos: internos ao Data Plane;
- ausência de endpoint, autenticação, exemplos e testes de contrato para satélite.

Copiar um schema interno ou o Contextual Link criaria uma interface fictícia.

## Decisão

Enquanto a Spider não publicar um Satellite Contract externo verificável, o SegSense **não** implementa:

- DTO ou tipo denominado Satellite Contract;
- mapper ContextInstance → payload Spider;
- client HTTP, credencial, callback, fila ou outbox;
- endpoint de “continuidade”, preview ou confirmação de plano;
- migration/tabela de integração.

A jornada pública permanece local. Qualquer HTTP real para a Spider permanece bloqueado **no sentido do Satellite Contract**. **Nota de sequência (12/09/2026):** o identificador `PRM_011` foi reutilizado para a âncora visual e o backoffice editorial; esta ADR **não** foi revertida. **Addendum 13/09/2026:** `SEGSENSE_ADR_004` autoriza uma fatia **demo local** (`/v1/demo/segsense/**`) que **não** revoga esta ADR nem satisfaz `SEGSENSE_REQ_002`.

## Alternativas rejeitadas

1. **Usar Intent Contract V1 como se fosse o contrato do satélite.** É `INTERNAL_ONLY`.
2. **Usar CanonicalExecutionRequest.** É contrato de execução interno, não de canal.
3. **Tratar Contextual Link / SpiderBank como prova de contrato.** ARCH-017 vigente os distingue.
4. **Inventar versão 1.0 “provisória”.** Violaria MOCK_ONLY e o PRM_010.

## Consequências

- SAT-03 permanece **não implementado**.
- A documentação PROPOSED em `documents/references/SPIDER-ARCH-017.md` continua baseline, não aceite.
- Desbloqueio: lista em `SEGSENSE_REQ_002`.

## Addendum SPIDER-SAT-003 (13/09/2026)

A Spider publicou o Satellite Contract V1 (`SPIDER-SAT-003`, DEMO ONLY). Esta ADR **não** é revogada: o SegSense continua proibido de **inventar** DTO `SatelliteContract*`, mapper de ContextInstance para Data Plane, ou endpoint próprio. O BFF **pode** consumir o contrato publicado (`POST /v1/satellites/interactions`) como EXPERIENCE SATELLITE. Preview, IdP, callback e Data Plane em `SEGSENSE_REQ_002` permanecem abertos.
