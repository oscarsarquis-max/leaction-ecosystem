# ACTIONFINANCE_REV_007 — Publicação restrita

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_007 |
| Prompt | [ACTIONFINANCE_PRM_007](../prompts/ACTIONFINANCE_PRM_007.md) |
| Adendo | [AUTORIZACAO](../prompts/ACTIONFINANCE_PRM_007_AUTORIZACAO.md); [ADENDO_001](../prompts/ACTIONFINANCE_PRM_007_ADENDO_001_GATEWAY.md); [ADENDO_002](../prompts/ACTIONFINANCE_PRM_007_ADENDO_002_MIGRACAO_ALB.md); [ADENDO_003](../prompts/ACTIONFINANCE_PRM_007_ADENDO_003_ENCODING.md); [REV ADENDO_001](ACTIONFINANCE_REV_007_ADENDO_001.md); [REV ADENDO_002](ACTIONFINANCE_REV_007_ADENDO_002.md); [REV ADENDO_003](ACTIONFINANCE_REV_007_ADENDO_003.md) |
| Data | 30/09/2026 |
| Executor | Cursor |
| Publicação | **Não declarada.** Login, nome e logout/CSRF autenticados comprovados em 30/09/2026. Restore PITR isolado feito e limpo; invalidação de `SPRING_SESSION` no restaurado **não** comprovada. |
| Aceite | **Não atribuído ao executor.** Sem autoaceite. PRM_008 aberto em ciclo separado (consulta isolada; sem ativação em produção). |

Este relatório não declara o produto em produção pronta.

## Concordância

O proprietário concordou com o plano [DEP_001](../operations/ACTIONFINANCE_DEP_001.md) (“concordo sim…”): conta corporativa, serviço próprio, RDS próprio, Cognito dedicado, estimativa **US$ 65–80/mês + impostos**. Essa aprovação de gasto não foi pedida de novo.

Dados posteriores usados neste ciclo:

- Login do operador: `admin@actionhub.com.br` (identificador, sem caixa postal).
- Contacto/convite/alertas: somente `oscar@oscarsarquis.com.br`.
- Empresa: **Loja de Pães** (nome de exibição; sem CNPJ).
- Papel: OPERATOR nessa empresa; sem ADMIN global.

## URL e acesso

| Item | Estado |
|---|---|
| Destino | `https://actionfinance.actionhub.com.br` |
| TLS | Certificado ACM `20d287ca-cc9c-4efe-8913-b79720b99718`, CN=`actionfinance.actionhub.com.br`, emitido por Amazon RSA 2048 M01. `GET /actuator/health/readiness` → **200** `{"status":"UP"}` sem ignorar TLS |
| SPA / origem | `GET /` → 200 |
| API sem sessão | `GET /api/titles` → **401** (não devolve HTML da SPA) |
| Alias público | A/ALIAS na zona `Z01698931CEOITJ7YYMYX` só para `actionfinance.actionhub.com.br` |
| Nomes preservados | apex, `www`, `api`, `school` continuam presentes; nenhum foi substituído |

A entrada pública está aberta. Operações continuam atrás de OIDC. **Login humano funcional confirmado pelo proprietário em 30/09/2026** (username `admin@actionhub.com.br`; senha/MFA não pedidas neste chat). Essa confirmação **não** prova logout, CSRF autenticado nem restore.

## Recursos efetivamente criados (conta `253137917703` / `us-east-2`)

Reutilizados sem substituição: VPC `vpc-017dc4cac16ba2c59`, subnets privadas `subnet-0a1da7a0765588962` / `subnet-0693afdb3330b683a`, públicas `subnet-04b323e5cea4d7273` / `subnet-01fb021f890fe6e09`, NAT **instance** `i-0bdd19288b5118611`. **Nenhum NAT Gateway** na região.

| Recurso | Identificador |
|---|---|
| State | bucket `actionfinance-tfstate-253137917703`, lock `actionfinance-tf-lock` |
| ECR | `253137917703.dkr.ecr.us-east-2.amazonaws.com/actionfinance` (imutável) |
| ALB | `actionfinance-alb-339693445.us-east-2.elb.amazonaws.com` |
| Target group | `actionfinance-tg` — 1 IP saudável |
| Cluster / serviço | `actionfinance-cluster` / `actionfinance` — desired 1, running 1 |
| RDS | `actionfinance.czqyam2auctn.us-east-2.rds.amazonaws.com:5432`, PG **17.9**, `db.t4g.micro`, privado, `deletion_protection`, retenção 7 dias |
| Cognito | pool `us-east-2_GYIa11WvX`, cliente `275ig9d7lfi0j7if9rqe374rqc`, domínio `actionfinance-253137917703` |
| Secrets | `actionfinance/oidc`, `actionfinance/runtime`, `actionfinance/migrator` (valores não impressos) |
| Logs | `/actionfinance/web`, `/actionfinance/migrate` (30 dias) |

Custo em curso: o desenho do DEP_001 já está contratado (ALB, RDS, Fargate 1 tarefa, Cognito, secrets, logs). Sem desvio material e sem NAT Gateway novo. A estimativa continua **US$ 65–80/mês + impostos**, não teto AWS.

## Imagem

| Artefato | Identificador |
|---|---|
| Digest ECR / local | `sha256:7c4cc0de22350fe0f3e62873d06fca6423cc25946205b4b70756822729da5b65` |
| Tag de rastreio | `prm007-20260930` (identidade da release é o digest) |
| URI do serviço | `253137917703.dkr.ecr.us-east-2.amazonaws.com/actionfinance@sha256:7c4cc0de…da5b65` |
| JAR host | `7b5ae57c05161bb2d130ce415f925dab28300f8fee440cf92810d0a08223aa67` |
| SPA | `index-C7esoAPC.js` / `index-Dd-41bzr.css` |

