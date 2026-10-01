# SPIDER-AWS-SANDBOX-001 — Sandbox AWS

Classificação atual (28/09/2026): **SANDBOX DEMONSTRÁVEL**. Não é `PRODUCTION`, `READY_FOR_PRODUCTION` nem `READY_FOR_PILOT`.

| Campo | Valor |
|---|---|
| Conta | `253137917703` (IAM user `paneldx-user-admin`, grupo com AdministratorAccess; sem alias) |
| Autenticação | AWS CLI perfil `default`, região default `us-east-2` |
| Região corporativa observada | `us-east-2` (ECS/ALB/RDS de Inove, PanelDX, Panne, **RDS `actionhub-prod`**) |
| Região da Spider | `us-east-2` (compute/ALB/API/DNS ops); certificados CloudFront em `us-east-1` |
| Parecer / produção | Não concedida |

## 0. Conclusão operacional (28/09/2026)

### Estado anterior (mesmo dia, antes desta execução)

| Recurso | Antes |
|---|---|
| WAF Monitor | default `BLOCK`, rules `[]` |
| Bucket `spider-sandbox-monitor-web` | vazio |
| ECR `spider-sandbox-backend` | sem imagens |
| ECS `spider-sandbox-backend` | desired=0, running=0, task def `:1` |
| Target group | nenhum target |
| API | HTTP 503 |
| Allowlist | vazia |

### Estado final

| Recurso | Depois |
|---|---|
| WAF Monitor | default `BLOCK` + regra `allow-sandbox-origins` (IP set IPv4 `/32` do operador) |
| WAF API regional | default `BLOCK` + a mesma allowlist |
| ALB SG :443 | somente CIDRs da allowlist (sem `0.0.0.0/0`) |
| CloudFront | IPv6 desligado; cache curto em HTML; `/assets/*` longo; 403 do WAF permanece 403 |
| Bucket | build do Monitor publicado; block public access intacto; OAC intacto |
| ECR | tag imutável `sandbox-20260928-7177805b2` |
| Digest | `sha256:0b5976c2488e26b3a690bcc3540e8bd7cd893600229d1ec4b9aa40c272f0830c` |
| Task definition | `spider-sandbox-backend:5` (anterior demonstrável: `:4`) |
| ECS | desired=1, running=1 |
| Target group | 1 target `healthy` |
| API | HTTPS 200 em health/readiness; sem 503 |
| Persistência | `memory` (RDS/JPA/Flyway desligados) |
| Callbacks | fora de operação |

### Allowlist do operador

- Variáveis Terraform: `sandbox_allowed_ipv4_cidrs`, `sandbox_allowed_ipv6_cidrs` (defaults vazios).
- CIDR IPv4 `/32` do operador: arquivo local gitignored `spider/infra/aws/environments/sandbox/operator-allowlist.auto.tfvars`.
- Documentação pública: último octeto vigente `.77`, máscara `/32`. Histórico: `.16` → `.92` → `.77`. Não repetir o endereço completo.
- IPv6: vazio (CloudFront IPv6 desligado para a allowlist IPv4 ser efetiva).
- WAF default continua `BLOCK`. Métricas e logs em `aws-waf-logs-spider-sandbox-monitor` (headers `authorization`, `cookie`, `x-spider-credential-ref` redigidos).

**Troca de IP:** obter o IPv4 público de saída, gravar `x.x.x.x/32` em `operator-allowlist.auto.tfvars`, `terraform apply` **somente com `-target` nos IP sets e no SG do ALB** no state `spider/sandbox`. Um `plan` sem target ainda mostra drift da task definition ECS (`:5` live vs imagem antiga no state) — **não aplicar** esse drift. Sem abrir `0.0.0.0/0`.

### Frontend

