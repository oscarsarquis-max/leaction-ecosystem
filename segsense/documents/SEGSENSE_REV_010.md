# SEGSENSE_REV_010 — Revisão de aderência do PRM_010

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_REV_010 |
| Título | Revisão de aderência do PRM_010 |
| Categoria | REV |
| Versão | 1.0 |
| Status | Executado; ramo B; etapa não autoaprovada |
| Data | 12/09/2026 |
| Dependências | SEGSENSE_PRM_010; SEGSENSE_INT_001; SEGSENSE_ARQ_003; SEGSENSE_ADR_003; SEGSENSE_REQ_002 |

## 1. Etapa anterior

PRM_009 foi **aprovado com ressalvas** após `SEGSENSE_PRM_009_COR_001`. Três ressalvas herdadas:

| Ressalva | Tratamento | Evidência |
|---|---|---|
| INSERT SQL em snapshot aprovado | V11 incremental (`database/migrations/V11__freeze_approved_notice_field_set.sql`). INSERT de campo só na transação do snapshot DRAFT (`age(xmin)=0`); INSERT de snapshot e mutação de identidade bloqueados quando APPROVED/RETIRED. V1–V10 intactas. Pré-validação fail-fast se houver classificação distinta de `NON_PERSONAL`. | `ContextInstanceIT.createsNoticeInstanceAndProtectsEvidence` (INSERT snapshot 99 após APPROVED rejeitado); `ContextInstanceIT.freezesCommittedDraftFieldsAndAllowsNewDraftSnapshot` (INSERT em DRAFT commitado rejeitado; POST `/draft` cria versão 2; INSERT em APPROVED rejeitado; UPDATE/DELETE append-only). Testcontainers aplicou V1–V11. |
| Auditoria visual | Sem ferramenta de browser nesta sessão; **não** foi criado login fictício, bypass, seeded credential ou mock de produção. Prova isolada: BFF real no profile `test` + `@WithMockUser` **somente no classpath de teste** (`ContextInstanceIT`) e testes de componente (`PublicInvitePage.test.tsx`, higiene de fonte). Desmontagem: o contexto Spring de teste termina com o Testcontainers; o profile `local` não foi alterado. Nenhum token ou credencial gravado em arquivo permanente. | **Não verificado visualmente.** Aceite visual humano pendente (públicos 1440×900, 390×844, 320×568; admin 1440×900 e 768×1024; zoom 200%; teclado). |
| npm audit high | Cadeia `react-router-dom@7.9.1` → `react-router@7.9.1` (advisories XSS / open redirect / RCE / DoS, predominantemente SSR/RSC). O app usa só `BrowserRouter`. Pin compatível no mesmo major: `react-router-dom` **7.18.3**. Sem `npm audit fix --force`. | `npm audit` após o pin: **0 vulnerabilities**. `npm ci` + lint + testes + build no frontend. |

## 2. SAT-01 a SAT-10

| SAT | Situação | Evidência |
|---|---|---|
| SAT-01 | PARCIAL | Identidade local `SEGSENSE`; sem registro na Spider |
| SAT-02 | PARCIAL | Manifesto preliminar inalterado (`DRAFT / NOT_CERTIFIED`) |
| SAT-03 | **NÃO IMPLEMENTADO** | Documentação conceitual **não** atende SAT-03; `SEGSENSE_ADR_003` |
| SAT-04 | PARCIAL | Browser → React → BFF; credencial anônima ≠ autenticação de pessoa/satélite |
| SAT-05 | PARCIAL | Correlação HTTP local; sem IDs da Spider |
| SAT-06 | NÃO APLICÁVEL NESTA ETAPA | Sem submissão de objetivo |
| SAT-07 | NÃO APLICÁVEL NESTA ETAPA | Sem execução |
| SAT-08 | PARCIAL | Deny-by-default; sem IdP, Guard ou Policy |
| SAT-09 | ATENDIDO | Frontend só chama o BFF SegSense |
| SAT-10 | ATENDIDO | Nenhum client Spider/Icatu; ArchUnit `no_invented_satellite_contract_types` + higiene FE |

O satélite **não** é certificável.

## 3. Ramo

**B.** Ver `SEGSENSE_INT_001`. Nenhum artefato `PUBLIC_EXECUTABLE`. Nenhum DTO `SatelliteContract`, mapper, client HTTP, endpoint, tabela ou CTA de continuidade.

## 4. Validação desta execução

- Backend `.\mvnw.cmd verify`: exit 0. Failsafe **25** completed, **0** errors/failures. `ContextInstanceIT` 3 testes. Flyway Testcontainers: “Successfully applied 11 migrations … now at version v11”.
- ArchUnit: 7 regras, inclusive proibição de tipos `SatelliteContract|SatelliteContractMapper|SpiderClient|IcatuClient`.
- Frontend: pin `react-router-dom` 7.18.3; `npm audit` 0; lint/test/build registrados na devolutiva.
- Sem `SEGSENSE_API_007`. Sem migration de integração. Superfície pública inalterada.

## 5. Limites

Sem commit, push, deploy, alteração da Spider/Panne/`.cursor/`, V1–V10 reescritas, mock Icatu, login fictício, export de credencial/token. Conformidade jurídica **não** concluída. Recarregar a página continua sem retomada. Sem IdP. SAT-03 não foi marcado atendido.
