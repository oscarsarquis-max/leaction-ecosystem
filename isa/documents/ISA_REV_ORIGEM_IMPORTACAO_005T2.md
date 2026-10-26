# ISA — Origem verdadeira das importações

26/10/2026. isa-piloto 0.6.13, schema 9. O extrato enviado por uma pessoa passa a ser gravado como arquivo real. Nenhum registro foi apagado, reimportado ou recriado. Números, telas financeiras e regras do motor não mudaram.

## Investigação

A origem gravada não dizia a verdade.

No navegador, o arquivo escolhido recebia `arquivo-teste`. O exemplo embutido recebia `exemplo-sintetico`. `statementSource()` devolvia `exemplo-sintetico` para qualquer outro valor, inclusive vazio. A prévia pública ia para `PUT /api/drafts/import` sem a origem, e a restauração depois do recarregamento copiava só as movimentações. A confirmação então caía no padrão e gravava `exemplo-sintetico`, com `simulated: true`.

No servidor, `import_batch` e `import_statement` usavam a mesma frase: `body.get("origin") or "exemplo-sintetico"`.

A origem fica em `batch.origin`, `movement.source`, `occurrence.payload_json.source`, `ledger_entry.payload_json` (`source` e `simulated`) e, quando a observação traz origem, em `statement_note.payload_json`. `sync_entries` marcava `simulated` quando `source == "exemplo-sintetico"`. `workspace` repetia essa comparação. `decide_occurrence` grava `decisao`, que não é origem de importação.

`cenario-sintetico-004` é origem de saldo e de cenário de laboratório, não de extrato. `extrato-sintetico` aparece no cálculo do mês e nos lotes de trabalho como leitura de linha de extrato. Nenhum dos dois entra na lista que se grava agora.

Quem lê a origem:

| Lugar | Uso |
|---|---|
| `isStatementEntry` em `prototype/app.js` | reconhece linha de extrato no detalhe |
| texto do detalhe | "Origem: Extrato BB…" |
| `prototype/calc.js` `isStatement` | separa linha de extrato de consumo no resumo do mês |
| `prototype/lotes.js` e `server/workbatches.py` | o mesmo reconhecimento no lote de trabalho |
| `engine.py` | não lê `source` nem `simulated` |
| `month_picture` | soma `amount_cents` por data, natureza e direção |
| `ai.entry_context` | id, estabelecimento, natureza, direção, valor, categoria, trava, arquivo, situação e datas. Sem origem e sem `simulated` |

`simulated: true` não muda o total do servidor, a lista do mês, o Início, o Planejar nem o contexto da IA. O que muda o resumo do mês no navegador é a origem ser reconhecida como extrato. Por isso `extrato-bb-arquivo` entrou no mesmo conjunto de `arquivo-teste`, `exemplo-sintetico` e `extrato-sintetico`. O teste de `calc.js` compara os dois resumos e exige o mesmo número de linhas não identificadas, a mesma saída e o mesmo pago.

Em produção, `/api/fixtures/*` continua 404 e `prototype/fixtures` fica fora da imagem. As pessoas de laboratório não existem nesse ambiente.

## Inventário antes

Leitura somente, sem escrita. A tarefa de cópia, com transação somente leitura, consultou a base publicada. A cópia `backups/20261026T173749+0000/dump.json` (4.731 bytes, 31 tabelas) foi conferida do mesmo modo, só com contagens.

Não havia linha de importação. Contagem por origem, em todas as tabelas e por pessoa: zero para `arquivo-teste`, `exemplo-sintetico`, `extrato-sintetico`, `extrato-bb-arquivo`, vazio e qualquer outro valor de origem de extrato. `cenario-sintetico-004` também não apareceu. Nada ficou de fora da reclassificação por ser inexplicável: não havia valor a reclassificar.

Tabelas com alguma linha, sem identificar a pessoa: `identity` 2, `person_profile` 1, `account_preference` 1, `work_batch` 5, `work_event` 5, `work_preference` 1. Conta, lote de importação, movimentação, ocorrência, lançamento, observação de extrato, disponibilidade, compromisso e entrada: 0.

