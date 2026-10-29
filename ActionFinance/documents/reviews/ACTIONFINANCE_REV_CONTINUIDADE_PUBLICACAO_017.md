# ACTIONFINANCE_REV_CONTINUIDADE_PUBLICACAO_017

Identificador: ACTIONFINANCE_REV_CONTINUIDADE_PUBLICACAO_017. Data: 05/10/2026. Documento independente. Aceite integral do produto: **NÃO**. A publicação desta fatia foi solicitada e executada.

O [REV_015](ACTIONFINANCE_REV_PRE_PUBLICACAO_CADASTROS_015.md) registrou, sob a restrição então vigente, que faltava um sim para a cópia do origin. Instrução posterior do proprietário: «por favor providencie, mas quero isso em producao logo». O Prompt 016 traduziu isso em cópia protegida, ensaio, migração e publicação após verificações satisfatórias. Este ciclo **não** pediu o mesmo sim outra vez.

O parecer de interface do 014 permanece encerrado. Pay, Spider, Panne, Hub e Cognito não foram alterados.

## Publicado versus só construído

| Estado | Peça | Evidência |
|---|---|---|
| **Publicado** | Schema origin em V19 | Inspect pós-migrate: `flyway=1..19`, `has_v14=true`, `has_v19=true`, V13 checksum `728072343` |
| **Publicado** | Serviço web `actionfinance-web:12` | ECS desired=1 running=1 rollout COMPLETED HEALTHY |
| **Publicado** | Imagem no serviço | `actionfinance@sha256:9b90e33984cef1ef0ae4fe6a066a4a89db348c9d594559b5bb2b66b6dcd3d894` |
| **Publicado** | Frontend servido | HTML 200 · hash `14ffc219…` · SPA `index-BYEiixeg.js` |
| Enviado ao registro, não é o serviço | Tag `cadastros-017` (mesmo digest) | Registro ≠ publicação até o `update-service` |
| Só auxiliar de ensaio | `copy-017` / `copy-017b` / `copy-017c` / `copy-017d` | Helpers do ensaio in-VPC; não servem o host |
| Registrado, não é o serviço | `actionfinance-migrate:5` | Família one-shot; encerrada após V19 |

## Tabela

| Item | Resultado | Evidência |
|---|---|---|
| Autorização desta fatia | **Vigente** | Instrução do proprietário + Prompt 016/017. Pedido 015 permanece histórico. |
| Canal de leitura | **Canal existente** | Fargate `actionfinance-dbadmin` / execution `actionfinance-migrate-execution` + `GetSecretValue` pontual no MasterUserSecret. **Não** há papel dedicado só-leitura. Política pontual removida após cada tarefa. Sem segredo no chat. |
| Cópia real do origin | **Executada** | Dump custom só do schema `actionfinance` dentro da tarefa. Destino: sidecar Postgres 17.6 na mesma task Fargate (awsvpc, `assignPublicIp=DISABLED`). Não é o RDS, não é `actionfinance_pgdata_17`, não é o disco do operador. |
| Ensaio V14–V19 na cópia | **Satisfatório** | IDs, títulos e `amount_minor` iguais; V13 `728072343`; V19; `document_pending=1`. `COPY_REHEARSAL_OK`. |
| Build da candidata | **Reproduzível** | Worktree destacada em `4e556ecd` + overlay da fatia. Working tree misto de `C:\Projetos` **não** entrou na imagem. |
| Migração do origin | **Aplicada** | `actionfinance-migrate:5` · «Successfully applied 6 migrations … now at version v19» |
| Publicação web | **Aplicada** | `actionfinance-web:12` estável |
| Prova autenticada pública | **Pendente de login humano** | Host e redirect OIDC prontos. Sem fornecedor fictício. Sem CSV sintético na empresa produtiva. |
| Aceite do produto | **Não atribuído** | Separado desta publicação |

## 1. Autorização e acesso

Autorização de publicar esta fatia: concedida. Impedimento de acesso **não** bloqueou a cópia: o canal operacional existente usa o secret master do RDS, não um papel de dump só-leitura. Isso foi o canal vigente, não um contorno. Sem infraestrutura paga nova.

## 2. Cópia e ensaio

Tarefa `19954fec0f5d44b4957aa9ba3eec519a`. Worker `copy-017d` · digest `sha256:f8056baeab5942b4bbb1072909810306d20ad87e0c8930943bfb14560d48cbfd` (Flyway 11.10.1 + `pg_dump` 17).

