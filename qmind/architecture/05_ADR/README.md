# Registros de Decisão Arquitetural

Um ADR registra uma decisão relevante, seu contexto e suas consequências. Use o arquivo `ADR-000-template.md` como ponto de partida.

Estados sugeridos: Proposto, Aceito, Substituído ou Rejeitado. ADRs aceitos não devem ser apagados; uma nova decisão deve apontar para a anterior.

## Índice

| ADR | Decisão | Estado |
|---|---|---|
| ADR-001 | Arquitetura modular da aplicação | Aceito |
| ADR-002 | Isolamento multiempresa | Aceito |
| ADR-003 | Backend e contrato de API | Aceito |
| ADR-004 | Experiência web e móvel | Aceito |
| ADR-005 | Banco de dados transacional | Aceito |
| ADR-006 | Autenticação e autorização | Aceito |
| ADR-007 | Armazenamento e proteção de evidências | Aceito |
| ADR-008 | Camada e governança de inteligência artificial | Aceito |
| ADR-009 | Hospedagem, observabilidade e continuidade | Aceito |
| ADR-010 | Homologação econômica (Lightsail) — emenda à 009 | Aceito |
| ADR-011 | Entrada consultancy-led B2B2B (dados da organização) | Aceito |

## Aceite

Aceitos em **2026-08-03** após confronto com o monorepo:

- Relatório: [`../04_Docs/005_Monorepo_Confrontation.md`](../04_Docs/005_Monorepo_Confrontation.md)

### Stack fechada no aceite (resumo)

| Camada | Decisão |
|---|---|
| Backend | Python FastAPI, `/api/v1`, OpenAPI |
| Frontend | Vite + React + TypeScript + Tailwind |
| Banco | PostgreSQL, base `qmind` no `leaction_db` |
| Auth | OIDC Cognito (alvo); sem senhas do Hub |
| Evidências | S3 bucket dedicado, `us-east-2` |
| IA | Camada própria; Bedrock elegível |
| Deploy | AWS `us-east-2`; homolog/piloto = EC2 mínima (ADR-010); futuro = ECS/RDS (ADR-009) |

## Estratégia de produto (2026-08-04)

- **ADR-011** + [`../04_Docs/012_Business_Model_and_Product_Focus.md`](../04_Docs/012_Business_Model_and_Product_Focus.md): entrada por consultorias; organização proprietária dos dados.
- Descoberta/piloto: [`../04_Docs/013_Discovery_and_Pilot_Plan.md`](../04_Docs/013_Discovery_and_Pilot_Plan.md) — **sem** implementação de `ConsultancyWorkspace` até evidência (H3+).
- Homologação técnica: ADR-010 **Lightsail** / gate `011` (`terraform-lightsail/`).

## Próxima etapa

1. Executar descoberta e piloto (013) em paralelo à homologação econômica (011 / ADR-010).
2. Emenda versionada de domínio (`02_Models` / DDL) **somente** após critérios do ADR-011.

Nenhuma tecnologia será assumida como compartilhada apenas por existir em outro produto do ecossistema. A reutilização deverá demonstrar compatibilidade, isolamento e responsabilidade operacional.
