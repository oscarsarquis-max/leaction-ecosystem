# Lançamento único — 005T3

26/10/2026. isa-piloto 0.6.14, schema 10. O lançamento passa a ter um lugar só, com os números do mês em colunas. As telas e o formato que o navegador já lia permanecem. Nenhum registro foi apagado.

## Investigação

A base publicada, lida antes da imagem, continuava vazia de dinheiro: conta, movimentação, ocorrência, lançamento, saldo, compromisso, entrada e vínculo em zero. Havia 2 identidades, 1 perfil e 5 lotes de trabalho. Nenhuma movimentação estava sem lançamento, porque as duas tabelas tinham zero linhas. O schema ainda era 9.

Há dois vocabulários para o mesmo fato. O extrato grava `entrada` / `saida` na movimentação e o lançamento copiado guarda `ganho` / `gasto` no JSON, com o valor absoluto em `amountMinor`. O id do lançamento copiado é o id da movimentação. O mês, até aqui, somava a movimentação e ignorava o JSON quando os dois existiam.

Quem lê e quem grava:

| Peça | Lê | Grava |
|---|---|---|
| `movement` | presença, retrato e o vínculo, quando o lançamento ainda não existe | importação e a decisão “outra” |
| `occurrence` | a área de trabalho, para a lista de linhas do arquivo | importação e a decisão |
| `ledger_entry` | mês, área de trabalho, presença, IA e lotes | só `write_entry` |
| `link_row` | o vínculo do pagamento | `link_movement`; `movement_id` é o id do lançamento |
| `statement_note` | a área de trabalho | a importação do arquivo, como antes |

O navegador continua lendo o JSON: estabelecimento, valor, direção `ganho`/`gasto`, situação, datas, natureza, categoria, origem da categoria, trava da pessoa, origem do arquivo, simulação, arquivado, conta, ocorrência, lote, motivo da IA, documento e rótulo da imagem. `calc.js` usa a data da situação para o realizado e a data de vencimento, ou a do documento, para o que ainda está em aberto. A lista de Lançamentos e a busca do lote usam data da situação, vencimento ou documento, nessa ordem. O Início não usa o vencimento para escolher o mês.

Não há índice novo no código do navegador. `calc.js`, `lotes.js` e as telas não foram alterados.

O `amount_cents` antigo da movimentação é `INTEGER`. No PostgreSQL isso cabe até 2.147.483.647 centavos. A coluna nova do lançamento é `BIGINT`.

## Regra da data do mês

`booked_on` é a data da situação e, se ela faltar, a data do documento. Na importação essa data é a do extrato, a mesma que a movimentação já usava. É a data com que o Início já escolhia o mês.

O vencimento não entra nessa coluna. Lançamentos, `calc.js` e a busca do lote continuam podendo cair no vencimento. Mudar isso mudaria a lista sem pedido deste recorte.

## O que mudou

`server/store.py` — schema 10, `write_entry`, preenchimento das colunas e a leitura do mês só em `ledger_entry`. A importação grava o lançamento na mesma transação da movimentação. A decisão “outra” faz o mesmo. A movimentação continua sendo gravada: a presença, o retrato e o vínculo ainda a leem. O mês não a lê mais.

`server/ai.py` — a categorização grava por `write_entry`. A fila pede ao banco só o que está sem categoria, sem arquivo e nas naturezas de consumo ou a conferir. O contexto enviado ao modelo continua o da pessoa inteira: um filtro de mês mudaria o que o modelo vê.

`server/workbatches.py` — carimbar o lote no lançamento passa por `write_entry`. A busca do lote não mudou de data.

`scripts/ops/reclassify-import-origin-005t2.py` — o lançamento reclassificado também passa por `write_entry`, para a coluna não ficar para trás do JSON.

`scripts/ops/provision-db.py` — o limite do papel `isa_app` fica em 16.

`VERSION` — isa-piloto 0.6.14.

Testes de versão de schema passaram a esperar 10. O cenário de 26/10, quando planta só a movimentação, completa o lançamento antes de ler o mês.

