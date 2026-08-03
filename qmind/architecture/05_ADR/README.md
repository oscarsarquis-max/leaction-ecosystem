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
| Deploy | AWS `us-east-2`, padrão ECS/RDS |

## Próxima etapa

Modelo de domínio conceitual (ainda sem código de aplicação), em `02_Models/`, refletindo o fluxo ISO 9001:2015 e os ADRs aceitos.

Nenhuma tecnologia será assumida como compartilhada apenas por existir em outro produto do ecossistema. A reutilização deverá demonstrar compatibilidade, isolamento e responsabilidade operacional.