- Origem: `spider/frontend` (Monitor / Simulação / Documentação).
- Versão: `spider-frontend@0.1.0`; bundle `assets/index-w3T1Q3kp.js` + `assets/index-BF2rwSPw.css` (correção visual 28/09/2026).
- `VITE_SPIDER_API_BASE=https://api.spider.actionhub.com.br`.
- Identificador de allowlist `sandbox-operator` (não é o JWT; JWT só no Secrets Manager).
- Build sem `localhost` / `127.0.0.1` / portas locais.

### Execução canônica demonstrada

| Campo | Valor |
|---|---|
| Horário (UTC) | 2026-09-28T17:36:20Z |
| Endpoint | `POST https://api.spider.actionhub.com.br/v1/canonical/executions` |
| HTTP | 200 |
| executionId | `exec-sandbox-demo-20260928-r2` |
| Origem | `console-sandbox` / `operational-console` |
| Rota | `demo-success_multi_step@1.0.0` (única rota sandbox, mock isolado) |
| correlationId | `corr-sandbox-demo-20260928-r2` |
| traceparent | `00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01` |
| Estado final | `SUCCEEDED` (2 steps) |
| Evidências | `ev-63e8c291-e11f-4166-9f99-6adee0a8482f`, `ev-a809a7bf-b25d-431d-88ac-782be72742cd` |
| Monitor | a mesma identidade em `GET /v1/console/executions` e detalhe/percurso |
| CloudWatch | `/spider/sandbox/backend` — `submission_accepted` e `ALL_STEPS_SUCCEEDED` com o mesmo `executionId` e `traceparent` |

Não é jornada de satélite. Satélites permanecem indisponíveis neste sandbox.

A execução `r2` existia só na memória da task `:4`. A correção do backend publicou a task `:5` e exigiu uma execução equivalente `exec-sandbox-demo-20260928-r3` (mesmo contrato, rota e origem).

## 0.1 Correção visual do Monitor publicado (28/09/2026)

Classificação após a correção: **SANDBOX DEMONSTRÁVEL**. A apresentação deixa de ser `PARTIAL` nos dois defeitos comprovados.

### Sintomas

1. Banner persistente `Unexpected orchestration error` acima de “Transação selecionada”.
2. Duas etapas consecutivas com o mesmo título `Interaction #1`, ambas `SUCCEEDED`.

O console do navegador não tinha erro JavaScript. A execução `exec-sandbox-demo-20260928-r2` carregava definição, execução e evidências.

### Causa raiz do banner

`TransactionWorkspace` consulta `GET /v1/context/executions/{id}` em toda transação canônica. No profile `sandbox`, `spider.context.enabled=false` e o controller de contexto não é registrado. O WebFlux emitia `404 No static resource`, mas o `GlobalExceptionHandler` genérico convertia essa ausência em HTTP 500 com título `Unexpected orchestration error`. O frontend trata 404 de contexto como ausência; 500 virava banner de orquestração sobre uma execução `SUCCEEDED`.

`GET /v1/console/executions`, detalhe, `/events` e `/monitor/events` já respondiam 200.

### Natureza das duas “Interaction #1”

Caso A — passos diferentes e legítimos. O plano `demo-success_multi_step@1.0.0` tem `step-1` (ordem 0) e `step-2` (ordem 1). Cada um tem `attemptNumber=1`. A projeção usava `Interaction #${attemptNumber}` como identidade visual, então os dois passos apareciam iguais. Não era duplicata da mesma tentativa.

### Arquivos corrigidos

- `spider/backend/src/main/java/br/com/banco/spider/web/controller/GlobalExceptionHandler.java` — `NoResourceFoundException` / `ResponseStatusException` preservam o status original (404 não vira 500).
- `spider/frontend/src/console/projectExecutionJourney.js` — título funcional do passo + tentativa; identidade estável `stepRef::attemptNumber::attemptId`.
- `spider/frontend/src/console/projectJourneyStepDetail.js` — detalhe com nome, posição, tentativa, correlação.
- `spider/frontend/src/console/api.js` — mensagem de erro em português com a operação que falhou.
- `spider/frontend/src/console/ExecutionJourney.jsx`, `TransactionWorkspace.jsx`, `MonitorShell.jsx` — falha de eventos relacionados só na seção correspondente.
- Testes: `SandboxCanonicalHttpAccessTest`, `MonitorSandboxPresentation.test.jsx`, `api.test.js`, projeções/jornada.

