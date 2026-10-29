# Adendo 101C — pedido em andamento visível (21/10/2026)

A etapa continua derivada. `ready` sem entrega confirmada entra no total vigente como exceção, com o rótulo Pronto — aguardando confirmação de entrega. Não é uma quinta etapa da sequência Aberto → Aceito → Pago → Em produção → Entregue. A leitura de produção não usou sessão de navegador. A fixtura visual do 101B não é prova desta publicação.

## Causa da passagem para pronto

`SD3CC4C139` está convertida no pedido `LPF891F9E5D1`. A solicitação foi criada em 20/10/2026 11:06, horário de Brasília, com data desejada 23/10/2026. Em 21/10 09:08:29 a conta `admin:admin@lojadepaes.com.br` confirmou o pedido. Às 09:23:48 o registro financeiro passou a `paid`, R$ 70,00, e o aviso de pagamento aprovado foi enviado. O status operacional permaneceu `confirmed`.

Às 12:38:09 a mesma conta levou o pedido de `confirmed` a `in_production`, sem texto de motivo. Às 12:38:12, três segundos depois, a mesma conta levou de `in_production` a `ready`, também sem motivo. O único caminho da aplicação que grava `ready` é `POST /api/v1/admin/orders/{id}/mark-ready`. Não há evento financeiro nesse horário. A imagem então publicada ainda oferecia Marcar pronto depois de iniciar a produção.

Lacuna: aquelas duas linhas não guardam o nome do comando, porque o motivo estava vazio. A identificação vem do ator, do horário e de ser o único escritor de `ready`. A linha antiga não foi reescrita. A partir desta imagem, Marcar pronto grava o motivo `marcado pronto pelo gestor`. Não havia outro pedido `ready`.

## Reparação

Imediatamente antes da escrita, o pedido ainda estava `ready`, pago em 7000 centavos, com reserva, sem carimbo de entrega, e o último histórico ainda era `in_production` → `ready`. A correção gravou uma linha nova, ator `assisted:101c`, de `ready` para `in_production`, com o motivo que registra os valores anterior e novo. Permanecem o pagamento, os itens, a reserva, o endereço pendente, o telefone vazio, o vínculo, `production_started_at` e `ready_at`. Não houve aviso, cobrança nem entrega. O histórico anterior ficou no lugar. Pedidos, avisos e cobranças continuam 17, 52 e 18. O histórico passou de 35 para 36.

Depois da correção, a classificação usada pelo resumo e pela fila coloca `LPF891F9E5D1` em Em produção, fora de Pago e fora da exceção Pronto. O endereço incompleto continua no marcador próprio. A faixa Pagos, com 13 pedidos, continua incluindo este pedido sem fazê-lo voltar à etapa Pago.

## Matriz reconciliada

O total vigente é a soma das quatro etapas com a exceção. Nesta leitura: 0 + 0 + 3 + 2 + 0 = 5. `unique_records` usa o mesmo total. A exceção com contagem zero continua no quadro e some do botão.

| Visível | Persistido | Fila |
|---|---|---|
| Aberto | Solicitação aberta ou pedido `submitted` | Vigente |
| Aceito | `confirmed` sem quitação regular, inclusive total zero | Vigente. Filtro `stage:accepted` |
| Pago | `confirmed` e classe `paid` | Vigente. Filtro `stage:paid` |
| Em produção | `in_production` | Vigente. Pagamento posterior não muda a etapa |
| Pronto — aguardando confirmação de entrega | `ready` sem carimbo de entrega | Vigente, como exceção. Lente `stage:ready_legacy` |
| Entregue | `completed` com `delivery_confirmed_at` | Histórico |
| Finalizado | `completed` sem o carimbo | Histórico |
| Cancelado | Pedido `cancelled` e o motivo | Histórico |
| Rejeitado | Solicitação `closed` | Histórico. A convertida não entra de novo ao lado do pedido |

Iniciar produção com valor pendente passa por `start_production`, também quando o chamador é `transition_order`. Sem `unpaid_exception` explícito a operação responde conflito e não muda o pedido. Total zero segue sem essa confirmação. A flag não nasce verdadeira.

## Versão

| Item | Valor |
|---|---|
| Imagem | `lojadepaes:prod-20261021e` |
| Rollback | `lojadepaes:prod-20261021d`. A coluna `delivery_confirmed_at` pode permanecer |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261021T183136Z.sql.gz` (99561 bytes) |
| Alembic | `e8a1b7c42d19`, sem revisão nova |
| Saúde | `health_ok` na terceira tentativa. Sem sessão, o resumo responde 401 |

Não houve sessão administrativa no navegador. A prova publicada é a classificação compartilhada, lida antes e depois da reparação.

## Prova isolada

`tests/test_prompt101c.py`, `test_prompt101.py`, `test_prompt101b.py`, `test_admin_orders.py`, `test_orders.py`, `test_prompt72.py`, `test_prompt100.py`, `test_prompt67.py`, `test_prompt87_date_request.py` e `test_schedule.py`: 70 testes. Interface: 16 testes e `tsc --noEmit`.

O conjunto mostra a exceção nas duas páginas da lente, Aceito separado de Pago, total zero fora de Pago, produção com pagamento pendente fora de Pago, `transition_order` sem confirmação recusado, reparação sem novo aviso nem cobrança, e o segundo chamado da reparação recusado.