Nenhum arquivo de tela, estilo ou cálculo do navegador entrou neste recorte.

## Schema 10

Só `ADD COLUMN` e `CREATE INDEX IF NOT EXISTS`. Nada de `DROP`. As colunas novas aceitam nulo.

Em `ledger_entry`: `direction`, `amount_cents` (`BIGINT`), `currency`, `booked_on`, `due_on`, `status`, `nature`, `category`, `source`, `occurrence_id`, `archived`, `simulated`.

Índices: lançamento por pessoa e data, e por pessoa, conta e data; único por pessoa e ocorrência quando a ocorrência existe; ocorrência por estado e por assinatura; compromisso e entrada por vencimento; saldo por ativo; conta por pessoa; movimentação por data, para o legado.

O preenchimento roda na migração e de novo em cada abertura com bootstrap. Ele só mexe em linha com direção ou valor ainda nulos, e cria o lançamento que faltar para uma movimentação, com o mesmo id. Rodar outra vez não altera a linha. Uma linha gravada pela 0.6.13, que não conhece as colunas, fica com elas nulas; a volta para a 0.6.14 preenche sem reescrever o JSON.

A direção da coluna é `entrada` ou `saida`. O JSON continua `ganho` ou `gasto`.

O valor da coluna, no lançamento manual, é o absoluto de `amountMinor`. No lançamento que tem movimentação com o mesmo id, a coluna repete o inteiro da movimentação — o número que o mês já somava. O extrato pode gravar a saída com sinal. Trocar esse inteiro pelo absoluto mudaria o Início. O JSON segue absoluto, que é o que o navegador e o `calc.js` somam.

Naturezas fora do resultado do mês: transferência, reembolso, empréstimo e `bb_rende_facil`. O efeito na soma é o de antes. A aplicação vinda do extrato continua rotulada como aplicação; a lançada à mão continua fora da soma, com o rótulo que o caminho antigo do JSON já usava.

Um lançamento importado arquivado continua no mês. Antes, o mês lia a movimentação e não olhava o arquivado do JSON. O lançamento manual arquivado continua de fora.

## Foto

A foto compara, nos mesmos dados, o cálculo antigo do mês com o cálculo novo. Entram Marina, Paulo e Eveline, pelo cenário de demonstração, e uma pessoa sintética com mais de 2.000 lançamentos: várias contas, meses e naturezas, importados e manuais, com lote e sem lote, saída com sinal e sem sinal.

O mês de cada período, o `home()` e o recorte por conta ficaram iguais. A área de trabalho devolve os mesmos JSON; a ordem passou a ser `booked_on`, como este recorte pediu. O resumo do `calc.js` é o mesmo nas duas ordens. Não houve diferença a explicar. O teste rodou em SQLite e no PostgreSQL local.

O cenário de 26/10 permanece: disponível R$ 1.200, falta R$ 150 em 28/10, fechamento R$ 1.350, reserva R$ 200, margem R$ 0, conta do Banco do Brasil R$ 1.000.

## Medição

SQLite nesta máquina, uma passagem, com 0, 2.000 e 5.000 lançamentos. “Antes” é o cálculo antigo do mês e a área de trabalho ordenada por `updated_at`. “Depois” é o código publicado.

| Lançamentos | Início, consultas | Início, ms | Área de trabalho, consultas | Área de trabalho, ms |
|---|---|---|---|---|
| 0 | 40 → 38 | 6,2 → 4,5 | 10 → 10 | 2,2 → 1,6 |
| 2.000 | 47 → 45 | 33,7 → 14,4 | 14 → 14 | 33,8 → 29,5 |
| 5.000 | 47 → 45 | 122,4 → 50,6 | 14 → 14 | 139,3 → 118,9 |

O Início deixa de ler todas as ocorrências e todos os lançamentos. Com 5.000 linhas, o tempo local caiu de 122 ms para 51 ms. A área de trabalho ainda devolve a lista inteira; a paginação fica para o 005T4. O número de consultas dela não mudou. Isto não mede o clique no navegador publicado.