Conexões do papel no momento da leitura: 3. `max_connections` da instância: 79. Limite do papel `isa_app`: 8.

## O que mudou

| Arquivo | Mudança |
|---|---|
| `server/store.py` | origens aceitas no servidor. Sem origem, origem desconhecida ou, em produção, `exemplo-sintetico` e `arquivo-teste`: recusa com "A origem do arquivo não foi reconhecida. Nada foi importado." `simulated` só para `exemplo-sintetico`. A confirmação usa a origem gravada na prévia quando o lote é o mesmo. A observação de saldo passa a carregar a origem. |
| `prototype/app.js` | arquivo escolhido usa `extrato-bb-arquivo` e grava essa origem na prévia. Sem origem conhecida, a confirmação não é enviada e a tela pede o arquivo de novo. A prévia restaurada devolve a origem. Em produção o exemplo embutido não abre. O detalhe diz "Extrato BB, arquivo enviado" para o arquivo real e para o `arquivo-teste` legado. O exemplo sintético só aparece no laboratório. |
| `prototype/calc.js`, `prototype/lotes.js`, `server/workbatches.py` | `extrato-bb-arquivo` continua linha de extrato, como as origens antigas. |
| `prototype/calc.test.mjs` | o resumo do mês fica igual entre `arquivo-teste` e `extrato-bb-arquivo`. |
| `server/test_accounts.py` | as duas importações de ensaio passam a origem válida, para continuar provando a moeda. |
| `server/test_origem_005t2.py` | os sete casos pedidos. |
| `scripts/ops/reclassify-import-origin-005t2.py` | simulação por padrão. `--apply` grava. Só `ISA_ENV=production`. Exige cópia verificada do mesmo dia. Uma transação por pessoa. `originLegacy` no JSON e `change_log` com ação `reclassificar-origem-005t2`. A segunda execução não muda nada. |
| `VERSION` | `isa-piloto 0.6.13`. |
| `documents/ISA_CONTINUIDADE_PRODUCAO.md` | uma frase: 0.6.13 não cria schema; a reclassificação não apagou registros; a origem anterior fica em `originLegacy` e no `change_log`. |

`arquivo-teste` não é mais gravado. Continua reconhecido na leitura. O schema permanece 9.

## Testes

`python -m unittest discover -s server -p "test_*.py"` no PostgreSQL isolado: 84 testes, OK. `node prototype/calc.test.mjs`, `bb-statement.test.mjs` e `lotes.test.mjs`: ok.

Coberto: gravação de `extrato-bb-arquivo` em lote, movimentação, ocorrência, lançamento e observação, com `simulated` falso; pedido sem origem, desconhecido ou `arquivo-teste` não grava e responde 400; em produção, `exemplo-sintetico` e `arquivo-teste` também; a prévia salva manda a origem na confirmação; a simulação não escreve, `--apply` troca, a segunda execução fica em zero, as somas de centavos permanecem, `change_log` e `originLegacy` existem, ids e vínculos permanecem; o script recusa laboratório e cópia que não é de hoje; o cenário de 26/10/2026 permanece (disponível R$ 1.200, falta R$ 150 em 28/10, fechamento R$ 1.350, reserva R$ 200, margem R$ 0, conta BB R$ 1.000); o lançamento de outra pessoa não aparece; a mesma `signature` não cria outra movimentação; os totais do mês ficam iguais.

A leitura de `extrato-bb-arquivo` passa por `workspace` e `home` sem erro. O código 0.6.12 não tem lista de origem na leitura, então também não recusa essa palavra.

## Script na base publicada

Cópia usada: `backups/20261026T183625+0000/`, `verifiedUpload` verdadeiro, 31 tabelas, criada no mesmo dia. Tarefa `551909202ff0486d87ea059935d938b2`, saída 0.

Simulação:

```json
{"modo": "simulacao", "wouldChange": 0, "changed": 0, "before": [], "after": [], "controleAntes": [], "controleDepois": [], "iguais": true}
```

