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

- ADRs 001–009 Aceitos — `04_Docs/005_Monorepo_Confrontation.md`.
- Domínio documental **Aceito** e congelado: **`domain-docs-v0`** — `04_Docs/006_Domain_Acceptance_Checklist.md`.
- Emenda implementação: `04_Docs/007_Domain_Docs_Amendment_001.md` (Alembic, porta 5433).
- **DDL v0 + Alembic:** `03_Database/003_DDL_v0.md` → `qmind/backend/` (database `qmind` no cluster `leaction_db`).
- **Gate Fase 0:** `04_Docs/008_Phase0_Technical_Gate.md` — veredito **APROVADO**.
- **Gate MVP E2E:** `04_Docs/009_MVP_End_to_End_Gate.md` — veredito **APROVADO** (domínio completo + isolamento 2 orgs).
- **Tag backend:** `mvp-backend-v0`
- **OpenAPI:** `../backend/openapi/openapi.json` — contrato versionado; freeze `openapi-v1-initial`
- **Cliente TS:** `../packages/api-client` (`@qmind/api-client`) — gerado do OpenAPI; `npm run generate:api-client`
- **API foundation:** FastAPI em `qmind/backend/app/` — health, Cognito/dev auth, Organization/Membership; módulos Evidence→Report.

