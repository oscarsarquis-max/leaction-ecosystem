# SPIDER-MONITOR-PERSISTENCE-SANDBOX-002

Preparação da persistência durável do Monitor. **Não aplicar sem aprovação explícita.**

## Arquitetura escolhida

- Persistência do Monitor: `spider.monitor.persistence.mode=memory|jpa`
- Independente de `spider.canonical.persistence.mode` (permanece `memory`)
- Modo `jpa` usa `monitorDataSource` (Hikari dedicado) + JDBC + `MonitorSchemaMigrator`
- Não liga `DataSourceAutoConfiguration`, Hibernate nem repositórios JPA canônicos
- Retenção efetiva P90D com `retention_until` e purge horário
- RDS sandbox: PostgreSQL 16.15, `db.t4g.micro`, single-AZ, privado, criptografado com a KMS já existente

## Identidades

| Tipo | ID | Origem exibida |
|---|---|---|
| Interação | `int:actionfinance:{messageId}` | ACTIONFINANCE |
| Sincronismo | `sync:{company}:{env}:{syncRunId}` | ACTIONFINANCE |
| Pagamento | `pay:{company}:{transactionId}` | ACTIONHUB PAY |

## Ownership residual (somente o que não pode ser codificado sem destroy)

Regras WAF, ingress do ALB, behaviors do CloudFront e policy S3/OAC foram **codificados**.
Ignores amplos desses blocos foram removidos.

| Recurso | Campo restante | Processo | Versionado em | Fonte de verdade | Drift | Rollback | Por que TF não publica | Risco de ignorar |
|---|---|---|---|---|---|---|---|---|
| `aws_lambda_function.oidc` | `filename`, `source_code_hash` | patch edge | `infra/aws/scripts/prm009-inc001-patch-edge.py` | Lambda `:6` | `aws lambda get-function --qualifier 6` | manter `:6` no CF | zip local != artefato publicado; apply criaria `:7` | evolução futura do edge só via script |
| `aws_lambda_permission.oidc_replication` | `qualifier` | mesmo script | idem | permissão residual `:1` no state | state vs `:6` | não destruir `:1` | replace destruiria a permission | permissão órfã `:1` permanece |
| CloudFront `comment` | `comment` | n/a | n/a | texto cosmética | encoding do travessão | irrelevante | não é controle | nenhum |
| ECS service `task_definition` | `task_definition` | deploy operacional | `docs/operations/SPIDER-SANDBOX-ECS-DEPLOY.md` | revisão **`:11`** | `describe-services` | `update-service …:11` | apply não pode voltar para `:4` | nova revisão só na Fase B |

Terraform state rastreia `spider-sandbox-backend:4` (tag `sandbox-20260928-7177805b2`). O serviço vivo usa a revisão **11** (`prova001-sim`, digest `sha256:51b05e39350327cdfa8fb9d2c5762689ab314abbc598ebab289488cb10a380ea`), com env operacional (empresas, telemetria, ActionFinance/Pay). O service tem `ignore_changes = [task_definition]`. Fase A não registra task nova. Fase B deve clonar a revisão 11, não a 4.

## Migrator

Mecanismo próprio, não Flyway no runtime: Flyway no classpath varreria schemas canônicos e conflitaria com o interruptor canônico.

Garantias:

- histórico `tb_monitor_schema_history` (versão, checksum SHA-256, status)
- `pg_advisory_xact_lock(88101316)` na mesma transação das DDL
- PostgreSQL trata DDL como transacional; crash reverte STARTED e o retry é seguro
- checksum divergente falha o boot
- status `STARTED`/`FAILED` residual falha o boot até correção operacional
- H2 de teste não usa advisory lock
- credencial única `spider_runtime` no sandbox; CAP-022 separa migrator/app
- CAP-022 deve rodar o migrator em job único antes de N tasks ECS

## Fases

### Fase A — banco e secrets (este plano)

Criar somente: subnet group, SG do banco, parameter group, log group, RDS, secret, IAM mínimo nas roles já existentes, alarmes CloudWatch. Sem nova task, sem imagem, sem WAF/CloudFront/Cognito/Lambda/ALB/DNS.

```powershell
cd spider/infra/aws/environments/sandbox
terraform plan -var enable_database=true
```

### Fase B — aplicação (depois da Fase A saudável)

1. Publicar imagem imutável do backend/frontend revisados
2. Nova task definition: `SPIDER_MONITOR_PERSISTENCE_MODE=jpa`, `SPIDER_CANONICAL_PERSISTENCE_MODE=memory`, `SPIDER_MONITOR_JDBC_*` a partir do secret
3. Circuit breaker do ECS; `ignore_changes` do service preserva rollback para `:4`
4. Smoke API + Monitor + ActionFinance controlado
5. Reinício da task e busca fora das cinco recentes

## Custo mensal estimado (sandbox, us-east-2, sem reserva)

| Componente | Hipótese | USD/mês |
|---|---|---|
| RDS db.t4g.micro | 730h, single-AZ | 11.50–13.00 |
| gp3 20 GB | armazenamento inicial | 1.60–2.00 |
| Autoscale até 50 GB | em repouso = 0 extra | 0 |
| Backup 7d | franquia 20 GB; extra se crescer | 0–1.00 |
| Snapshot final | só no destroy | 0 em operação |
| Secrets Manager | 1 secret, sem rotação | 0.40 |
| CloudWatch logs RDS | 30d, volume baixo | 0.50–1.50 |
| CloudWatch métricas/alarmes | 3 alarmes + tópico SNS existente | 0.30–0.60 |
| KMS | chave já existente, rotação anual | ~0 incremental |
| NAT | não criado (`enable_nat=false`) | 0 |
| ECS | desired_count=1, sem mudança de CPU/mem | 0 |
| I/O gp3 | incluído no baseline | 0–1.00 |

Total em repouso: **USD 14–19/mês**. Pico com storage no teto: **USD 20–25/mês**. Sem apply, incremental = 0.

## Deploy (não executar agora)

1. Snapshot textual: task `:4`, Lambda OIDC `:6`, WAF ids, imagem `sandbox-20260928-7177805b2`
2. Apply Fase A somente após aprovação
3. Validar endpoint privado, secret e SG
4. Boot controlado do migrator contra o RDS (job ou task temporária)
5. Validar `tb_monitor_schema_history` e checksums
6. Publicar imagem imutável
7. Registrar task nova com circuit breaker
8. Smoke `/actuator/health`, `/v1/console/monitor/records`
9. Interação AF + sync de duas páginas + pagamento único
10. Substituir a task e repetir a busca
11. Não apagar dados válidos na retenção
12. Gate de não regressão

## Rollback

- ECS service volta para `spider-sandbox-backend:4`
- RDS e snapshot permanecem para investigação
- Não fazer downgrade destrutivo de schema
- WAF, Cognito, CloudFront e Lambda@Edge intactos
- Voltar `SPIDER_MONITOR_PERSISTENCE_MODE=memory` só perde registros voláteis novos

## Riscos

- `company-scope` do sandbox exige `SPIDER_MONITOR_ALLOWED_COMPANIES`
- Histórico AF já perdido não será fabricado
- Usuário único de banco no sandbox (limitação explícita até CAP-022)
- Single-AZ não é HA
