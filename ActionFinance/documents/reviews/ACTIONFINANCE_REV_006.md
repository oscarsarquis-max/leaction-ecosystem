# ACTIONFINANCE_REV_006 — Acesso de produção e pacote de publicação

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_006 |
| Prompt | ACTIONFINANCE_PRM_006 |
| Data | 29/09/2026 |
| Executor | Cursor |
| Aceite | **Não atribuído ao executor.** Pendente do analista |
| Ativação pública | **Não realizada** |

Este relatório não declara o produto pronto para produção.

## 1. O que foi implementado e como experimentar

OIDC Authorization Code com sessão no servidor (Spring Security 6.4 / Boot 3.4.2), contrato `ApplicationPrincipal`, tabelas V6–V7, CSRF em cookie/sessão, comando administrativo e UI de entrada de produção. O adaptador demo continua só em `local-demo` e implementa o mesmo contrato.

**Demo local (sem credenciais neste texto):** `.\scripts\dev\setup-local.ps1` e `start-local.ps1`. Tokens ficam em `.local/demo-tokens.env` (gitignored). Abrir `http://127.0.0.1:5179/`.

**OIDC descartável (ensaio):** IT `OidcAuthorizationCodeIT` sobe `ghcr.io/navikt/mock-oauth2-server:2.1.10` + Postgres 17.6. Não é o provedor real.

**Admin:** `.\scripts\ops\access-admin.ps1 provision -DisplayName ... -Issuer ... -Subject ... -TenantId ... -CompanyId ... -Role OPERATOR -Reason "..." [-DryRun]`. Sem senha. Sem concessão genérica.

## 2. Infraestrutura existente — evidências

Conta verificada em ambiente: `253137917703` (IAM `paneldx-user-admin`). Região de compute observada: `us-east-2`.

| Item | Achado | Natureza |
|---|---|---|
| Conta / região | `253137917703` / `us-east-2` | Verificado em ambiente |
| Destino pretendido | `https://actionfinance.actionhub.com.br` | Documentado (proprietário) |
| Ingresso HTTPS / certificado `actionfinance` | Nenhum certificado ACM `actionfinance` em `us-east-1` | Verificado em ambiente (ausência) |
| Autoridade DNS | Zona `actionhub.com.br` `Z01698931CEOITJ7YYMYX`. Sem registro `actionfinance`. Apex/`www`/`api`/`school` intactos | Verificado em ambiente |
| Execução | Clusters ECS `spider-sandbox`, `inove4us-prod`, `paneldx-cluster`. Sem serviço ActionFinance | Verificado em ambiente |
| Registry | ECR `spider-sandbox-backend`. Sem repositório `actionfinance` | Verificado em ambiente |
| Rede / ALB | ALBs de outros produtos; `spider-sandbox-alb` é sandbox | Verificado em ambiente |
| PostgreSQL | Instâncias alheias (`actionhub-prod` **não público**, não usar). Sem banco ActionFinance | Verificado em ambiente |
| Segredos | Nenhum secret `actionfinance` listado | Verificado em ambiente (ausência) |
| Logs / backup / alertas AF | Não existem como serviço deste produto | Não verificado / não existente |
| Identidade corporativa | Nenhum IdP ActionFinance configurado nesta conta | Não verificado como IdP; ausência observada |
| Permissão de implantação | CLI com AdministratorAccess nesta sessão | Verificado em ambiente |
| `spider/infra/aws` | README: **sandbox/homologação**, não produção | Documentado |

Reutilizar a conta e o padrão (ECS + ALB + CloudFront + Postgres isolado + Secrets Manager), com **banco/schema/usuário/cookie/processo próprios**. Sem cluster físico exclusivo obrigatório. Custo incremental: existe (serviço + banco + certificado + tráfego); **sem estimativa numérica inventada**. Responsável operacional: o mesmo da conta corporativa, a confirmar pelo proprietário.

Sandbox Spider ≠ produção ActionFinance.

## 3. Modelo físico, autorização e sessões

Migrations **V6** e **V7** após V5. V1 checksum 1488219560 preservado. Runtime sem DDL. DELETE só em tabelas de sessão.

