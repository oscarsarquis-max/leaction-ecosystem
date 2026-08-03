# QMind — Gate de prontidão para homologação

- Status: **EM ANDAMENTO** (aberto 2026-08-03)
- Baseline recuperável: tag **`mvp-fullstack-v0`** (`82e637f`)
- Pré-requisitos concluídos:
  - Domínio API: `009_MVP_End_to_End_Gate.md` (**APROVADO**)
  - Frontend browser: `010_MVP_Web_End_to_End_Gate.md` (**APROVADO**)
  - OpenAPI + `@qmind/api-client` versionados
- Região alvo: **AWS `us-east-2`** (ADR-009)
- Forma alvo: ECS Fargate + ALB + RDS PostgreSQL + S3 privado + Cognito + Secrets Manager
- Incrementos: a partir deste ciclo, mudanças entram **versionadas sobre** `mvp-fullstack-v0` (não reescrever o marco)

## 1. Política de baseline

| Regra | Detalhe |
|---|---|
| Baseline | `git checkout mvp-fullstack-v0` restaura o MVP fullstack validado |
| Incrementos | commits/tags `homolog-*` / `qmind-homolog-v*` sobre `main` após o baseline |
| Não misturar | homologação não usa `AUTH_MODE=dev` nem `STORAGE_BACKEND=memory` |
| Identidades DB | migrações/seeds = **admin**; runtime API/worker = **`qmind_app`** (FORCE RLS) |
| Dados | homologação sem dados reais de cliente por padrão (ADR-009) |

## 2. Checklist — provisionamento AWS (`us-east-2`)

| # | Critério | Evidência esperada | Resultado |
|---|---|---|---|
| H1 | Conta/ambiente isolado de produção | Conta ou prefixo `qmind-homolog`; tags `Project=qmind` `Environment=homolog` | PENDENTE |
| H2 | Rede (VPC, subnets públicas/privadas, NAT) | Diagrama + IDs no Terraform/`DEPLOY.md` | PENDENTE |
| H3 | ECR + imagens API/web/worker | Repositórios + push imutável por tag git | PENDENTE |
| H4 | ECS Fargate + ALB (HTTPS/ACM) | Serviço estável, health `/health` `/ready` | PENDENTE |
| H5 | RDS PostgreSQL dedicado | Instância privada; SG só tasks; backup automático | PENDENTE |
| H6 | Bucket S3 privado (evidências) | Block Public Access; KMS opcional; chaves `org/.../evidence/...` | PENDENTE |
| H7 | Cognito User Pool + App Client | OIDC; MFA admin; callbacks do domínio homolog | PENDENTE |
| H8 | Secrets Manager | `DATABASE_URL_ADMIN`, `DATABASE_URL_APP`, Cognito, S3 — sem plain text em task def | PENDENTE |
| H9 | Logs (CloudWatch) | Log groups API/worker/ALB access; `correlation_id` | PENDENTE |
| H10 | Métricas e alarmes | 5xx ALB, CPU/mem ECS, conexões RDS, idade de jobs falhos | PENDENTE |

Scaffold inicial: `../../infra/` (Terraform + `DEPLOY.md`) — **ainda sem apply na conta**.

## 3. Checklist — migrações e seeds (identidade separada)

| # | Critério | Evidência esperada | Resultado |
|---|---|---|---|
| M1 | Migrações via role admin (Alembic) | `alembic upgrade head` com `DATABASE_URL_ADMIN` | PENDENTE |
| M2 | Seeds de catálogo (não cliente) | `seeds/001_*.sql` + `002_*.sql` aplicados como admin | PENDENTE |
| M3 | Runtime nunca usa admin URL | Task ECS só `DATABASE_URL_APP` → `qmind_app` | PENDENTE |
| M4 | Script documentado | `infra/scripts/migrate-and-seed-homolog.ps1` (recusa URL `qmind_app`) | PASS (scaffold; execução no RDS homolog ainda pendente) |

## 4. Checklist — validação de homologação