### Testes

- Frontend: 189 testes, lint limpo, build sem `localhost`/`127.0.0.1`.
- Backend: `SandboxCanonicalHttpAccessTest` (contexto 404, detalhe multi-step com dois `stepRef`, eventos 200, estado da execução inalterado, sem dado protegido).

### Versões publicadas

| Peça | Valor |
|---|---|
| Frontend | `assets/index-w3T1Q3kp.js` (etag `48d3145befb2377ce0b496386b18129d`) + `assets/index-BF2rwSPw.css` |
| Invalidação CloudFront | `ILLOS7JXZACTHZ3KEJ9QL8FCW` em `E2E4ORTD4DHI1D` |
| Imagem | `sandbox-20260928-monitorfix` |
| Digest | `sha256:72ed3a8c70121d3c169ac984afce8add2e0ee962f9650ce51b33fe62f9b9f4a1` |
| Task definition | `spider-sandbox-backend:5` |
| ECS | desired=1, running=1 |
| Target group | 1/1 `healthy` |
| Persistência | `memory` |
| Execução de prova | `exec-sandbox-demo-20260928-r3` / `corr-sandbox-demo-20260928-r3` / `SUCCEEDED` |

### Validação visual

Roteiro em `https://monitor.spider.actionhub.com.br` com origem autorizada, sem cache antigo. Playwright: `spider/frontend/scripts/capture-sandbox-monitor-fix.mjs`.

Capturas em `spider/docs/operations/screenshots/sandbox-monitor-fix-20260928/`:

| Arquivo | Conteúdo |
|---|---|
| `01-fluxo-transacao.png` | Fluxo com `r3` selecionada; sem banner de orquestração |
| `02-percurso-completo.png` | Percurso com `Etapa 1 · tentativa 1` e `Etapa 2 · tentativa 1` |
| `03-passo-1-aberto.png` | `step-1`, posição 1 |
| `04-passo-2-aberto.png` | `step-2`, posição 2 |
| `05-eventos-relacionados.png` | Eventos da etapa sem erro indevido |
| `06-apos-polling-sem-banner.png` | Seleção e detalhe estáveis após polling |

### Allowlist

O IPv4 público do operador mudou (último octeto `.16` → `.92`). A allowlist `/32` do WAF (Monitor + API) e o SG HTTPS do ALB foram atualizados só por isso. WAF default permanece `BLOCK`. Sem `0.0.0.0/0`. Sem alteração da zona pai.

### Não regressão

Monitor autorizado HTTP 200. WAF default `BLOCK` + regra `allow-sandbox-origins`. API health/readiness 200. Context lookup desabilitado = 404 `Resource not found`, não 500. ECS 1/1. Persistência memory. Callbacks fora. `https://actionhub.com.br/api/health` = 200. Sem mudança em ActionHub, Panne, Inove, DNS pai, RDS, JPA, Flyway ou CAP-021.

### Rollback desta correção

1. Frontend: republicar o bundle anterior `assets/index-D3IABmgJ.js` e invalidar CloudFront.
2. Backend: `aws ecs update-service --task-definition spider-sandbox-backend:4 --desired-count 1` (imagem `sandbox-20260928-7177805b2`). A memória da task nova some.
3. Allowlist: gravar o `/32` vigente do operador; não abrir público.

### Limitações restantes

- Persistência em memória: restart apaga execuções.
- Context Plane desligado no sandbox; 404 é esperado e silencioso no Monitor.
- Eventos operacionais da execução demo continuam vazios (`items: []`); a timeline persistida alimenta “Eventos relacionados”.
- Sem IdP corporativo; Monitor não é anônimo.
- Sem commit e sem push.

### Custos mensais aproximados (atualizado)

