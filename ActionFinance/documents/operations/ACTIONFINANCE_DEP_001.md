# ACTIONFINANCE_DEP_001 — Plano de publicação restrita

| Campo | Valor |
|---|---|
| Data | 30/09/2026 |
| Conta | `253137917703` (confirmada por `sts get-caller-identity`, IAM `paneldx-user-admin`) |
| Região | `us-east-2` |
| Destino | `https://actionfinance.actionhub.com.br` |
| Estado | Aprovado e aplicado. Ingresso no `paneldx-alb` (Adendo 002). ALB dedicado excluído ~14:55 UTC. Publicação ainda não declarada. |

Este documento é o plano concreto. Concordância de recursos e gasto (US$ 65–80/mês + impostos, estimativa, não teto AWS) registada em 30/09/2026. Adendo: [ACTIONFINANCE_PRM_007_AUTORIZACAO](../prompts/ACTIONFINANCE_PRM_007_AUTORIZACAO.md). Não voltar a pedir a mesma aprovação.

A prioridade de integração (ActionHub Pay, Loja de Pães, compras do Panne, caminho via Spider) está em DOM_001 / INT_001. **Não altera** este plano de publicação nem o custo. Sem conectores neste ciclo.

## 1. Recursos reutilizados e novos

### Reutilizados (já existem; não substituir)

| Recurso | ID / nome | Justificativa |
|---|---|---|
| Conta / região | `253137917703` / `us-east-2` | Mesma conta corporativa; compute dos demais produtos |
| VPC | `vpc-017dc4cac16ba2c59` (`PanelDX-vpc`, `10.0.0.0/16`) | Já hospeda ALBs e RDS de produtos reais (Inove, Panne, Hub). Não é a sandbox da Spider |
| Subnets privadas | `subnet-0a1da7a0765588962` (2a), `subnet-0693afdb3330b683a` (2b) | Mesmo padrão do serviço `inove4us-prod` (`assignPublicIp=DISABLED`) |
| Subnets públicas | `subnet-04b323e5cea4d7273` (2a), `subnet-01fb021f890fe6e09` (2b) | Somente para o ALB do ActionFinance |
| Saída 0.0.0.0/0 privada | instância NAT `i-0bdd19288b5118611` (`PanelDX-NAT-Instance`, `t3.nano`) | Já paga; evita NAT Gateway novo (~US$ 33/mês) |
| Endpoints VPC | ECR api/dkr, S3 gateway, Secrets Manager, CloudWatch Logs | Pull de imagem e secrets sem NAT Gateway |
| Zona DNS | `actionhub.com.br` `Z01698931CEOITJ7YYMYX` | Só registros `actionfinance` e validação ACM |
| PostgreSQL gerenciado | motor **17.9** disponível (versões 17.5–17.11 listadas em 30/09) | Compatível com Flyway/local 17.6; não usar a instância `actionhub-prod` |

### Explicitamente fora

| Recurso | Motivo |
|---|---|
| `spider-sandbox-vpc` / cluster `spider-sandbox` / Cognito `spider-sandbox-monitor` | Sandbox ≠ produção |
| RDS `actionhub-prod` | Decisão já registada; banco de outro produto |
| Cluster `inove4us-prod` / `paneldx-cluster` | Não misturar serviço nem IAM |
| Apex / `www` / `api` / `school` | Não alterar |
| CloudFront / WAF | Fora deste recorte |

### Novos (só ActionFinance; após concordância)

State S3+DynamoDB, ECR `actionfinance`, ALB+TG+listener 443, cluster/serviço ECS, RDS `actionfinance` (novo), três secrets (`oidc`, `runtime`, `migrator`), Cognito User Pool + cliente confidencial, log groups, certificado ACM `actionfinance.actionhub.com.br`, CNAME/ALIAS do host **só quando** `enable_public_dns=true`.

## 2. Arquitetura

