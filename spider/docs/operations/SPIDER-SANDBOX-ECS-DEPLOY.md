# SPIDER-SANDBOX-ECS-DEPLOY

Fonte de verdade da task definition **em execução** no sandbox. O Terraform cria a família
`spider-sandbox-backend` e o service, mas **não** promove revisão: o service tem
`lifecycle.ignore_changes = [task_definition]`.

## Processo que modifica a task

| Campo | Valor |
|---|---|
| Processo | Deploy operacional do sandbox (prova/homologação) |
| Scripts versionados | `infra/aws/scripts/prm009-prova001-*.py`, registro ECS via AWS CLI |
| Quem executa | Operador do sandbox Spider (conta `253137917703`) |
| Fonte de verdade | Revisão **ativa do service**, hoje `:11` |
| Imagem viva | `spider-sandbox-backend@sha256:51b05e39350327cdfa8fb9d2c5762689ab314abbc598ebab289488cb10a380ea` (`prova001-sim`) |
| State Terraform | ainda aponta `:4` / tag `sandbox-20260928-7177805b2` |

## Inventário da revisão 11 (sem secrets)

Variáveis presentes além das do state `:4`:

- `SPIDER_CANONICAL_PERSISTENCE_MODE=memory`
- `SPIDER_MONITOR_ALLOWED_COMPANIES` (duas empresas de homolog)
- `SPIDER_TELEMETRY_ENABLED=true`
- `SPIDER_ACTIONHUB_PAY_EDGE_URL=https://api.actionhub.com.br`
- `SPIDER_CANONICAL_SIGNAL_HTTP_ENABLED=true`
- `SPIDER_CORS_ORIGINS`, `SPIDER_SANDBOX_CREDENTIAL_REF`, `SPRING_PROFILES_ACTIVE=sandbox`
- secrets de aplicação injetados como env na revisão 11 (devem migrar para Secrets Manager na Fase B; não gravar valores em git)

Secret ECS: `SPIDER_JWT_SECRET` ← `spider-sandbox/jwt`.

## Drift

```powershell
aws ecs describe-services --region us-east-2 --cluster spider-sandbox --services spider-sandbox-backend --query services[0].taskDefinition
aws ecs describe-task-definition --region us-east-2 --task-definition spider-sandbox-backend --query taskDefinition.revision
```

Divergência `:4` (state) vs `:11` (vivo) é esperada até a Fase B registrar uma revisão nova a partir de `:11`.

## Rollback

```powershell
aws ecs update-service --region us-east-2 --cluster spider-sandbox --service spider-sandbox-backend --task-definition spider-sandbox-backend:11 --force-new-deployment
```

## Por que o Terraform não governa `task_definition` do service

Uma apply da stack principal não pode derrubar a revisão operacional nem republicar a tag antiga. A persistência do Monitor cria revisão nova só na Fase B, clonando `:11`.
