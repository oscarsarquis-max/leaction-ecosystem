# Levantamento só-leitura — 01/10/2026

Conta `253137917703`, IAM `paneldx-user-admin`, região `us-east-2`. Sem escrita AWS. Sem inferir que a engine pública está atualizada porque a local está.

## ActionFinance `https://actionfinance.actionhub.com.br`

| Item | Observado |
|---|---|
| Readiness | `GET /actuator/health/readiness` → 200 `{"status":"UP"}` |
| SPA | `GET /` → 200 “Action Finance Capital / Carregando acesso…” |
| API sem sessão | `GET /api/v1/pay-receipts` → 401 |
| Rota HTML `/pay-receipts` | 403 sem sessão |
| Cluster / serviço | `actionfinance-cluster` / `actionfinance` — desired 1, running 1 |
| Task | `actionfinance-web:1` |
| Imagem | `actionfinance@sha256:7c4cc0de22350fe0f3e62873d06fca6423cc25946205b4b70756822729da5b65` (PRM_007; sem V12 / sem `/pay-receipts`) |
| Flyway no RDS | Último relato REV_007: **v7**. V8–V12 não aplicados |
| Perfil | `homolog=false`, `demo-auth=false`, OIDC ligado. URL/secret Spider **ausentes na imagem publicada** |
| Empresa operacional | Loja de Pães `624023a4-57e3-415c-b7d0-925ca1acd3b7` — **não** usar na 1ª demonstração |
| Ingresso | `paneldx-alb`, regra host, sem ALB dedicado |
| VPC | PanelDX `vpc-017dc4cac16ba2c59` — não é a sandbox da Spider |

## Spider engine `https://api.spider.actionhub.com.br`

| Item | Observado |
|---|---|
| Health público | timeout / 504. **Não** concluir que a engine está atualizada |
| Cluster / serviço | `spider-sandbox` / `spider-sandbox-backend` — desired **1**, running **1** |
| Task | `spider-sandbox-backend:5` |
| Imagem | tag `sandbox-20260928-monitorfix` digest `sha256:72ed3a8c70121d3c169ac984afce8add2e0ee962f9650ce51b33fe62f9b9f4a1` (push 28/09/2026) |
| Profile | `sandbox` |
| Persistência | `SPIDER_CANONICAL_PERSISTENCE_MODE=memory` |
| Contrato 1.4 / `LIST_PAYMENT_TRANSACTIONS` | **Não** está neste digest (anterior ao PRM_009 local de 01/10) |
| Réplicas | 1. Compatível com RAM se permanecer 1. Segunda tarefa faria a execução desaparecer |

## Monitor `https://monitor.spider.actionhub.com.br`

| Item | Observado |
|---|---|
| Sem sessão | 302 para Cognito (WebFetch sem cookie viu 403 de WAF) |
| Identidade | Cognito `spider-sandbox-monitor`, grupo `spider-sandbox-operators` |
| Autorização por empresa | **Ausente.** Operador do grupo vê o recorte da réplica, não um tenant |
| Badge | SPA publicada rotula “AMBIENTE MOCK” de forma fixa |
| Engine usada | A do cluster sandbox acima — não a localhost `:8080` |

## ActionHub Pay `https://actionhub.com.br`

| Item | Observado |
|---|---|
| Health FE | `GET /api/health` → `ok`, `git_sha=49b2a83` |
| Listagem | `GET /v1/integration/payments` → **404** |
| Flags LOOKUP | Não presentes no task `inove4us-prod:63` (outro produto). Hub vivo no EC2 `action_hub_prod` `i-07f42e668d62038cd` (DEP_001) |
| Isolamento físico | Mesma tabela `orders` da operação. Separação só por `app_id` + `sandbox`/`test_order` se a rota for ligada |

## Classificação

A jornada pública **não** é possível no estado atual: Finance público sem V12/sync; Spider pública sem contrato 1.4; Pay público sem listagem; Monitor sem recorte por empresa e com badge MOCK.