```
Internet --HTTPS:443--> ALB (subnets públicas, cert ACM us-east-2)
                         |
                         v
              ECS Fargate privado (0.5 vCPU / 1 GB)
                         |
                         +--> RDS PostgreSQL 17.9 privado (db.t4g.micro, Single-AZ)
                         +--> Cognito (OIDC Authorization Code, client secret)
                         +--> Secrets Manager (papéis separados)
```

Sem CloudFront. Cookie host-only do subdomínio. A aplicação não confia em `X-Forwarded-*`.

Liveness do processo: `curl` em `/actuator/health/liveness` (binário **presente** na imagem atual). Readiness do ALB: `/actuator/health/readiness` (banco). A tarefa web sobe com Flyway **desligado** e **sem** secret migrator.

## 3. Dimensionamento, limites, backup, logs

| Tema | Escolha inicial | Limitação |
|---|---|---|
| Compute | 1 tarefa 512 CPU / 1024 MB | Sem HA de aplicação; queda = indisponibilidade até o Fargate recolocar |
| Banco | `db.t4g.micro` Single-AZ, 20 GB gp3, PG 17.9 | Sem failover Multi-AZ; RPO/RTO limitados ao backup |
| Egress | NAT instance compartilhada `t3.nano` | Ponto único já existente; saturação possível sob tráfego alto |
| Backup RDS | retenção 7 dias, `deletion_protection`, snapshot final | Restore em instância isolada **depois** do primeiro backup real |
| Logs | `/actionfinance/web` e `/migrate`, 30 dias | Sem tokens, cookies, senhas ou payloads financeiros |
| Alertas | Destino ainda não definido | Não enviar e-mail/SMS de teste sem autorização |
| Identidade | Cognito dedicado, cadastro público desligado, MFA **opcional** (TOTP) | MFA habilitado ≠ MFA comprovado no utilizador real |
| Responsável operacional | O mesmo da conta corporativa | Confirmar nome/e-mail (insumo em falta) |

## 4. Estimativa mensal (30/09/2026)

Premissas: 730 h, 1 tarefa contínua, tráfego baixo (~1 LCU), 20 GB RDS, 2 GB de logs ingeridos, 3 secrets, 2 IPv4 públicos do ALB (2 AZ), **sem** NAT Gateway novo, endpoints e NAT instance **já existentes** (custo incremental de dados só). Câmbio não convertido; valores em USD.

