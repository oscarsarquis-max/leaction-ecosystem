# QMind — Confronto dos ADRs com o monorepo

- Status: Aprovado (base para aceitar ADR-001…009)
- Data: 2026-08-03
- Escopo: inventário factual do monorepo `C:\Projetos` versus ADRs em `05_ADR/`

## Método

1. Inventariar padrões reais (backend, frontend, Postgres, auth, S3, IA, deploy, filas, testes).
2. Classificar cada tema como **compatível**, **tensão** ou **lacuna**.
3. Fechar decisões de aceitação nos ADRs sem assumir reutilização automática.

Regra mantida: existência em outro produto não autoriza compartilhamento; reutilização exige compatibilidade, isolamento e responsabilidade operacional.

## Inventário resumido

| Tema | O que existe no monorepo | Referências |
|---|---|---|
| Backend | Flask (inove4us ~5010); Express gateway + Flask marketplace (Hub); FastAPI (phanton) | `inove4us/backend`, `leaction-platform/services/gateway-api`, `phanton/backend` |
| Frontend | Vite+React+Tailwind (inove/phanton); Next+React+Tailwind (Hub) | apps respectivos |
| Postgres | Container `leaction_db` (PG 18); DB por app; host local **5434→5432** (docs antigos citam 5433) | `leaction-platform/docker-compose.yml`, `infra/ecosystem-databases.sql` |
| Auth | inove: e-mail + código SES + sessão Flask; Hub: senha+JWT; **sem OIDC/Cognito** | `inove4us/backend/app.py`, Hub `hub-auth.js` |
| Tenant legado | Predomina `id_clie` (inteiro), não `organization_id` | apps satélite |
| Objetos | S3 CMS no Hub (`us-east-2`); sem custódia de evidências de auditoria | `cms-s3-storage.js` |
| IA | Bedrock (inove, região tipicamente `us-east-1`); phanton com abstração de provedor | `wizard_routes.py`, `phanton/services/llm` |
| Async | Outbox+worker in-process (Hub); threads SES (inove); **sem Redis/SQS padrão** | `outbox-worker.js` |
| Deploy | inove: Terraform ECS/ALB/RDS `us-east-2`; Hub: PM2/EC2-style | `inove4us/infra/terraform` |
| CI/contratos | Poucos testes; sem OpenAPI/contract CI monorepo | — |

`qmind` ainda **não** está em `infra/ecosystem-databases.sql`.

## Matriz ADR × monorepo

| ADR | Resultado | Ajuste ao aceitar |
|---|---|---|
| 001 Modular | Compatível | Manter monólito modular; não copiar multi-processo do Hub |
| 002 Multiempresa | Tensão de nomenclatura | QMind usa `organization_id` (UUID); **não** reutilizar `id_clie` |
| 003 API | Compatível em estilo REST; lacuna de contrato | Python **FastAPI** + OpenAPI `/api/v1`; jobs via outbox/worker PG no MVP |
| 004 UX | Compatível web | Vite + React + TS + Tailwind; design system próprio (não importar Hub/inove) |
| 005 Banco | Compatível Postgres | Base lógica `qmind` no `leaction_db`; migrações SQL versionadas; RLS como defesa adicional |
| 006 Auth | Tensão forte | **Não** reutilizar senhas do Hub; alvo OIDC (**AWS Cognito** em `us-east-2`); dev pode usar código por e-mail só como transição documentada |
| 007 Evidências | Compatível direção S3 | Bucket **dedicado** QMind (privado); metadados no PG; não usar bucket CMS |
| 008 IA | Tensão de governança | Camada própria obrigatória; Bedrock elegível; nunca chamar provedor do domínio |
| 009 Ops | Compatível AWS | Preferir padrão inove (ECS/RDS/S3/SES) em `us-east-2`; Bedrock pode permanecer `us-east-1` |

## Tensões não resolvidas por este documento

- Harmonizar documentação de porta local 5433 vs 5434 no ecossistema (fora do QMind; QMind documentará 5434 enquanto o compose vigente for esse).
- RPO/RTO numéricos do piloto (definir antes de dados reais — ADR-009).
- Matriz completa papel×ação×recurso (produto — ADR-006).
- Conjunto de avaliação de IA (ADR-008) antes de integração produtiva.

## Decisão de aceite

Em 2026-08-03 os ADRs 001–009 passam a **Aceito**, incorporando as decisões da coluna “Ajuste ao aceitar”. Alterações futuras incompatíveis exigem novo ADR ou revisão explícita do ADR afetado.
