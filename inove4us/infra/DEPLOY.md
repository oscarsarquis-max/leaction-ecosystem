# Deploy AWS — inove4us.com.br (Top of Funnel isolado)

Infraestrutura **própria** do inove4us, separada do PanelDX.  
**Único recurso compartilhado:** PostgreSQL `LeAction_SysF` (mesmo banco do PanelDX).

## Decisão de arquitetura

| Opção | Quando usar |
|-------|-------------|
| **ECS Fargate + ALB** (recomendado neste repo) | Alto tráfego ToF, autoscaling por CPU/QPS, SG preciso no RDS via VPC |
| **App Runner + VPC Connector** | Time-to-market; veja `infra/apprunner/` |

Este roteiro assume **ECS Fargate + ALB + Route 53 + ECR**.

```
Internet → Route 53 (inove4us.com.br)
        → ALB (HTTPS/ACM)
        → ECS Fargate (N≥2, autoscale)
        → RDS PostgreSQL compartilhado (SG: só tasks inove4us:5432)
```

---

## 1. Containerização

Arquivos na raiz do app:

- `Dockerfile` — multi-stage (Vite build + Gunicorn)
- `docker-compose.yml` — smoke test local da imagem
- `.env.production.example` — template de segredos

### Build local / validação

```powershell
cd C:\Projetos\inove4us
copy .env.production.example .env.production
# edite DB_* / SECRET_KEY apontando ao Postgres acessível

docker compose build
docker compose up -d
curl http://localhost:8080/api/health
```

### Push ECR

```powershell
cd C:\Projetos\inove4us\infra\scripts
.\build-and-push.ps1 -AwsRegion us-east-1 -AccountId 123456789012 -Tag v1.0.0
```

---

## 2. Pré-requisitos AWS (uma vez)

1. **Hosted Zone** `inove4us.com.br` no Route 53 (NS no registrador).
2. **Certificado ACM** (mesma região do ALB) para `inove4us.com.br` + `www.inove4us.com.br` (DNS validation).
3. **VPC** com:
   - 2+ subnets públicas (ALB)
   - 2+ subnets privadas (tasks) com rota NAT para ECR/SES/Bedrock
   - Preferência: **mesma VPC (ou peer) do RDS PanelDX** — obrigatório para regra SG→SG
4. **SG do RDS** atual (anote o ID `sg-...`).
5. Usuário DB `inove4us_app` no Postgres (privilégios necessários nas tabelas `ctdi_*` / `inov_*`), senha no Secrets.

---

## 3. Terraform (ECS Fargate)

```powershell
cd C:\Projetos\inove4us\infra\terraform
copy terraform.tfvars.example terraform.tfvars
# preencha vpc, subnets, hosted_zone_id, certificate_arn, rds_security_group_id, secrets

terraform init
terraform plan
terraform apply
```

O módulo cria:

- ECR
- Security Groups (ALB + ECS tasks)
- **Regra no SG do RDS**: `5432` ← SG das tasks inove4us (**sem** `0.0.0.0/0`)
- ALB + Target Group (`/api/health`)
- Cluster/Service Fargate + autoscaling (CPU 60% e ALB RequestCountPerTarget)
- IAM task (SES + Bedrock)
- Route 53 alias A para apex e `www`

Outputs úteis: `ecr_repository_url`, `alb_dns_name`, `ecs_tasks_security_group_id`.

Após o primeiro apply, faça o push da imagem e force novo deploy do service:

```powershell
aws ecs update-service --cluster inove4us-prod --service inove4us-prod --force-new-deployment
```

> Segredos estão em variáveis de ambiente da task definition neste bootstrap.  
> **Hardening:** migrar `DB_PASS` / `SECRET_KEY` para AWS Secrets Manager + input `valueFrom` na task.

---

## 4. Conexão segura ao PostgreSQL compartilhado

### Modelo correto (Security Group ↔ Security Group)

