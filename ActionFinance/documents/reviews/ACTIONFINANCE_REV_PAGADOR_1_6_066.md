# ACTIONFINANCE 066 — pagador real nas vendas

11/11/2026. A listagem pede o contrato 1.6 da Spider e a V28 guarda os oito campos. Spider, Loja e Hub não foram alterados.

## SSH

Os security groups `actionfinance-svc` e `actionfinance-db` continuam sem regra na porta 22. O serviço roda em Fargate, sem SSH. Nenhuma regra foi aberta.

## Arquivos

- `HttpSpiderInteractionClient`: a listagem envia `contractVersion` e `schemaVersion` 1.6 e só aceita a resposta 1.6. O lookup permanece 1.3.
- `PayReceiptSyncService`: lê os oito campos, string vazia vira nulo, e-mail `@amount.hub.local` é descartado, e um nulo que chega não apaga o valor gravado. Os campos entram na detecção de mudança. `payerKind`, `payerLabel`, `payerProvenance` e `orderReference` seguem a regra anterior.
- `PayReceiptViews`, `JdbcPayReceiptRepository` e a API expõem `payerName`, `payerEmail`, `storeOrderReference`, `storePaymentRequestId`, `processorPaymentId`, `processorApprovedAt`, `processorInstallments` e `purchaseDescription`.
- `V28__pay_receipt_payer_fields.sql`: oito colunas nullable em `actionfinance.pay_receipt_transaction`, sem default e sem backfill. A V12 já concede a tabela ao papel de execução, então não houve grant separado.
- Tela pelo patch `P04-pagador-real-1.6.patch`, aplicado com `git am -3` sobre `87103a5`, sem conflito.
- Versão 0.2.18 em `pom.xml`, `package.json`, `application.properties` e no script de imagem.

## Testes

Antes: `PayReceiptSyncMergeTest` 10, `HttpSpiderInteractionClientTest` 3, `PayReceiptMigrationV20Test` 1, `PayReceiptSyncIT` 9, `PayReceiptsPage.test.tsx` 8. Todos passaram.

Depois: `PayReceiptSyncMergeTest` 12, `HttpSpiderInteractionClientTest` 4, `PayReceiptMigrationV20Test` 1, `PayReceiptMigrationV28Test` 1, `PayReceiptSyncIT` 10, `PayReceiptsPage.test.tsx` 11. Todos passaram. O banco limpo do teste aplicou as 28 migrações, com as colunas novas nullable e sem default. O log de teste não contém nome nem e-mail.

## Publicação

| Item | Valor |
|---|---|
| Versão | 0.2.18, em `GET /api/v1/system/info` |
| Snapshot | `actionfinance-pre-v28-20261111`, available |
| Migração | task `actionfinance-migrate:10`. Flyway chegou à v28 a partir da v27 e a task foi encerrada |
| Task web | `actionfinance-web:35`, copiada da `:34`; só a imagem mudou |
| Flyway na web | `false` |
| Perfil | `production`. Sincronização de recebimentos ligada |
| Imagem | `sha256:e24aed7229409a9bfd13a06123ebdf6d63eb982ae0401afee4ddc501cd10a8f8` |
| Rollout | `COMPLETED`, desired 1, running 1, failed 0 |
| Health | `GET /actuator/health` 200 |

Retorno da aplicação: `actionfinance-web:34`, a 0.2.17. As colunas novas são nullable, então a 0.2.17 continua rodando com elas. O snapshot é o retorno do banco.

## Vendas

O ciclo automático das 12:53 UTC gravou a produção: 21 vendas, 21 com nome e e-mail, nenhuma sem o dado. A sincronização atualizou 21 e importou 0. O log desse ciclo não traz nome nem e-mail.

Há um segundo vínculo que a listagem continua recusando com `INVALID_PAYLOAD`, como já acontecia na 0.2.17. Essas linhas não foram regravadas.
