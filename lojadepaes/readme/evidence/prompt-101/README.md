# Prompt 101 — Resumo gerencial dos pedidos (21/10/2026)

Leitura e navegação. A imagem nova não cria pedido, não muda status, não envia aviso e não cobra. O healthcheck não prova o resumo. A captura visual é do componente, com números do conjunto isolado. A produção foi lida sem sessão de navegador.

## O que o domínio não tem

Não há estado de expedição nem prova de entrega. Finalizar grava conclusão, não entrega. Por isso a linha não tem Enviados nem Entregues. O destino real se chama Finalizados e fica no histórico, fora do total vigente.

Pagamento não escolhe a etapa operacional. A faixa financeira usa só o registro já gravado. Abrir ou atualizar o resumo não consulta o provedor.

Telefone vazio não é pendência de entrega. O campo obrigatório de entrega continua sendo rua, número, bairro, cidade, estado e CEP, e só em pedido de entrega que não está cancelado.

## Matriz

| Rótulo | Condição real | Universo | Clique |
|---|---|---|---|
| Vigentes agora | soma das quatro etapas abaixo | solicitações abertas e pedidos atuais, uma vez cada | não é filtro |
| Aguardando avaliação | solicitação `pending`, `alternative_proposed` ou `awaiting_details`, ou pedido `submitted` | um registro por vez; solicitação já convertida não entra | `stage:evaluation` |
| Confirmados | pedido `confirmed` | o pedido, não a solicitação que o originou | `stage:confirmed` |
| Em produção | pedido `in_production` | idem | `stage:in_production` |
| Prontos | pedido `ready` | idem | `stage:ready` |
| Finalizados | pedido `completed` | histórico, fora dos vigentes | `stage:completed` |
| Cancelados | pedido `cancelled` | histórico | `stage:cancelled` |
| Solicitações encerradas | solicitação `closed` | histórico; `converted` não entra | `stage:date_closed` |
| Aguardando pagamento | cobrança `pending` sem referência externa | pedidos não rascunho | `payment:awaiting` |
| Em processamento | cobrança `pending` com referência externa | idem | `payment:processing` |
| Pagos | quitado e status `paid`, sem estorno | idem | `payment:paid` |
| Falha de pagamento | status `failed` | idem | `payment:failed` |
| Sem cobrança iniciada | há valor e não há cobrança; pedido não cancelado | idem | `payment:no_charge` |
| Sem valor a pagar | total zero, inclusive resgate | idem; não conta como não pago nem como pago regular | `payment:no_amount` |
| Estornados / Estorno parcial | `refunded` / `partially_refunded` | idem | `payment:refunded` / `payment:partial_refund` |
| Estado desconhecido | total ausente ou status `unknown` | idem | `payment:unknown` |
| Cobrança cancelada | status financeiro `cancelled` | idem | `payment:charge_cancelled` |
| Cancelado sem pagamento regular | pedido cancelado sem outra classe acima | idem | `payment:cancelled_open` |
| Endereço de entrega incompleto | entrega com rua, número, bairro, cidade, estado ou CEP vazio | pedido não cancelado | `pending:address` |
| Aviso na fila / Falha no aviso / Aviso não disparado | último aviso ao cliente daquele tipo, status `pending`, `failed` ou `skipped` | pedidos ou solicitações afetados, não tentativas | `pending:notice_*` |
| Data ultrapassada | data desejada ou data da fornada anterior a hoje em `America/Sao_Paulo` | solicitação aberta ou pedido ainda vigente | `pending:overdue` |
| Adaptação em aberto | adaptação que não está aceita nem com alternativa aceita | pedido vigente; conta o pedido, não cada linha | `pending:adaptation` |

O resumo não filtra por data de criação. A data ultrapassada usa a data da fornada ou a data desejada, não a regra de 48 horas. O clique zera os outros filtros da fila para o total bater com o número. Busca por nome ou escolha de Todos, Finalizados e Cancelados limpa esse clique e volta ao comportamento anterior da fila.

## Conjunto isolado

`tests/test_prompt101.py`, base `lojadepaes_test`, dados fictícios.

- Vigentes 13 = 4 avaliação + 5 confirmados + 2 em produção + 2 prontos. Histórico 4, fora dessa soma.
- Pedidos classificados no pagamento: 14. Não é o total vigente.
- Oito pães num pedido contam como 1 registro.
- Solicitação convertida entra só pelo pedido.
- Endereço incompleto não vira etapa de expedição. E-mail enviado não vira entrega. Falha de aviso seguida de envio sai da falha. Duas tentativas contam um pedido.
- Cada indicador, com página de 1, devolve os mesmos registros do número, inclusive depois da primeira página, e o detalhe abre.
- Busca por nome acha finalizado e cancelado. Recorte pela data de criação tira um confirmado antigo da lista e o resumo continua contando ele.
- Leitura com falha não devolve um quadro de zeros. Duas leituras não mudam pedido, solicitação, aviso nem pagamento.
- Sem sessão, o resumo e a lista respondem 401.

Regressão: `test_prompt100.py`, `test_prompt87_date_request.py` e `test_prompt67.py`. A frase antiga do aceite sem produto foi alinhada ao texto do prompt 100 (“quantidade informada”, “confirme o produto”). Interface: `AttendanceSummary.test.tsx` e `AdminApp.test.tsx`. O clique filtra, a falha conserva o número anterior, e a primeira falha não mostra zero.

## Figuras

Números do conjunto isolado, não da loja publicada. Largura medida no navegador: 1280, 390 e 320. Nas três, a diferença entre a largura do conteúdo e a da janela foi 0.

- `before-desktop.png` — lista anterior, com “tipo + ID”, “entrega pendente” e “Nenhuma pendência prioritária agora”.
- `after-desktop.png`, `after-390.png`, `after-320.png` — fluxo, pagamento e pendências.

## Produção, só leitura

Imagem `lojadepaes:prod-20261021b`. Rollback de imagem: `lojadepaes:prod-20261021a`. Backup `/opt/lojadepaes/backups/lojadepaes-20261021T151728Z.sql.gz` (99448 bytes). Alembic `d7e0f5a24b38`, sem migração. Sem sessão, o resumo responde 401. A leitura interna, às 12:18 de 21/10/2026 no horário de Brasília, não alterou as contagens (17 pedidos, 4 solicitações, 52 avisos, 18 cobranças, antes e depois).

Recorte: situação atual, sem filtro de data de criação.

| Indicador | Quantidade |
|---|---|
| Vigentes | 5 |
| Aguardando avaliação | 0 |
| Confirmados | 4 |
| Em produção | 1 |
| Prontos | 0 |
| Finalizados | 4 |
| Cancelados | 8 |
| Solicitações encerradas | 1 |
| Aguardando pagamento | 4 |
| Pagos | 13 |
| Demais classes financeiras | 0 |
| Pedidos classificados no pagamento | 17 |
| Endereço de entrega incompleto | 3 |
| Data ultrapassada | 4 |
| Aviso na fila, falha de aviso, aviso não disparado, adaptação | 0 |

`LPF891F9E5D1`, vindo de `SD3CC4C139`: confirmado, total 7000 centavos, pagamento registrado como pago, endereço de entrega ainda incompleto, telefone ausente. Não foi aceito, avisado nem cobrado nesta entrega.

## Rollback

Voltar a imagem `lojadepaes:prod-20261021a` e recriar a API. O backup só entra se for preciso desfazer dados desta janela. Esta entrega não migrou nem gravou pedido.