| Agregado | Origin (antes) | Cópia restaurada | Cópia após V19 |
|---|---|---|---|
| Flyway | 1–13 | 1–13 | 1–19 |
| Checksum V13 | 728072343 | 728072343 | 728072343 |
| Contraparte | 1 (`6efb95bb-b29c-4ad0-b4f8-f6de0b60ad88`) | mesmo ID | mesmo ID |
| Títulos / vínculos / soma | 0 / 0 / 0 | iguais | iguais |
| `document_pending` | (coluna ainda não existia) | — | 1 |

Dump: SHA-256 `8c347249bd1e042549bfe9c7c25efb6aec147049060ba78aa5a977ea0d733542`, 126336 bytes. Destruído na tarefa. Retenção: efêmera até o stop da task. Destino e prazo: sidecar Fargate, até `COPY_REHEARSAL_OK`. Dump **não** foi ao repositório, ao chat nem ao disco do operador.

Ensaio sintético do 015 não foi refeito e não substitui esta cópia. Rollback isolado do 015 permanece válido: imagem anterior `sha256:06e067e7…` contra schema V19, documento `77000000000116` e claim=1 intactos; Flyway da imagem anterior avisou «schema 19 newer than latest available migration 12» e não aplicou nada.

## 3. Identidade da candidata

Manifesto de 25 arquivos do 015 foi o ponto de partida. A imagem saiu de worktree em `4e556ecd` (logout/Cognito 010) mais overlay de cadastros e patches compartilhados necessários (não o working tree misto).

| Campo | Valor |
|---|---|
| Tag local | `actionfinance:cadastros-017` |
| Digest | `sha256:9b90e33984cef1ef0ae4fe6a066a4a89db348c9d594559b5bb2b66b6dcd3d894` |
| JAR | `df50a6bfbb0e20934d319722f225c59b15a3ddb2ae01bb4746ca413aae315180` |
| Flyway no JAR | V1–V19 |
| SPA | `index-BYEiixeg.js` |
| `index.html` | `14ffc219b5110fd54438c967e5fd3125079f44a33a3188c1748bd5423d1efd41` |

## 4. Origin, backup e rollout

Revalidação imediatamente antes do migrate (ainda V13, 1 contraparte, 0 títulos). Backup final: retenção automática RDS 7 dias; `LatestRestorableTime` 05/10/2026 19:56 UTC. Sem dump extra no laptop.

1. Registro: `actionfinance-web:12` e `actionfinance-migrate:5` no digest `9b90e339…`. Neste ponto **ainda não** estava no serviço.
2. `run-task` migrate. Flyway validou 19 arquivos, aplicou V14–V19 no RDS `actionfinance`.
3. A imagem candidata **sobe** Tomcat após o Flyway (OIDC presente). A família migrate:4 antiga saía 1. A tarefa foi interrompida após V19 (exit 143 / SIGTERM). Não ficou como serviço.
4. Inspect: origin `1..19`, V13 intacto, mesmas contagens.
5. `update-service` → `actionfinance-web:12`. Rollout COMPLETED. Tarefa HEALTHY. `ACTIONFINANCE_FLYWAY_ENABLED=false`.

## 5. Verificações públicas (sem sessão)

Host `https://actionfinance.actionhub.com.br/`:

- HTML 200, hash idêntico ao JAR, SPA e CSS 200.
- `/actuator/health` UP (liveness, readiness).
- `/oauth2/authorization/actionfinance` → 302 para o Hosted UI Finance do produto.
- API de cadastros anônima: 401.

Não houve INSERT de fornecedor fictício nem confirmação de CSV sintético na empresa produtiva.

Prova autenticada pendente: **só o login humano**. Abrir o host e autenticar. Sem senha, MFA ou cookies por mensagem. Alcance da prova em falta: listar o cadastro legado, abrir detalhe e confirmar que a fatia de cadastros responde na sessão real — sem gravar fornecedor novo e sem importar o CSV de ensaio.

## 6. Recuperação disponível

| Peça | Ação |
|---|---|
| Frontend / API | Recolher `actionfinance-web:11` · `sha256:06e067e772f65d37a0cf43c53022e32d9e0a76eb9841cfebaf75d684b28f953c` (ensaio 015 contra V19). |
| Schema | **Não** desfazer. Restore sobre produção e apagar escritas posteriores **não** autorizados. |
| Dump do ensaio | Destruído. Não é o meio de recuperação. |

## Limites

Sem restore sobre produção. Sem importação produtiva em massa. Sem APPLY de pagamentos. Sem movimentação financeira. Sem integração nova. Sem alteração de Pay, Spider, Panne ou Cognito.

Evidência: `documents/reviews/evidence/continuidade-publicacao-017/`.
