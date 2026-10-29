# Adendo 101B — estados, cores e produção sem pagamento (21/10/2026)

A etapa visível é derivada. O status persistido e o estado financeiro continuam em campos separados. A imagem não criou pedido, não marcou entrega, não rejeitou, não enviou aviso e não cobrou. O healthcheck não prova o quadro. A captura visual é uma fixtura isolada. A produção foi lida sem sessão de navegador.

## Versão publicada

| Item | Valor |
|---|---|
| Imagem em produção | `lojadepaes:prod-20261021d` |
| Rollback de imagem | `lojadepaes:prod-20261021c` |
| Imagem anterior deste adendo | `lojadepaes:prod-20261021c` — transições, confirmação de entrega e coluna nova |
| Backup desta publicação | `/opt/lojadepaes/backups/lojadepaes-20261021T172710Z.sql.gz` (99560 bytes) |
| Backup da imagem `21c` | `/opt/lojadepaes/backups/lojadepaes-20261021T171153Z.sql.gz` (99547 bytes) |
| Alembic | `e8a1b7c42d19` (head). Revisa `d7e0f5a24b38`. Coluna anulável `orders.delivery_confirmed_at`, sem preenchimento |
| Saúde | três tentativas até `health_ok`; sem sessão o resumo responde 401 |
| Leitura | 21/10/2026 14:27, `America/Sao_Paulo`. Contagens iguais antes e depois: 17 pedidos, 4 solicitações, 52 avisos, 18 cobranças |

O `alembic upgrade head` desta publicação não aplicou revisão nova: a coluna já estava no head desde a imagem `21c`. Reverter a imagem para `prod-20261021c` recria a API e pode deixar a coluna. O downgrade da revisão só cabe se a coluna precisar sumir e `delivery_confirmed_at` estiver inteiramente nula.

## Matriz ratificada

A etapa sai do status do pedido, do carimbo `delivery_confirmed_at` e da classe financeira já gravada. A classe financeira não consulta o provedor.

| Estado visível | Significado ratificado | O que está persistido | Ação autorizada | Fila |
|---|---|---|---|---|
| Aberto | Solicitação ou pedido recebido, ainda na avaliação do fluxo existente | Solicitação `pending`, `alternative_proposed` ou `awaiting_details`; ou pedido `submitted`. Pedido `submitted` permanece Aberto mesmo se já houver quitação | Aceite automático do pedido padrão, ou aceite humano da exceção, conforme as regras já existentes | Vigente. Lente `stage:open` |
| Aceito | Pedido formalizado, pagamento disponível, ainda não quitado de forma regular e ainda fora da produção | Pedido `confirmed` cuja classe financeira não é `paid`. Inclui sem valor a pagar, aguardando, em processamento, falha, sem cobrança, desconhecido, estorno e estorno parcial | Iniciar produção. Se a quitação estiver regular ou o total for zero, a ação segue direto. Se houver valor pendente ou a consulta local for inconclusiva, a API exige `unpaid_exception` | Vigente. Lente `stage:accepted` |
| Pago | Pagamento confirmado e produção ainda não iniciada | Pedido `confirmed` e classe `paid` | Iniciar produção pela ação operacional. O pagamento sozinho não muda o status | Vigente. Lente `stage:paid` |
| Em produção | Produção iniciada por ação operacional autorizada | Pedido `in_production`. A classe financeira não rebaixa esta etapa para Pago nem a promove a Entregue | Confirmar entrega, ou cancelar com motivo. Pagamento posterior permanece nesta etapa | Vigente. Lente `stage:in_production` |
| Entregue | Entrega confirmada pela ação correspondente | Pedido `completed` com `delivery_confirmed_at` preenchido. O histórico grava o motivo `entrega confirmada pelo gestor`, o autor e a data | A segunda confirmação do mesmo pedido é idempotente e não grava outro histórico | Histórico. Sai do total vigente. Lente `stage:delivered`. Continua em Todos, no histórico e na busca por nome ou referência |
| Rejeitado | Solicitação recusada pelo proprietário, fora do fluxo vigente | Solicitação `closed`, com a justificativa já gravada em `admin_note`. Não existe status de pedido `rejected` | Encerrar a solicitação, como já era | Histórico. Lente `stage:rejected` |
| Cancelado | Cancelamento do pedido, distinto da rejeição | Pedido `cancelled`, com o motivo exigido | Cancelar com motivo. O aviso já existente permanece | Histórico. Lente `stage:cancelled`. O rótulo continua Cancelado |
| Pronto | Registro antigo `ready`. Fora da sequência principal. Não é Entregue | Pedido `ready`, sem carimbo de entrega | A interface do gestor deixa de oferecer “Marcar pronto”. O endpoint antigo permanece. A ação nova Confirmar entrega pode ser usada neste status, com permissão e auditoria; esta publicação não a executou em produção | Histórico. Lente `stage:ready_legacy`. Fora do total vigente. O endereço incompleto continua no marcador próprio |
| Finalizado | Conclusão antiga, sem prova de entrega | Pedido `completed` com `delivery_confirmed_at` nulo. O motivo histórico `entregue ou retirado` e `fulfilled_at` não preenchem o carimbo | Confirmar entrega recusa converter esta linha em Entregue | Histórico. Lente `stage:finalized` |

