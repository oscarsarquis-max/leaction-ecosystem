# QMind

Workspace documental do QMind, plataforma inteligente de apoio à consultoria, auditoria e gestão de sistemas de gestão.

## Como usar este workspace

1. Leia `00_Architecture/000_Project_Vision.md`.
2. Consulte `00_Architecture/001_System_Architecture.md` para a visão técnica inicial.
3. Use `00_Architecture/002_Folder_Structure.md` como referência de organização.
4. Registre decisões relevantes em `05_ADR`.
5. Planeje as entregas por meio de `04_Docs/004_Initial_Backlog.md` e `roadmap.md`.

## Estrutura

- `00_Architecture`: visão, arquitetura e padrões do projeto.
- `01_Prompts`: prompts versionados por sprint e finalidade.
- `02_Models`: modelos de domínio, avaliação e IA.
- `03_Database`: desenho de dados, dicionários e migrações futuras.
- `04_Docs`: documentação funcional, backlog e guias.
- `05_ADR`: registros de decisões arquiteturais.
- `99_Reference`: normas, glossário e materiais de referência permitidos.

## Estado atual

- ADRs **001–012** Aceitos (012 = Foundation v1.0 + linha OI).
- **Foundation Baseline v1.0:** [`00_Architecture/004_Foundation_Baseline_v1.md`](00_Architecture/004_Foundation_Baseline_v1.md) — marco ARCH-001.
- **Mapa Foundation ↔ OI:** [`00_Architecture/005_Foundation_OI_Layer_Map.md`](00_Architecture/005_Foundation_OI_Layer_Map.md).
- **Roadmap OI (Alpha):** [`04_Docs/014_OI_Architectural_Roadmap.md`](04_Docs/014_OI_Architectural_Roadmap.md).
- **Evolução incremental:** [`04_Docs/015_Foundation_OI_Evolution_Strategy.md`](04_Docs/015_Foundation_OI_Evolution_Strategy.md).
- **Core → OI HTTP V1:** [`04_Docs/016_Core_OI_HTTP_Integration_V1.md`](04_Docs/016_Core_OI_HTTP_Integration_V1.md).
- **Persistência de insights OI V1:** [`04_Docs/017_Core_OI_Intelligence_Persistence_V1.md`](04_Docs/017_Core_OI_Intelligence_Persistence_V1.md).
- **Compatibilidade de contrato Core ↔ OI V1:** [`04_Docs/018_Core_OI_Contract_Compatibility_V1.md`](04_Docs/018_Core_OI_Contract_Compatibility_V1.md).
- **Baseline Context ↔ OI V1:** [`04_Docs/021_Context_OI_V1_Baseline.md`](04_Docs/021_Context_OI_V1_Baseline.md) — marco operacional Profile → Insights → Completar → Reanalisar (OI-019).
- **ISO Intelligence V1 — inspeção Caso de Melhoria:** [`04_Docs/022_ISO_Intelligence_V1_Improvement_Case_Inspection.md`](04_Docs/022_ISO_Intelligence_V1_Improvement_Case_Inspection.md) — ISOI-001 (modelagem; sem implementação).
- Domínio documental **Aceito** e congelado: **`domain-docs-v0`** — `04_Docs/006_Domain_Acceptance_Checklist.md`.
- Emenda implementação: `04_Docs/007_Domain_Docs_Amendment_001.md` (Alembic, porta 5433).
- **DDL v0 + Alembic:** `03_Database/003_DDL_v0.md` → `qmind/backend/` (database `qmind` no cluster `leaction_db`).
- **Gate Fase 0:** `04_Docs/008_Phase0_Technical_Gate.md` — veredito **APROVADO**.
- **Gate MVP E2E:** `04_Docs/009_MVP_End_to_End_Gate.md` — veredito **APROVADO** (domínio completo + isolamento 2 orgs).
- **Gate Web E2E:** `04_Docs/010_MVP_Web_End_to_End_Gate.md` — veredito **APROVADO** (Playwright + build produção).
- **Baseline fullstack:** tag **`mvp-fullstack-v0`** — marco recuperável; incrementos versionados a partir daqui.
- **Modelo de negócio:** `04_Docs/012_Business_Model_and_Product_Focus.md` — consultancy-led B2B2B (**Aceito**).
- **Descoberta / piloto:** `04_Docs/013_Discovery_and_Pilot_Plan.md` — **Em andamento** (sem código de workspace de consultoria até evidência).
- **Gate Homologação:** `04_Docs/011_Homologation_Readiness_Gate.md` — **EM ANDAMENTO** (Lightsail, ADR-010; domínio `qmind.com.br`).
- **Infra homolog:** `../infra/terraform-lightsail/` + `DEPLOY.md`; futuro `terraform-enterprise/`.
- **Tag backend:** `mvp-backend-v0`
- **OpenAPI:** `../backend/openapi/openapi.json` — contrato versionado; freeze `openapi-v1-initial`
- **Cliente TS:** `../packages/api-client` (`@qmind/api-client`) — gerado do OpenAPI; `npm run generate:api-client`
- **API foundation:** FastAPI em `qmind/backend/app/` — health, Cognito/dev auth, Organization/Membership; módulos Evidence→Report; Organization Profile (ICP-01).

