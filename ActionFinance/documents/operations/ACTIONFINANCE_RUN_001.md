# ACTIONFINANCE_RUN_001 — Operação local da fundação

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_RUN_001 |
| Versão | 0.5 |
| Data | 30/09/2026 |
| Prompt | PRM_007 |
| Autorização | Concordância de gasto registada; apply executado |
| Deploy / produção | Host no ar; **publicação não declarada** (falta login humano) |

## Pré-requisitos

- Java 21 no PATH (`java -version`)
- Docker Desktop com engine acessível pelo CLI (`docker` + contexto `desktop-linux`)
- Node 24+ e npm (apenas frontend)
- Portas livres no loopback: `5439` (Postgres), `8091` (API), `5179` (UI)

Não use as portas de Hub (`5433`/`4000`), Loja (`5438`/`5175`/`5075`), Spider (`5436`/`8080`/`5180`), SegSense (`5437`/`8088`), Panne (`5545`) ou demais satélites.

## Primeira configuração

```powershell
cd C:\Projetos\ActionFinance
.\scripts\dev\setup-local.ps1
```

Cria `.local/secrets.env` e `.local/demo-tokens.env` se ainda não existirem (não sobrescreve), renderiza o SQL de bootstrap e sobe só o container `actionfinance-postgres-17` (`postgres:17.6`). Volume `actionfinance_pgdata_17` sobrevive a parada. O volume PG18 legado permanece no Docker e não deve receber imagem 17.

Não imprime senhas nem tokens. Não versionar `.env` real.

## Subir / estado / parar

```powershell
.\scripts\dev\start-local.ps1
.\scripts\dev\status-local.ps1
.\scripts\dev\stop-local.ps1
```

`start-local` espera o Postgres próprio, sobe API e UI em processos ocultos e grava PIDs em `scripts/dev/.pids`. Só encerra processos cuja ownership confirma ActionFinance. `stop-local` faz `docker compose stop postgres` — **não** `down -v`.

## Endereços efetivos (host)

| Recurso | URL |
|---|---|
| UI fundação | http://127.0.0.1:5179/ |
| API info | http://127.0.0.1:8091/api/v1/system/info |
| Liveness | http://127.0.0.1:8091/actuator/health/liveness |
| Readiness | http://127.0.0.1:8091/actuator/health/readiness |
| Postgres | 127.0.0.1:5439 → container 5432 |

Endpoints autenticados (`/api/v1/access/me`, `/api/v1/access/context`) exigem Bearer demo. Tokens ficam só em `.local/demo-tokens.env`.

## Host vs container

| Papel | Onde corre nesta etapa |
|---|---|
| PostgreSQL | container `actionfinance-postgres-17` (`postgres:17.6`) |
| Backend Java | host, Maven Wrapper, bind `127.0.0.1:8091` |
| Frontend Vite | host, proxy `/api` → `http://127.0.0.1:8091` sem secret VITE |

O backend no host usa usuário **runtime** no datasource e credenciais **migrator** só para Flyway. Schema `actionfinance` é criado no bootstrap do container (`create-schemas=false` no Flyway) para não ciclar permissão.

## Diagnóstico

1. `status-local.ps1` e `GET /api/v1/system/info` — disponibilidade de produto, não readiness.
2. Liveness = processo; readiness = banco próprio + Flyway válido. Timeout Hikari 3 s.
3. Falha de migration impede subida utilizável.
4. Detalhes de health e SQL não são expostos.

## Persistência e backup isolado

- Reinício do container próprio preserva `actionfinance.flyway_schema_history`.
- `.\scripts\dev\verify-backup.ps1` faz `pg_dump --no-owner --no-acl`, restaura em container descartável rotulado (sem porta publicada) e confere checksum, owner e restrições do runtime **incluindo V6/V7**. O ACL completo está em `scripts/dev/restore-runtime-privileges.sql`. Uma falha deliberada no mesmo script não imprime sucesso. Não restaura sobre o volume de desenvolvimento.
- `.\scripts\dev\verify-upgrade-restore.ps1` cria base descartável até V5 com fatos de teste, atualiza até a versão atual, faz backup/restore noutro banco descartável e invalida só `SPRING_SESSION`.
- Há dados financeiros no recorte local (títulos, baixas, contas, identidade V6/V7). O dump precisa cobrir essas tabelas e `SPRING_SESSION`.
- Após restore operacional: `.\scripts\ops\invalidate-sessions.ps1` apaga só sessões. Fatos financeiros e `access_admin_audit` permanecem. Restart normal da aplicação deve preservar a sessão JDBC.

## Autenticação demo

Ver `documents/security/ACTIONFINANCE_SEC_001.md`. Sem perfil/flag, os endpoints protegidos permanecem 401. Esta identidade não é o login da UX operacional.

## Pacote de publicação (PRM_007) — aplicado; publicação não declarada

Plano e custo: `documents/operations/ACTIONFINANCE_DEP_001.md`. Relatório: `documents/reviews/ACTIONFINANCE_REV_007.md`.