O total vigente é a soma de Aberto, Aceito, Pago e Em produção. Entregue, Finalizado, Pronto, Cancelado e Rejeitado ficam de fora. Solicitação `converted` entra uma vez, pelo pedido vinculado. Quantidade de pães não é quantidade de pedidos.

A faixa financeira classifica os pedidos já criados, inclusive os que estão em produção, finalizados, prontos ou cancelados. O universo dela é o dos pedidos, não o do fluxo vigente. “Pagos” nessa faixa é a classe financeira `paid`. A etapa Pago é só `confirmed` + `paid`.

## Incompatibilidades reais

- Não há status de pedido rejeitado. Rejeitado é a solicitação `closed`.
- `completed`, `fulfilled_at` e o motivo `entregue ou retirado` não comprovam entrega. Os quatro pedidos `completed` de produção permanecem Finalizado.
- O dropdown “Aceito ou pago” filtra o status persistido `confirmed` e portanto mistura as lentes Aceito e Pago. As lentes separam as duas.
- `unique_records`, do resumo antigo, ainda soma solicitações abertas, `submitted` e `ACTIVE_ORDER` (`confirmed`, `in_production` e `ready`). O total vigente do quadro novo não inclui Pronto. Os dois números podem divergir enquanto existir `ready`.
- `transition_order` interno ainda aceita `confirmed` → `in_production` sem a flag de exceção. A trava vale no `POST /api/v1/admin/orders/{id}/start-production`, que é o caminho do gestor. Corpo ausente ou `unpaid_exception: false` responde 409 `unpaid_production` e não muda o pedido.
- A fila padrão (`submitted`, `confirmed`, `in_production`) não lista Pronto. Pronto continua em Todos, em `status=ready`, na lente de histórico e na busca.
- O indicador de acessibilidade `queue_total` ainda conta `ready`. Ele não é o total vigente.

## Produção sem pagamento

Pedido pago, ou com total zero / resgate válido, inicia produção pela ação existente. Total zero é Aceito e “Sem valor a pagar”; não é inadimplência.

Se a classe local não está quitada, o primeiro clique abre a confirmação e não executa. Texto do valor pendente: “Este pedido ainda não está pago. Deseja iniciar a produção mesmo assim?”. Se a classe é `unknown`: “O pagamento deste pedido não pôde ser confirmado. Deseja iniciar a produção mesmo assim?”. A caixa mostra referência, total e a condição financeira observada. Total ausente aparece como não calculado; a API devolve `total_cents` nulo.

