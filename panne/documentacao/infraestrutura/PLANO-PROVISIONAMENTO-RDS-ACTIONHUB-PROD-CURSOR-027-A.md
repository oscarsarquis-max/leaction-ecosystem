# Plano de provisionamento — RDS `actionhub-prod` (CURSOR-027-A)

**Status:** plano apenas. **Gate:** aguardar autorização explícita do proprietário/Cortex.

Referências: [ADR](ADR-RDS-ACTIONHUB-PROD-CURSOR-027-A.md) · [Custo](CUSTO-RDS-ACTIONHUB-PROD-CURSOR-027-A.md) · [Checklist](CHECKLIST-RDS-ACTIONHUB-PROD-CURSOR-027-A.md)

---

## 1. Rede

### 1.1 DB subnet group (a criar)

| Campo | Valor |
|---|---|
| Nome proposto | `actionhub-prod-private` |
| VPC | `vpc-017dc4cac16ba2c59` |
| Subnets | `subnet-0a1da7a0765588962` (private1, us-east-2a) + `subnet-0693afdb3330b683a` (private2, us-east-2b) |

**Por que não reutilizar existentes**

- `default-vpc-017dc4cac16ba2c59` inclui **subnets públicas**.
- `inove4us-prod` usa apenas as duas **públicas**.

Egress das apps continua via `PanelDX-NAT-Instance`; o RDS permanece privado (sem IP público).

### 1.2 Security group do RDS (a criar — não nesta passagem)

| Campo | Valor |
|---|---|
| Nome proposto | `actionhub-prod-rds-sg` |
| VPC | `vpc-017dc4cac16ba2c59` |
| Descrição | RDS Action Hub / Panne — PostgreSQL 5432 |

**Ingress (exato)**

| Proto | Porta | Origem | Motivo |
|---|---|---|---|
| tcp | 5432 | SG `panne-prod-fargate-sg` (a criar no deploy API) | runtime + migração prod via task/bastion controlado |
| tcp | 5432 | SG `panne-demo-fargate-sg` (a criar) | runtime + migração demo |
| tcp | 5432 | SG `paneldx-bastion-sg` (`sg-030b0217eee978745`) **opcional**, só se break-glass aprovado | admin emergencial |

**Egress**

| Proto | Destino | Motivo |
|---|---|---|
| (nenhum necessário além do default deny implícito) | — | RDS tipicamente egress all; manter default AWS ou restringir se política exigir |

**Não incluir nesta fase**

- CIDR `0.0.0.0/0`
- SG do PanelDX Fargate (`sg-0b8d724a5cc3b8c4e`) — evita acesso cruzado PanelDX→Panne
- IP do MAtivas / Action Hub atuais no SG do PanelDX DB

### 1.3 Security groups de origem (apps — futuros)

| SG proposto | Uso | Ingress típico | Egress |
|---|---|---|---|
| `panne-prod-fargate-sg` | tasks API produção | somente ALB SG / listener | 443 egress + 5432 para `actionhub-prod-rds-sg` |
| `panne-demo-fargate-sg` | tasks API demo | somente ALB SG | idem |

Até existirem esses SGs, o RDS **não** deve ser aberto a CIDRs amplos. Ordem sugerida no provisionamento: criar SGs app (mesmo vazios de serviço) **ou** criar RDS SG sem ingress e adicionar regras quando os SGs app existirem (janela curta sem conectividade).

---

## 2. Instância RDS

### 2.1 Parâmetros create

Sanitizado (valores secretos omitidos):

```text
create-db-instance
  --db-instance-identifier actionhub-prod
  --db-name actionhub_prod
  --engine postgres
  --engine-version 17.9
  --db-instance-class db.t4g.small
  --allocated-storage 20
  --max-allocated-storage 100
  --storage-type gp3
  --storage-encrypted
  --no-publicly-accessible
  --vpc-security-group-ids <actionhub-prod-rds-sg>
  --db-subnet-group-name actionhub-prod-private
  --backup-retention-period 7
  --preferred-backup-window 06:00-06:30
  --preferred-maintenance-window tue:07:00-tue:07:30
  --deletion-protection
  --copy-tags-to-snapshot
  --enable-performance-insights
  --performance-insights-retention-period 7
  --manage-master-user-password
  --master-username actionhub_admin
  --port 5432
  --tags Key=Product,Value=actionhub Key=Component,Value=rds Key=Env,Value=shared-platform
```

Notas:

- `--manage-master-user-password` cria/gerencia segredo no Secrets Manager (**sem** passar senha na CLI).
- Não usar `--master-user-password` em claro.
- Enhanced Monitoring omitido (off).
- Janelas em **UTC** (AWS). Equivalente aproximado BRT (UTC−3): backup 03:00–03:30; manutenção ter 04:00–04:30.

### 2.2 Ordem operacional sugerida (pós-autorização)

1. Criar SG `actionhub-prod-rds-sg` (ingress vazio ou só bastion se já aprovado).
2. Criar DB subnet group `actionhub-prod-private`.
3. `create-db-instance` com manage master password.
4. Aguardar `available`.
5. Confirmar endpoint privado, encryption, PI, deletion protection, subnet/SG.
6. Criar SGs app (se ainda não) e **autorizar** 5432 no SG do RDS.
7. Procedimento de databases/roles (abaixo) via canal seguro (Session Manager / task one-shot), **sem** eco de senha.
8. Validar TLS (`sslmode=require` ou verify-full com CA RDS).
9. Somente então migrations Alembic.

