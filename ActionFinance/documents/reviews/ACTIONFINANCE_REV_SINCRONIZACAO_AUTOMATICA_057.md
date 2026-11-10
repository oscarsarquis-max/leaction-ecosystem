# ACTIONFINANCE_REV_SINCRONIZACAO_AUTOMATICA_057

10/11/2026. O Finance passa a puxar os recebimentos do ActionHub Pay sozinho, loja por loja, a cada 30 minutos. A chamada continua sendo `LIST_EXTERNAL_PAYMENTS`, contrato 1.4. Spider, Loja de Pães e Hub não foram alterados.

Código em `4abe6677`, na branch `feat/actionfinance-extrato-032`. A cópia do prompt está em [ACTIONFINANCE_PROMPT_SINCRONIZACAO_AUTOMATICA_057.md](../prompts/ACTIONFINANCE_PROMPT_SINCRONIZACAO_AUTOMATICA_057.md).

## Investigação

O botão **Sincronizar recebimentos** chama `PayReceiptSyncService.synchronize` em `POST /api/v1/pay-receipts/sync`.

O bloqueio de uma empresa é o índice único parcial `pay_receipt_sync_run_one_running` em `(tenant, company, origin_system, environment)` onde `status = 'RUNNING'`. Se já existe execução em andamento, `insertRunning` não insere e o serviço responde `VersionConflictException` (HTTP 409). Uma linha `RUNNING` mais velha que `sync-stale-after` (`PT60S`) é recuperada.

O histórico fica em `actionfinance.pay_receipt_sync_run`. A coluna `origin_system` guarda a origem dos dados (sempre `ACTIONHUB_PAY`). Não havia coluna para dizer se a execução foi manual ou automática. Na tela, o texto era "Última sincronização concluída" e "Última tentativa", sem a origem da execução.

## O que mudou

O agendador percorre as empresas com mapeamento Pay autorizado e chama o mesmo serviço do botão, uma empresa por vez. O intervalo é `actionfinance.pay-sync.interval`, 30 minutos em produção. A primeira execução ocorre na subida do processo; a seguinte espera 30 minutos depois que a anterior termina.

Se a empresa já tem sincronização em andamento, o ciclo registra o pulo e segue. A falha de uma empresa não interrompe as outras. Um único ciclo por vez usa o advisory lock de sessão `57057101`, segurado durante o percurso.

A migração V26 só acrescenta `trigger_kind varchar(16) not null default 'MANUAL'`, com a checagem `MANUAL` ou `AUTOMATIC`. Os registros antigos ficam como manuais. A interface ganhou a linha "Última execução: Automática · hh:mm" (ou Manual). O horário é o de São Paulo. As linhas que já existiam permanecem.

O agendador só existe com o perfil `production` e `actionfinance.pay-sync.scheduler-enabled=true`. Em `local-demo` e nos testes a propriedade fica falsa, e o perfil impede o bean mesmo que a variável de ambiente esteja ligada.

## SSH

Os security groups `actionfinance-svc` e `actionfinance-db` não têm regra na porta 22. O serviço roda em Fargate, sem SSH. Nenhuma regra foi aberta. A publicação usou a API da AWS, no mesmo caminho do 054R1.

## Publicação 0.2.12

| Item | Valor |
|---|---|
| Versão | 0.2.12 |
| Snapshot | `actionfinance-pre-v26-20261109`, `available`, progresso 100, antes da migração |
| Migração | `actionfinance-migrate:8`, Flyway ligado só nessa task. V26 aplicada: schema estava em 25, passou para "26 - pay receipt sync trigger", "now at version v26" |
| Task de migração | parada de propósito depois da V26. Código de saída 143. O log dela diz `pay-sync cycle skipped: receipt sync disabled` |
| Task web | `actionfinance-web:29`. Copiada da `:28`; só a imagem mudou |
| Flyway na web | `false` |
| Perfil | `production`. Sincronização de recebimentos ligada |
| Imagem na task | `sha256:f194e9991b1d3196706ba7f98a5e6bbf17c766cea392dd2152fad378a5ae8553` (linux/amd64) |
| Tag `0.2.12` no ECR | índice `sha256:f1c0b40aa8399c4153b03ac4c40685a9132a2f3ffecd1afc0e494b72e64c73c0`. A task usa o digest amd64, não o índice |
| Rollout | `COMPLETED`, desired 1, running 1, task `HEALTHY` desde 2026-11-10T09:52:24-03 |
| Health | `GET /actuator/health` 200, `{"status":"UP","groups":["liveness","readiness"]}` |
| SPA | `index-CIVwxnFE.js`, `index-DdIcnaWp.css` |

Retorno da aplicação: `actionfinance-web:28`, versão 0.2.11, imagem `sha256:f4fe545976b6dded0c9a3c4cab0d16c4eefcac21c077230ce3851505d0edf208`. Reverter a task não remove a coluna da V26.

## Testes da área

Não rodei a suíte inteira.

- `PayReceiptSyncSchedulerIT`: 7 testes, 0 falhas, depois da trava que deixa o agendador fora de `local-demo`. Cobre uma chamada por empresa ativa, empresa bloqueada, falha isolada, origem gravada, repetição sem recebimento novo, espera do advisory lock e ausência do bean de agendamento.
- `PayReceiptsPage.test.tsx`: 8 testes, entre eles o texto exato "Última execução: Automática · 15:30".
- `PayReceiptSyncIT`: 9 testes na execução anterior à trava de perfil. O caminho do botão não mudou com essa trava.

## Evidência em produção

Nenhum dado foi inserido à mão. O ciclo real consultou a Spider.

Aplicação no ar em 10/11/2026 09:53 (−03). Duas empresas autorizadas, nesta ordem:

| Quando (−03) | Origem | Resultado | Incluídos | Atualizados | Sem mudança |
|---|---|---|---|---|---|
| 09:53:10 | Automática | SUCCESS | 7 | 8 | 4 |
| 09:53:11 | Automática | FAILED | 0 | 0 | 0 |
| 10:23:12 | Automática | EMPTY | 0 | 0 | 19 |
| 10:23:12 | Automática | FAILED | 0 | 0 | 0 |

O segundo ciclo começou 30 minutos depois do primeiro. Na empresa que concluiu, os 19 recebimentos já vistos (7 + 8 + 4) voltaram como sem mudança: nada novo foi gravado. O status `EMPTY` é o da execução quando não há inclusão nem atualização; a linha de histórico dessa execução existe.

A outra empresa falhou nos dois ciclos, na primeira página, e a primeira empresa mesmo assim concluiu. A Spider respondeu 400 `INVALID_PAYLOAD`: "Atributo companyId não permitido neste ambiente." O Finance não alterou a Spider. A falha ficou registrada na execução dessa empresa.

## Tela

Não havia sessão autenticada de produção, o mesmo limite do 054R1 e do 055. A prova pública é o pacote `index-CIVwxnFE.js`, que contém "Última execução" e "Automática". A linha antiga "Última sincronização concluída" continua no pacote, porque este prompt só acrescentou a origem.

## Aceite

A sincronização automática está no ar a cada 30 minutos, com a origem gravada e uma loja isolada da outra. A Spider não foi alterada. A repetição não duplicou recebimentos. A empresa que a Spider recusa continua falhando sem impedir a outra.