Voltar, Escape e o fundo da caixa não enviam pedido. Não há checkbox. O segundo clique, “Iniciar mesmo sem pagamento”, reenvia com `unpaid_exception: true`. O servidor reclassifica dentro do lock. Se nesse intervalo a quitação ficou regular, inicia com motivo vazio e não grava exceção falsa. Se continua pendente ou inconclusiva, grava uma linha de histórico com autor, data e o texto “produção iniciada sem quitação confirmada; financeiro observado: {rótulo} ({classe})”. Não cria cobrança, não marca pago, não concede crédito e não enfileira aviso financeiro.

Clique repetido com o pedido já em produção devolve o mesmo estado e não acrescenta histórico. A etapa fica Em produção e o marcador ao lado diz “Pagamento pendente” ou “Pagamento não confirmado”. Pagamento posterior mantém Em produção. Só Confirmar entrega leva a Entregue.

A confirmação de entrega parte de `in_production` ou `ready`, grava `completed`, `completed_at`, `delivery_confirmed_at` e o motivo explícito, com o mesmo efeito de fidelidade que a conclusão já tinha. Não envia e-mail por causa dessa ação.

## Cores

Fundo pastel, texto `#36392e`, borda discreta. A cor acompanha o rótulo. A faixa “Pagos” não usa o azul da etapa Pago. “Pagamento pendente” é um marcador branco com borda cinza, ao lado da etapa.

| Estado | Fundo / borda | Origem da cor |
|---|---|---|
| Aberto | `#eceae4` / `#c8c4b8` | Proposta para completar o estado sem cor definida pelo proprietário |
| Aceito | `#f8e7a0` / `#d9c36a` | Definida pelo proprietário: amarelo pastel |
| Pago | `#d7e6f6` / `#b5cbe4` | Proposta para completar o estado sem cor definida pelo proprietário: azul pastel, distinto do verde de produção |
| Em produção | `#d7ecd6` / `#b3d2b2` | Definida pelo proprietário: verde pastel |
| Entregue | `#ffffff` / `#5c564c` | Definida pelo proprietário: branco, com borda que o separa do papel `#faf8f2` |
| Rejeitado | `#f8d6d2` / `#e0b0aa` | Definida pelo proprietário: vermelho pastel claro |
| Cancelado | `#f3eee8` / `#8a8175` | Tratamento visual próprio; a semântica de cancelamento não muda |
| Finalizado e Pronto | `#f7f4ee` / `#d4cec2` | Histórico, fora da sequência principal |

A mesma classe vale no resumo, na fila e no detalhe. Pendência de endereço ou de pagamento não substitui a cor da etapa.

## Contagem em produção

Leitura interna de 21/10/2026 14:27, sem filtro de data de criação. A imagem `21d` já estava no ar. A leitura deu rollback da sessão. Status persistidos, iguais ao dump anterior à troca da imagem: `cancelled` 8, `completed` 4, `confirmed` 3, `in_production` 1, `ready` 1.

| Indicador | Quantidade | Universo |
|---|---|---|
| Vigentes | 4 | Aberto 0 + Aceito 0 + Pago 3 + Em produção 1 |
| Entregue | 0 | `completed` com `delivery_confirmed_at` |
| Finalizado | 4 | `completed` sem o carimbo |
| Pronto | 1 | `ready` |
| Cancelado | 8 | pedido `cancelled` |
| Rejeitado | 1 | solicitação `closed` |
| Aguardando pagamento | 4 | faixa financeira, 17 pedidos classificados |
| Pagos | 13 | faixa financeira; inclui produção, finalizado e o Pronto |
| Endereço de entrega incompleto | 1 | `submitted`, `confirmed`, `in_production` e `ready` |
| Data ultrapassada | 4 | solicitação aberta ou pedido do fluxo vigente |
| Avisos e adaptação | 0 | último aviso e adaptação sem desfecho |

`delivery_confirmed_at` está nulo nos 17 pedidos. Os quatro históricos com destino `completed` têm o motivo `entregue ou retirado`. Nenhum tem `entrega confirmada pelo gestor`.

