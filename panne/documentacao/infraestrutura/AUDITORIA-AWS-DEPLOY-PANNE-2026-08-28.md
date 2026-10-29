# Auditoria AWS — preparação de deploy Panne (somente leitura)

| Campo | Valor |
|---|---|
| Data | 2026-08-28 |
| Conta | `253137917703` |
| Identidade | `arn:aws:iam::253137917703:user/paneldx-user-admin` |
| Região efetiva | `us-east-2` |
| Monorepo referência | `origin/main@142b356` (consolidação Panne `5cc13ba`) |
| Escopo | inspeção; **sem** create/update/delete/restart/deploy |
| CURSOR-027 | **não iniciado** |
| Segredos | **não lidos nem exibidos** (somente nomes/ARNs) |

## Aviso sobre credenciais

A identidade usada pertence ao grupo `paneldx-group-admin` com política **`AdministratorAccess`**. Ou seja: a conta **permite** mutações; esta passagem **optou** por comandos exclusivamente de leitura (`list` / `describe` / `get` / métricas). Não é um principal “read-only” por IAM.

Não foi alterado perfil AWS nem credenciais.

---

## 1. Inventário

### 1.1 Rede — VPC PanelDX

| Item | ID / valor | Prova |
|---|---|---|
| VPC | `vpc-017dc4cac16ba2c59` (`PanelDX-vpc`) | tag Name + `describe-vpcs` |
| CIDR | `10.0.0.0/16` | idem |
| DNS support | habilitado | `describe-vpc-attribute` |
| DNS hostnames | habilitado | idem |
| IGW | `igw-0a169325bcd70e941` (`PanelDX-igw`) | anexado a esta VPC |
| NACL | `acl-0d31013b376043768` (default, allow all) | associada às 4 sub-redes |

**Sub-redes (todas nesta VPC):**

| Nome | Subnet | CIDR | AZ | Papel (rota) |
|---|---|---|---|---|
| PanelDX-subnet-public1-us-east-2a | `subnet-04b323e5cea4d7273` | `10.0.0.0/20` | us-east-2a | pública → IGW |
| PanelDX-subnet-public2-us-east-2b | `subnet-01fb021f890fe6e09` | `10.0.16.0/20` | us-east-2b | pública → IGW |
| PanelDX-subnet-private1-us-east-2a | `subnet-0a1da7a0765588962` | `10.0.128.0/20` | us-east-2a | privada → NAT instance |
| PanelDX-subnet-private2-us-east-2b | `subnet-0693afdb3330b683a` | `10.0.144.0/20` | us-east-2b | privada → NAT instance |

`MapPublicIpOnLaunch=false` nas quatro; IPs públicos existem onde atribuídos explicitamente (NAT, bastion, etc.).

**Outra VPC na conta:** `vpc-0e05974106395b2b4` (`172.31.0.0/16`, default) — Academy/Moodle/Chamelleon. **Não** é a VPC do PanelDX/RDS alvo.

### 1.2 PanelDX-NAT-Instance

| Campo | Valor |
|---|---|
| Instance ID | `i-0bdd19288b5118611` |
| Nome | `PanelDX-NAT-Instance` |
| Tipo | `t3.nano` |
| AMI | `ami-06f1fc9ae5ae7f31e` — Amazon Linux 2023 (x86_64) |
| Estado / checks | `running`; instance/system/EBS reachability **ok** |
| VPC / subnet / AZ | `vpc-017dc4cac16ba2c59` / `subnet-04b323e5cea4d7273` / `us-east-2a` |
| IP privado | `10.0.4.159` |
| Elastic IP | `3.143.92.115` (`eipalloc-0683f6912231584bc`) |
| Source/dest check | **desabilitado** (adequado a NAT) |
| SG | `sg-0acf4c4b3dde5cbae` (`launch-wizard-1`) |
| IAM instance profile | nenhum |
| Monitoring detalhado | desabilitado |
| Proteção terminação API | desabilitada |
| Alarmes CloudWatch nomeados NAT/PanelDX | nenhum encontrado |

**Rotas que apontam para a NAT:**

- `rtb-086fc0be189ac78f9` (private1 / `subnet-0a1da7a0765588962`) → `0.0.0.0/0` → `i-0bdd19288b5118611`
- `rtb-00cdb8f28801964ad` (private2 / `subnet-0693afdb3330b683a`) → `0.0.0.0/0` → `i-0bdd19288b5118611`

