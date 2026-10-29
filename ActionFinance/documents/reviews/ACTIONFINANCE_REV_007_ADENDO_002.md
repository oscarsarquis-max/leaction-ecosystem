# ACTIONFINANCE_REV_007_ADENDO_002 — Migração para paneldx-alb

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_007_ADENDO_002 |
| Prompt | [ADENDO_002](../prompts/ACTIONFINANCE_PRM_007_ADENDO_002_MIGRACAO_ALB.md) |
| Data | 30/09/2026 |
| Autorização | Proprietário: “autorizo”. Não pedida de novo |
| Publicação | Continua **não declarada** |
| Aceite | Não atribuído ao executor. Sem PRM_008 |

Complementa [REV_007](ACTIONFINANCE_REV_007.md) e [ADENDO_001](ACTIONFINANCE_REV_007_ADENDO_001.md).

## Factos (observados)

| Instantâneo | Valor |
|---|---|
| Conta / região | `253137917703` / `us-east-2` |
| Digest ECR | `sha256:7c4cc0de22350fe0f3e62873d06fca6423cc25946205b4b70756822729da5b65` |
| Controller ECS | `ECS` (rolling); 2 TGs na transição, 1 no fim |
| Prioridades no `paneldx-alb` :443 **antes** | 1, 2, 5, 10, default |
| Prioridades livres &lt; 10 | 3, 4, 6, 7, 8, 9 |
| Regra AF | prio **6**, host exacto `actionfinance.actionhub.com.br`, TG `actionfinance-px-tg` |
| `/api*` prio 10 / default / mudaedu / panne demo | **inalterados** |
| SNI | ACM `20d287ca-cc9c-4efe-8913-b79720b99718` associado ao listener partilhado |
| State Terraform | `paneldx-alb` só via `data`; sem import |
| Smoke pré-DNS (`--resolve` + SNI, TLS verify 0) | readiness 200; `/` 200; `/api/titles` 401; OIDC 302 para Cognito com `redirect_uri` do produto |
| Smokes legado (GET) | `actionhub.com.br` 200; `www` 200; `api.actionhub.com.br/` 404; `mudaedu.com.br` 200; `api.demo.panne.ia.br/health` 200 |
| Alias após troca | `actionfinance.actionhub.com.br` → `paneldx-alb-2081687910.us-east-2.elb.amazonaws.com` |
| Apex/www/api/school | continuam `3.17.19.188` |
| Público pós-DNS e pós-delete | readiness 200, `/` 200, API 401, TLS verify 0 |
| Exclusão do ALB dedicado | ~**2026-09-30T14:55Z**; `LoadBalancerNotFound` em `actionfinance-alb` |
| Plano destrutivo inspeccionado | 0 add, 1 change (ECS), 4 destroy (ALB, listener, `actionfinance-tg`, SG `actionfinance-alb`) |
| Preservado | ACM, cluster/serviço ECS, RDS, logs, secrets, Cognito, `paneldx-alb` |
| TG final | `10.0.131.115` healthy; desired/running 1 |

Login humano, CSRF/logout na sessão real e restore RDS isolado: **não** comprovados neste adendo. Username `admin@actionhub.com.br`; contacto `oscar@oscarsarquis.com.br`; Loja de Pães sem CNPJ.

## Estimativas (não fatura)

Horas + 2 IPv4 do ALB dedicado: **US$ 23,73/mês** (premissas §4). A reserva de 1 LCU (US$ 5,84) **não** foi medida na fatura. Depois da migração, LCU incremental conta no `paneldx-alb` (≈0 neste dia). Faixa restante indicativa **US$ 35–50/mês**.

## Reversão

Depois das 14:55 UTC, rollback exige **recriar** o caminho dedicado no IaC. Não há ALB “desligado” a faturar.
