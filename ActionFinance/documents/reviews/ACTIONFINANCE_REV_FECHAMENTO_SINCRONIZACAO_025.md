# ACTIONFINANCE_REV_FECHAMENTO_SINCRONIZACAO_025

Data: 15/10/2026. Baseline: AF-BL-023 revisão 1.0. Produto: **0.1.0** (sem versão nova). Prompt 023 não foi implementado.

A Spider não foi alterada. O incidente **não** está tecnicamente encerrado: a tela autenticada ainda não mostrou uma sincronização nova depois da correção.

## Causa comprovada

A tentativa `b39468f1-3ab2-4396-b070-15514fb34ee4` chegou ao Finance, a Spider devolveu a página, e a gravação local quebrou.

| Peça | Evidência |
|---|---|
| Horário do run | `started_at` 15/10/2026 10:24:46.911Z · `finished_at` 10:24:51.114Z |
| Empresa / ambiente | `624023a4-57e3-415c-b7d0-925ca1acd3b7` · `PRODUCTION` |
| Correlação Finance | `afr-b39468f1-3ab2-4396-b070-15514fb34ee4` |
| `spider_message_id` | nulo. O id da interação não foi gravado porque a transação da página reverteu antes de `attachMessage` |
| Status no Finance | `FAILED` · `imported_count=0` · `updated_count=0` · `page_count=0` |
| Erro gravado | `commercial_application` ausente no `ResultSet` de `select * from actionfinance.pay_receipt_transaction` |
| Onde | `JdbcPayReceiptRepository` lido por `applyPage` (`PayReceiptSyncService` linha da chamada) e, 12 s antes, por `listReviews` no overview |
| Schema na hora | Flyway **1–19**. `commercial_application` = 0 |
| Serviço | `actionfinance-web:14` · digest `sha256:cb0619f2f1b4b38c86da43298cc11cd1979dbe25dc4dc5f25c1f6533072c528a` · `ACTIONFINANCE_FLYWAY_ENABLED=false` |

O código publicado já lia a coluna. O Flyway do processo web está desligado de propósito; a migration V20 não tinha sido aplicada no origin.

Os contadores do Monitor (2 encontrados, 0 criados, 2 atualizados, `COMPLETED`) **não** são os do Finance. O Finance ficou 0 criados e 0 atualizados, com status `FAILED`. `COMPLETED` é o estado técnico da projeção na Spider. O HTTP que o Finance aceita para seguir a gravação é `READY` (ou status ausente). Esta tentativa passou dessa porta: o erro está no `SELECT` seguinte, não numa troca genérica de `READY` por `COMPLETED`.

A mensagem da SPA “Não foi possível concluir a operação” é o fallback de `api.ts` quando o POST/GET volta com erro HTTP sem texto próprio. “Nenhuma sincronização ainda” é o estado da tela quando `latestRun` vem vazio. Às 10:24:39 o overview já quebrava no mesmo `SELECT`, então a tela não conseguia mostrar o run.

## Destino da tentativa original

| Etapa | Resultado |
|---|---|
| Recepção no BFF | Sim. Run inserido `RUNNING` e depois fechado `FAILED` |
| Chamada à Spider | Sim, a ponto de entrar em `applyPage`. Id da mensagem: **lacuna** — não persistido |
| Persistência dos dois pagamentos | Não. A página reverteu. Os 11 recebimentos já armazenados da empresa permaneceram |
| Resposta à SPA | Erro HTTP. O corpo útil não foi um resumo de sucesso |

Não reescrevi esse run para parecer sucesso.

## Correção

Ensaio na mesma base, dentro de transação: V20 aplicada, coluna presente, `ROLLBACK`, coluna ausente de novo. Em seguida o mesmo script com `COMMIT` e o registro Flyway.

| Campo | Valor |
|---|---|
| Script | `V20__pay_receipt_commercial_identity.sql` |
| Checksum | `-145522935` |
| Efeito | colunas anuláveis de identidade comercial/pagador e check de `payer_kind` |
| Run original | continua `FAILED`, 0/0 |
| Recebimentos PRODUCTION da empresa | 11 antes e 11 depois |
| Títulos / baixas / movimentos | 0 / 0 / 0 antes e depois |

Nenhuma imagem nova. Nenhuma task web reiniciada. Host público depois da correção: `version=0.1.0`, `receiptSyncEnabled=true`, SPA `index-CRjEQs1k.js`. Sem sessão, `GET` dos recebimentos responde 401 `UNAUTHORIZED`, não 500.

## Mapeamento de estados

| Camada | Valores desta jornada |
|---|---|
| HTTP Spider aceito pelo Finance | `READY` ou ausente segue a gravação. Outro valor encerra o run sem gravar a página |
| Run Finance | `RUNNING`, `SUCCESS`, `EMPTY`, `PARTIAL`, `FAILED` |
| Monitor | estado técnico da projeção, aqui `COMPLETED`. Não substitui o status do run |
| Contadores Monitor | encontrados / criados / atualizados da projeção. Não são `imported_count` / `updated_count` |

## Provas novas

Não houve clique autenticado depois da correção. Uma sonda direta não substitui esse clique. A repetição, a recarga e a ausência de duplicação na interface ficam **não verificadas**.

## Rollback

O serviço web não mudou. Para desfazer só o schema:

```sql
BEGIN;
ALTER TABLE actionfinance.pay_receipt_transaction
    DROP COLUMN commercial_application,
    DROP COLUMN commercial_description,
    DROP COLUMN payer_kind,
    DROP COLUMN payer_label,
    DROP COLUMN payer_provenance,
    DROP COLUMN payment_method,
    DROP COLUMN processor_name,
    DROP COLUMN provider_status;
DELETE FROM actionfinance.flyway_schema_history WHERE version = '20';
COMMIT;
```

Isso devolve a falha do `SELECT`. Não foi executado.

## Critérios

| Critério | Resultado |
|---|---|
| Tentativa original localizada no Finance | PASS |
| Causa da falha de gravação | PASS — coluna ausente |
| Spider e Hub intocados | PASS |
| Schema V20 no origin, histórico do run preservado | PASS |
| Sem efeito em título, baixa, movimento e saldo | PASS — contagens 0/0/0 |
| Imagem nova desnecessária | PASS — mesmo digest |
| Clique autenticado, lista, detalhe, repetição e recarga | NÃO VERIFICADO |
| Incidente encerrado na interface | FAIL — falta a prova autenticada |
| Tesouraria 023 | Não iniciada |
| Aceite do proprietário | Não atribuído |

## O que permanece

O impedimento desta tentativa (o `SELECT` quebrado) foi removido. Continua pendente a sincronização vista na interface, com última tentativa, último sucesso e os registros correspondentes. Também continuam abertas a integridade dos recebimentos (019), a rastreabilidade pública (020), a captura (021) e a Tesouraria MP (023).