Tarefa web: Flyway desligado, secret só `runtime`. Tarefa migrate: Flyway V1–V7 aplicados (log `Successfully applied 7 migrations … now at version v7`). Segundo `run-task` confirmou schema já em v7.

## Identidade

Pool **sem** `username_attributes=email` e sem alias de e-mail. Login é o username `admin@actionhub.com.br`. Atributo `email` = `oscar@oscarsarquis.com.br`. `email_verified` **não** foi marcado verdadeiro por admin. MFA do pool: OPTIONAL (TOTP). Recuperação: `verified_email` — só funciona depois da verificação aplicável.

Convite Cognito enviado **apenas** ao contacto autorizado. Nada foi dirigido a `admin@actionhub.com.br` nem a `admin@lojadepaes.com.br`.

`bootstrap-org` dry-run + execução: tenant/empresa `loja-de-paes` / **Loja de Pães**, fuso `America/Sao_Paulo`. O nome de exibição foi gravado com mojibake no *override* ECS do Windows e reparado no Adendo 003 (hex `…c3a36573`; ver [REV_007_ADENDO_003](ACTIONFINANCE_REV_007_ADENDO_003.md)).

| Entidade | UUID |
|---|---|
| Tenant | `4f150085-f5f0-4138-80c3-fcf06db15c3c` |
| Company | `624023a4-57e3-415c-b7d0-925ca1acd3b7` |
| App user (OPERATOR) | `3548715b-d5fc-494a-a3ed-cfbc9b680125` |

Vínculo: issuer Cognito real + `sub` lido por `AdminGetUser` (subject não publicado aqui). Papel **OPERATOR** só nessa empresa. Sem ADMIN global. Sem dados demo copiados.

## Banco

Papéis `actionfinance_migrator` e `actionfinance_runtime` criados no RDS novo (Fargate `postgres:17.6`, política IAM temporária removida). Schema `actionfinance` com owner migrator. Grants V3/V5/V7 no histórico Flyway. Serviço web sem secret migrator e sem DDL.

## Backup / monitoramento / reversão

| Tema | Fato |
|---|---|
| Backup RDS | retenção 7 dias; PITR usado em 30/09/2026 (`UseLatestRestorableTime`; snapshot automático `rds:actionfinance-2026-09-30-13-45` existia e era mais antigo) |
| Restore isolado | Instância `actionfinance-restore-prm007` (privada, cifrada, sem DNS). Flyway V1–V7 e checksums iguais à origem; 1 tenant/empresa/ator/vínculo; auditoria 6; títulos/baixas **0**; owner `actionfinance_migrator`; runtime sem CREATE e sem DELETE em auditoria. Tempo até `available` neste ensaio ≈ **18 min** (não é RTO/RPO). Invalidação de `SPRING_SESSION` no restaurado **falhou** (identificador citado partido no script). Limpeza: instância **inexistente**; origem `available`. Custo transitório ≪ US$ 1 |
| Monitoramento | log groups + Container Insights no cluster; **sem** alarme SNS/e-mail ainda |
| Rollback | `desired_count=0` e, se preciso, `enable_public_dns=false`; preservar RDS/logs/secrets. Não destruir VPC/NAT/DNS alheios |

## Gates da continuidade (30/09/2026)

| Gate | Resultado | Data | Evidência |
|---|---|---|---|
| Login humano | **Passou** (confirmação do proprietário) | 30/09/2026 | Relato do responsável; username `admin@actionhub.com.br` |
| Nome com acentos | **Passou** (Adendo 003 encerrado pelo analista) | 30/09/2026 | Confirmação visual **Loja de Pães**; hex `…c3a36573` |
| Logout/CSRF autenticados | **Passou** | 30/09/2026 17:31 UTC | [`logout-csrf-log.json`](screenshots/prm-007-encerramento/logout-csrf-log.json): `/me` 200, empresa `624023a4-…` só, logout sem CSRF e token inválido 403 com `/me` 200, logout válido `/me` 401; UI sem sucesso na recusa |
| Restore real isolado | **Parcial** | 30/09/2026 | PITR + Flyway + grants + factos 0; sessões no restaurado **não** invalidadas. [`restore-log.json`](screenshots/prm-007-encerramento/restore-log.json) |
| Limpeza do ensaio | **Passou** | 30/09/2026 17:45 UTC | Só RDS `actionfinance` `available`; `actionfinance-restore-prm007` removido |

URL: `https://actionfinance.actionhub.com.br`. Digest em uso: `sha256:7c4cc0de22350fe0f3e62873d06fca6423cc25946205b4b70756822729da5b65`.

## Evidências ainda em falta para aceite final de publicação

1. Invalidação comprovada de `SPRING_SESSION` **num** restore isolado futuro (o ensaio de hoje não a fechou). Não repetir login/ALB/encoding.
2. Alarme com destino `oscar@oscarsarquis.com.br` (autorizado; não disparado).
3. Sujeito sem vínculo recusado — não reensaiado neste retorno.

**Não** está pronto para aceite final de publicação pelo analista: falta o fecho da invalidação de sessões no restore. Aceite **não** atribuído ao executor. Sem PRM_008. Sem integração ActionHub Pay / Spider / Panne.
