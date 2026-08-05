# Estimativa de custo — QMind homolog (`us-east-2`)

**Status:** ADR-010 emenda **Lightsail** (2026-08-04).  
Perfil ativo: `infra/terraform-lightsail/`.  
Enterprise ECS/RDS: **não** aplicar (`infra/terraform-enterprise/`).

## Controle financeiro

| Item | Valor |
|---|---|
| Budget AWS | `qmind-homolog-monthly-30` |
| Limite | **US$ 30 / mês** (custo da conta) |
| Alertas reais | 50%, 80%, 100% |
| Alertas previstos | 80%, 100% |
| E-mail | `gestao@leaction.com.br` |
| Monitoramento Budgets | gratuito |

> Nota: o budget atual é da **conta** (não só tag QMind). Em 2026-08-04 o spend calculado da conta já podia ultrapassar US$ 30 por outros workloads — os alertas ajudam a perceber isso. Filtrar por tag `Project=qmind` é evolução opcional após ativar cost allocation tags.

## Perfil ativo — Lightsail (~US$ 15–25/mês típico)

| Recurso | Config | Ordem (USD/mês) | Notas |
|---|---|---|---|
| Lightsail | `small_3_0` (2 GB, 2 vCPU, 60 GB, 3 TB xfer) | **~12** | IPv4 incluído no plano |
| IP estático | associado à instância | **0** | cobrança só se desassociado ocioso |
| S3 evidências | baixo volume | <3 | |
| S3 backups | `pg_dump` + lifecycle 35d | <2 | |
| Cognito | MAU baixos | free / <2 | |
| Route 53 | zona já existente `qmind.com.br` | ~0,50 + queries | zona já na conta |
| Logs / misc | leve | 1–3 | |
| **Total típico QMind homolog** | | **~15–25** | sob teto do budget 30 |

DNS: `api.homolog.qmind.com.br` + `app.homolog.qmind.com.br` → mesmo IP estático.

HTTPS: **Caddy / Let's Encrypt** — sem ACM/ALB.

## Não criar nesta fase

ALB, ECS/Fargate, RDS, NAT, API Gateway, ACM para o servidor, autoscaling, VPC complexa.

## Anexo — enterprise (futuro)

ECS+ALB+RDS: ~55–95 sem NAT; ~90–130 com NAT. Só quando receita/uso justificarem.

## Antes do apply

1. Revisar `terraform plan` em `terraform-lightsail/`.
2. Confirmar preço do bundle na região ([Lightsail pricing](https://aws.amazon.com/lightsail/pricing/)).
3. Apply só com aprovação explícita.
