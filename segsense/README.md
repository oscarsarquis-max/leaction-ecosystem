# SegSense

Fundação técnica local do **Insurance Reference Satellite** no monorepo `leaction-ecosystem`. “Satellite” é um **padrão de integração**, não incorporação à Spider. SegSense, Spider e o Insurance Provider Mock são aplicações fisicamente independentes: nenhum código, banco, runtime ou deployment do SegSense (ou do mock) pertence à Spider.

O SegSense é o primeiro **EXPERIENCE SATELLITE** do `SPIDER-SAT-003` (Satellite Contract V1, **IMPLEMENTADO / DEMO ONLY** na Spider). O BFF declara identidade, objetivo, contexto governado e finalidade; a Spider decide. O mock é **TEST DOUBLE**, não Provider Satellite certificado. Icatu permanece **NOT_IMPLEMENTED**.

O backend Java é o **Satellite BFF**, com identidade local `SEGSENSE`, manifesto preliminar não certificado, correlação HTTP, **segurança deny-by-default**, catálogo administrativo local, **oportunidades contextuais versionadas**, **governança editorial**, **links contextuais seguros** e **apresentações demonstrativas**. A entrada pública é `http://127.0.0.1:5178/` (posicionamento do SegSense). A demonstração Icatu é `http://127.0.0.1:5178/demonstracao/icatu` — cenário **não oficial**, não a home. O MVP integrado sintético é `http://127.0.0.1:5178/demonstracao/mvp-integrado` (EXPERIENCE → Satellite Contract V1 → Spider → Test Double). Segredos: `scripts/setup-mvp-demo-secrets.ps1` (não versionar nem imprimir). Sem IdP, `/api/v1/admin/**` responde **401**.

A Spider permanece no boundary `SIMULATED_INFRASTRUCTURE / MOCK_ONLY`. O contrato canônico é `POST /v1/satellites/interactions`. A fatia `POST /v1/demo/segsense/protection-decisions` permanece **deprecated** (anti-corrupção). `/go` e SpiderBank não são o caminho de seguros.

## 1. Visão

O SegSense é o Insurance Reference Satellite do padrão `SPIDER-ARCH-017` e o primeiro EXPERIENCE SATELLITE do `SPIDER-SAT-003`. O frontend React chama somente o Satellite BFF. A UI não conhece o envelope canônico. O BFF é a única fronteira com o Satellite Contract. Operações exclusivamente locais (esta página, `system/info`, health) não passam pela Spider.

## 2. Relação entre SegSense, Spider e Icatu

- **SegSense** é o primeiro **EXPERIENCE SATELLITE**: experiência de domínio e apresentação, com runtime, banco e frontend próprios. Não escolhe provider. As regras de seguros ainda não foram implementadas.
- O **backend Java** (`segsense-backend`) é o Satellite BFF. O frontend nunca chama a Spider nem guarda credenciais técnicas.
- **Spider** é plataforma independente. Boundary atual: `SIMULATED_INFRASTRUCTURE / MOCK_ONLY`. Dona do Satellite Contract, da decisão, da policy e da resolução de capability. Não altera `/go`, SpiderBank nem o Data Plane neste incremento.
- **Icatu** é um executor potencial futuro. O SegSense não escolhe nem implementa integração operacional direta com a Icatu.
- O **Insurance Provider Mock** (`C:\Projetos\segsense-provider-mock`) é aplicação irmã independente (porta `8095`). Só a Spider o chama. **TEST DOUBLE / ILLUSTRATIVE / NOT ICATU**. Não é Provider Satellite certificado.

Os diretórios `services/spider-integration` e `services/icatu-integration` documentam esses limites. O BFF não importa o mock nem tipos `SatelliteContract*`. Consome o contrato publicado pela Spider no profile `local/test`.

## 3. Pré-requisitos e versões

| Ferramenta | Versão validada |
|---|---|
| JDK | 21 LTS |
| Maven Wrapper | 3.9.16 (versionado em `backend/`) |
| Node.js | 24 LTS |
| npm | 11.x, com `package-lock.json` |
| Docker Engine + Compose | 29.x / v2 |
| PostgreSQL (imagem) | `postgres:18.6` |
| Spring Boot | 4.1.1 |
| React | 19.2.8 |

