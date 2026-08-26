# QMind — Gate de prontidão para homologação

- Status: **LIBERADO PARA PILOTO** (observação 7d em paralelo; produção ampla **não** autorizada)
- Aberto: 2026-08-03 · Lightsail: 2026-08-04 · Baseline observação: 2026-08-04
- Baseline produto: tag **`mvp-fullstack-v0`**
- Região: **AWS `us-east-2`**
- Domínio zona: **`qmind.com.br`** (Route 53)
  - **Piloto:** `https://qmind.com.br` + `https://api.qmind.com.br` (+ `www` → apex)
  - **Testes:** `*.homolog.qmind.com.br` (exclusivo)
- Forma: **Lightsail** + Compose + Caddy + Postgres no host + S3 + Cognito (**ADR-010**)
- Forma futura: `infra/terraform-enterprise/` (ECS/ALB/RDS) — **não apply**
- Produto: `012` + ADR-011; descoberta/piloto: `013`

## 0. Decisão atual (2026-08-04)

| Dimensão | Estado |
|---|---|
| Homologação funcional | **Aprovada** |
| Homologação técnica | **Aprovada** |
| Piloto controlado | **Ativo no domínio principal** |
| Observação de sete dias | **Monitoramento pós-liberação** — **não bloqueante** |
| Produção ampla | **Não autorizada** |

Acesso do piloto: https://qmind.com.br/ (API https://api.qmind.com.br)  
Homolog (testes): https://app.homolog.qmind.com.br/  
Ativação: `infra/terraform-lightsail/PILOT_DOMAIN_20260804.md`  
Observação: `infra/terraform-lightsail/OBSERVATION_7D_20260804.md`  
Fechamento definitivo do gate 011: ao completar 7 dias sem gatilho crítico aberto (ou dispensa formal).

## 1. Política de baseline

| Regra | Detalhe |
|---|---|
| Baseline | `mvp-fullstack-v0` recuperável |
| Perfil TF | só `infra/terraform-lightsail/` |
| Auth / storage | Cognito + S3 reais; sem `AUTH_MODE=dev` / `STORAGE_BACKEND=memory` |
| DB | migrações admin; runtime `qmind_app` |
| Budget | `qmind-homolog-monthly-30` (US$ 30) |
| Piloto | poucos usuários; orgs fictícias / dados não sensíveis; limite de evidências |

## 2. Checklist — provisionamento

| # | Critério | Evidência | Resultado |
|---|---|---|---|
| H0 | Budget US$ 30 + alertas e-mail | Budget `qmind-homolog-monthly-30` → gestao@leaction.com.br | **PASS** |
| H1 | Tags / isolamento homolog | `Project=qmind` `Environment=homolog` `Profile=lightsail` | **PASS** |
| H2 | DNS homolog + piloto | `*.homolog` + apex/`www`/`api.qmind.com.br` → `3.20.155.196` | **PASS** |
| H3 | Imagens tagadas | tag git imutável no deploy | PENDENTE (não bloqueia piloto) |
| H4 | Lightsail Ubuntu + IP estático | `qmind-homolog-app`; só 80/443; SSH fechado | **PASS** |
| H5 | Postgres Compose sem porta pública | + `pg_dump` → S3 | **PASS** |
| H6 | S3 evidências | privado BPA + versioning | **PASS** |
| H7 | Cognito | pool `us-east-2_ewD6ck5PM`; `deletion_protection=ACTIVE` | **PASS** |
| H8 | Credenciais split + 0600 | keys só em `/opt/qmind/secrets/*.env` | **PASS** |
| H9 | HTTPS Caddy / Let's Encrypt | homolog + piloto (apex/api/www) | **PASS** |
| H10 | Snapshot + alarmes | AutoSnapshot; LS alarms; backup CW **OK** | **PASS** |
| H11 | S3 backups isolados | bucket privado + policy deny delete servidor | **PASS** |
| H12 | Backup operacional | cron + restore V2 testado | **PASS** |

**Fora de escopo desta fase:** ALB, ECS, RDS, NAT, API Gateway, ACM servidor, autoscaling, VPC complexa, produção ampla (apex piloto ≠ produção).

## 3. Migrações e seeds

| # | Critério | Resultado |
|---|---|---|
| M1–M3 | Admin migrate/seed; runtime só `qmind_app` | **PASS** |
| M4 | `migrate-and-seed-homolog.ps1` / exec no host | **PASS** |

## 4. Validação