No SG do **RDS / Postgres atual**:

| Tipo | Porta | Origem | Descrição |
|------|-------|--------|-----------|
| Ingress | TCP 5432 | `sg-…-inove4us-…-ecs-tasks` | inove4us ECS Fargate |

**Não** libere `0.0.0.0/0` nem o SG do ALB (ALB não fala com o banco).

Terraform já aplica:

```hcl
resource "aws_security_group_rule" "rds_from_inove4us" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = var.rds_security_group_id
  source_security_group_id = aws_security_group.ecs_tasks.id
}
```

### Fallback AWS CLI

```powershell
.\authorize-rds-sg.ps1 `
  -RdsSecurityGroupId sg-RDS `
  -Inove4usTasksSecurityGroupId sg-INOVE4US-TASKS `
  -Region us-east-1
```

### Se o RDS estiver em outra conta/VPC

1. VPC Peering ou Transit Gateway  
2. Rotas nas tabelas de rota privadas  
3. Mesma regra SG (IDs referenciáveis após peering) **ou**, se SG cross-VPC não for possível, prefix list / CIDR **somente** das subnets privadas do ECS (ainda assim sem Internet)

### App Runner (alternativa)

1. Crie **VPC Connector** nas subnets privadas  
2. Serviço App Runner com `EgressType=VPC`  
3. No SG do connector (ENIs), ou no SG associado, libere saída 5432  
4. No SG do RDS, ingress 5432 a partir do **SG do VPC Connector**

Nunca publicar o Postgres publicamente.

### SSL

Use `DB_SSLMODE=require` (ou `verify-full` com CA RDS) no `.env` de produção.

---

## 5. Route 53 → serviço

Com Terraform (`route53.tf`), os registros alias já apontam ao ALB:

- `inove4us.com.br` → ALB  
- `www.inove4us.com.br` → ALB  

### Manual (Console / CLI)

1. Route 53 → Hosted Zone `inove4us.com.br`  
2. Create record:
   - **Name:** (vazio / apex) e `www`  
   - **Type:** A — Alias  
   - **Alias target:** Application Load Balancer do inove4us  
3. Confirme NS do domínio no registrador = NS da hosted zone  
4. ACM: status **Issued** para SAN `inove4us.com.br` e `www.inove4us.com.br`

### App Runner

Alias A/AAAA para o domínio customizado do App Runner **ou** CNAME do `www` para `xxxxx.awsapprunner.com` + validação do certificado no próprio App Runner.

---

## 6. Checklist go-live

- [ ] Imagem no ECR com tag imutável (`vX.Y.Z`)  
- [ ] ECS desired ≥ 2, autoscale max definido  
- [ ] Health `https://inove4us.com.br/api/health` → 200  
- [ ] Login freemium + `/inovador/` ok  
- [ ] SES: domínio/identity verificados; `EMAIL_SENDER` ok  
- [ ] Bedrock: model access na conta/região  
- [ ] RDS: só SG das tasks inove4us em 5432  
- [ ] PanelDX continua isolado (sem SG cruzado ALB↔ALB)  
- [ ] `SECRET_KEY` / senhas **fora** do Git  

---

## 7. Diagrama lógico

```
Internet
   │
   ▼
Route 53  (inove4us.com.br / www)
   │
   ▼
ALB + ACM HTTPS     SG-ALB :443 ← world
   │ :8080
   ▼
ECS Fargate (N tasks, autoscale)     SG-ECS-TASKS
   │
   │ TCP 5432  (origem = somente SG-ECS-TASKS)
   ▼
RDS PostgreSQL LeAction_SysF         SG-RDS (compartilhado com PanelDX)
```

---

## Contatos operacionais

- Deploy app: `infra/scripts/build-and-push.ps1` + `aws ecs update-service --force-new-deployment`  
- IaC: `infra/terraform`  
- Smoke local: `docker compose up`