**SG ingress (resumo):** all protocols from `10.0.0.0/16`; TCP/22 from `0.0.0.0/0`. Egress: all → `0.0.0.0/0`.

**Métricas ~3 dias (leitura):**

- CPU: máximos horários ≈ **0,2%–0,5%** (ociosa)
- NetworkOut diário ≈ **120–700 MB/dia** (ordem de grandeza baixa)

Encaminhamento iptables/nft **não** foi inspecionado (exigiria sessão interativa — fora do escopo).

### 1.3 ECS / Fargate (cluster PanelDX)

**Cluster:** `paneldx-cluster` (também existe `inove4us-prod`, fora do escopo Panne).

| Serviço | Desired/Running | Task def | Subnets | IP público | SG |
|---|---|---|---|---|---|
| `paneldx-backend-service` | 1/1 | `paneldx-backend-task:87` | privadas 2a+2b | DISABLED | `sg-0b8d724a5cc3b8c4e` |
| `paneldx-frontend-service` | 1/1 | `paneldx-frontend-task:117` | privadas 2a+2b | DISABLED | idem |
| `leactionf-ai-worker-service` | 1/1 | `leactionf-ai-processor-task:74` | mistas (priv+públ) | ENABLED | — |
| `calc-microservice-service` | 0/0 | `calc-microservice-task:50` | mistas | ENABLED | — |

**Backend task (padrão reutilizável):**

- Fargate, `awsvpc`, CPU **512** / mem **1024**
- Imagem ECR `paneldx-backend` (tag versionada)
- Porta **5000**; log group `/ecs/paneldx-backend-task`
- Secrets (somente nomes/ARN): `DB_USERNAME` / `DB_PASSWORD` ← `paneldx-db-credentials-…`
- Env (nomes apenas): `DB_HOST`, `DB_PORT`, `DB_SSLMODE`, hub/SMTP, etc. — **não** listar valores

**Frontend PanelDX atual:** também Fargate (CPU 256 / mem 512), **não** S3/CloudFront. Isso diverge do alvo Panne (frontend estático).

**ALB `paneldx-alb`:**

- internet-facing, VPC PanelDX, AZs 2a+2b
- :80 → redirect; :443 HTTPS com ACM `paneldx.com.br`
- Regras: `/api*` → `paneldx-backend-tg`; default → `paneldx-frontend-tg`; redirects mudaedu
- Health: backend `/health`; frontend `/`

**SG tarefas `paneldx-fargate-sg`:** ingress 5000 e 3001 de `0.0.0.0/0` (alvo real é ALB; regra ampla).

### 1.4 DNS / certificados / estático

| Item | Estado |
|---|---|
| Hosted zone `panne.ia.br` | `Z0036120YQCHVOKHX8H7` (pública) |
| Registros | apenas **NS** + **SOA** (sem A/AAAA/CNAME/ALIAS de app) |
| ACM `us-east-2` | paneldx, leactiona, inove4us, mudaedu — **sem** `panne.ia.br` |
| ACM `us-east-1` | nenhum certificado `panne` / `ia.br` listado |
| CloudFront | quantidade de distributions = **0** (nenhuma distribuição na conta, nesta consulta) |
| S3 relevante | `paneldx-cms-assets-2026` (CMS PanelDX); **sem** bucket Panne dedicado |
| ECR | sem repositório `panne*` hoje |

Sugestão de hostnames (não criados):

- produção: `panne.ia.br` (+ opcional `www`)
- demo: `demo.panne.ia.br` (ou `homolog.panne.ia.br`)

### 1.5 RDS `paneldx-database`

| Campo | Valor |
|---|---|
| Engine | PostgreSQL **17.9** |
| Classe | `db.t3.micro` |
| Status | available |
| Storage | 20 GB **gp2**, autoscaling até 1000 GB |
| Free storage (~3d) | ≈ **17–18 GB** livres |
| Multi-AZ | **não** |
| PubliclyAccessible | **sim** (risco; mitigação parcial via SG) |
| VPC | `vpc-017dc4cac16ba2c59` (mesma do PanelDX) |
| Subnet group | `default-vpc-017dc4cac16ba2c59` (inclui subnets públicas e privadas) |
| AZ primária | us-east-2a |
| Criptografia | sim (KMS gerenciado/conta) |
| Backup retention | **1 dia**; janela `05:10–05:40` UTC |
| Performance Insights | sim (retenção 7d) |
| Enhanced Monitoring | off (intervalo 0) |
| Endpoint (sanitizado) | `paneldx-database.****.us-east-2.rds.amazonaws.com:5432` |
| Param group | `default.postgres17` |