Sem NAT e sem RDS. ALB ~USD 16 + Fargate 0.5 vCPU / 1 GB 24×7 ~USD 15–18 + CloudFront/WAF/Route 53 baixos. Ordem de **USD 35–45/mês**. Restart da única task apaga as execuções em memória.

### Rollback

1. `desired_count = 0` no tfvars e apply, ou `aws ecs update-service --desired-count 0`.
2. Esvaziar `operator-allowlist.auto.tfvars` e apply (WAF volta a bloquear todos).
3. Task definition anterior demonstrável: `:4` (imagem `sandbox-20260928-7177805b2`) se precisar reverter só o backend desta correção. A vigente é `:5`.
4. Não destruir a zona pai. Não tocar em `actionhub-prod`.

### Fora de escopo (confirmado)

Callbacks, RDS, JPA, Flyway, CAP-021, `local-demo` na AWS, produção. Sem commit e sem push neste ciclo.

## 0.2 Incidente 403 CloudFront do Monitor (29/09/2026)

Classificação permanece **SANDBOX DEMONSTRÁVEL**. Acesso do operador restaurado sem abrir o ambiente.

| Campo | Valor |
|---|---|
| Horário observado (UTC-3) | ~09:15 e ~11:47 de 29/09/2026 (sampled requests WAF em `GET /`) |
| URL | `https://monitor.spider.actionhub.com.br` |
| Sintoma | página genérica CloudFront `403 ERROR — The request could not be satisfied — Request blocked` |
| Distribuição | `E2E4ORTD4DHI1D` (`monitor.spider.actionhub.com.br` + apex) |
| Web ACL | `spider-sandbox-monitor` (scope `CLOUDFRONT` / `us-east-1`) |
| Ação padrão | `BLOCK` (inalterada) |
| Regra explícita | `allow-sandbox-origins` — não disparou no bloqueio |
| Causa do 403 | ação **default** do WAF (ClientIP fora do IP set IPv4) |
| Não foi | S3 público/privado, OAC, função CloudFront, certificado, DNS, frontend, ECS |

### Evidência

- Sampled request: `Action=BLOCK`, `Rule` ausente (default ACL), `Host=monitor.spider.actionhub.com.br`, `URI=/`, país `BR`, Chrome.
- CloudFront com IPv6 desligado; o caminho efetivo é IPv4. A máquina do operador tem IPv6 local, mas o WAF viu IPv4.
- CLI e WAF amostraram o mesmo IPv4 de saída.
- IP set `spider-sandbox-monitor-allow-v4` ainda tinha só `191.57.x.92/32`.
- ClientIP observado: `191.57.x.77`.

### Alteração realizada

Arquivo local gitignored `spider/infra/aws/environments/sandbox/operator-allowlist.auto.tfvars`: `191.57.x.92/32` → `191.57.x.77/32` (um único `/32`; o anterior foi removido). Defaults versionados continuam vazios.

`terraform plan` sem `-target` no workdir `spider/infra/aws/environments/sandbox` (state `spider/sandbox`) também mostrava drift de task definition ECS e `deregistration_delay` do TG. **Esse plano não foi aplicado.** A task live permanece `:5`.

`terraform apply` **targetado** (0 add / 3 change / 0 destroy):

1. `module.frontend.aws_wafv2_ip_set.allow_ipv4[0]`
2. `module.compute.aws_wafv2_ip_set.api_allow_ipv4[0]`
3. `module.compute.aws_security_group.alb` (HTTPS :443)

Nenhum recurso ActionHub, Panne, Inove, DNS pai, S3 policy, CloudFront, certificado ou ECS.

Planos locais (`allowlist-targeted.tfplan`, `plan-raw.txt`) foram apagados após o apply.

### Validação