Ordem executada em 30/09/2026: state → fundação → secrets (JSON via ficheiro) → digest ECR `7c4cc0de…` → bootstrap RDS (`scripts/ops/run-rds-bootstrap.ps1`) → migrate Fargate V7 → `bootstrap-org` / `provision` via `scripts/ops/run-access-admin-ecs.ps1` → `desired_count=1` → alias público → ingresso no `paneldx-alb` (Adendo 002) e exclusão do ALB dedicado ~14:55 UTC. Adendo 003: nomes de exibição da Loja de Pães reparados no RDS (`scripts/ops/repair-loja-de-paes-names.ps1`); novos cadastros ECS usam `af-ecs-override-json.ps1` (`\uXXXX`). Sem nova imagem. Restore isolado: plano em `ACTIONFINANCE_RESTORE_PRM007_ENSAIO.md`; execução `.\scripts\ops\run-rds-isolated-restore.ps1` (PITR para `actionfinance-restore-prm007`, nunca sobre a origem). Prova logout/CSRF no destino: `frontend/scripts/prove-prm-007-logout-csrf.mjs` (login humano no Chromium; sem gravar cookies).

Rollback: `desired_count=0` e, se preciso, `enable_public_dns=false`. Preservar RDS e logs.

A tarefa web usa `ACTIONFINANCE_FLYWAY_ENABLED=false` e só o secret `actionfinance/runtime`. O migrator é outro secret e outra execution role.

Convite Cognito: `.\scripts\ops\prepare-cognito-operator.ps1 -SendInvite` só com destino `oscar@oscarsarquis.com.br`. Recusa contactos `@actionhub.com.br` / `@lojadepaes.com.br`. Login do hosted UI é o **username**, não o e-mail de contacto.

## Pacote local anterior (PRM_006) — ensaio, não destino

Destino: `https://actionfinance.actionhub.com.br`. Este ciclo **não** aplica DNS, ECS nem certificado.

1. Backup do Postgres alvo (se já existir). Não restaurar o volume demo.
2. Migrator separado do runtime: `.\scripts\ops\migrate.ps1` com usuário `actionfinance_migrator` até a versão atual (V7). Runtime sem DDL. Não alterar checksums já aplicados.
2b. Banco vazio: `.\scripts\ops\access-admin.ps1 bootstrap-org` com `-DryRun` e depois execução, valores explícitos do responsável. Só então `provision` com issuer+subject lidos no provedor (não e-mail).
3. Construir imagem: `.\scripts\ops\build-production-image.ps1`. O JAR e o frontend são compilados no host; a imagem de runtime só copia `ops/image-staging/actionfinance-backend.jar`. Anotar image ID local. Digest remoto só se houver registry autorizado já usado; este ciclo não faz push. `-SkipNpmCi` só quando `npm ci` falhar por ficheiro em uso e `node_modules` já existir.
4. Configurar variáveis de `ops/env.production.example` no secret store (OIDC, senhas, origem pública).
5. Subir o serviço com o digest. Health: `/actuator/health/liveness` e `/readiness` (detalhes ocultos).
6. Registrar só `actionfinance.actionhub.com.br` (CNAME/ALIAS). Não alterar apex/`www`/`api`/`school`.
7. Teste de entrada com usuário já provisionado via `access-admin` (valores do proprietário).
8. Teste financeiro controlado no ambiente autorizado — não no banco demo.
9. Rollback de aplicação: voltar o digest anterior. Não apagar dados para “desfazer” V6/V7. Se o rollback exigir restore, há perda das escritas posteriores ao backup.

Sessão: 30 minutos de inatividade (`ACTIONFINANCE_SESSION_TIMEOUT_MINUTES`). Cookie Secure em HTTPS.

Backup proposto (não é compromisso operacional aceito): dump diário cifrado, retenção 14 dias, restore ensaiado em instância descartável (`verify-backup.ps1` local). RPO/RTO desejados dependem do responsável de operação; este ciclo não os aceita.

Alertas: health do serviço + destino configurável; nenhuma mensagem enviada neste ciclo.

## Limites

- Sem deploy, sem sync de banco do monorepo, sem cliente Spider/Panne/Hub.
- Testcontainers do PRM_006 já correu com `mvnw verify` nesta máquina (40 ITs). Se o engine falhar de novo, reportar BLOQUEADO com a tentativa; não inventar sucesso.
- Ensaio HTTPS descartável (perfil `production`): gerar certificados com `.\scripts\ops\generate-https-trial-certs.ps1` e subir `.\scripts\ops\run-https-trial.ps1`. Origem `https://finance.trial.localhost:18443`, IdP `https://idp.trial.localhost:18444/default`. Portas 18443/18444/15439 e volume `actionfinance_https_trial_pg` — não reutiliza portas/volumes dos outros produtos. Senhas `change-me` de `bootstrap-prod-like.sql` são exclusivas deste ensaio; não são instrução de produção. O Compose HTTP `actionfinance-prod-like.yml` continua no perfil `oidc-it`.
- Infra AWS: `ops/aws/terraform/` e `ops/aws/state/` — `terraform validate` em 30/09. **Não aplicar** sem concordância do DEP_001.
