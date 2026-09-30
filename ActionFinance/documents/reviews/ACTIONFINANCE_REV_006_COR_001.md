# ACTIONFINANCE_REV_006_COR_001 — Correções C1–C6

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_006_COR_001 |
| Prompt | ACTIONFINANCE_PRM_006_COR_001 + [complemento de encerramento](../prompts/ACTIONFINANCE_PRM_006_COR_001_ENCERRAMENTO.md) (29/09/2026) |
| Data | 29/09/2026 |
| Executor | Cursor |
| Parecer de origem | [ACTIONFINANCE_REV_006_PARECER_ANALISTA](ACTIONFINANCE_REV_006_PARECER_ANALISTA.md) |
| Relatório original | [ACTIONFINANCE_REV_006](ACTIONFINANCE_REV_006.md) (preservado) |
| Aceite parcial (analista, 29/09) | Autorização por empresa, configuração de produção, imagem/ensaio HTTPS, cookie e jornada OIDC nas três larguras — **aceitos neste recorte**. Provas C1–C6 da retomada preservadas. Imagem da retomada `sha256:cb6736f5…ceb523a1` não cobre as correções deste complemento. |
| Aceite integral do PRM_006 | **Ainda pendente do analista.** Dependia só dos três pontos abaixo. Sem autoaceite. |
| PRM_007 / DNS / produção | **Não iniciados** |

Este relatório não declara o produto pronto para produção nem para o alvo remoto.

## Distinção de maturidade

| Camada | Estado |
|---|---|
| Implementação no repositório | Pronta para C1–C6 no código e nos procedimentos locais |
| Comprovada localmente | Maven (15 unitários + 43 ITs, 0 skip, sessão anterior — Java inalterado neste complemento), frontend **36** testes + lint + build (complemento), Terraform `validate` (sessão anterior), imagem local **nova** do complemento, ensaio HTTPS/OIDC + restart + cadastro rápido + restore |
| Ainda não validada no alvo remoto | DNS, IdP corporativo, ALB/ECS/RDS, certificado ACM, digest de registry |

## Tabela C1–C6

| Item | Alteração | Prova | Resultado |
|---|---|---|---|
| **C1** | `ApplicationPrincipal.permissionsByCompany`; escrita na empresa do recurso; idempotência autoriza **antes** do replay; API `/me` com permissões por empresa; UI da empresa selecionada; demo mista sem poderes extras | `MixedCompanyAuthorizationIT` e `OidcAuthorizationCodeIT.mixedRolesAcrossTenantsRevokeAndJsonLogout` (sessão anterior). Navegador do ensaio: OPERATOR em A / VIEWER em B, troca de empresa, POST em B com CSRF+idempotência → 403; botão Novo recebível ausente em B | **Comprovado** (IT + ensaio HTTPS) |
| **C2** | Logout SPA só após 204; pendência de escrita em memória; 401 nova ≠ 401 de repetição; aviso de conferência e de sessão expirada no nível da aplicação | Testes frontend da sessão anterior. Ensaio: Sair confirma e oculta dados; reentrada OIDC reencontra o mesmo título (sem duplicar o lançamento da jornada) | **Comprovado** em testes; continuidade no navegador **comprovada** no ensaio |
| **C3** | Parsing de URI de produção; HTTPS obrigatório; Secure alinhado; sem production+demo/`oidc-it`; headers encaminhados não definem origem/callback | Unidades da sessão anterior. Ensaio perfil `production` atrás de Caddy: `AFSESSION` HttpOnly, Secure, SameSite=Lax, domain `finance.trial.localhost` (sem ponto inicial), Path=/; `XSRF-TOKEN` não HttpOnly, Secure, Lax | **Comprovado** (unidades + cookies no Chromium) |
| **C4** | JAR e frontend compilados no host; imagem JRE só copia `ops/image-staging/actionfinance-backend.jar`; script confere exit code de npm/mvnw/docker; dist antigo removido se o build frontend falhar; sem Maven/`go-offline` na imagem | `npm ci` EPERM em `esbuild.exe` → script encerrou **sem** “Built”. Depois `npm ci` em `node_modules` novo (exit 0, 274 pacotes, audit 0) + `build-production-image.ps1 -SkipNpmCi`: `npm run build` 0, `mvnw -DskipTests package` SUCCESS (4,4 s, cache local), `docker build` 0. Imagem ensaiada: `actionfinance:local-prm006` **id `sha256:cb6736f5b16b6860870543c332b76ab1b330a6eeaee44a3f4d75e833ceb523a1`**. JAR host sha256 `7ee74dae09016db724bb31b17d0ceedb00fdce0b12c0b256ded1ae380ad20dbe`. SPA servida (`index-DxK6JWgG.js`), sem Vite. `GET /api/v1/does-not-exist-cor001` → JSON (403 autenticado), não `index.html`. Sem Spider/Hub/Panne | **Comprovado localmente**. Sem digest remoto (sem push) |
| **C5** | Terraform ALB+ECS (não aplicado); `bootstrap-org` dry-run + execução; migrate; DAT/RUN | Terraform validate (sessão anterior, aws 5.100.0). Ensaio: Flyway V1→V7 em Postgres descartável; `bootstrap-org` dry-run e execução para TENANT-A/B; `provision` OPERATOR/VIEWER no subject lido do IdP. Sem apply AWS | Definições e bootstrap **comprovados**; apply remoto **não feito** |
| **C6** | Conjunto focado | Maven/FE da sessão anterior (não reexecutados: Java de negócio inalterado). Imagem + Playwright headless 360/768/1280 em `https://finance.trial.localhost:18443`: entrar OIDC → empresa A → conta → título → baixa 50,00 → extrato → empresa B (sem escrita) → sair → entrar de novo no mesmo título. Capturas novas em `documents/reviews/screenshots/prm-006-cor-001/` e `journey-log.json`. Sem capturas PRM_005 | **Comprovado no ensaio descartável** |

