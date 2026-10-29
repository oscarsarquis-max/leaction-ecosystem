# CURSOR-027-C1 — Fundação de acesso (sem conexão / sem bootstrap)

| Campo | Valor |
|---|---|
| Status | **Fundação criada; roles Postgres ainda NÃO existem** |
| Data (UTC) | 2026-08-28 |
| Conta / região | `253137917703` / `us-east-2` |
| Conexão ao RDS | **não realizada** |
| SQL / psql / Alembic | **não executados** |
| Task definition / Fargate run | **não criados** |
| Commit/push | **não** |

## Diagrama de acesso (estado C1)

```
[Future] panne-prod-fargate-sg  ──5432──┐
[Future] panne-demo-fargate-sg  ──5432──┼──► actionhub-prod-rds-sg ──► RDS actionhub-prod (private)
[Future] panne-db-bootstrap-sg  ──5432──┘         (3 regras SG-ref; zero CIDR)

Egress app SGs: TCP/443 → 0.0.0.0/0 (APIs AWS) + TCP/5432 → RDS SG
Inbound app SGs: nenhum
```

## Inventário criado

### Security groups

| Nome | ID | Inbound | Egress |
|---|---|---|---|
| `panne-prod-fargate-sg` | `sg-0b4dcda30650d419e` | 0 | 443/any + 5432→RDS SG |
| `panne-demo-fargate-sg` | `sg-0f41648d1720bca80` | 0 | idem |
| `panne-db-bootstrap-sg` | `sg-0c7a0ce1c81ed4cf6` | 0 | idem |

### RDS SG `actionhub-prod-rds-sg` (`sg-04269196534d71e08`)

Três regras TCP **5432**, somente por referência de SG (sem CIDR):

1. prod Fargate → descrição `Panne prod Fargate to actionhub-prod:5432`
2. demo Fargate → `Panne demo Fargate to actionhub-prod:5432`
3. bootstrap → `Panne DB bootstrap task to actionhub-prod:5432`

Sem PanelDX, bastion, NAT ou `0.0.0.0/0`.

### Secrets Manager (valores **não** lidos nesta passagem)

| Secret | Username planejado | dbname | syncStatus |
|---|---|---|---|
| `panne/prod/db/migrator` | `panne_prod_migrator` | `panne` | **pending_postgres_role_bootstrap** |
| `panne/prod/db/runtime` | `panne_prod_runtime` | `panne` | pending… |
| `panne/demo/db/migrator` | `panne_demo_migrator` | `panne_demo` | pending… |
| `panne/demo/db/runtime` | `panne_demo_runtime` | `panne_demo` | pending… |

ARNs (sufixo aleatório AWS): `…:secret:panne/prod/db/migrator-****` etc.

**Estado explícito:** senhas existem só no Secrets Manager; **roles PostgreSQL ainda não foram criadas**; secrets **não** estão sincronizados com o banco até C2. Rotação automática **não** habilitada.

Master RDS: permanece o segredo gerenciado `rds!db-…` — **GetSecretValue não chamado** em C1.

### IAM

| Role | ARN | Políticas gerenciadas anexadas |
|---|---|---|
| `panne-ecs-task-execution-role` | `arn:aws:iam::253137917703:role/panne-ecs-task-execution-role` | nenhuma (só inline) |
| `panne-db-bootstrap-task-role` | `arn:aws:iam::253137917703:role/panne-db-bootstrap-task-role` | nenhuma (só inline) |

**Menor privilégio / wildcards**

| Sid | Wildcard? | Justificativa |
|---|---|---|
| `EcrAuthToken` | `Resource: *` | Exigência AWS para `ecr:GetAuthorizationToken` |
| ECR pull | repo `panne/backend` exato | — |
| Logs execution | `/ecs/panne/*` | família Panne apenas |
| Secrets execution | `panne/prod/db/*` e `panne/demo/db/*` | cobre sufixo aleatório do ARN |
| Bootstrap secrets | ARN exato do master + prefixos Panne | sem PanelDX |
| Bootstrap logs | só `/ecs/panne/db-bootstrap` | — |

Sem `AdministratorAccess`. Sem recursos `paneldx*` nas policies.

### ECR

| Campo | Valor |
|---|---|
| Repository | `panne/backend` |
| URI | `253137917703.dkr.ecr.us-east-2.amazonaws.com/panne/backend` |
| Scan on push | **true** |
| Tag mutability | **IMMUTABLE** (padrão seguro: tags de release não sobrescritas) |
| Encryption | AES256 (default AWS) |
| Images | **0** (vazio) |
| Lifecycle | keep last 20 tagged; expire untagged after 7 days |

### Logs

| Log group | Retenção |
|---|---|
| `/ecs/panne/db-bootstrap` | **30** dias |

## Custo incremental estimado

| Item | ≈ US$/mês |
|---|---|
| 4 secrets | 1,60 |
| CloudWatch log group (vazio) | ~0 |
| ECR vazio | ~0 |
| IAM / SG | 0 |
| **Total C1** | **≈ 1,60** (+ RDS já provisionado em 027-B) |

## Procedimento planejado para CURSOR-027-C2 (não executado)

1. Publicar imagem bootstrap mínima em `panne/backend` (tag imutável).
2. Criar **task definition** one-shot (rede privada, SG bootstrap, roles C1).
3. Run task descartável que: lê master + 4 secrets; cria DBs `panne`/`panne_demo`; cria roles; aplica GRANTs; opcional `unaccent`; **não** roda Alembic completo salvo autorização.
4. Validar CONNECT com runtime/migrator; negar cruzado.
5. Marcar secrets `syncStatus=synced` (PutSecretValue sem eco).
6. Destruir task; revisar logs sem senhas.

## Rollback C1 (se autorizado depois)

1. Remover 3 regras inbound do RDS SG (ou revogar por rule id).
2. Delete secrets Panne (após backup de metadados se necessário).
3. Delete roles IAM + inline policies.
4. Delete ECR (se ainda vazio) e log group.
5. Delete os 3 SGs Panne.
6. **Não** tocar em `actionhub-prod` nem PanelDX.

## Evidência de não-conexão

- Nenhum `psql`, SDK SQL, Session Manager DB tunnel ou Alembic nesta passagem.
- Nenhum `GetSecretValue` (master ou app) além do write implícito em `CreateSecret`.
- RDS permanece `available`; databases adicionais não foram criados via SQL.

## Diferenças / alertas

1. Egress default `0.0.0.0/0 all` foi removido após create; ficou 443+5432.
2. Lifecycle ECR exigiu `file://` (PowerShell quebrou JSON inline).
3. Secrets carregam `host` interno da instância (útil ao C2); valor não documentado aqui.