`LPF891F9E5D1`, originado em `SD3CC4C139`, está `ready`, etapa Pronto, total 7000 centavos, classe financeira `paid`, endereço de entrega incompleto, telefone vazio, entrega não confirmada. Às 12:18, na leitura do Prompt 101, o mesmo pedido estava `confirmed` e a contagem de Prontos era 0. O status passou a `ready` antes desta imagem; o quadro anterior o mostrava como Pronto histórico e o marcador de endereço do resumo o omitia, porque o recorte de endereço parava em `submitted`, `confirmed` e `in_production`. A imagem `21d` inclui `ready` nesse marcador. A contagem de endereço passou a 1. O pedido continua Pronto, fora dos 4 vigentes, e não foi marcado Entregue. Finalizado e Cancelado continuam fora desse marcador: se os quatro `completed` tivessem entrado, o número não seria 1.

A confirmação de entrega disponível para um Pronto não foi usada neste pedido. A reparação do incidente segue os limites do 101A.

## Prova isolada das transições

Base `lojadepaes_test`, dados fictícios. Não é a loja publicada.

`tests/test_prompt101b.py` cobre: aceite sem endereço vira um Aceito e a solicitação não é contada de novo; pago espera a ação de iniciar produção e não gera cobrança nem e-mail; pedido sem quitação, sem corpo ou com `unpaid_exception: false`, responde 409 com a frase, a referência, o total e “Aguardando pagamento”; a exceção grava Em produção, mantém o pagamento pendente e uma linha de histórico com o autor; o segundo clique não duplica o histórico; quitação ocorrida entre o 409 e a confirmação inicia sem motivo de exceção; pagamento posterior permanece Em produção e entra em `payment:paid`, não em `stage:paid` nem em `stage:delivered`; total zero inicia sem exceção e não é etapa Pago; total ausente é incerteza, `total_cents` nulo, e a exceção grava “Pagamento não confirmado” sem criar cobrança; Confirmar entrega grava Entregue, sai do vigente e a busca por nome o encontra junto com Finalizado e Pronto antigos; completar pelo caminho antigo permanece Finalizado e a confirmação de entrega responde 409; Pronto antigo permanece Pronto; rejeitar solicitação e cancelar pedido guardam motivos distintos; sem sessão, resumo, início de produção e confirmação de entrega respondem 401; duas leituras não alteram contagens nem carimbos.

O teste acrescentado com a imagem `21d` cria um pedido de entrega com rua vazia, pago, levado a `ready` pelo endpoint antigo: o rótulo é Pronto, `delivery_confirmed_at` fica nulo, o total vigente fica 0, Entregue fica 0 e a lente `pending:address` devolve esse único pedido.

`tests/test_prompt101.py` permanece verde com o quadro novo: vigentes = Aberto + Aceito + Pago + Em produção; `unique_records` continua no critério antigo; Pronto não entra na fila padrão; o endereço do conjunto isolado do 101 continua 1. Na mesma rodada anterior entraram `test_admin_orders.py`, `test_prompt100.py`, `test_prompt67.py` e `test_prompt87_date_request.py`. Interface: `AttendanceSummary.test.tsx` e `AdminApp.test.tsx` (15 testes) e `tsc --noEmit`. O clique em Aberto pede `stage:open`. O chip Pagos não recebe a classe azul da etapa Pago. Voltar na confirmação não dispara a ação; “Iniciar mesmo sem pagamento” dispara só o segundo envio.

## Figuras

Fixtura `stages.html`. Não é sessão autenticada e os números impressos não são os da loja. Larguras 1280, 390 e 320; a rolagem extra medida foi 0 nas três.

- `stages-desktop.png` — fluxo, histórico, faixa Pagos sem o azul da etapa, chip Em produção com o marcador Pagamento pendente, e a confirmação com referência LPSEM1, R$ 45,00, Aguardando pagamento, Voltar e Iniciar mesmo sem pagamento.
- `stages-390.png` e `stages-320.png` — a mesma linguagem em coluna. No 320 os dois botões ficam empilhados, com o texto inteiro.

## O que esta publicação não altera

Provedor, Pay, planos, fidelidade, receitas, Agenda, capacidade e fechamento permanecem como estavam. Nenhuma entrega, rejeição, cobrança ou mensagem de teste foi emitida na loja publicada.
