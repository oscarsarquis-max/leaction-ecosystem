# SEGSENSE_REV_011 — Revisão de aderência do PRM_011

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_REV_011 |
| Título | Revisão de aderência do PRM_011 |
| Categoria | REV |
| Versão | 1.0 |
| Status | Executado; etapa **não** autoaprovada |
| Data | 12/09/2026 |
| Dependências | SEGSENSE_PRM_011; SEGSENSE_SRC_001; SEGSENSE_UX_004; SEGSENSE_DOM_003; SEGSENSE_DAT_006; SEGSENSE_API_007; SEGSENSE_SEC_004; SEGSENSE_ADR_003; SEGSENSE_REQ_002 |

## 1. Sequência

O PRM_011 originalmente planejado para integração Spider foi **reprogramado** para a âncora visual comercial e o backoffice editorial. `SEGSENSE_ADR_003` e `SEGSENSE_REQ_002` foram preservados: a integração HTTP real com a Spider **não** foi realizada. PRM_012/013 (pesquisa verificável do portal e provider mock independente) só depois da aprovação formal desta etapa.

## 2. Ressalva visual herdada e desta etapa

| Superfície | Situação | Evidência substituta |
|---|---|---|
| `/c/{token}` (PRM_009/010) | **Não verificado visualmente.** Sem browser de sessão e sem IdP no runtime. Não foi criado login fictício, bypass no perfil `local`, token permanente, seed privilegiado ou mock de produção. | `PublicInvitePage.test.tsx`, `ContextInstanceIT`, HTTP real de convite/admin 401 |
| `/demonstracao/icatu` | **Não verificada em browser real** (1440×900, 768×1024, 390×844, 320×568, zoom 200%, teclado, contraste, scroll horizontal). Sem screenshots. | `IcatuDemonstrationPage.test.tsx` (base, 404, rede, 503, texto hostil inerte); HTTP `GET /api/v1/public/demonstrations/icatu-demonstracao` → 404 `DEMONSTRATION_NOT_PUBLISHED` + `Cache-Control: no-store` |
| Admin `/admin/demonstracoes` | Runtime sem IdP: **401**. Sem prova visual de formulário autenticado. | `DemonstrationsPage.test.tsx`; HTTP anônimo 401 |

Nenhum token bruto ou credencial foi gravado em screenshot, console persistente ou documento.

## 3. SAT-01 a SAT-10

| SAT | Situação | Evidência |
|---|---|---|
| SAT-01 | PARCIAL | Identidade local `SEGSENSE`; sem registro na Spider |
| SAT-02 | PARCIAL | Manifesto preliminar inalterado (`DRAFT / NOT_CERTIFIED`) |
| SAT-03 | **NÃO IMPLEMENTADO** | `SEGSENSE_ADR_003`; nenhum mapper, client HTTP ou tabela de integração |
| SAT-04 | PARCIAL | Browser → React → BFF; credencial anônima ≠ autenticação de pessoa/satélite |
| SAT-05 | PARCIAL | Correlação HTTP local; sem IDs da Spider |
| SAT-06 | NÃO APLICÁVEL NESTA ETAPA | Sem submissão de objetivo |
| SAT-07 | NÃO APLICÁVEL NESTA ETAPA | Sem execução |
| SAT-08 | PARCIAL | Deny-by-default; autoridades `segsense.demonstration.*`; sem IdP |
| SAT-09 | ATENDIDO | Frontend só chama o BFF SegSense; `/demonstracao/icatu` não consulta Spider/Icatu/mock |
| SAT-10 | ATENDIDO | ArchUnit proíbe `SatelliteContract`, `SpiderClient`, `IcatuClient`, `IcatuProduct`, `IcatuAdapter` |

O satélite **não** é certificável.

## 4. Validação desta execução

- Backend `.\mvnw.cmd verify`: exit 0. Failsafe **27** completed, **0** errors/failures (inclui `DemonstrationStoryIT` 2 testes). Testcontainers aplicou V1–V12.
- Frontend: `npm ci` (0 vulns); lint 0 erros após correção ESLint; **55** testes; build OK; `npm audit` **0**.
- Volume `segsense_pgdata` preservado. Flyway no runtime `local`: v11 → **v12** (`create demonstration story`).
- HTTP real: público editorial ausente 404; admin 401; CORS origem `evil.example` 403; `system/info` 200; health UP.
- Logo SHA-256 inalterado: `CEF4A9C0B8F7B0D8F2A50D85DE41FEA02498B15E3021EBB063E75945810C089D`.
- Sem commit, push ou deploy.

## 5. Limites

Sem alteração da Spider, Panne ou `.cursor/`. Sem mock Icatu, produto, cotação, apólice, login fictício ou PII. Conformidade jurídica **não** concluída. Aceite visual humano pendente. Esta etapa **não** está marcada como aprovada.