| Checagem | Resultado |
|---|---|
| Operador → Monitor `GET /` | HTTP 200, HTML da app (`#root`, título Monitor, bundle `index-w3T1Q3kp.js`) |
| Bundle publicado | contém navegação Monitor / Simulação / Documentação; sem string `Unexpected orchestration error` |
| Origem não autorizada (egress controlada, sem credenciais) | 403 CloudFront `Request blocked` |
| API autorizada | liveness/readiness HTTP 200 `UP`; sem 503 |
| ECS | desired=1, running=1, task definition `:5` |
| Target group `spider-sandbox-tg` | 1/1 healthy |
| WAF default | `BLOCK` |
| S3 `spider-sandbox-monitor-web` | block public access all true; OAC intacto |
| Hub `https://actionhub.com.br/api/health` | 200 |
| Zona pai `actionhub.com.br` | apex / `www` / `api` / `school` inalterados |

### Prevenção (não implantada nesta tarefa)

1. **Recomendada no sandbox:** VPN corporativa ou NAT com IPv4 estático; autorizar só esse CIDR no WAF e no ALB.
2. **Antes de piloto:** autenticação corporativa/IdP; WAF como camada complementar. Sem senha no JavaScript nem Basic Auth improvisado.

### Rollback deste incidente

1. Restaurar `191.57.x.92/32` em `operator-allowlist.auto.tfvars` (ou o `/32` vigente anterior).
2. `terraform apply` com os mesmos três `-target` no state `spider/sandbox`.
3. Manter WAF `default BLOCK`. Não destruir a stack. Não alterar DNS. Não tocar ActionHub.

## 0.3 Acesso por identidade (30/09/2026)

O Monitor deixa de usar o IPv4 residencial `/32` como identidade. Detalhe em `spider/docs/architecture/ADR-SPIDER-MONITOR-IDENTITY-ACCESS.md`.

| Campo | Valor |
|---|---|
| IdP | Cognito User Pool exclusivo `spider-sandbox-monitor` `us-east-2_PM4xeCwRp` |
| Login | managed login, Authorization Code + PKCE, sem self-signup |
| Grupo | `spider-sandbox-operators` |
| Edge | Lambda@Edge `spider-sandbox-monitor-oidc:2` em `us-east-1` (não `$LATEST`) |
| Console API | `https://monitor.spider.actionhub.com.br/v1/console/*` (mesma origem, cache off) |
| API canônica | `https://api.spider.actionhub.com.br` sem login interativo |
| WAF Monitor | default `BLOCK`; rules: IP reputation, Common, Known Bad Inputs, rate 2000/5min, allow GET/HEAD/OPTIONS, allow writes só em `/v1/console/*`. Sem regra de IP. |
| S3 / OAC | privados, intactos |
| Frontend | `assets/index-Chah2Lqj.js` + `assets/index-CkU0BY1u.css` |
| ECS | `spider-sandbox-backend:5`, desired=1, running=1, sem republicação |
| Persistência | `memory`; execução `r3` continua visível |
| ActionHub | `https://actionhub.com.br/api/health` = 200 |
| Commit / push | nenhum |

**Operador:** convidar com `spider/infra/aws/environments/sandbox/invite-monitor-operator.ps1`. Não gravar e-mail nem senha no Terraform, no state ou neste documento.

**Prova de duas redes:** login do operador a partir da saída atual (já fora do `/32` da allowlist canônica) e 302 de autenticador observado por health checks Route 53 em várias regiões AWS. Os health checks foram apagados depois da prova.

**Troca de IP do operador:** não é mais passo do Monitor. `operator-allowlist.auto.tfvars` permanece só para a API canônica / SG do ALB.

**Logout:** `https://monitor.spider.actionhub.com.br/logout` → Cognito → `/logged-out` → novo login.

**Rollback:** associação CloudFront anterior (`spider-sandbox-monitor-oidc:1` ou a função CloudFront `apex-redirect`) e, se necessário, `monitor_ip_fallback_enabled = true` com o `/32` vigente. Sem `terraform destroy`. Sem tocar ActionHub.

## 1. Inventário encontrado (somente leitura)

### AWS e governança