**SG `paneldx-db-sg`:** TCP 5432 a partir de:

- `sg-0b8d724a5cc3b8c4e` (`paneldx-fargate-sg`)
- `sg-030b0217eee978745` (`paneldx-bastion-sg`)
- `sg-08a0721444e6176b3` (`action_hub_sg`)
- e CIDR `10.0.2.103/32` (host MAtivas na mesma VPC)

**Métricas ~3 dias:**

- CPU máx. horária ≈ **7%**
- Conexões máx. ≈ **6–7**
- FreeableMemory mín. diária ≈ **130–150 MB** (classe com ~1 GB RAM — folga limitada)

**Limite aproximado de conexões:** em `db.t3.micro` Postgres, tipicamente da ordem de **~80–100** (fórmula AWS por memória). Hoje o uso observado é baixo, mas o teto é compartilhado entre todos os consumidores do instance.

**Databases / roles:** **não enumerados**. Listar exigiria autenticar no Postgres (uso de segredo). Sem `get-secret-value` e sem conexão administrativa nesta passagem.

**Secrets Manager:** existe `paneldx-db-credentials` (ARN `…:secret:paneldx-db-credentials-…`). Nenhum segredo `panne*` listado.

---

## 2. Diagrama textual (IDs comprovados)

### Caminho de entrada (padrão PanelDX atual; Panne API pode espelhar)

```
Internet
  → ALB paneldx-alb (vpc-017dc4cac16ba2c59, internet-facing)
  → Target Group (IP mode)
  → Fargate tasks nas subnets privadas
       subnet-0a1da7a0765588962 (2a) + subnet-0693afdb3330b683a (2b)
  → RDS paneldx-database (mesmo vpc-017dc4cac16ba2c59, porta 5432 via SG)
```

### Saída à Internet das tarefas privadas

```
Fargate (subnets privadas)
  → rota 0.0.0.0/0 nas route tables privadas
  → ENI/instance i-0bdd19288b5118611 (PanelDX-NAT-Instance, SrcDestCheck=false)
  → EIP 3.143.92.115 → Internet
```

### Frontend Panne desejado (ainda inexistente)

```
Internet → CloudFront (a criar) → S3 (a criar)
API: Internet → (ALB novo ou host-header no ALB existente) → Fargate Panne → RDS
```

**Prova de mesma VPC:** ECS subnets, ALB, NAT, RDS subnet group e VPC IDs coincidem em `vpc-017dc4cac16ba2c59`. A VPC `vpc-0e05974106395b2b4` é outra topologia.

---

## 3. Recursos reutilizáveis

- VPC PanelDX + subnets públicas/privadas + IGW + NAT instance (egress)
- Cluster ECS `paneldx-cluster` (padrão Fargate privado)
- Padrão ALB + target group IP + awslogs
- ECR na região (criar repos Panne no mesmo registry)
- Instância RDS Postgres 17 (capacidade e isolamento lógico a decidir)
- Hosted zone `panne.ia.br` (DNS raiz já na conta)
- Papel conceitual Secrets Manager (criar segredos **novos** para Panne)

---

## 4. Recursos que precisam ser criados (proposta; não executado)

| Área | Demo | Produção |
|---|---|---|
| ACM | certificado `demo.panne.ia.br` (+ SAN) | certificado `panne.ia.br` / `www` |
| DNS | registros demo | registros produção |
| Frontend | S3 + CloudFront (ou padrão escolhido) | S3 + CloudFront |
| API | serviço ECS + task def + TG | serviço ECS + task def + TG |
| ALB | host-header no ALB existente **ou** ALB dedicado | idem |
| SG | SG de tarefas Panne demo | SG de tarefas Panne prod |
| RDS lógico | DB `panne_demo` + role exclusiva | DB `panne` + role exclusiva |
| Secrets | segredo demo | segredo produção |
| ECR | `panne-api` (e artefatos FE se aplicável) | mesmo repo, tags distintas |
| Logs | log groups `/ecs/panne-*-demo` | `/ecs/panne-*-prod` |