---

## 3. Bancos, roles e segredos

### 3.1 Databases lógicos

| Database | Função |
|---|---|
| `actionhub_prod` | DB inicial da instância; uso administrativo/plataforma; apps Panne **não** conectam aqui no dia a dia |
| `panne` | Produção Panne |
| `panne_demo` | Demo Panne |

### 3.2 Roles (nomes propostos)

| Role | Escopo | Privilégios (diretriz) |
|---|---|---|
| `panne_prod_migrator` | só DB `panne` | DDL + DML necessários a Alembic; sem CREATEDB/CREATEROLE na instância |
| `panne_prod_runtime` | só DB `panne` | DML/SELECT mínimos nas schemas app; sem DDL |
| `panne_demo_migrator` | só DB `panne_demo` | idem migrator |
| `panne_demo_runtime` | só DB `panne_demo` | idem runtime |

Regras:

- Master `actionhub_admin` **somente** break-glass / bootstrap (Secrets Manager).
- Sem acesso cruzado: role prod sem `CONNECT` em `panne_demo` e vice-versa.
- Apps usam **apenas** runtime (ou migrator em job de migration).

### 3.3 Segredos (nomes — sem valores)

| Secret (proposta) | Conteúdo lógico |
|---|---|
| (gerenciado RDS) master | usuário master + senha rotacionável |
| `panne/prod/db-migrator` | URL/user/pass migrator prod + host/db |
| `panne/prod/db-runtime` | runtime prod |
| `panne/demo/db-migrator` | migrator demo |
| `panne/demo/db-runtime` | runtime demo |

Nunca gravar senhas em Git, docs, tickets ou saída de agente.

### 3.4 Criação segura (procedimento)

1. Obter master secret via IAM + `GetSecretValue` **somente** em sessão administrativa controlada (não nesta passagem).
2. Conectar com TLS a partir de host autorizado (bastion SSM ou task).
3. Scripts SQL idempotentes: `CREATE DATABASE`, `CREATE ROLE`, `GRANT CONNECT`, `GRANT USAGE`, default privileges.
4. Gerar senhas com Secrets Manager (`CreateSecret` / random) — não inventar na mão.
5. Testar `CONNECT` e negar cruzado.
6. Revogar sessões de teste; não logar connection strings completas.

---

## 4. Estratégia Alembic

| Ambiente | Database | Role | Gate |
|---|---|---|---|
| Produção | `panne` | `panne_prod_migrator` | job one-shot / pipeline com secret migrator |
| Demo | `panne_demo` | `panne_demo_migrator` | idem, pipeline separado |

- Rodar `alembic upgrade head` **por database**, nunca apontando para `actionhub_prod` como schema app.
- Extensão `unaccent`: na primeira migration que a exige, com role que possa `CREATE EXTENSION` (master ou role com privilégio concedido uma vez).
- Rollback de migration: seguir política Alembic do produto; restore de instância só com autorização (PITR afeta **toda** a instância).
- Não misturar seed demo em `panne` produção.

---

## 5. Compatibilidade Panne

| Tema | Status |
|---|---|
| Postgres 17.9 | OK (validado na região) |
| `unaccent` + TSVECTOR | OK com CREATE EXTENSION |
| SSL | Apps com `sslmode=require` (mínimo) |
| Timezone app `America/Sao_Paulo` | OK sem mudar GUC global |
| Dois DBs + roles mínimas | Alinha a `PANNE_DATABASE_URL` / runtime URL |
| ARM tasks Fargate + RDS t4g | Independentes (cliente rede); Graviton no RDS OK |

---

## 6. Rollback da criação

Se o provisionamento for autorizado e precisar desfazer **antes** de dados de negócio:

1. Remover regras de ingress do SG RDS.
2. Desabilitar deletion protection.
3. Criar snapshot final opcional (se houver dúvida).
4. `delete-db-instance` com skip/final snapshot conforme política.
5. Apagar subnet group e SG se não usados.
6. Apagar secrets Panne criados (não o de outros produtos).
7. Registrar incidente/postmortem curto.

Se já houver dados: preferir stop + snapshot; delete só com autorização explícita.

---

## 7. Comandos/API planejados (não executados)

```text
# Subnet group
aws rds create-db-subnet-group
  --db-subnet-group-name actionhub-prod-private
  --db-subnet-group-description "Action Hub / Panne private subnets"
  --subnet-ids subnet-0a1da7a0765588962 subnet-0693afdb3330b683a
  --region us-east-2

# Security group
aws ec2 create-security-group
  --group-name actionhub-prod-rds-sg
  --description "RDS actionhub-prod PostgreSQL"
  --vpc-id vpc-017dc4cac16ba2c59
  --region us-east-2
# authorize-security-group-ingress ... SourceSecurityGroupId=<panne-*-fargate-sg> FromPort=5432 ToPort=5432

# Instância (trecho; master via Secrets Manager)
aws rds create-db-instance ... --manage-master-user-password ...
  --region us-east-2

# Validação pós
aws rds describe-db-instances --db-instance-identifier actionhub-prod
aws rds describe-db-instances --db-instance-identifier paneldx-database
  # confirmar paneldx inalterado
```

Nenhum dos comandos acima foi executado nesta passagem.