Portas locais (evitam colisão com Hub `:5433`, PanelDX `:5434`, Phanton `:5435` e Spider `:5436`): PostgreSQL `5437`, backend `8088`, frontend `5178`.

## 4. Estrutura das pastas

O SegSense segue a convenção do monorepo: um diretório de produto na raiz do workspace (`C:\Projetos\segsense`), no mesmo nível de `spider/` e `panne/`. Não é um repositório Git aninhado.

```text
segsense/
├── frontend/                 # React 19; não chama a Spider
├── backend/                  # Satellite BFF (segsense-backend)
├── services/
│   ├── spider-integration/   # limites do contrato; sem client
│   └── icatu-integration/    # executor potencial; sem integração direta
├── database/
│   ├── migrations/           # migrations canônicas (Flyway)
│   └── seeds/                # política futura; sem dados
├── documents/                # índice em documents/README.md
├── .editorconfig
├── .gitignore
├── .env.example
├── compose.yaml
└── README.md
```

As migrations canônicas ficam em `database/migrations`. O backend as copia para o classpath `db/migration` no build Maven.

A documentação oficial está em `documents/`. O índice navegável é `documents/README.md`. Arquiteturas: `SEGSENSE_ARQ_001` v0.4, `SEGSENSE_ARQ_002` v1.6, `SEGSENSE_ARQ_003` e `references/SPIDER-ARCH-017.md` (cópia PROPOSED, distinta do texto vigente na Spider). Domínio e dados: `SEGSENSE_DOM_001`, `SEGSENSE_DOM_002` v1.2, `SEGSENSE_DOM_003`, `SEGSENSE_DAT_001`, `SEGSENSE_DAT_002`, `SEGSENSE_DAT_003` v1.1, `SEGSENSE_DAT_004` v1.1, `SEGSENSE_DAT_005` v1.2 (V9–V11), `SEGSENSE_DAT_006` (V12). Governança: `SEGSENSE_GOV_001` v1.2. Link: `SEGSENSE_LNK_001` v1.2. Experiência: `SEGSENSE_UX_001` v1.1, `SEGSENSE_UX_002`, `SEGSENSE_UX_003`, `SEGSENSE_UX_004`. Frontend implementado: `SEGSENSE_UI_001`. Convenções HTTP: `SEGSENSE_API_001`, catálogo: `SEGSENSE_API_002`, oportunidade: `SEGSENSE_API_003`, governança: `SEGSENSE_API_004`, links: `SEGSENSE_API_005` v1.1, aviso: `SEGSENSE_API_006`, demonstrações editoriais: `SEGSENSE_API_007` (APIs do SegSense, não Satellite Contract). Segurança: `SEGSENSE_SEC_001` v1.4, `SEGSENSE_SEC_002` v1.1, `SEGSENSE_SEC_003`, `SEGSENSE_SEC_004`. Fontes públicas: `SEGSENSE_SRC_001`. Decisões: `SEGSENSE_ADR_001`, `SEGSENSE_ADR_002`, `SEGSENSE_ADR_003`. PRM_006 e `SEGSENSE_PRM_006_COR_001` estão aprovados. PRM_007 recebeu o corretivo único `SEGSENSE_PRM_007_COR_001`. PRM_008 implementou o sistema visual e a página pública `/c/{token}`. PRM_009 adiciona aviso de finalidade versionado, instância contextual local e trilha de evidência minimizada. O corretivo único `SEGSENSE_PRM_009_COR_001` endurece V10, idempotência sem cache de segredo e justificativa persistida. O PRM_010 está **preparado documentalmente / implementação bloqueada por contrato externo ausente** (ramo B): `SEGSENSE_INT_001`, `SEGSENSE_ARQ_003`, `SEGSENSE_ADR_003`, `SEGSENSE_REQ_002`, `SEGSENSE_REV_010`. O PRM_011 entregou `/demonstracao/icatu` e `DemonstrationStory` e foi **aprovado com ressalvas**. O PRM_012 tornou `/` a entrada pública de posicionamento (`SEGSENSE_POS_001`, `SEGSENSE_UX_005`); a integração Spider **não** foi realizada. Não há Satellite Contract implementado. O mock de provedor está só especificado (`SEGSENSE_MCK_001`). Documentos: `SEGSENSE_FUN_002`, `SEGSENSE_DAT_005`, `SEGSENSE_API_006`, `SEGSENSE_SEC_003`, `SEGSENSE_REV_009`, `SEGSENSE_PRM_009_COR_001`, `SEGSENSE_REV_011`, `SEGSENSE_ASM_001`, `SEGSENSE_SRC_002`, `SEGSENSE_REV_012`.