## Diagnóstico do `go-offline` (retomada)

A etapa `./mvnw -q -DskipTests dependency:go-offline` no Dockerfile antigo não é requisito de aceite. A tentativa anterior foi interrompida sem image ID; tempo decorrido sozinho não diagnosticava rede. Nesta retomada a etapa foi **removida**. O `package` correu no host com cache Maven já populado pelo `verify` anterior: compile “Nothing to compile / up to date”, BUILD SUCCESS em 4,4 s, sem download visível e sem falha de DNS/TLS/repositório. A imagem de runtime não contém `.m2`, `settings.xml` nem fontes.

`npm ci` no script oficial falhou com EPERM ao desligar `esbuild.exe` (ficheiro em uso) e **não** imprimiu Built. O `node_modules` quebrado foi renomeado; `npm ci` seguinte: exit 0. O build da imagem usou `-SkipNpmCi` sobre essa instalação recém-concluída.

## Ensaio HTTPS/OIDC (descartável)

| Peça | Valor |
|---|---|
| Compose | `ops/compose/actionfinance-https-trial.yml` (portas 18443 / 18444 / 15439, volume `actionfinance_https_trial_pg`) |
| Perfil da app | `production` |
| Origem | `https://finance.trial.localhost:18443` |
| Issuer | `https://idp.trial.localhost:18444/default` (mock-oauth2 com TLS PKCS12 de ensaio) |
| Certificados | `scripts/ops/generate-https-trial-certs.ps1` (gitignorados; CA de 2 dias; não entram na imagem) |
| Senhas | `runtime-change-me` / `migrator-change-me` de `bootstrap-prod-like.sql` — **só este ensaio**, não instrução de produção |
| Subject | gerado pelo mock a cada login; lido em `/me` e provisionado via `java -jar` `access-admin` |
| Navegador | Playwright Chromium headless, `--host-resolver-rules` + `ignoreHTTPSErrors` (CA de ensaio) |

O diálogo HTML de cadastro rápido não disparou POST no headless; contraparte/categoria foram criadas pela **mesma API autenticada** da sessão. Título, baixa, extrato e saída foram pela UI.

`OidcLoginFailureHandler` agora regista `error` e `description` do OAuth2 (sem tokens). Isso revelou `invalid_id_token` / `{sub=null}` quando o JSON do mock forçava `tokenCallbacks`; o IdP de ensaio voltou ao padrão do IT.

## BLOQUEADO / pendências externas

| Gate | Causa | Tentativa concreta |
|---|---|---|
| Digest de registry / push | Ciclo não autoriza push | Nenhum `docker push` |
| IdP real, DNS, AWS | Ativação externa | Terraform só `validate`; ensaio local no lugar |
| `npm ci` com `esbuild.exe` bloqueado | Ficheiro em uso no Windows | Script parou sem Built; `npm ci` seguinte após renomear `node_modules` |

IdP corporativo, DNS e recursos AWS continuam pendências externas de ativação.

## Complemento de encerramento (29/09/2026)

O parecer focado aceitou o recorte da retomada (imagem, HTTPS, cookie, jornada OIDC nas três larguras, autorização por empresa). **Não reabriu C1–C6.** A inspeção de capturas não é aprovação estética. Este complemento trata só os três pontos que ainda impediam o aceite integral.

Causa do cadastro rápido: `QuickCatalog` vivia dentro do `<form>` do título e o `Modal` renderizava o `<dialog>` no mesmo sítio, sem portal — formulários aninhados. O diálogo passou a sair do formulário pai e o `Modal` usa portal em `document.body`. Foco, Escape, retorno ao acionador e rascunho do título foram preservados.