**Não reutilizar:** segredo `paneldx-db-credentials`, SG único compartilhado sem segmentação, task definitions PanelDX, bucket CMS PanelDX como origem do FE Panne.

---

## 5. Riscos

| Risco | Severidade | Nota |
|---|---|---|
| NAT instance **SPO F** (`t3.nano`, 1 AZ, sem Multi-AZ NAT GW) | Alta p/ disponibilidade | CPU ociosa hoje; falha derruba egress de **todas** as tasks privadas |
| SSH `0.0.0.0/0` na NAT | Alta (superfície) | SG `launch-wizard-1` |
| RDS `PubliclyAccessible=true` | Alta | Mesmo com SG restritivo |
| Backup retention **1 dia** | Alta p/ recuperação | Pouca folga PITR |
| Single-AZ RDS | Alta | Sem failover automático |
| Memória RDS ~150 MB livres | Média | Contenção se PanelDX + Panne + Hub crescerem |
| Mesmo instance RDS = blast radius compartilhado | Alta p/ isolamento | CPU/conexões/storage/manutenção afetam todos os DBs |
| ALB PanelDX com regras de outros produtos | Média | Host-headers Panne precisam disciplina |
| IAM de auditoria = AdministratorAccess | Processo | Risco operacional se scripts mutantes forem rodados por engano |
| Sem CloudFront hoje | — | FE estático Panne é greenfield |
| Sem certificado ACM para `panne.ia.br` | Bloqueio deploy HTTPS | Precisa emissão (validação DNS) |
| Extensão `unaccent` | Média | Migração Alembic `0006` exige `CREATE EXTENSION unaccent` (suportável em RDS com privilégio adequado) |

---

## 6. Custos estimados (incrementais, ordem de grandeza us-east-2)

Valores aproximados em USD/mês para carga baixa; sem Savings Plans/reservas.

| Item | Estimativa |
|---|---|---|
| 2× API Fargate ~0.25–0.5 vCPU / 0.5–1 GB (demo+prod, 1 task cada) | ~US$ 25–60 |
| ALB **novo** dedicado | ~US$ 16+ + LCU |
| ALB **existente** (só host-header/LCU extra) | baixo (poucos dólares) se tráfego pequeno |
| CloudFront + S3 (2 origins/sites leves) | tipicamente **&lt; US$ 5** em tráfego baixo |
| CloudWatch logs (2–4 log groups) | US$ 1–10 conforme retenção/volume |
| Tráfego via NAT instance | instance já paga (~t3.nano); egress incremental + data transfer |
| RDS existente (sem upgrade de classe) | custo de storage/IO marginal; **risco** de precisar `db.t3.small+` |
| Secrets Manager (2–4 segredos) | ~US$ 0,40 × N / mês |
| ECR (imagens Panne) | ~US$ 0,10/GB-mês armazenado |

**Qualitativo:** o maior custo *fixo* novo é Fargate (+ ALB se dedicado). O maior custo *de risco* é upgrade forçado do RDS e/ou substituição da NAT por NAT Gateway (bem mais caro, mais resiliente).

---

## 7. Requisitos de segurança (mínimos recomendados)

1. Segredos **distintos** demo vs prod; nunca reutilizar `paneldx-db-credentials`.
2. Roles Postgres sem privilégio sobre DBs alheios; sem uso da master nas apps.
3. TLS obrigatório app→RDS (`sslmode` verify/require conforme padrão Panne).
4. SG de tarefas Panne: ingress **somente** do ALB (SG do ALB), não `0.0.0.0/0` nas portas de app.
5. SG do RDS: liberar 5432 apenas aos SGs Panne (+ bastion se necessário); não abrir à Internet.
6. Preferir `PubliclyAccessible=false` no RDS (mudança futura — fora desta auditoria).
7. Frontend estático: bucket privado + OAC CloudFront; sem listing público.
8. IAM task roles mínimos; execution role só para pull ECR + secrets nomeados.
9. Isolar log groups e métricas por ambiente.
10. Restringir SSH da NAT (remover `0.0.0.0/0`) — decisão do proprietário.

---

## 8. Proposta separada Demo × Produção (não implementada)