## 5. Preparação do `.env`

No PowerShell, a partir de `C:\Projetos\segsense`:

```powershell
Copy-Item .env.example .env
```

Ajuste portas, JDBC, origem CORS (`SEGSENSE_FRONTEND_ORIGIN`), identidade (`SEGSENSE_APPLICATION_ID`), `SEGSENSE_PUBLIC_BASE_URL`, `SPRING_PROFILES_ACTIVE=local` e `VITE_API_BASE_URL` se necessário. Não use curinga em CORS.

O Compose lê `.env` automaticamente neste diretório. O Vite lê o `.env` da raiz do SegSense (`envDir` aponta para o diretório pai de `frontend/`). O Spring Boot não carrega `.env`; se você alterar as variáveis, exporte-as na sessão antes de subir o backend:

```powershell
Get-Content .env | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
  $name, $value = $_ -split '=', 2
  Set-Item -Path ("Env:" + $name.Trim()) -Value $value.Trim()
}
```

`.\mvnw.cmd spring-boot:run` ativa o profile `local` (`spring-boot.run.profiles`). HTTP em loopback só é aceito com `local` ou `test` explícitos. Sem esse profile, `SEGSENSE_PUBLIC_BASE_URL` em HTTP impede a subida.

## 6. Inicialização do PostgreSQL

```powershell
Set-Location C:\Projetos\segsense
docker compose --env-file .env config --quiet
docker compose --env-file .env up -d postgres
docker compose --env-file .env ps
```

Aguarde `healthy`. Conferência:

```powershell
docker inspect --format "{{.State.Health.Status}}" segsense-postgres
```

O volume nomeado `segsense_pgdata` preserva os dados entre reinícios.

## 7. Execução do backend (Windows / PowerShell)

```powershell
Set-Location C:\Projetos\segsense\backend
.\mvnw.cmd spring-boot:run
```

A API escuta em `http://127.0.0.1:8088`. As migrations Flyway aplicam-se na subida. Não registre senhas, JDBC completo ou payloads sensíveis nos logs.

## 8. Execução do frontend (Windows / PowerShell)

Em outro terminal:

```powershell
Set-Location C:\Projetos\segsense\frontend
npm ci
npm run dev
```

Abra `http://127.0.0.1:5178/` (também `http://localhost:5178/` no CORS local). O visitante vê o **posicionamento do SegSense**. A demonstração Icatu **não oficial** está em `http://127.0.0.1:5178/demonstracao/icatu`. O MVP integrado sintético está em `http://127.0.0.1:5178/demonstracao/mvp-integrado` (`SEGSENSE_DEMO_RUN_001`). Em `http://127.0.0.1:5178/admin/demonstracoes`, o bloqueio 401 inclui links públicos; editar/aprovar/publicar continua indisponível sem identidade. `/c/{token}` permanece a jornada de convite. Sem IdP, GET/POST administrativos continuam 401. Não há tela de login.

## 9. Execução de todos os testes

```powershell
Set-Location C:\Projetos\segsense\backend
.\mvnw.cmd verify

Set-Location C:\Projetos\segsense\frontend
npm ci
npm run lint
npm test
npm run build
```

`mvn verify` executa o teste unitário e o teste de integração com PostgreSQL via Testcontainers (Docker obrigatório).

## 10. Health e readiness

Com o backend no ar:

```powershell
Invoke-RestMethod http://127.0.0.1:8088/api/v1/system/info
Invoke-RestMethod http://127.0.0.1:8088/actuator/health
Invoke-RestMethod http://127.0.0.1:8088/actuator/health/readiness
```