| Item | Base oficial / consulta | Cálculo | USD/mês |
|---|---|---|---|
| Fargate Linux/x86 0,5 vCPU + 1 GB | [ECS/Fargate pricing](https://aws.amazon.com/ecs/pricing/); Price List `AmazonECS` (us-east-2: US$ 0,04048/vCPU-h e US$ 0,004445/GB-h, revalidado em fontes de 2026-09) | (0,5×0,04048 + 0,004445)×730 | **18,02** |
| ALB | [ELB pricing](https://aws.amazon.com/elasticloadbalancing/pricing/) US$ 0,0225/h + US$ 0,008/LCU-h | 0,0225×730 + ~1 LCU | **16,43 + ~5,84** |
| IPv4 público do ALB | [VPC pricing](https://aws.amazon.com/vpc/pricing/) US$ 0,005/h por endereço | 2×0,005×730 | **7,30** |
| RDS PostgreSQL `db.t4g.micro` Single-AZ | Price List API 30/09/2026, `US East (Ohio)`: **US$ 0,016/h** | 0,016×730 | **11,68** |
| Storage gp3 20 GB | Lista RDS (Ohio ~US$ 0,08/GB-mês; confirmar na fatura) | 20×0,08 | **~1,60** |
| Backup RDS | Armazenamento de backup até o tamanho da instância sem custo extra típico | 20 GB | **0** (excesso cobra) |
| Secrets Manager | [Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/) US$ 0,40/secret/mês | 3 secrets | **1,20** |
| CloudWatch Logs | [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/) ingestão ~US$ 0,50/GB | 2 GB | **~1,00** |
| Cognito User Pool | [Cognito pricing](https://aws.amazon.com/cognito/pricing/) 10 000 MAU no nível essencial | poucos operadores | **0** (SMS MFA sairia à parte; não previsto) |
| ECR | armazenamento de imagens | <1 GB | **~0,10** |
| State S3 + DynamoDB lock | S3 + on-demand lock | mínimo | **~0,30** |
| ACM + Route53 (1 alias) | certificado público gratuito; zona já existe | — | **0** |
| NAT Gateway **novo** | [VPC pricing](https://aws.amazon.com/vpc/pricing/) US$ 0,045/h | **não criar** | **0** |
| Endpoints VPC novos | interface ~US$ 7,3/AZ | **reutilizar** | **0** |
| Dados NAT instance | US$ 0,09/GB saída Internet típica + processamento da instância | poucos GB IdP | **1–4** (não zero) |

**Faixa recomendada a reservar: US$ 65–80 / mês** no arranque, mais impostos. O maior risco de surpresa é IPv4 + LCU + saída pela NAT instance compartilhada, não o Fargate.

Não há gratuidade presumida de ALB, RDS, IPv4 nem logs.

## 5. Plano Terraform (aplicado 30/09/2026)

Módulos: `ops/aws/state` (bucket/lock) e `ops/aws/terraform` (produto). State próprio; `check` exige `account_id == 253137917703` e recusa a VPC sandbox.

**Create previsto (produto):** ECR, SGs, ALB, TG, listener, ACM + records de validação, cluster ECS, IAM (execution web ≠ execution migrate ≠ task), 3 secrets vazios, RDS novo, Cognito pool/client/domain, log groups, subnet group `actionfinance-private`. Serviço ECS e alias DNS só depois de digest + `enable_public_dns`.

**Change/destroy de outros produtos:** nenhum. Não se importa `actionhub-prod-private` nem se altera clusters alheios.

`terraform fmt` / `validate` locais. `plan` real só após concordância (o plan remoto lê a conta).

## 6. Sequência e reversão

1. Concordância deste plano (custo + Cognito + VPC PanelDX).
2. Apply do **state** (S3+lock). Custo mínimo contínuo.
3. Apply da fundação (`desired_count=0`, `enable_public_dns=false`, `image_uri=""`): RDS, ALB, ECR, Cognito, ACM/validação, secrets.
4. Preencher secrets por CLI (sem imprimir). Criar papéis `actionfinance_runtime` / `actionfinance_migrator` no RDS com o master gerido pela AWS.
5. Build + push ECR; guardar digest. Manifesto em `ops/aws/releases/` (gitignored se contiver hashes operacionais locais).
6. `run-task` migrate; validar Flyway V7 e grants. Web sem DDL.
7. `bootstrap-org` dry-run + execução com empresa real; `provision` OPERATOR com issuer+subject do Cognito (não e-mail).
8. Apply com `image_uri=@sha256:…` e `desired_count=1`. Provar readiness.
9. Só então `enable_public_dns=true`.
10. Login humano do responsável. Logout e isolamento de quem não tem vínculo.

**Rollback inicial (não há versão anterior):** `desired_count=0` e, se preciso, `enable_public_dns=false`. Preservar RDS, logs e secrets. Não `terraform destroy` na VPC/NAT/DNS de outros produtos. Não apagar o banco para “desfazer” a estreia.

**Critério para abrir o host:** certificado válido, OIDC preenchido, migrations/grants ok, primeiro OPERATOR provisionado, desired_count≥1 saudável.

## 7. Insumos (adendo de 30/09/2026)

| Insumo | Estado |
|---|---|
| Login do operador | `admin@actionhub.com.br` (não é caixa postal) |
| Contacto / convite / alertas | `oscar@oscarsarquis.com.br` (único destinatário deste produto) |
| Empresa | Loja de Pães — sem CNPJ; cadastro inicial feito |
| IdP | Cognito dedicado `us-east-2_GYIa11WvX`; username ≠ e-mail de contacto |
| Convite Cognito | Enviado ao contacto autorizado |
| Login humano no destino | **Pendente** — não pedir senha no chat |

Apply da fundação, digest, migrate, OPERATOR e alias público **já ocorreram**. A publicação continua não declarada até a prova de login.

## Recomendação principal ao proprietário (30/09, pré-adendo)

Histórico: aprovar a faixa **US$ 65–80/mês** com ALB dedicado. O proprietário concordou (“concordo sim…”). Essa concordância **não** obriga a manter o ALB se o ingresso compartilhado for adequado. A reavaliação está na §8.

## 8. Adendo 001 — ingresso compartilhado vs ALB dedicado (30/09/2026)

Fonte: [PRM_007_ADENDO_001_GATEWAY](../prompts/ACTIONFINANCE_PRM_007_ADENDO_001_GATEWAY.md). Avaliação em [REV_007_ADENDO_001](../reviews/ACTIONFINANCE_REV_007_ADENDO_001.md). A tabela da §4 **permanece** como estimativa do plano original (não é cotação nova).

### 8.1 Estado na avaliação (Adendo 001)

O ALB `actionfinance-alb` existia (criado 13:40 UTC de 30/09), internet-facing na VPC PanelDX, 2 AZ, listener só 443. Métricas ~3 h: `RequestCount` 5, `ConsumedLCUs` ≈ 0,00003. A parcela **US$ 29,57/mês** da §4 inclui reserva de ~1 LCU (US$ 5,84); horas + 2 IPv4 são **US$ 23,73/mês** + LCU efectiva. **Retirado em 30/09/2026 ~14:55 UTC** após o Adendo 002.

### 8.2 O que é o “gateway existente”

| Candidato | Tecnologia | Papel real | É ingresso HTTP compartilhado para o ActionFinance? |
|---|---|---|---|
| EC2 `action_hub_prod` `i-07f42e668d62038cd` + EIP `3.17.19.188` | `t3.micro`, SG `action_hub_sg`, VPC PanelDX | Destino A de `actionhub.com.br` / `www` / `api` / `school` — processo **gateway-api** do Hub | **Não.** É o produto Hub. Encaminhar o financeiro por ele misturaria cookies, rotas e o módulo de pagamentos |
| ALB `paneldx-alb` | Application Load Balancer, `us-east-2`, VPC `vpc-017dc4cac16ba2c59`, desde 2025-11-04 | Ingresso HTTPS multi-host: default → `paneldx-frontend-tg`; `/api*` (sem host) → `paneldx-backend-tg`; host `api.demo.panne.ia.br` → `panne-demo-api-tg`; hosts mudaedu → redirect | **Sim.** Este é o gateway HTTP compartilhado da conta |
| HTTP API `spider-sandbox-callbacks` `1lm2s8jf69` | API Gateway v2 | Callbacks da sandbox da Spider | **Não.** Excluído pelo adendo |
| NAT instance / S3 gateway endpoint | saída / VPC endpoint | Não são ingresso de browser | **Não** |
| ALBs `inove4us-prod`, `panne-prod-alb`, `moodle-alb` | ALB dedicados de outros produtos | Path rules próprias; sem host ActionFinance | **Não** reutilizar (misturaria produtos) |

`C:\Projetos\PanelDX` não foi lido (acesso negado). Identificação feita por API AWS já autorizada e docs em `mudaedu/` e `panne/`.

### 8.3 Cabimento da aplicação num ALB compartilhado

A app é SPA+API na mesma origem, OIDC Authorization Code, cookie host-only `AFSESSION`, CSRF, **não** confia em `X-Forwarded-*`. Um ALB como terminador TLS (o que o dedicado já faz) cobre assets, `/api`, redirects, Set-Cookie, health e descoberta IP das tarefas privadas. Timeout idle 60 s no ALB AF (360 s no `paneldx-alb`) é suficiente. Limite de payload do ALB é o adequado; o da HTTP API (10 MB / 30 s) não é necessário.

API Gateway HTTP API + VPC Link/Cloud Map ([docs](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-private.html)) **não** existe para este produto. Criar um novo e ainda deixar o ALB atrás **não** retira o custo do ALB. Expor a tarefa Fargate publicamente para baratear está fora.

### 8.4 Sequência executada (Adendo 002 — autorização “autorizo”)

Fonte: [PRM_007_ADENDO_002](../prompts/ACTIONFINANCE_PRM_007_ADENDO_002_MIGRACAO_ALB.md). O state ActionFinance **não** importa o `paneldx-alb`; só data source + TG/regra/SNI/SG rule próprios.

Prioridades livres abaixo de 10 no listener 443: **3, 4, 6, 7, 8, 9**. Uma regra de host exacto na **prioridade 6** (livre) encaminha todos os caminhos ao mesmo TG. `/api*` prio 10 e default **não** foram alterados.

Ordem real:

1. Registo do estado (digest, DNS, regras, health).
2. Criar `actionfinance-px-tg` (IP, :8091, readiness). SNI do ACM `20d287ca-…`. Regra host `actionfinance.actionhub.com.br` prio 6. Ingress 8091 a partir de `sg-08301fbf0d3dec27e`. ECS com **dois** TGs (controller ECS rolling).
3. Health de ambos os TGs **antes** do DNS.
4. Smoke com `--resolve` + SNI/TLS sem ignorar validação; smokes GET dos hosts legados.
5. Trocar **só** o alias `actionfinance.actionhub.com.br` → `paneldx-alb`. Caminho dedicado manteve-se operacional na janela.
6. Observação (~minutos; alias Route53). Recheck público 200/401/TLS.
7. `retire_dedicated_alb=true`: desassociar TG antigo; plano destrutivo 0 add / 1 change / **4 destroy** (`actionfinance-alb`, listener, `actionfinance-tg`, `actionfinance-alb` SG). Preservados ACM, ECS, RDS, logs, secrets, Cognito, `paneldx-alb`.
8. Exclusão do ALB dedicado ~**2026-09-30T14:55Z**. Cobrança de horas/IPv4 desse ALB cessa após o delete.

### 8.5 Custo indicativo (premissas da §4, não fatura)

| Item | Valor | Natureza |
|---|---|---|
| Horas + 2 IPv4 do ALB dedicado | US$ 23,73/mês | estimativa §4; **deixou de ocorrer** após o delete |
| Reserva ~1 LCU no ALB dedicado | US$ 5,84/mês | estimativa §4, **não** medição de fatura |
| LCU incremental no `paneldx-alb` | ~0 observado neste dia; reserva ~US$ 0–6 | estimativa |
| Restante (Fargate, RDS, secrets, logs, NAT partilhada) | ~US$ 35–45 | estimativa §4 |
| Faixa após migração | **US$ 35–50/mês** + impostos | indicativa, não teto |

### 8.6 Reversão em duas fases

**Fase A — enquanto o ALB dedicado ainda existia:** repor `ingress_alias=dedicated` (só o alias). Não usada; o caminho novo validou.

**Fase B — depois da exclusão (estado actual):** rollback **não** é troca de DNS. É recriar ALB/listener/TG/SG dedicados a partir do IaC (`retire_dedicated_alb=false`, `ingress_alias=dedicated`) e voltar a associar o serviço. O `paneldx-alb` e as regras 1/2/5/10/default não se apagam.

Sem PRM_008. Sem alteração ao módulo de pagamentos do Hub.

## 9. Adendo PRM_009 — jornada pública (01/10/2026)

Pacote concreto: [ACTIONFINANCE_PRM_009_PACOTE_PUBLICACAO](ACTIONFINANCE_PRM_009_PACOTE_PUBLICACAO.md). **Não aplicar** até autorização final.

Reutiliza `paneldx-alb`, ECS/RDS/Cognito do AF, cluster `spider-sandbox` (1 tarefa, memory), CloudFront do Monitor e o EC2 do Hub. Sem ALB dedicado, sem NAT Gateway, sem RDS da Spider, sem alterar apex/`www`/`api`/`school`.

Custo incremental estimado **US$ 0–2/mês** (migrate pontual + NAT já paga). A faixa já contratada do AF **não** é pedida de novo.

Publicação global **continua não declarada**. Invalidação de sessão no restore (PRM_007) **permanece pendente**. Este adendo não a resolve e não recria RDS.
