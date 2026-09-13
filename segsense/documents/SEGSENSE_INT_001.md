# SEGSENSE_INT_001 — Matriz de evidência do contrato SegSense–Spider

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_INT_001 |
| Título | Evidência do Satellite Contract externo versus artefatos internos da Spider |
| Categoria | INT — integração |
| Versão | 1.0 |
| Status | Ramo B: contrato externo ausente |
| Data | 12/09/2026 |
| Dependências | SEGSENSE_PRM_010; leitura de `spider/docs/architecture/SPIDER-ARCH-017-satellite-architecture.md` |

## 1. Quatro camadas (não equivalentes)

| Camada | Artefato inspecionado | Status |
|---|---|---|
| Ideal arquitetural de satélite | `spider/docs/architecture/SPIDER-ARCH-017-satellite-architecture.md` (último commit Spider 2026-09-09 `4ba112d`): “Ideal **não implementado**”; Contextual Link ≠ Satellite Contract; SpiderBank DEMO-002 sem Satellite Contract | `PROPOSED` |
| Baseline SegSense (cópia distinta) | `segsense/documents/references/SPIDER-ARCH-017.md` — **Status: PROPOSED / ARCHITECTURAL BASELINE**, texto mais extenso | `PROPOSED` (não é aceite da Spider) |
| Intent Contract interno | `spider/backend/src/main/resources/context/intent-contract-v1.schema.json` (`$id` `spider://context/intent-contract/1.0`); teste interno `IntentContractSchemaTest` | `INTERNAL_ONLY` |
| Data Plane canônico | `spider/backend/src/main/resources/contracts/canonical/1.0/canonical-execution-request.schema.json`, `canonical-execution-result.schema.json`, `canonical-error.schema.json` | `INTERNAL_ONLY` |
| Contrato externo Satellite → Spider | Nenhum schema público versionado, endpoint, autenticação de satélite, exemplo oficial ou teste de contrato publicado para consumo externo | `ABSENT` |

Não há `@RequestMapping` de satélite nem tipo `SatelliteContract` nos controllers Java da Spider inspecionados.

## 2. Matriz

| Requisito | Evidência exata | Status | Implicação para o SegSense | Bloqueio | Responsável pela definição |
|---|---|---|---|---|---|
| Identidade de aplicação e registro de satélite | SegSense: `applicationId=SEGSENSE` local (`SEGSENSE_ARQ_002`, manifesto preliminar). Spider ARCH-017 atual exige “autenticação e autorização do canal” no ideal, sem registro executável. | `ABSENT` (externo) | Identidade local não equivale a registro na Spider | PRM_011 | Spider |
| Autenticação do satélite e do usuário/ator | SegSense: deny-by-default, sem IdP (`SEGSENSE_ADR_002`). Nenhum issuer/JWKS de satélite na Spider. | `ABSENT` | Não inventar token de satélite nem usuário | PRM_011 / PRM_003 residual | Spider + IdP do ecossistema |
| Autorização / catálogo de solicitações permitidas | ARCH-017 ideal: “publicação governada de capacidades”. Sem catálogo externo publicado. | `ABSENT` | SegSense não escolhe capability | PRM_011 | Spider |
| Schema de entrada versionado e semântica do objetivo | Intent Contract V1 interno (`intent-contract-v1.schema.json`). Não é contrato Satellite. | `INTERNAL_ONLY` | Não copiar o schema interno para o BFF | PRM_011 | Spider |
| Contexto, origem/canal, constraints e referências | Intent: `constraints`, `provenance`. Canonical execution: `origin.channel`, `contextRef.*`. Internos. | `INTERNAL_ONLY` | Não mapear ContextInstance para esses IDs | PRM_011 | Spider |
| Correlação local vs `requestId` / `decisionId` / `planId` / `executionId` / `interactionId` | SegSense: `X-Correlation-ID` local. Spider: `canonical-execution-request` exige `executionId`, `correlationId`, `traceparent`. Sem contrato que ligue os dois. | `ABSENT` (ligação) | Não fabricar IDs da Spider | PRM_011 | Spider |
| Preview de compreensão, sem execução | ARCH-017 / ARCH-015 descrevem compreensão no Context Intelligence. Sem endpoint público de preview para satélite. | `ABSENT` | Sem CTA de preview | PRM_011 | Spider |
| Confirmação explícita e ligação ao preview | Inexistente como API externa. Confirmação local do SegSense é autorização de uso **no SegSense**, não confirmação de plano Spider. | `ABSENT` | UI termina no SegSense | PRM_011 | Spider |
| Submissão, idempotência e proteção contra replay | Idempotência local da **instância** (`Idempotency-Key`). Canonical execution tem `idempotencyKey` interno. Sem submissão satélite. | `ABSENT` (submissão) | Não reutilizar a chave da instância como chave Spider | PRM_011 | Spider |
| Estados assíncronos, consulta e/ou callback | Sem URL de callback, webhook ou status de execução para satélite. | `ABSENT` | Sem tela de espera/resultado Spider | PRM_011 / PRM_014 | Spider |
| Erros canônicos, indisponibilidade e timeouts | `canonical-error.schema.json` interno (`errorId`, `retryable`). Sem binding externo. | `INTERNAL_ONLY` | SegSense continua com erros humanos locais | PRM_011 | Spider |
| Transporte seguro, TLS, trust e segredos | SegSense: HTTPS fail-closed fora de `local`/`test` (`PRM_007_COR_001`). Sem mTLS/client secret de satélite. | `ABSENT` | Não criar client secreto | PRM_011 | Spider |
| Retenção e minimização dos valores consentidos | Local: `FUN_002`, `DAT_005`, somente `NON_PERSONAL`, evidência sem valores pessoais. Sem política de retenção cruzada Spider. | `PROPOSED` (política cruzada) | Não exportar valores coletados | PRM_011 | Spider + SegSense |
| Versão / compatibilidade / evolução | Sem versão de contrato Satellite publicada (`v1` de Intent/canonical não conta). | `ABSENT` | Sem mapper versionado | PRM_011 | Spider |
| Testes contratuais publicados pela Spider | `IntentContractSchemaTest` e testes internos do Data Plane. Nenhum pact/contrato publicado para satélites. | `INTERNAL_ONLY` | Sem fixture oficial para mapper | PRM_011 | Spider |

## 3. Decisão

**Ramo B.** Não existe artefato `PUBLIC_EXECUTABLE` do Satellite Contract. Contextual Link e SpiderBank não o substituem. O SegSense não implementa DTO, mapper, client, endpoint, tabela nem botão de continuidade à Spider nesta etapa.

## Addendum SPIDER-SAT-003 (13/09/2026)

A matriz acima é o snapshot de 12/09/2026. Em 13/09 a Spider publicou `PUBLIC_EXECUTABLE` (DEMO ONLY): `SPIDER-SATELLITE-CONTRACT-V1`, JSON Schema em `spider/backend/src/main/resources/contracts/satellite/1.0/`, `POST /v1/satellites/interactions`, registry `spider.satellite`, testes `SatelliteContractV1Test`. Intent Contract e Data Plane continuam `INTERNAL_ONLY`. `/go` continua outra estratégia de aquisição. O mock não foi certificado como Provider Satellite.