| Ponto | Prova | Resultado | Evidência |
|---|---|---|---|
| Restart real do processo | OIDC no ensaio descartável; ator `04cfb1b7-4867-4d5b-9bd9-e445ccfd6447` e empresa A `23cc1d84-…fa12fd` (sem cookie/token em claro; só SHA-256 do `AFSESSION`); `docker compose restart app` (Postgres/IdP/navegador mantidos); `/me` após readiness com o mesmo ator/escopo, sem novo login nem reprovisionamento; `revoke` do vínculo A → POST seguinte 403; Sair efetivo | **Comprovado** | [`screenshots/prm-006-cor-001/session-restart-log.json`](screenshots/prm-006-cor-001/session-restart-log.json) |
| Upgrade V5→atual e restore V6/V7 | Base descartável V1–V5 com fatos; checksums de título/baixa/movimento/histórico iguais após migrate V6/V7 (V1=1488219560); identidade/vínculo/auditoria/sessão acrescentados; dump → outro Postgres descartável; owners migrator; ACL completo (`restore-runtime-privileges.sql`); Flyway validate; runtime lê tabelas novas, sem DDL nem DELETE em fatos/auditoria; `invalidate-sessions` 1→0. Cookie operacional: dump do ensaio → Postgres+app descartáveis; cookie autenticou (200) no restore; após invalidação, 401; títulos/users/vínculos/auditoria 11\|31\|62\|127 inalterados, sessões 4→0. Volume local `actionfinance-postgres-17` (ainda V1–V5) **não** foi migrado nem restaurado | **Comprovado** | [`screenshots/prm-006-cor-001/upgrade-restore-log.json`](screenshots/prm-006-cor-001/upgrade-restore-log.json), [`restore-session-invalidate-log.json`](screenshots/prm-006-cor-001/restore-session-invalidate-log.json) |
| Cadastro rápido pela UI | OIDC desktop 1280 e 360: Novo recebível incompleto → diálogo contraparte (POST `/catalogs/counterparties`) → seleção automática → diálogo categoria (POST `/catalogs/categories`) → completar e Registrar (POST `/receivables`); Escape/Voltar preservam o rascunho; Salvar do diálogo não submeteu o título. Frontend: 36 testes, lint, build. Sem criação via API substituta | **Comprovado** | [`screenshots/prm-006-cor-001/quick-catalog-log.json`](screenshots/prm-006-cor-001/quick-catalog-log.json); capturas `*-quick-catalog-*.png` |

Imagem **deste complemento** (não atribuir as correções à imagem da retomada): `actionfinance:local-prm006` id `sha256:329a018e649ebc00ce5a7722b95866d575467b0fcd6821df7e299757640a30cd`. JAR host sha256 `5dcde9c70436da79e1539a9f4801c03ed03fcc6afee07874d60d0baa8c280974`. Frontend `index-Bic8tzlK.js`.

## Limitações restantes

- Aceite **integral** do PRM_006 continua com o analista. O aceite **parcial** do recorte da retomada está registado acima.
- Sem digest remoto.
- Terraform validado, **não aplicado**.
- `bootstrap-org` audita com `PROVISION_USER` / `IDENTITY` e metadado `kind=BOOTSTRAP_ORGANIZATION` (CHECK V6).
- `verify-backup.ps1` agora exige fonte V1–V7. A fonte local `actionfinance-postgres-17` permanece em V1–V5 (não tocada). O ensaio de upgrade/restore usou bancos descartáveis.
- IdP real, DNS e AWS continuam separados como próximos passos de publicação.

## Arquivos entregues / alterados nesta retomada (principais)

- `documents/prompts/ACTIONFINANCE_PRM_006_COR_001.md` (prompt integral com orientação de retomada)
- `Dockerfile` e `.dockerignore` (runtime só com o JAR)
- `scripts/ops/build-production-image.ps1`, `generate-https-trial-certs.ps1`, `run-https-trial.ps1`
- `ops/compose/actionfinance-https-trial.yml`, `ops/compose/https-trial/*`
- `frontend/scripts/capture-prm-006-https-trial.mjs`
- `OidcLoginFailureHandler` (log do erro OIDC)
- `ops/env.production.example` (`forward-headers-strategy=none`)
- `documents/operations/ACTIONFINANCE_RUN_001.md`
- `documents/reviews/ACTIONFINANCE_REV_006_COR_001.md` (este)
- Capturas: `documents/reviews/screenshots/prm-006-cor-001/`

## Arquivos deste complemento

- `documents/prompts/ACTIONFINANCE_PRM_006_COR_001_ENCERRAMENTO.md`
- `frontend/src/ui/Modal.tsx` (portal), `frontend/src/App.tsx` (diálogo fora do form do título)
- `frontend/src/ui/Modal.test.tsx`, testes de cadastro rápido em `App.test.tsx`
- `scripts/dev/restore-runtime-privileges.sql`, `verify-upgrade-restore.ps1`, `verify-backup.ps1` (V6/V7)
- `scripts/ops/invalidate-sessions.ps1` (`-ContainerName`)
- `frontend/scripts/capture-prm-006-quick-catalog.mjs`, `prove-prm-006-session-restart.mjs`, `prove-prm-006-restore-session.mjs`
- `documents/operations/ACTIONFINANCE_RUN_001.md`

## Encerramento

Complemento encerrado para revisão focada dos três pontos. Relatório original e provas da retomada preservados. Sem PRM_007, publicação, commit ou push.