Respostas esperadas: `system/info` com `name`, `version`, `applicationId` (`SEGSENSE`) e `operationalState` (sem dados sensíveis); health e readiness em `UP` quando o banco responde. Requisições `/api/**` devolvem `X-Correlation-ID` (UUID). `GET /api/v1/admin/publishers` anônimo responde **401**. Demais rotas `/api/**` sem política respondem **401** a chamadores anônimos (deny-by-default). Detalhes internos do Actuator permanecem ocultos. Não há login nem HTTP Basic.

## 11. Encerramento sem apagar dados

```powershell
Set-Location C:\Projetos\segsense
docker compose --env-file .env down
```

Isso remove o contêiner e a rede. O volume `segsense_pgdata` permanece.

## 12. Remoção opcional do volume

**Atenção: este comando apaga o banco local do SegSense de forma irreversível.**

```powershell
Set-Location C:\Projetos\segsense
docker compose --env-file .env down -v
```

Use apenas se quiser recomeçar o PostgreSQL do zero. As migrations serão reaplicadas na próxima subida do backend.

## 13. Solução de problemas comuns

| Sintoma | Causa provável | Correção |
|---|---|---|
| `Bind for 0.0.0.0:5437 failed` | Porta em uso | Altere `SEGSENSE_POSTGRES_PORT` no `.env` e o JDBC correspondente |
| Backend recusa conexão JDBC | Postgres ainda não está `healthy` | Espere o healthcheck e confira `docker compose ps` |
| Backend recusa `SEGSENSE_PUBLIC_BASE_URL` HTTP | Profile `local`/`test` ausente | Use `.\mvnw.cmd spring-boot:run` ou `SPRING_PROFILES_ACTIVE=local` |
| Flyway não acha V1 | Execução fora do Maven | Use `.\mvnw.cmd`; as migrations são copiadas no `process-resources` |
| Frontend em `localhost` com CORS recusado | Origem diferente da configurada | O local aceita `http://127.0.0.1:5178` e `http://localhost:5178` (lista explícita, sem `*`). Reinicie o backend após alterar `SEGSENSE_FRONTEND_ORIGIN` |
| `npm ci` falha | Node diferente de 24 ou lockfile alterado | Instale Node 24 LTS; não edite o lockfile à mão |
| Testcontainers falha | Docker parado | Inicie o Docker Desktop e rode `.\mvnw.cmd verify` de novo |
| Página mostra backend indisponível | API fora do ar ou URL errada | Confira `VITE_API_BASE_URL` e os três endpoints da seção 10 |

## 14. Segurança nesta etapa

O BFF usa Spring Security com deny-by-default. Públicos: `GET /api/v1/system/info`, `GET /actuator/health`, `GET /actuator/health/readiness`, `GET /api/v1/public/context-links/{opaqueToken}` e `GET /api/v1/public/demonstrations/{key}` (somente snapshot editorial `LIVE`). Oportunidades exigem `segsense.opportunity.read` / `write` / `submit` / `review`. Publicação autorizada internamente exige `segsense.publication.manage`. Links exigem `segsense.link.read` / `segsense.link.manage`. Demonstrações editoriais exigem `segsense.demonstration.read` / `write` / `approve` / `publish`. O restante de `/api/v1/admin/**` exige `segsense.catalog.read` / `segsense.catalog.write`. Sem IdP, chamadas administrativas reais recebem 401. Não há login, usuário local, token de sessão, API key, JWT próprio ou IdP. O frontend não armazena credencial, não persiste o token público e não simula cotação.

Detalhes: `documents/SEGSENSE_SEC_001.md` e `documents/SEGSENSE_ADR_002.md`.

## 15. Spider (Satellite Contract V1) e Icatu

O Satellite Contract V1 existe na Spider (`SPIDER-SAT-003`, DEMO ONLY). O SegSense EXPERIENCE consome `POST /v1/satellites/interactions`. O frontend não chama a Spider. O BFF não interpreta Intent, não escolhe route, adapter, executor nem Execution Plan. A Icatu permanece **NOT_IMPLEMENTED**. `SEGSENSE_ADR_003` continua a impedir que o SegSense **invente** o contrato; o consumo do contrato publicado pela Spider é o caminho autorizado. Preview canônico, IdP, callback e Data Plane (`SEGSENSE_REQ_002`) permanecem lacunas de produção.

Boundary da plataforma: `SIMULATED_INFRASTRUCTURE / MOCK_ONLY`.

O índice documental está em `documents/README.md`.
