# ACTIONFINANCE_REV_INTEGRIDADE_RECEBIMENTOS_019

Identificador: ACTIONFINANCE_REV_INTEGRIDADE_RECEBIMENTOS_019. Data: 09/10/2026. Documento independente. Aceite de cadastros **não** é aceite desta integração. Conciliação bancária, contas a pagar e baixa automática **não** foram implementadas e permanecem fora do recorte.

## 1. Causa demonstrada

O caso de R$ 90,00 (prefixo visível `b6cf9b7a`, atualizado em 06/10/2026) não se explica só pelos nove pedidos antigos. Há duas perdas distintas.

### 1.1 Interface pública do Finance (build publicado)

Host `https://actionfinance.actionhub.com.br/` serve `index-BYEiixeg.js` (imagem `actionfinance-web:12` / cadastros-017). O código local correspondente a esse build, em `PayReceiptsPage.tsx`, grava **Contraparte / método / processador / conta de destino** como texto fixo «Não informado». `PayReceiptViews.TransactionView` publicado não transporta pagador, aplicação comercial nem método. Isso é limitação da implementação, não prova de ausência na origem.

`paidText` trata `paidAmountMinor == null` como ausente. `pendingText` / `isPending` só olhavam `paidAmountAbsent === true`. Se a API omite a flag, a lista mostra **Pago: Não informado** e **Pendência: Nenhuma**. O cálculo de `reviewRequired` no backend também não inclui valor pago ausente.

### 1.2 Contrato operacional Hub → Spider → Finance

O admin Hub (`GET /admin/payments`) junta `users.email`, contrato/`subject_id`, produto e o payload (`paid_amount_cents` só com `paid_amount_confirmed === true`). Isso é **dado persistido**, não consulta ao Mercado Pago no momento da listagem.

`LIST_PAYMENT_TRANSACTIONS` lia só a linha de `orders` (sem join de cliente/produto) e **não expunha** pagador, descrição comercial nem nome do processador. Já expunha `paidAmountMinor` quando o payload confirma o pago, e `paymentMethod` quando o payload tem método.

A Spider (`ActionHubPayListIdentity.normalizeItem`) reencaminhava cobrado/pago e **descartava** `paymentMethod` e qualquer campo comercial novo.

O Finance persistia cobrado/pago e **não persistia** pagador, aplicação, método ou processador. Sincronização bem-sucedida avançava o checkpoint e **não relia** itens já vistos: enriquecimento com o mesmo `updated_at` era ignorado. `amountMinor` nunca é copiado para pago.

A base Hub **local** (`leaction_hub` em `:5433`) tem 9 pedidos e **não** contém `b6cf9b7a…`. A transação de R$ 90,00 está no Hub público. Identidade só pelo prefixo não foi usada como prova final.

## 2. Matriz por campo (percurso autorizado)

Fontes: código publicado vs. código corrigido; admin Hub vs. `publicListItem`; Spider `normalizeItem`; Finance `toView` / UI. Instante: 09/10/2026. Sem e-mail real, CPF, token ou ID completo de pagamento no relatório.

| Campo | Admin Hub (persistido) | LIST (antes → depois) | Spider (antes → depois) | Finance persistido (antes → depois) | Finance UI publicada | Primeira fronteira da perda |
|---|---|---|---|---|---|---|
| ID da operação | `orders.id` | presente | presente | `transaction_id` | prefixo | — |
| Empresa AF | vínculo autorizado | `companyId` no envelope | conferido | `company_id` | rastreio | — |
| Aplicação comercial | `app_id` / lojadepaes | ausente → `commercialApplication` | descartado → passa | ausente → coluna | «ActionHub Pay» só | LIST + UI |
| Descrição / pedido | plano/produto | só `orderReference`=id → + descrição | id só → passa descrição | só referência | referência curta | LIST |
| Cliente | e-mail / subject | ausente → `payerKind/Label` | ausente → passa | ausente → colunas | «Não informado» fixo | LIST (sem join) + UI |
| Contraparte interna | — | não criada | — | não criada | — | não aplicável |
| Método | `payload.method` | já no item | **descartado** → passa | ausente → coluna | fixo | Spider |
| Processador | evidência MP no payload | ausente → `processorName` se MP evidenciado | ausente → passa | ausente → coluna | fixo | LIST + UI |
| Ref. no processador | `gateway_reference` | `processorReference` | passa | passa | só no bloco recolhido | UI (escondido) |
| Conta de destino | não no contrato de lista | ausente | ausente | ausente | fixo «Não informado» | origem não coletou neste contrato |
| Moeda | payload | `currency` se ISO-3 | passa | passa | implícita | — |
| Cobrado | `amount_cents` / negociado | `amountMinor` | passa | `amount_minor` | R$ 90,00 no caso | — |
| Pago | `paid_amount_cents` se confirmado | idem; sem confirmação = ausente | passa | `paid_amount_minor` | «Não informado» no caso | ver §3 |
| Estorno / tarifa / líquido / disponibilidade | não no contrato | não derivado | — | não derivado | — | não coletado; não inferir |
| Datas | created/updated | `createdAt`/`updatedAt`/`originRevision` | passa | passa | datas no detalhe recolhido | UI (escondido) |
| Ambiente / classificação | live_mode / flags | `classification` | passa | passa | classificação | — |
| Pendência | — | `reviewRequired` (cobrado) | idem | flag sem pago | «Nenhuma» com pago ausente | Finance UI + regra |

O admin Hub em «Todas as apps» + «Incluir testes» **não** é comparável ao recorte Loja/`LIST` sem alinhar app e critério de teste.

## 3. O que o caso de R$ 90,00 prova e o que não prova