Autorização: VIEWER/OPERATOR no banco. Claims, email, headers e query não concedem privilégio. Bloqueio/revogação valem no pedido seguinte.

Sessão JDBC Spring Session 3.4; timeout inicial 30 min. Nome de principal indexado = UUID do ator (ou `unprovisioned`), para caber em `VARCHAR(100)` oficial.

## 4. Provedor real

**Pendente.** Configuração é independente de fornecedor (`issuer`, `client-id`, `client-secret`, `redirect-uri` explícita). Ensaio com mock-oauth2-server.

Insumo faltante: emissor, client id/secret, URI de retorno já combinada, e `issuer`+`subject` dos usuários iniciais (fornecidos pelo responsável — não cadastrar sem eles).

## 5. Gates

| Gate | Resultado | Evidência |
|---|---|---|
| `backend/mvnw verify` | Verde; ITs sem skip | Failsafe: 40 testes / 0 skip (inclui `OidcAuthorizationCodeIT`, `AccessAdminServiceIT`, títulos/baixas, fundação) |
| OIDC descartável | Login, não provisionado, duas empresas, CSRF, logout, Bearer demo recusado | `OidcAuthorizationCodeIT` (protocolo real; não é Mockito) |
| Viewer / email≠vínculo | Isolamento por subject | `AccessAdminServiceIT` |
| Frontend lockfile + lint + test + build + audit | 29 testes; lint ok; audit 0 vulnerabilidades | `frontend/` |
| Imagem | `Dockerfile` + `scripts/ops/build-production-image.ps1` (FE no host, runtime sem root) | Duas tentativas locais falharam por rede Docker (`npm ECONNRESET`; depois EOF no pull da JRE). Artefato e procedimento prontos; digest ainda não gerado nesta máquina |
| Jornada headed 360/768/1280 financeira OIDC | Não executada contra compose (depende de IdP+imagem no host) | Vitest cobre entrada OIDC e telas aprovadas; captura PRM_005 permanece para o recorte visual |

Provedor de teste ≠ identidade real.

## 6. Pacote, destino e ativação

- Imagem: `Dockerfile` (frontend compilado + JAR, user 10001, sem `.local`).
- Exemplo: `ops/env.production.example`.
- Compose de ensaio: `ops/compose/actionfinance-prod-like.yml` (Postgres sem porta pública).
- AWS parametrizado: `ops/aws/README.md` — **não aplicado, não validado na conta como stack AF**.
- Destino: `https://actionfinance.actionhub.com.br`.
- Ativação: ver `ACTIONFINANCE_RUN_001` § pacote. Rollback = digest anterior; não dropar V6/V7.

## 7. Pendências externas (finitas)

| # | Pendência | Responsável sugerido | Impacto |
|---|---|---|---|
| 1 | Provisionar IdP (issuer, client, redirect `https://actionfinance.actionhub.com.br/login/oauth2/code/actionfinance`) | TI / identidade | Sem isto a URL pública não autentica |
| 2 | Criar Postgres isolado (não `actionhub-prod`) + secrets runtime/migrator | TI / dados | Sem banco próprio não há sessão nem vínculos |
| 3 | Certificado ACM + registro **somente** `actionfinance` | TI / DNS | Sem HTTPS no host combinado |
| 4 | Serviço ECS/ECR/ALB ou equivalente do AF | TI / runtime | Sem processo de publicação |
| 5 | `issuer`+`subject` e empresas reais para `access-admin` | Proprietário | Sem usuários autorizados a tela fica “acesso não liberado” |
| 6 | Destino de alerta/health | Operação | Monitoração |

Domínio e preferência pela infra existente já estavam decididos. Este ciclo não os reabre.

## Rollback

Restaurar digest da aplicação. Manter WAF/default BLOCK se o ingresso seguir o padrão sandbox. Não `terraform destroy`. Não alterar ActionHub/Panne/Inove. Não commitar/push neste ciclo.

## Encerramento

Ciclo **pronto para revisão do analista**. Sem PRM_007. Sem publicação do endereço.
