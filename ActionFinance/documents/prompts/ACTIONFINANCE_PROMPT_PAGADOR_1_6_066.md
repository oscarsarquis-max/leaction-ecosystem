# ACTIONFINANCE — Prompt 066 · Pagador real nas vendas (contrato 1.6 da Spider)

Baseado no prompt da conversa da Spider (`2026-11-09-spider-contextual-platform/PROMPT-CURSOR-FINANCE-PAGADOR-1.6.md`), **com duas correções: a migração é a V28 e ela segue o procedimento do Finance.**

## Contexto
A `spider-runtime-prod:5` está no ar. Com `contractVersion` e `context.snapshot.schemaVersion` **1.6**, cada item de `LIST_PAYMENT_TRANSACTIONS` traz `payerName`, `payerEmail`, `storeOrderReference`, `storePaymentRequestId`, `processorPaymentId`, `processorApprovedAt`, `processorInstallments` (número) e `purchaseDescription`. A chave vem sempre, com `null` quando não há o dado. Hoje o Finance pede 1.4, e é isso que gera "Pagador não identificado".

## Regras (sem regressão)
- Mudança só aditiva: `payerKind`, `payerLabel`, `payerProvenance`, `orderReference` e o merge atual ficam como estão.
- O lookup em **1.3** não muda.
- O isolamento por empresa não muda.
- **Nome e e-mail nunca no log.**
- Nada de taxa, líquido, liberação, itens ou documento do pagador: esses campos não existem.
- Não alterar a Spider, a Loja nem o Hub.
- Se algo disso não puder ser garantido, parar e relatar.

## Passos
0. **SSH:** atualizar a regra para o IP público atual (abrir a nova, testar, só então fechar a antiga).
1. **`HttpSpiderInteractionClient`:** só a listagem passa a enviar 1.6, nos dois campos. Validar que a resposta voltou em 1.6.
2. **Migração `V28__pay_receipt_payer_fields.sql`** em `ActionFinance/database/migrations` (o Finance está na **V27**; não usar V10). Mais os grants, se o padrão das migrações de `pay_receipt` exigir.
   - 8 colunas **nullable** em `pay_receipt`, sem default e sem backfill: `payer_name`, `payer_email`, `store_order_reference`, `store_payment_request_id`, `processor_payment_id`, `purchase_description` (texto com limite, como as atuais), `processor_approved_at` (texto ISO, como recebido) e `processor_installments` (integer).
3. **`PayReceiptSyncService`:**
   - lê os 8 campos sem transformar;
   - string vazia vira `null`;
   - `payerEmail` terminado em `@amount.hub.local` vira `null`;
   - merge `first(incoming, stored)`: um `null` que chega não apaga o valor gravado;
   - os campos entram na detecção de mudança.
4. **`PayReceiptViews`, `JdbcPayReceiptRepository` e a API:** expor os 8 campos com esses nomes em camelCase.
5. **Frontend, patch do Claude:**
   `git am -3 "C:\Projetos\claude\2026-11-09-actionfinance-corporate-analyser\patches\P04-pagador-real-1.6.patch"`
   (base `87103a5`; é o patch v2 da conversa da Spider, já revisado). Se houver conflito, parar e relatar. Não reescrever a tela.
6. **Testes, só da área, antes e depois:**
   - backend (`PayReceiptSyncService`, `HttpSpiderInteractionClient`, `JdbcPayReceiptRepository`): os 8 campos gravados; `null` que chega não apaga valor gravado; e-mail técnico descartado; log sem nome e sem e-mail; V28 em banco limpo;
   - frontend: `npx vitest run src/PayReceiptsPage.test.tsx`.
7. **Publicar 0.2.18:**
   - snapshot RDS `actionfinance-pre-v28-<data>`;
   - task de migração (Flyway continua desligado na web);
   - nova task web (`:35`); retorno para `:34` (as colunas novas são nullable, então a 0.2.17 roda com elas).
8. **Verificar:** depois do próximo ciclo automático (até 30 min) ou de uma sincronização manual da Loja de Pães:
   - quantas vendas passaram a ter pagador;
   - as vendas sem o dado continuam como antes;
   - o log não traz nome nem e-mail.

## Entrega
- `documents/reviews/ACTIONFINANCE_REV_PAGADOR_1_6_066.md` (curto): arquivos alterados, testes antes e depois, V28, versão, task, retorno e contagem de vendas com pagador identificado.
- Copiar este prompt para `documents/prompts/`. Commit, push e deploy.