| Afirmação | Estado |
|---|---|
| Prefixo `b6cf9b7a` no Hub e no Finance refere a mesma operação | **Não confirmado em produção neste ciclo** — falta leitura autenticada do ID completo nas duas pontas |
| Hub admin mostra cliente, cobrado R$ 90, pago R$ 90, approved | Evidência do proprietário; admin lê **pedido persistido** |
| Finance publicado mostra cobrado R$ 90, pago/contraparte «Não informado», pendência «Nenhuma» | Coerente com o build `index-BYEiixeg.js` |
| Pago ausente no Finance = Hub não tem pago | **Não.** LIST já pode ter `paidAmountMinor` se `paid_amount_confirmed`. A UI e o checkpoint podem esconder |
| Os nove históricos estão completos após esta correção | **Não.** Continua a faltar coleta histórica / APPLY separado |

## 4. Alterações feitas (código; via Spider)

| Peça | Mudança |
|---|---|
| Hub `spider-pay-lookup.js` | LIST junta e-mail/produto quando não isolado; expõe pagador, aplicação, descrição, método, processador evidenciado, `providerStatus`. Pago **não** sai de `amount_cents` |
| Spider `ActionHubPayListIdentity` | Reencaminha os campos comerciais |
| Finance V20 | Colunas comerciais/pagador/método/processador. Sem título, baixa ou movimento |
| Finance sync | Relê a janela em sync novo (não usa checkpoint para pular). Atualiza no mesmo `originRevision` se enriquece. Recusa observação mais antiga. `pendingKind` separado: ambiente / pago ausente em aprovado / revisão / não pago esperado |
| Finance UI | Lista: cliente, aplicação, método, valores, situação, pendência. Detalhe: identidade, cliente com proveniência, pedido, método, cobrado, pago e datas visíveis. Rastreio técnico recolhido. Sem fabricar cadastro |

Não há acesso direto AF→Hub/MP.

## 5. Testes

| Prova | Resultado |
|---|---|
| Hub `spider-pay-lookup.test.js` (18) | ok — inclui pagador/método/pago confirmado e pago não inventado |
| Spider `ActionHubPayListIdentityTest` | ok — preserva pago, pagador, método, aplicação |
| Finance `PayReceiptSyncIT` + OIDC (10) | ok — pago presente; pagador; aprovado sem pago = `PAID_AMOUNT_MISSING`; pendente sem pago = `UNPAID_EXPECTED`; enriquecimento no mesmo revision; observação antiga não apaga; idempotência; sem movimento financeiro |
| Finance `PayReceiptsPage.test.tsx` (5) | ok — pendência correta; detalhe com cliente recuperado sem inventar contraparte |

Regressão de carris de pagamento do Hub: `spider-pay-lookup.test.js` e `pay-regression.test.js` existentes não foram relaxados. Sem cobrança real criada para teste.

## 6. Dados recuperados, não coletados e dependências

### Recuperados no contrato (novos eventos e releitura)

Pagador externo (e-mail ou subject, com proveniência ActionHub Pay), aplicação comercial, descrição/plano quando persistidos, método, processador se o payload evidencia Mercado Pago, situação no processador, pago confirmado, pendência específica.

### Não coletados neste contrato

Conta de destino, identificador do recebedor no processador, tarifas, líquido, disponibilidade bancária, estorno detalhado, itens de linha além da descrição, nome civil quando só há e-mail. Nove históricos sem `paid_amount_confirmed` / sem cliente no pedido **não** ficam completos só com esta mudança. APPLY histórico de pedidos Hub permanece **separado** e não autorizado aqui.

### Dependências reais

1. Publicar **Hub + Spider + Finance V20** a partir de um candidato **identificado**, não do working tree misto de `C:\Projetos`.
2. Sincronização autenticada no Finance público (Cognito do operador). Sem sessão neste ciclo; senha/MFA/cookies não foram pedidos no chat.
3. Prova do ID completo `b6cf9b7a…` no host público depois do sync — HTML 200 e fixture local **não** bastam.
4. Monitor / correlação da execução real só depois do sync publicado.

## 7. Versões

| Peça | Publicado agora | Candidato desta correção |
|---|---|---|
| Finance | `actionfinance-web:12` · SPA `index-BYEiixeg.js` · Flyway **v19** | código local + V20; **não publicado** (árvore mista) |
| Hub LIST | admin com cliente/pago; LIST sem pagador | `publicListItem` ampliado; **não publicado** |
| Spider | descarta método/pagador | passa os campos; **não publicado** |
| Rollback AF | imagem 017 / `web:12` | — |

Funções explícitas **fora** deste recorte: conciliação bancária, contas a pagar, baixa automática. Importar continua a não criar título nem movimento.

## 8. Antes / depois (mesma transação — prova de código, não do host)

| Superfície | Antes (build público / código inspecionado) | Depois (candidato local) |
|---|---|---|
| Lista | Contraparte fixa «Não informado»; pendência «Nenhuma» com pago nulo | Cliente da origem; pendência só se ambiente, pago ausente em aprovado, ou revisão |
| Detalhe | Essenciais dentro de `details` | Operação, cliente, pedido, método, cobrado, pago e datas visíveis |
| Sync | Checkpoint pula item já visto | Relê e enriquece sem apagar observação mais nova |
| Pago | Null ≠ pendência | `PAID_AMOUNT_MISSING` se aprovado; `UNPAID_EXPECTED` se pendente/cancelado |

A prova pública do ID `b6cf9b7a…17133322` **não** foi encerrada neste ciclo. Impedimento concreto: sem sessão autenticada no Finance e sem publicação identificada de Hub+Spider+AF. O trabalho independente (contrato, persistência, UI, testes, esta revisão) está concluído.
