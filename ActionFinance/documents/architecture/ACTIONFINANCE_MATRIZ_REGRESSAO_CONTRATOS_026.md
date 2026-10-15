# ACTIONFINANCE_MATRIZ_REGRESSAO_CONTRATOS_026

Data: 15/10/2026. Complementa [ACTIONFINANCE_PROPOSTA_CONTRATOS_FINANCEIROS_026](ACTIONFINANCE_PROPOSTA_CONTRATOS_FINANCEIROS_026.md). Nada desta matriz foi executado como publicação. Dados marcados como sintéticos não entram no produto.

## 1. Referências congeladas

| Referência | Valor observado em 15/10/2026 |
|---|---|
| Produto | 0.1.0 |
| Imagem | `actionfinance-web:14` · `sha256:cb0619f2f1b4b38c86da43298cc11cd1979dbe25dc4dc5f25c1f6533072c528a` |
| Schema | Flyway V20 |
| Pedido de lista | contrato 1.4 |
| Pedido pontual | contrato 1.3 |
| Catálogo no repositório | 1.0 a 1.5; 1.5 já contém `biblioteca` e o mesmo `financialList` |
| Empresa | `loja-de-paes` / Loja de Pães / `624023a4-57e3-415c-b7d0-925ca1acd3b7` / `America/Sao_Paulo` |
| Caso R$ 90 | `b6cf9b7a-d8d3-42a7-873e-818f17133322`, cobrado 9000, pago ausente, `INDETERMINATE` |
| Run original | `b39468f1-3ab2-4396-b070-15514fb34ee4` = `FAILED` |
| Run seguinte | `1f159934-4b30-446c-8c2c-3f84176e3025` = `EMPTY`, 0/0 |
| Armazenados | 11; títulos 0; baixas 0; movimentos 0 |
| Spider | não publicada neste ciclo; diff local de identidade da lista permanece fora do ar |

Invariantes que uma implementação futura não pode quebrar: pedidos 1.3 e 1.4, isolamento da Spider, Monitor como observação, planos e pagamentos da Loja no percurso próprio, autenticação, filtro por empresa, e o histórico desses 11 registros.

## 2. Compatibilidade

| Produtor | Consumidor | Resultado exigido |
|---|---|---|
| Lista 1.4 atual | Finance atual | id, cobrado e situação como hoje; pago continua ausente se a origem não confirmar |
| Lista 1.4 com campos novos aditivos | Finance atual | grava o que já entende; não falha por chave desconhecida; não copia cobrado para pago |
| Lista 1.4 atual | Finance futuro | `fieldPresence=UNKNOWN` não apaga pago ou pagador que já existirem |
| Propósito novo de movimento | Finance atual | não é chamado; a sincronização de cobrança não cria movimento |
| Envelope `PRODUCTION` | qualquer um | não grava `classification=REAL` sem evidência do pagamento |

## 3. Testes de contrato a escrever na implementação

Não rodar contra produção neste ciclo.

| Caso | Entrada | Resultado |
|---|---|---|
| Resposta atual | item só com id e `amountMinor=9000` | grava cobrado; pago ausente; não cria título |
| Campo novo | o mesmo item mais `paidAmountMinor` confirmado | atualiza pago; cobrado permanece 9000 |
| Ausência explícita | `paidAmountAbsent=true` e sem valor | não herda 9000 |
| Omissão | segunda resposta sem a chave de pago, `fieldPresence=UNKNOWN` | conserva o pago já gravado |
| Estado desconhecido | `normalizedStatus=NOVO` | guarda o original; não confirma pago |
| Página repetida | mesmo cursor e mesmos ids | 0 criados na repetição |
| Fora de ordem | revisão antiga depois de revisão nova | a antiga não substitui |
| Timeout | sem corpo | run `FAILED` ou `PARTIAL`; linhas anteriores ficam |
| Falha no meio da página | erro de persistência | a transação da página reverte; o run não vira `SUCCESS` |
| `EMPTY` | página sem item novo | status `EMPTY`; não é enriquecimento |
| Outra empresa | mesmo `transactionId` em outro `companyId` | não aparece no seletor da Loja |
| Sandbox no envelope | `environment=SANDBOX` | não entra na lista `PRODUCTION` |

## 4. Casos financeiros sintéticos

Marca obrigatória no fixture: `"synthetic": true`. Proibido enviá-los ao host público.

| Caso | Cobrado | Pago | Efeito permitido |
|---|---|---|---|
| R$ 90 identificado, como o caso real | 9000 | ausente | observação; pendência de ambiente se não houver `live_mode` |
| Aprovado sem pago confirmado | 9000 | ausente, situação confirmada | pendência de pago; não liquidar |
| Cancelado | 9000 | ausente | situação cancelada; histórico permanece |
| Parcial | 9000 | 4000 confirmado | pago 4000; saldo da obrigação, se existir, não se fecha sozinho |
| Tarifa e líquido | — | movimento `FEE` 500 e `RELEASE` 8500 | não somar os dois como duas receitas |
| Estorno | — | `REFUND` ligado ao id original | duas linhas |
| Transferência | — | `TRANSFER` | não é despesa operacional até o operador classificar |
| Liberação | — | `RELEASE` com `relatedPaymentId` | não é segunda receita do mesmo pagamento |

## 5. Implantação futura, em ordem

1. Ensaio em cópia: imagem nova lê schema antigo; imagem antiga sobe com schema novo sem apagar coluna.
2. Publicar o Finance só se o schema que ele exige já estiver aplicado. Bloquear o contrário: foi o incidente V19/V20.
3. Adapter da lista só com autorização específica. Não publicar o diff local como atalho.
4. Movimento e posição não saem no mesmo release da observação.
5. Nenhuma etapa desliga a Spider, o Hub ou a Loja para comparar.

Rollback de aplicação: voltar a imagem anterior se ela ainda lê o schema. Rollback de schema destrutivo (apagar coluna já preenchida) não é o plano de recuperação. Escritas já commitadas permanecem; o run seguinte é que deixa de enriquecê-las.

Interromper a publicação se: a lista 1.4 passar a responder erro para o pedido atual; o número de recebimentos da empresa cair; aparecer título, baixa ou movimento gerado pela sincronização; ou um pagamento `SANDBOX` surgir na visão `PRODUCTION`.

## 6. Aceite desta proposta

| Critério | Resultado neste ciclo |
|---|---|
| Mapa do contrato publicado e do domínio interno | entregue para revisão |
| Caso R$ 90 sem transformar cobrado em pago | entregue |
| Runs `FAILED` e `EMPTY` distinguidos | entregue |
| Número 1.5 não reutilizado | entregue; o próximo número fica em aberto |
| Implementação, migration, backfill, publicação | não feitos |
| Aprovação do analista e do proprietário | não atribuída |
