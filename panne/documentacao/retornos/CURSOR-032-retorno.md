# CURSOR-032 (revisto) - Encerrar a operacao da Loja por lancamentos, sem apagar

**Resultado:** operacao da Loja de Paes encerrada em producao. 10 saldos zerados por ajuste de saida, nada apagado, nenhum trigger/RLS/FK desligado. Segundo dry-run com zero itens em todos os passos.

## O que foi entregue

- Comando `python -m app.ops.close_operations --org <id> --dry-run | --execute --confirm <slug>` (`panne/backend/app/ops/close_operations.py`), commit `69255cfb` em `feat/panne-032-reset`. Sem migracao.
- Usa o papel de **runtime** (RLS ativo) e os servicos existentes: `release_reservation`, `cancel_order` / `short_close_order`, `cancel_document` (nota fiscal de entrada), `post_movement` com `adjust_minus` (motivo "Encerramento do piloto", `approved=True`). Nenhum SQL de escrita.
- Uma transacao. `--execute` confirma so se nao houver erro; qualquer erro desfaz tudo. `--dry-run` roda os mesmos comandos e desfaz no fim (mostra os erros reais do dominio).
- Idempotente: cada passo parte do estado atual (provado pelo 2o dry-run e por teste).
- Recusa `--execute` sem `--confirm` igual ao slug (exit 3, nada gravado).
- Testes (`tests/test_close_operations.py`, 6 passando, base descartavel): saldo da org alvo vai a zero, outra org intacta, cadastro intacto, segunda execucao sem efeito, recusa sem `--confirm`, rollback total com erro (contagem aberta trava o local).

## Casos sem comando no dominio (listados, nao inventados)

| Caso | Existe comando? | Contagem na Loja |
|---|---|---|
| Planos de producao (draft/scheduled) | nao (nao ha encerrar/arquivar plano) | 0 |
| Recebimentos de compra em rascunho | nao (nao ha cancelar recebimento) | 0 |
| Saldo negativo | so existe ajuste de saida | 0 |
| Pedidos de compra pendentes (fora dos passos) | informado, nao alterado | 0 |
| Requisicoes de compra pendentes (fora dos passos) | informado, nao alterado | 0 |
| Notas com recebimento ja lancado (mantidas como historico) | n/a | 0 |

Passos 1 a 3 (reservas, pedidos de producao, notas de entrada) nao tinham nada em aberto na Loja.

## Producao

- Imagem `panne/backend:69255cfb` (`prod-69255cfb`), digest `sha256:de6f4ca6d0bf488c8d9265df12dcddea2f70924b534514a18f281ba8eb12d12c`.
- Task definition `panne-prod-api:23` (so a imagem mudou em relacao a `:22`); servico `panne-prod-api` em `paneldx-cluster`. `/health` e `/ready` = 200. Tag git `panne-prod-2026-11-02b`. Rollback: `panne-prod-api:22` / `prod-d8d22fe9`.
- **Snapshot manual:** `actionhub-prod-pre-encerramento-loja-20261102`, `available`, 100%, criptografado, 20 GB.
  ARN: `arn:aws:rds:us-east-2:253137917703:snapshot:actionhub-prod-pre-encerramento-loja-20261102`
- **Desvio de procedimento:** nao deu para usar "a mesma task definition mudando so o comando". O `ENTRYPOINT` da imagem e `uvicorn` e o ECS nao permite trocar o entrypoint no `run-task`. Registrei a familia `panne-prod-ops:1` (copia da `:23`, mesma imagem/roles/segredos/rede, so com `entryPoint = ["python"]` e sem porta publicada) e passei o comando como argumentos. O servico nao foi tocado.
- Antes de ter o id da Loja, uma tarefa read-only (`default_transaction_read_only`) listou organizacoes e voltou vazia (RLS forcado exige id), e um smoke com org inexistente respondeu `organizacao_inexistente` (exit 2). Nada gravado.