| # | Critério | Evidência esperada | Resultado |
|---|---|---|---|
| V1 | FORCE RLS | SQL: `relrowsecurity` + `relforcerowsecurity` nas tabelas tenant; cross-org 404 | PENDENTE |
| V2 | Backup e restauração | Snapshot RDS + restore exercise documentado (RPO/RTO provisórios) | PENDENTE |
| V3 | HTTPS, CORS, headers | ACM no ALB; CORS allowlist do front; HSTS/security headers | PENDENTE |
| V4 | Cognito real | Login browser homolog; refresh/logout; sem `AUTH_MODE=dev` | PENDENTE |
| V5 | S3 real + quarentena | authorize→PUT→receive→security_pass; objetos só no bucket privado | PENDENTE |
| V6 | Exportação PDF | Job `queued`→worker→`export_storage_key` ou falha observável | PENDENTE |
| V7 | Observabilidade | Alarme de smoke disparado e resolvido; log com `correlation_id` | PENDENTE |
| V8 | Rollback de implantação | Redeploy tag anterior `mvp-fullstack-v0` (imagem) com health OK | PENDENTE |

## 5. Checklist — preparação do piloto controlado

| # | Critério | Evidência esperada | Resultado |
|---|---|---|---|
| P1 | Organização piloto | Org criada em homolog; sem dados de produção | PENDENTE |
| P2 | Usuários e papéis | Mínimo: org_admin, quality_manager, consultant_auditor, process_owner, reader | PENDENTE |
| P3 | Escopo ISO 9001:2015 autorizado | Catálogo seed + escopo acordado no termo do piloto | PENDENTE |
| P4 | Termo de uso e privacidade | Documento aprovado (link/versão no gate) | PENDENTE |
| P5 | Roteiro de avaliação | Passo a passo Assessment→Report alinhado ao MVP | PENDENTE |
| P6 | Canal de suporte | Canal + SLA piloto (ex.: e-mail/Slack) | PENDENTE |
| P7 | Métricas | Produtividade, qualidade, aceitação — baseline e forma de coleta | PENDENTE |

### 5.1 Métricas mínimas do piloto (definição inicial)

| Área | Métrica | Como medir |
|---|---|---|
| Produtividade | Tempo médio draft→published (Report) | timestamps em `assessments` / `reports` + audit |
| Produtividade | Evidências aprovadas / Assessment | contagens por org |
| Qualidade | Taxa SoD bloqueada vs aprovada | audit `sod_violation` vs approve/publish |
| Qualidade | Rework de findings/reports | contagens reject/request_changes |
| Aceitação | Conclusão do roteiro sem bloqueio P0 | checklist do facilitador |
| Aceitação | NPS/CSAT piloto (opcional) | pesquisa pós-sessão |

## 6. Ordem de execução recomendada

```
1. Preencher infra/terraform/*.tfvars (homolog) + VPC/ACM/domínio
2. terraform apply (ECR, Cognito, S3, Secrets, RDS, ECS/ALB)
3. migrate-and-seed com DATABASE_URL_ADMIN
4. Deploy imagens tagadas (preferir tag git ≠ latest)
5. Validar V1–V8
6. Preparar P1–P7
7. Fechar este gate como APROVADO → tag homolog-ready-v0 (sugerida)
```

## 7. Ambiente / artefatos

| Item | Valor |
|---|---|
| Baseline tag | `mvp-fullstack-v0` |
| Scaffold infra | `qmind/infra/` |
| Deploy guide | `qmind/infra/DEPLOY.md` |
| Conta AWS apply | **ainda não executado** nesta abertura do gate |
| Domínio homolog | a definir (ex.: `homolog.qmind.…`) |

## 8. Veredito

**EM ANDAMENTO** — ciclo de homologação aberto formalmente.

Não há aprovação para piloto com dados reais até H1–H10, M1–M4, V1–V8 e P1–P7 estarem **PASS**.

## 9. Como atualizar este gate

1. Executar o item (provisionar / validar / documentar evidência).
2. Atualizar a coluna **Resultado** (`PASS` / `PASS*` / `FALHA` / `PENDENTE`).
3. Registrar commit/tag do incremento e data na §7.
4. Quando completo: mudar Status para **APROVADO** e criar tag anotada sugerida `homolog-ready-v0`.