| # | Critério | Resultado |
|---|---|---|
| V1 | FORCE RLS | **PASS** |
| V2 | Snapshot Lightsail + restore `pg_dump` | **PASS** — `RESTORE_V2_20260804T124851Z.md` |
| V3 | HTTPS/CORS em homolog.qmind.com.br | **PASS** |
| V3b | HTTPS/CORS no domínio piloto | **PASS** — `PILOT_DOMAIN_20260804.md` |
| V4 | Cognito E2E | **PASS** — `COGNITO_E2E_V4_20260804.md` |
| V4b | Cognito E2E no domínio piloto | **PASS** — `PILOT_COGNITO_E2E_evidence.json` |
| V5 | Isolamento 2 orgs | **PASS** — `ISOLATION_S3_V5V6_20260804.md` |
| V6 | S3 evidências reais | **PASS** — mesmo artefato V5/V6 |
| V6b | Isolamento + S3 no domínio piloto | **PASS** — `PILOT_ISOLATION_S3_evidence.json` |
| V7 | Jornada completa | **PASS** — `JOURNEY_V7_20260804.md` |
| V7b | Worker PDF real | **PASS** — `WORKER_PDF_V7b_20260804.md` |
| V7c | Worker PDF no domínio piloto | **PASS** — `PILOT_WORKER_PDF_evidence.json` |
| V8 | Observabilidade/custo 7 dias | **EM ANDAMENTO** (pós-liberação; não bloqueia piloto) — `OBSERVATION_7D_20260804.md` |
| V9 | ISOI-009 Execution Intelligence R1 | **IMPLEMENTADO LOCALMENTE, AGUARDA HOMOLOGAÇÃO** — refs por campo compartilhadas Core/OI; `is_terminal`, `claims_execution`, `baseline_status`; idempotência vinculada ao snapshot; histórico integral na Evolução |

## 5. Piloto controlado (autorizado)

Alinha a `013_Discovery_and_Pilot_Plan.md`, com restrições operacionais:

- Poucos usuários **convidados** (Cognito `allow_admin_create_user_only`); organizações fictícias ou dados **não sensíveis**
- Limite claro de volume/tamanho de evidências
- Sem dados reais de cliente de produção / PII desnecessário
- Sem conteúdo normativo sem licença
- Piloto: `qmind.com.br` / `api.qmind.com.br`; testes: `*.homolog.qmind.com.br`
- Canal único de incidentes; respeitar gatilhos de interrupção (abaixo)

## 6. Observação 7 dias (paralela)

| Item | Valor |
|---|---|
| Início | 2026-08-04 (baseline dia 0) |
| Fim previsto | 2026-08-11 |
| Scripts | `observe-homolog-host.sh` (cron host) + `observe-homolog-daily.ps1` |
| Artefatos | `infra/terraform-lightsail/observe/` |

### Gatilhos de interrupção do piloto

- Backup ausente ou restauração comprometida  
- Isolamento entre organizações violado  
- Exposição de segredo ou evidência  
- Custo projetado do QMind acima de **US$ 30/mês**  
- Disco acima de **80%**  
- Indisponibilidade recorrente  
- Jobs presos ou crescimento contínuo da fila  

Detalhamento: `OBSERVATION_7D_20260804.md`.

## 7. Ordem de execução

```
1–10. Provision + E2E + worker PDF     ← feito (V2–V7b PASS)
11. Baseline observação 7d + cron      ← aberto (paralelo ao piloto)
12. Piloto no domínio principal        ← ativo (qmind.com.br)
13. Fechar gate 011 após 7d            ← pendente
14. Produção ampla                     ← NÃO autorizada
```

Runbook: `../../infra/terraform-lightsail/PROVISIONING_RUNBOOK.md`.

## 8. Ambiente / artefatos

| Item | Valor |
|---|---|
| TF ativo | `qmind/infra/terraform-lightsail/` |
| Hosts | `api.homolog.qmind.com.br`, `app.homolog.qmind.com.br` |
| Zone | `Z10252021E8KYKLG3TEOS` |
| Bundle | `small_3_0` |
| Budget | US$ 30 / gestao@leaction.com.br |
| Conta | `253137917703` |
| IP | `3.20.155.196` |

## 9. Veredito

**Homologação funcional e técnica aprovadas. Piloto controlado autorizado.**  
Observação de sete dias corre **em paralelo** como monitoramento pós-liberação.  
**Produção ampla não autorizada** até fechar V8 e decisão explícita de go-live.
