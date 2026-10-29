# Fluxos do kit e estados

29/10/2026. O fluxo atual está no código. O fluxo do kit é proposta para ratificação, não comportamento implementado.

## Fluxo atual, executável

Escolha no catálogo ou no criador → carrinho local, sem pedido → `Finalizar compra` em `/pedido/novo` → cotação e um `Order` com uma ou mais linhas → autoaceite se for pão regular com data e sem adaptação; senão `submitted` → cobrança só depois do aceite → confirmação financeira por evento ou consulta, sem mudar produção → produção, pronto e entrega por ações administrativas → histórico quando a entrega é confirmada.

Prova isolada em 29/10/2026: várias linhas, um pedido e um pagamento (C01 e o teste de carrinho). Adaptação segura o conjunto até o aceite. Produção não começa com a quitação. Detalhe em [matriz-regressoes-e-validacao.md](matriz-regressoes-e-validacao.md).

Estados que já são independentes e devem continuar:

| Dimensão | Onde vive hoje | Exemplo que não pode ser colapsado |
|---|---|---|
| Compromisso comercial | `Order.status` | Aceito não significa pago |
| Pagamento | `PaymentRecord.financial_status` | Pago não significa em produção |
| Reserva | `holds_capacity` e fornada/slot | Cancelado só segura vaga se a produção já começou |
| Entrega | `delivery_confirmed_at` | `ready` e `completed` sem esse carimbo não são entrega comprovada |
| Exclusão de teste | marcador gerencial reversível | Some da fila sem apagar o pedido |

## Fluxo proposto do kit

Ainda sem escolher o ponto de consolidação. Faixas: cliente, Loja, parceiro, consolidação, transportador, financeiro.

```text
Cliente escolhe kit e data
        |
        v
Validar composição vendida, rendimento e capacidade de cada produtor
        |
        v
Compromisso comercial do kit (não é o estado de um componente)
        |
        +--> Tarefa do pão na Loja ----+
        |                               v
        +--> Tarefa do parceiro ----> Conferência do conjunto
                                        |
                                        v
                                 Uma entrega ao cliente
                                        |
                                        v
                          Cliente prepara com as instruções

Pagamento do cliente  -->  participação econômica versionada  -->  obrigação e repasse
```

Uma etapa concluída no parceiro não marca o kit pronto. “Mensagem enviada”, “componente embalado”, “volume recebido”, “kit conferido” e “kit entregue” são registros diferentes.

## Dimensões que o pedido agregado precisa mostrar

| Dimensão | Entra quando | Avança quando | Não avança sozinha por |
|---|---|---|---|
| Compromisso do cliente | Envio do carrinho | Aceite da política conjunta | Componente embalado |
| Tarefa de cada produtor | Compromisso aceito | Embalado e identificado | Pagamento aprovado |
| Reserva | Cotação confirmada | Capacidade debitada pelo rendimento, não por um pão inteiro se a receita não exigir | Quantidade comercial de kits |
| Consolidação | Volumes a caminho | Todos os volumes conferidos contra a composição vendida | Um volume isolado |
| Entrega | Kit conferido | Prova de entrega do conjunto | Componente pronto |
| Cobrança | Depois do aceite conjunto, salvo regra ratificada | Provedor aprova o valor do pedido | Tarefa de um parceiro |
| Obrigação | Regra versionada da compra | Fato que a política definir (proposta: recebimento conferido) | Webhook de pagamento |

## Aceite conjunto, proposta

Pão avulso regular pode manter o autoaceite atual. Kit, ou carrinho que mistura kit e pão, não herda esse autoaceite para a parte do parceiro.

Proposta a ratificar: o kit só libera cobrança quando a Loja e o parceiro tiverem aceitado as tarefas daquela data, ou quando o prazo de aceite expirar sem cobrança. Se só um aceitar, não há cobrança e a reserva da parte aceita expira. Pagamento aprovado depois da expiração não inicia produção; cai na mesma recuperação financeira já exigida para não avançar operação, e a política comercial decide devolver ou renegociar. Isso não reescreve o aceite histórico de pedidos antigos.

Carrinho com kit e pão avulso: uma compra e uma cobrança, se o proprietário mantiver a experiência de um pagamento. As obrigações do parceiro só incidem sobre os componentes do kit. A capacidade do pão avulso e a do pão do kit somam pelo rendimento, sem duplicar a cobrança.

## Falhas que a política precisa nomear

Nenhuma está implementada para kit. São decisões, detalhadas em [decisoes-para-ratificacao.md](decisoes-para-ratificacao.md).

| Ocorrência | Efeito no kit | Quem a proposta coloca para decidir |
|---|---|---|
| Parceiro aceita e a Loja não, ou o inverso | Sem cobrança; reserva expira | Operação da Loja informa o cliente |
| Componente falta depois do pagamento | Kit indivisível não segue incompleto | Loja, com o cliente; substituição não é silenciosa |
| Parceiro atrasa e o pão está pronto | Não despacha o conjunto | Consolidação; custo conforme a política de perda |
| Embalagem danificada ou perda de conservação | Bloqueia a entrega daquele volume | Qualidade; descarte com registro |
| Transportador ausente ou cliente ausente | Reentrega, sem marcar entregue | Logística |
| Endereço alterado depois da coleta | Novo compromisso de janela | Atendimento |
| Dois clientes na última vaga | Um fica sem reserva | Capacidade no servidor, não na tela |
| Dois operadores no mesmo pedido | A segunda gravação enxerga a primeira | Versão do pedido |
| Preço, receita ou produtor mudam depois | A compra guarda a versão vendida | Catálogo versionado |
| Reembolso depois de repassar | Obrigação de devolver, não edição de saldo | Financeiro e o contrato |

Kit indivisível: cancelar um componente essencial cancela o conjunto e recalcula a participação. Itens independentes no mesmo carrinho podem seguir. O sistema não deve tratar as duas situações com a mesma regra.

## Concorrência

O bloqueio de linha na transição do pedido e na aplicação do pagamento é suficiente para não aplicar duas vezes o mesmo evento financeiro, no desenho atual. Não é suficiente para duas organizações editando tarefas, nem para esperar parceiro ou provedor com transação aberta. A espera externa continua fora do bloqueio, como o worker financeiro já faz antes da consulta HTTP.

Não há, no código lido, eleição explícita se a API subir em mais de um processo. F12 na [matriz](matriz-capacidades-riscos.md).