## Comandos executados (todos via `aws ecs run-task`, cluster `paneldx-cluster`, task def `panne-prod-ops:1`)

Org: `f1045531-e32b-48d6-a62b-2b11086100b4` (slug `loja-de-paes`, "Loja de Paes").

1. Dry-run (task `2657c2b40402441681f0e0979ed081e9`, exit 0): `-m app.ops.close_operations --org f1045531-e32b-48d6-a62b-2b11086100b4 --dry-run`
2. Execute (task `ec86aecc364442cb85726b8ac4ba0176`, exit 0): `-m app.ops.close_operations --org f1045531-e32b-48d6-a62b-2b11086100b4 --execute --confirm loja-de-paes` (COMMIT)
3. Segundo dry-run (task `ca9ab3ae5c754315a115322b434d9d23`, exit 0): igual ao 1.

## Dry-run antes

~~~
Encerramento da opera├º├úo: Loja de P├úes (loja-de-paes) org=f1045531-e32b-48d6-a62b-2b11086100b4
Modo: dry-run
Passo 1 - liberar reservas abertas: 0 a afetar/afetado(s), 0 erro(s), 0 sem comando, 0 mantido(s)
Passo 2 - encerrar pedidos de produ├º├úo (planos s├│ listados): 0 a afetar/afetado(s), 0 erro(s), 0 sem comando, 0 mantido(s)
Passo 3 - cancelar notas de entrada n├úo confirmadas: 0 a afetar/afetado(s), 0 erro(s), 0 sem comando, 0 mantido(s)
Passo 4 - zerar saldos (ajuste de sa├¡da por lote e local): 10 a afetar/afetado(s), 0 erro(s), 0 sem comando, 0 mantido(s)
  ok: {"lote": "LOT-000002", "local": "loja-virtual-ce8a", "saldo": "3.000000", "unidade": "un", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000008", "local": "loja-virtual-ce8a", "saldo": "450.000000", "unidade": "g", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000004", "local": "loja-virtual-ce8a", "saldo": "2.000000", "unidade": "un", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000001", "local": "loja-virtual-ce8a", "saldo": "250.000000", "unidade": "g", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000009", "local": "loja-virtual-ce8a", "saldo": "200.000000", "unidade": "g", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000006", "local": "loja-virtual-ce8a", "saldo": "500.000000", "unidade": "g", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000003", "local": "loja-virtual-ce8a", "saldo": "1.000000", "unidade": "un", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000007", "local": "loja-virtual-ce8a", "saldo": "200.000000", "unidade": "g", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000005", "local": "loja-virtual-ce8a", "saldo": "3.000000", "unidade": "un", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000010", "local": "loja-virtual-ce8a", "saldo": "1000.000000", "unidade": "g", "acao": "ajuste de sa├¡da at├® zero"}
Saldos diferentes de zero depois dos passos: 0
Fora dos passos (n├úo alterado, s├│ informado): {"pedidos_de_compra_pendentes": 0, "requisicoes_de_compra_pendentes": 0}
Total a afetar/afetado: 10; erros: 0; resultado: OK
ROLLBACK: dry-run n├úo altera nada.
~~~

## Execucao

~~~
Encerramento da opera├º├úo: Loja de P├úes (loja-de-paes) org=f1045531-e32b-48d6-a62b-2b11086100b4
Modo: execute
Passo 1 - liberar reservas abertas: 0 a afetar/afetado(s), 0 erro(s), 0 sem comando, 0 mantido(s)
Passo 2 - encerrar pedidos de produ├º├úo (planos s├│ listados): 0 a afetar/afetado(s), 0 erro(s), 0 sem comando, 0 mantido(s)
Passo 3 - cancelar notas de entrada n├úo confirmadas: 0 a afetar/afetado(s), 0 erro(s), 0 sem comando, 0 mantido(s)
Passo 4 - zerar saldos (ajuste de sa├¡da por lote e local): 10 a afetar/afetado(s), 0 erro(s), 0 sem comando, 0 mantido(s)
  ok: {"lote": "LOT-000002", "local": "loja-virtual-ce8a", "saldo": "3.000000", "unidade": "un", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000008", "local": "loja-virtual-ce8a", "saldo": "450.000000", "unidade": "g", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000004", "local": "loja-virtual-ce8a", "saldo": "2.000000", "unidade": "un", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000001", "local": "loja-virtual-ce8a", "saldo": "250.000000", "unidade": "g", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000009", "local": "loja-virtual-ce8a", "saldo": "200.000000", "unidade": "g", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000006", "local": "loja-virtual-ce8a", "saldo": "500.000000", "unidade": "g", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000003", "local": "loja-virtual-ce8a", "saldo": "1.000000", "unidade": "un", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000007", "local": "loja-virtual-ce8a", "saldo": "200.000000", "unidade": "g", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000005", "local": "loja-virtual-ce8a", "saldo": "3.000000", "unidade": "un", "acao": "ajuste de sa├¡da at├® zero"}
  ok: {"lote": "LOT-000010", "local": "loja-virtual-ce8a", "saldo": "1000.000000", "unidade": "g", "acao": "ajuste de sa├¡da at├® zero"}
Saldos diferentes de zero depois dos passos: 0
Fora dos passos (n├úo alterado, s├│ informado): {"pedidos_de_compra_pendentes": 0, "requisicoes_de_compra_pendentes": 0}
Total a afetar/afetado: 10; erros: 0; resultado: OK
COMMIT: encerramento aplicado.
~~~
(As 10 linhas de saldo sao as mesmas do dry-run acima.)

## Dry-run depois (segundo)

~~~
Encerramento da opera├º├úo: Loja de P├úes (loja-de-paes) org=f1045531-e32b-48d6-a62b-2b11086100b4
Modo: dry-run
Passo 1 - liberar reservas abertas: 0 a afetar/afetado(s), 0 erro(s), 0 sem comando, 0 mantido(s)
Passo 2 - encerrar pedidos de produ├º├úo (planos s├│ listados): 0 a afetar/afetado(s), 0 erro(s), 0 sem comando, 0 mantido(s)
Passo 3 - cancelar notas de entrada n├úo confirmadas: 0 a afetar/afetado(s), 0 erro(s), 0 sem comando, 0 mantido(s)
Passo 4 - zerar saldos (ajuste de sa├¡da por lote e local): 0 a afetar/afetado(s), 0 erro(s), 0 sem comando, 0 mantido(s)
Saldos diferentes de zero depois dos passos: 0
Fora dos passos (n├úo alterado, s├│ informado): {"pedidos_de_compra_pendentes": 0, "requisicoes_de_compra_pendentes": 0}
Total a afetar/afetado: 0; erros: 0; resultado: OK
ROLLBACK: dry-run n├úo altera nada.
~~~

## Verificacoes

- Saldos da Loja: 0 diferentes de zero depois da execucao (o 2o dry-run, pelo papel de runtime com RLS, lista zero saldos a ajustar e zero residual).
- Fluxo sem notas/pedidos pendentes: passos 2 e 3 do 2o dry-run com zero itens (e zero tambem antes).
- `/health` 200 e `/ready` 200 apos a execucao.
- CloudWatch (`/ecs/panne/prod-api`, de 18:37:30Z a 18:49Z, ou seja 10+ min depois do commit): 770 eventos, **zero 5xx**, zero Traceback. 50 respostas 200 e 688 respostas 404, todas de varredura da internet (`/.env`, `/config/aws.yml`, `/.gitlab-ci.yml`...), sem relacao com o encerramento. `/health` e `/ready` = 200 as 18:49Z.
- Nao consegui abrir a tela de estoque da Loja logado (sem credencial de usuario); a conferencia de saldo zero foi feita pelo proprio comando, com o papel de runtime.