| Item | Achado |
|---|---|
| Perfis | somente `default` |
| Tags corporativas obrigatórias | **não encontradas** na zona `actionhub.com.br` (tags vazias). Padrão adotado: `Project=spider`, `Environment=sandbox`, `ManagedBy=terraform`, `Domain=spider.actionhub.com.br`, `Class=SANDBOX` |
| Convenção de nomes | ECS/ALB existentes usam prefixos de produto (`inove4us-prod`, `panne-prod-alb`, `actionhub-prod`). Spider usa `spider-sandbox-*` |
| Orçamento | `qmind-homolog-monthly-30` (USD 30). Nenhum budget específico da Spider |
| IaC corporativo | Terraform no Inove (`hashicorp/aws ~> 5.70`, backend S3 comentado). **Não havia Terraform da Spider** |
| Pipeline de implantação da Spider | **não encontrado** |

### DNS

| Item | Achado |
|---|---|
| Zona pai | pública `actionhub.com.br` `Z01698931CEOITJ7YYMYX` |
| Registros pai **antes** | apex A, NS, SOA, `api` A, `school` A, `www` A |
| Conflito `spider.*` | **nenhum** |
| ACM `actionhub`/`spider` | nenhum certificado reutilizável em `us-east-1` ou `us-east-2` |
| Split-view / DNS privado | só `paneldx-internal.` (privado). Sem split-view de `actionhub.com.br` |

### Rede e execução (não alterados)

VPCs `us-east-2`: default `172.31.0.0/16` e `PanelDX-vpc` `10.0.0.0/16`. Clusters ECS `inove4us-prod`, `paneldx-cluster`. ALBs PanelDX/Moodle/Inove/Panne. CloudFront só `panne.ia.br` / `demo.panne.ia.br`. RDS inclui `actionhub-prod` (Postgres, **não público**) — **não usado**. Sem API Gateway REST em `us-east-2`. Sem WAF CloudFront. Sem VPN/Direct Connect. Sem ECR `spider`.

### Aplicação (código)

- Monitor: React/Vite `:5180`, proxy local `/v1` `/api` `/actuator` → `:8080`. **Vite não é solução de publicação.**
- Backend: Java 21, Spring Boot 3.4.2, WebFlux. Sem Dockerfile prévio. Sem Flyway no POM. `spider.canonical.persistence.mode=memory`. JPA `ddl-auto=validate`.
- Health: Actuator `/actuator/health`. Probes habilitadas no profile `sandbox`.
- Entrada canônica: `POST/GET /v1/canonical/executions` (flags). Console em `/v1/console/**`.
- Callback publicável: **não há** ingresso de provedor isolado. Existe webhook legado `POST /api/v1/webhooks/callback/{correlationId}` (audit trace) — **não** é publicado em `callbacks`.
- CORS local era só `/api/**` + origens loopback. Profile sandbox passa a usar origens explícitas e `/v1/**`.
- Autenticação: DenyAll no default; `local-demo` **não** entra no sandbox.
- Working tree da Spider estava limpo no início desta frente. ActionHub local: health 200 em `:4000` `:4001` `:4012`.

ActionFinance e CAP-021 não foram misturados.

## 2. Arquitetura escolhida

Referência Inove (ECS Fargate + ALB + Terraform), isolada:

```text
actionhub.com.br (pai, intacta exceto NS spider)
    NS → zona pública spider.actionhub.com.br
        A/alias monitor + apex → CloudFront + S3 privado + OAC + WAF (default BLOCK)
        A/alias api → ALB HTTPS → ECS Fargate privado
        A/alias callbacks → API Gateway HTTP + WAF (default BLOCK, sem rotas admin)
```

`spider.actionhub.com.br` redireciona para `monitor.spider.actionhub.com.br` (CloudFront Function).

API pública protegida (satélites futuros sem VPN). Monitor **não** é anônimo: WAF default BLOCK até `allowed_cidr_blocks`.

RDS: módulo existe, `enable_database=false`. Persistência efetiva: **memory**.

## 3–7. Recursos / DNS / certificados / acesso

Terraform apply do ambiente sandbox: **completo** (após contornar cota de EIP e associação WAF HTTP API).