| Dimensão | Produção | Demo |
|---|---|---|
| Hostname | `panne.ia.br` | `demo.panne.ia.br` (sugestão) |
| Serviço ECS | `panne-api-prod` | `panne-api-demo` |
| Task def / imagem tag | `prod-*` | `demo-*` |
| Database | `panne` | `panne_demo` |
| DB user | role exclusiva prod | role exclusiva demo |
| Secret | `panne/prod/db` (nome a definir) | `panne/demo/db` |
| SG tarefas | `panne-prod-fargate-sg` | `panne-demo-fargate-sg` |
| Config | `PANNE_ENV=production` (ou equivalente) | `PANNE_ENV=demo` + âncora |
| FE | distribuição CF/S3 prod | distribuição CF/S3 demo |
| Dados | reais / clientes | seed determinístico; sem misturar |

### Limitações PostgreSQL/RDS ao isolamento

- **PITR / restore** atua na **instância** inteira — não restaura só `panne_demo` sem afetar os demais DBs no mesmo host (restore cria nova instância).
- Falha de classe, storage full, manutenção e reboot impactam PanelDX + Panne + outros consumidores.
- `max_connections`, CPU e RAM são **compartilhados**.
- Isolamento forte de falha exigiria instância RDS separada (custo maior) ou ao menos Multi-AZ + retenção de backup maior.
- Isolamento lógico (DB+role+secret+SG) é **adequado para segurança de acesso**, insuficiente para blast radius de infraestrutura.

---

## 9. Plano de rollback (conceitual, pós-decisão)

1. Remover regras de listener/host-header Panne no ALB (ou desativar serviço ECS desired=0).
2. Remover/desassociar registros DNS Panne.
3. Desabilitar distribuições CloudFront Panne.
4. Revogar SG do RDS para SGs Panne.
5. Rotacionar/invalidar segredos Panne (sem tocar no segredo PanelDX).
6. Manter DBs lógicos até confirmação; dropar só com autorização explícita.
7. Não reverter mudanças PanelDX existentes nesta preparação.

---

## 10. Decisões que dependem do proprietário / Cortex

1. **Compartilhar** ALB `paneldx-alb` (host-header) vs **ALB dedicado** Panne?
2. Frontend: confirmar **S3+CloudFront** (alvo) vs Fargate como PanelDX?
3. RDS: hospedar `panne`/`panne_demo` em **`paneldx-database`** vs instância nova?
4. Aceitar SPOF da **NAT instance t3.nano** ou migrar para NAT Gateway / NAT HA?
5. Hostnames finais demo (`demo.panne.ia.br`?) e emissão ACM (região ALB `us-east-2` + `us-east-1` se CloudFront).
6. Endurecer RDS (`PubliclyAccessible=false`, backup &gt; 1 dia, Multi-AZ)?
7. Restringir SSH da NAT e renomear SG `launch-wizard-1`?
8. Orçamento mensal-alvo e se demo pode ficar desired=0 fora de janelas?
9. Autorização formal para iniciar implementação (CURSOR-027 ou ciclo de deploy separado)?

---

## 11. Compatibilidade Panne (código × infra)

| Tema | Avaliação |
|---|---|
| Postgres 17.9 | Compatível com stack async SQLAlchemy/Alembic atual |
| Extensão `unaccent` | Exigida pela migração `0006_knowledge_grounding`; disponível no catálogo RDS com privilégio de criação de extensão |
| TSVECTOR / FTS | Nativo; ok |
| Duas URLs DB (runtime vs admin) | Modelo local já separa `database_url` / `runtime_database_url` — alinha a roles distintas |
| FE estático Vite | Adequado a S3+CloudFront; build já validado na consolidação 026 |
| Health | API expõe `/health` e `/ready` — alinhável a TG |
| Isolamento demo/prod | Exige config/serviço/secret/DB distintos — **não** existe ainda na AWS |

---

## 12. Confirmações desta passagem

- Nenhuma alteração criada/alterada/reiniciada/escalada/associada/desassociada/apagada na AWS por esta auditoria.
- Nenhum segredo, senha, token ou connection string exibido.
- Nenhum commit/push.
- CURSOR-027 não iniciado.
- Deploy não executado.

---

*Fim da auditoria. Aguardar decisão do Cortex/proprietário.*