## Testes

`python -m unittest discover -s server -p "test_*.py"`: 95 testes, ok, com o PostgreSQL local. `prototype/calc.test.mjs`, `bb-statement.test.mjs` e `lotes.test.mjs`: ok.

A suíte nova cobre a migração 9 → 10 com dados e com a base vazia, a repetição que não altera nada, cada escritor, a ausência de outro `INSERT`/`UPDATE` em `ledger_entry`, a foto, o isolamento, a assinatura repetida, o vínculo, o cenário de 26/10, a medição e a sentença SQL da 0.6.13 sobre o schema 10. A 0.6.13 para a migração antes da versão 10, ignora as colunas novas e continua inserindo o JSON. Na volta, o preenchimento completa as colunas.

## Publicação

Cópia antes da imagem: `backups/20261026T202439+0000/`, `verifiedUpload` verdadeiro, 31 tabelas. Naquele momento o schema era 9 e as tabelas de lançamento estavam em zero.

Commit `39bcc977`, enviado sem force-push. Imagem `sha256:f0ba8d83de6dc0c3ad59919a5749ffba2d5248660edc39fc269c099ddd4a0977`. Tarefa `isa-web:23`. Retorno: `isa-web:22`, isa-piloto 0.6.13. O Financeiro permanece `actionfinance-web:28`.

A troca usou a parada curta que já estava no serviço: mínimo 0, máximo 100, rebalanceamento de zona desligado. A tarefa antiga chegou a sair antes da nova entrar. O rollout de `isa-web:23` concluiu com uma tarefa em execução.

`/api/ready` responde `schema` 10. `/api/health` responde `isa-piloto 0.6.14`, postgres, oidc. `/api/home` e `/api/workspace` sem sessão respondem 401. A contagem depois da imagem segue zero em movimentação, ocorrência, lançamento, nota, saldo, compromisso, entrada, vínculo e conta. A coluna `booked_on` existe. O log da tarefa mostra a abertura e leituras de `/api/ready`. Não houve sessão autenticada em `/api/home` ou `/api/workspace` nesse intervalo.

Conexões lidas imediatamente antes de subir o limite do papel: `actionfinance_runtime` 10 no Financeiro, `isa_app` 3 na ISA, `max_connections` 79, limite do papel 8. O limite passou a 16 sem trocar a senha. Em seguida o serviço voltou a mínimo 100, máximo 200 e rebalanceamento de zona ligado. A permissão temporária usada só para essa alteração foi removida. Duas tarefas de 6 conexões mais a cópia cabem em 16. O Financeiro não foi alterado.

## Limitações

A área de trabalho ainda entrega todos os lançamentos. A busca do lote ainda abre o JSON, porque a data dela não é a `booked_on`. O contexto do modelo também. A movimentação permanece. O valor importado na coluna pode ter sinal. Nada disso muda a tela nem o número que o Início já mostrava.

## Critérios

| # | Resultado | Evidência |
|---|---|---|
| 1 | atendido | Investigação e regra da data neste relatório |
| 2 | atendido | Schema 10 só acrescenta; o preenchimento repetido não muda a linha; o teste de migração não perde id |
| 3 | atendido | `test_only_write_entry_writes_the_ledger` |
| 4 | atendido | O mês não contém leitura de `movement` nem de `occurrence`; presença conta; a fila da IA filtra no SQL |
| 5 | atendido | Foto igual em SQLite e PostgreSQL, sem diferença |
| 6 | atendido | Nenhum arquivo de tela mudou; o JSON do lançamento é o mesmo |
| 7 | atendido | Tabela de medição acima |
| 8 | atendido | 95 testes e os três arquivos do protótipo; cenário de 26/10 igual |
| 9 | atendido | 0.6.14 no ar, schema 10, cópia `backups/20261026T202439+0000/`, retorno `isa-web:22` provado no laboratório sobre o schema 10 |
| 10 | atendido | Limite 16, publicação contínua restaurada, 10 conexões do Financeiro registradas antes da troca |