| Recurso | Identificador público |
|---|---|
| Zona Spider | `Z0546498APG2Z5CPDZEI` |
| CloudFront Monitor | `E2E4ORTD4DHI1D` |
| Bucket | `spider-sandbox-monitor-web` |
| ECR | `…/spider-sandbox-backend` |
| Cluster ECS | `spider-sandbox` (`desired_count=0`) |
| VPC Spider | `vpc-0048417ebcf7b7447` (isolada; sem PanelDX/Hub) |

| Endereço | Política |
|---|---|
| `monitor.spider.actionhub.com.br` | HTTPS + WAF default BLOCK |
| `spider.actionhub.com.br` | redirect para o Monitor |
| `api.spider.actionhub.com.br` | TLS no ALB; DenyAll da aplicação; CORS explícito |
| `callbacks.spider.actionhub.com.br` | domínio + WAF BLOCK; **sem** integração funcional |

Zona pai após delegação: os 6 registros originais **permanecem** + `spider.actionhub.com.br NS`.

## 8. Persistência

**memory**. RDS não ligado. Sem Flyway. Não declarar persistente.

## 9–10. Testes e evidências

| Prova | Estado |
|---|---|
| Inventário AWS/DNS | IMPLEMENTED |
| Delegação NS sem tocar A do Hub | IMPLEMENTED (pai: 6 originais + `spider` NS) |
| Health ActionHub após NS | IMPLEMENTED (local `:4000/:4001/:4012` = 200; `https://actionhub.com.br/api/health` = 200) |
| Certificados ACM us-east-1 e us-east-2 | IMPLEMENTED (`ISSUED`) |
| Resolução Monitor / API | IMPLEMENTED (DNS público) |
| Monitor HTTPS anônimo | IMPLEMENTED bloqueio (HTTP 403 WAF); operador allowlisted = 200 |
| Build do Monitor no S3 | IMPLEMENTED (28/09/2026) |
| API canônica no ar | IMPLEMENTED (1 task, target saudável, HTTPS sem 503) |
| Callbacks funcionais | BLOCKED (sem ingresso publicável; fora de escopo) |
| NAT / Fargate privado | NOT IMPLEMENTED por desenho — Fargate com `assign_public_ip=true` |
| PostgreSQL persistente | BLOCKED |
| Pipeline CI | NOT VERIFIED / ausente |
| CAP-021 | não iniciado |

## 11. Custo mensal aproximado (sandbox)

Sem NAT. ALB ~USD 16 + Fargate 0.5 vCPU/1 GB ligado (`desired_count=1`) ~USD 15–18 + CloudFront/WAF/Route 53 baixos. Ordem de **USD 35–45/mês**, sem RDS. Ver secção 0.

## 12. Riscos e lacunas

- Sem IdP corporativo; Monitor permanece bloqueado no WAF.
- Sem Flyway; não ligar RDS.
- Webhook legado não deve ser exposto em `callbacks`.
- Frontend de produção não deve embutir `localhost` — build sandbox deve definir `VITE_*` ou deixar vazio (`PROD`).
- `local-demo` continua só local.
- Testcontainers/npipe e outras frentes do working tree não foram tocadas.

## 13. Rollback

1. Não destruir a zona pai.
2. Remover só `aws_route53_record.spider_delegation` (NS `spider`) se for preciso desfazer DNS.
3. `terraform destroy` **apenas** no state `spider/sandbox` — nunca recursos `actionhub-prod`, ALBs de Panne/Inove/PanelDX.
4. Confirmar que `actionhub.com.br` / `api` / `www` / `school` continuam com type A.

## 14. Arquivos

Novos sob `spider/infra/aws/**`, `spider/docs/operations/SPIDER-AWS-SANDBOX-001.md`, `application-sandbox.yml`, `backend/Dockerfile`, ajustes mínimos de CORS/frontend para não vazar `localhost` no build `PROD`. Sem commit/push.

## 15. Git

Sem commit e sem push neste ciclo.
