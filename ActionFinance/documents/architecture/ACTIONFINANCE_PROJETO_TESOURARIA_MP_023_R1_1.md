# ACTIONFINANCE_PROJETO_TESOURARIA_MP_023_R1_1

Data: 15/10/2026. Baseline AF-BL-023 revisão 1.1. Produto **0.1.0**. Este documento não implementa tesouraria, não importa extrato e não altera saldo. Aceite do proprietário: **não atribuído**.

A Spider permanece como está. Onde a lista de cobranças não traz o campo, a dependência fica registrada e o trabalho segue sem atalho Finance → Hub ou Finance → Mercado Pago.

## 1. Fontes que já existem

| Fonte | O que é | O que não é |
|---|---|---|
| ActionHub Pay, lista `LIST_PAYMENT_TRANSACTIONS` | Cobranças já gravadas no Hub, lidas pelo Finance via Spider | Extrato, liberação, tarifa ou saldo da conta MP |
| Mercado Pago como processador | Meio das cobranças e, no futuro, das saídas | A própria contabilidade da empresa |
| Mercado Pago como conta | Dinheiro em conta e liberações, quando houver evidência da conta | A lista de pagamentos do Hub |
| Finance | Obrigações, recebimentos observados, contas a pagar já existentes | Não executa o pagamento nesta etapa |

A capacidade publicada não cobre extrato nem relatório de liberações. Documentação do MP, se consultada depois, não prova que a conta da Loja tenha esse acesso. Não há cliente direto, scraping nem relatório agendado.

Enquanto a Spider não transportar um extrato — e esta revisão proíbe criá-lo nela — a fonte distinta proposta é arquivo real, com prévia, validação, proveniência e deduplicação. Não está implementada.

## 2. Perímetro da conta

Não equiparar `lojadepaes`, a empresa `624023a4-57e3-415c-b7d0-925ca1acd3b7`, um `collector_id` e a conta MP. Este ciclo não leu titularidade, moeda da conta nem período acessível no MP. Sem isso, nenhum saldo da conta pode ser atribuído à Loja.

Pergunta que só o proprietário fecha: a conta que recebe a Loja também recebe outra aplicação ou movimento pessoal? Até a resposta, o projeto trata o perímetro como **não demonstrado** e não soma o saldo.

## 3. Três bases

| Base | Conteúdo | Condição para afirmar |
|---|---|---|
| Posição informada pelo MP | Conta, moeda, instante, disponível segundo a fonte | Extrato ou relatório daquela conta. Não existe hoje |
| Saldo gerencial | Saldo inicial comprovado mais movimentos válidos | Saldo inicial ainda não comprovado. Não preencher zero |
| Projeção | Saldo-base declarado, compromissos restantes, hipóteses nomeadas | Não altera o realizado |

Cobrado, pago, líquido, retido, a liberar e disponível permanecem distintos. Aprovação não é saldo e não é conciliação. Recebível, pagamento e liberação não se somam como três entradas.

## 4. Obrigações e saídas

Reaproveitar contas a pagar e cadastros. Fornecedor, documento, finalidade, categoria, competência, vencimento, valor e parcelas. Conta prevista não é baixa.

Depois do pagamento no MP, a liquidação e o movimento importado devem encontrar o mesmo fato, com confirmação explícita. Sem título, parcial ou agrupado não gera obrigação fictícia.

Compra, estoque, consumo e pagamento são eventos diferentes. Saída nem sempre é despesa de resultado; entrada nem sempre é receita. O modelo não fica preso ao MP.

## 5. Conciliação

Identidade da conta e do evento. Valor e data iguais não bastam. Sugestão não confirma vínculo. Desfazer a conciliação desfaz só o vínculo; estorno é outro fato.

Saldo inicial + créditos − débitos = saldo final apenas no recorte cuja semântica estiver comprovada. Bruto, taxa e líquido sem contar duas vezes. Transferência, bloqueio e liberação não voltam a ser venda. Reembolso, contestação, reversão e antecipação só com dado e regra comprovados. Hoje essa prova não existe.

## 6. Projeção

Curto prazo diário e, até 13 semanas, semanal: saldo-base + entradas futuras elegíveis − saídas futuras elegíveis. O que já ocorreu fica de fora. Data desconhecida permanece incerta. Cenário base e ajustes de prazo ou valor ficam nomeados. Sem previsão estatística.

Todo total abre a composição, a fonte e o período. Resultado econômico e caixa ficam separados.

Prévia para avaliação, com dados **sintéticos**, não é posição real:

```text
Faixa azul, marca branca. Duas barras horizontais. Sem sidebar.

Posição em 15/10/2026 — exemplo sintético, não é a Loja
  Base declarada                 R$ 1.000,00   origem: saldo inicial hipotético
  A receber nos próximos 7 dias  R$   200,00   2 compromissos, não conciliados
  A pagar no vencimento          R$   150,00   1 título em aberto
  Menor saldo do período         R$   850,00   em 18/10, se as datas se confirmarem
  Cobertura                      nenhuma       sem extrato MP
```

## 7. Plano de captura

| Dado | Quem produz | Quando | Obrigatoriedade | Ausência |
|---|---|---|---|---|
| Cobrado, id, situação, datas | Hub, pedido | na cobrança | já atravessa | não inventar |
| Pago confirmado, método, aplicação, pagador, `live_mode` | Hub, payload e cadastro | na confirmação do provedor | necessário para tirar a pendência | permanece pendente; não copiar cobrado |
| Tarifa, líquido, liberação, saldo | conta MP | extrato ou relatório | necessário para conciliação | não derivar da lista de cobranças |
| Competência e finalidade de despesa | Finance, no título | antes do pagamento | necessário para resultado | extrato não classifica pelo favorecido |

O diff local da Spider que reencaminharia pagador, método, aplicação e pago **exigiria publicação da Spider**. Fica pendente sob a restrição do proprietário. Não é executado.

Histórico: os 11 registros atuais são recuperáveis no que já está gravado (id, cobrado, situação, data). Pago, cliente, método e ambiente dessas linhas são lacuna enquanto o contrato publicado não os entregar. Operações novas terão a mesma lacuna até essa dependência ser aceita numa revisão que autorize a Spider.

## 8. Primeiro recorte implementável sem mudar a Spider

Não há migration nova. O schema V20 já está no origin e o código do Finance já gravaria os campos se eles chegassem. O recorte utilizável é o que a lista já mostra, com a pendência de ambiente explícita.

| Item | Estado |
|---|---|
| Migration proposta | nenhuma neste recorte |
| Teste de não inventar pago | já coberto pela regra `paid_amount_confirmed` no código do Hub e por `paidAmountAbsent` no Finance |
| Recuperação | não há deploy novo. Rollback de V20 está no REV_025 |
| Aceite | não declarar pago, cliente ou caixa a partir destes 11 registros |
| Prévia | a caixa sintética da seção 6, só para leitura |

## 9. Spider

Nenhum arquivo, serviço, variável ou banco da Spider foi alterado neste ciclo. O arquivo `ActionHubPayListIdentity.java` já tinha modificação local não commitada antes deste trabalho; ela continua local e não publicada.