`--apply`:

```json
{"modo": "aplicado", "wouldChange": 0, "changed": 0, "before": [], "after": [], "controleAntes": [], "controleDepois": [], "iguais": true}
```

Segunda execução:

```json
{"modo": "aplicado", "wouldChange": 0, "changed": 0, "before": [], "after": [], "controleAntes": [], "controleDepois": [], "iguais": true}
```

Quantidade e soma de `amount_cents` por pessoa: listas vazias antes e depois, iguais. Não havia movimentação. Nada foi apagado.

## Orçamento de conexões

Antes da publicação, o serviço estava em `minimumHealthyPercent` 100, `maximumPercent` 200, rebalanceamento de zona ligado, tarefa `isa-web:21`. O pool de cada processo vai até 6. O papel aceita 8. Na troca contínua, duas tarefas somam 12, acima de 8, e a cópia soma mais uma.

A instância informa `max_connections` 79. Havia 3 conexões do papel na leitura.

O rebalanceamento de zona recusou `maximumPercent` 100. A saída escolhida foi a parada curta, sem mexer no pool nem no limite do papel: rebalanceamento desligado, `minimumHealthyPercent` 0 e `maximumPercent` 100. Só uma tarefa existe durante a troca. O pico do pool fica em 6, abaixo de 8. A cópia terminou antes da troca. A reclassificação correu depois, com a tarefa nova já sozinha. Na troca, a tarefa antiga chegou a zero antes da nova subir.

## Publicação

Commit `35ac85c0`, enviado sem force-push. Imagem `sha256:5b0241ce8800c9931400bc7fa70688b8d178f08ff121636135a0696de3e058df`. Tarefa `isa-web:22`. Retorno: `isa-web:21`, isa-piloto 0.6.12. O Financeiro permanece `actionfinance-web:28`.

`GET /api/ready`: 200, `{"ready": true, "schema": 9}`. `GET /api/health`: `isa-piloto 0.6.13`, postgres, oidc. `GET /api/home` sem sessão: 401. O `app.js` publicado contém `extrato-bb-arquivo` e a frase "arquivo enviado".

Não havia sessão do proprietário. Lançamentos e o detalhe de um lançamento importado não foram abertos.

## Critérios

| # | Resultado | Evidência |
|---|---|---|
| 1 | atendido | inventário só de contagens, sem identidade; zero origens de extrato |
| 2 | atendido | servidor e navegador recusam origem ausente ou desconhecida; o padrão silencioso saiu |
| 3 | atendido | a prévia guarda a origem e a confirmação usa essa origem |
| 4 | atendido | em produção o exemplo não abre e `exemplo-sintetico` recebe 400 |
| 5 | atendido | simulação por padrão, só produção, cópia do dia, idempotente, `change_log` e `originLegacy` no ensaio |
| 6 | atendido | somas de controle iguais no ensaio e na base publicada (vazias e iguais) |
| 7 | atendido | zero `arquivo-teste` e zero `exemplo-sintetico` depois do `--apply` |
| 8 | atendido | 84 testes e os três arquivos do protótipo; cenário de 26/10 e totais do mês iguais |
| 9 | atendido | 100/200 contra limite 8; parada curta aplicada e registrada, sem alterar o papel |
| 10 | atendido | 0.6.13 no ar, schema 9, cópia `backups/20261026T183625+0000/`, retorno `isa-web:21` |

## Limitações

A base publicada não tinha extrato gravado. A reclassificação correu e alterou zero linhas. O próximo arquivo enviado entra como `extrato-bb-arquivo`.

Sem sessão do proprietário, a frase do detalhe não foi vista na tela. O arquivo publicado já a contém.

A parada curta desligou o rebalanceamento de zona, porque o serviço não aceita `maximumPercent` 100 com ele ligado. O pool e o limite do papel continuam 6 e 8. Uma publicação futura com duas tarefas ao mesmo tempo voltaria a passar de 8.
