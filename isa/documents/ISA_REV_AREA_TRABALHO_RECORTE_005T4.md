# Área de trabalho por recorte — 005T4

26/10/2026. isa-piloto 0.6.15, schema 11. A área de trabalho passa a devolver o recorte que a tela está mostrando. As listas, contagens, totais, lotes, o aviso de duplicidade e o detalhe permanecem os mesmos. O catálogo de bancos sai dessa resposta.

## Investigação

`store.workspace()` lia todos os lançamentos, todas as ocorrências, todas as notas, todos os lotes e o catálogo de bancos. O navegador pedia `/api/workspace` ao entrar, ao recarregar a lista e em cada gravação que devolve a área de trabalho. `applyWorkspace` substituía `state.entries` inteiro.

O que cada tela lia:

| Chamada | Recorte que a tela usa | Campos |
|---|---|---|
| Entrar e recarregar a lista | Mês de `state.month`, ou o lote aberto em `#lote/{id}`, ou todos os meses | `entries`, `workBatches`, `accounts`, `context`, `profile` |
| Lançamentos | O mesmo recorte, filtrado ainda no navegador por direção, categoria, situação, moeda, busca, busca rápida, consumo e resultado | `entries`, `workBatches`, `occurrences` pendentes do mês |
| Registrar e conferir | Duplicidade contra todos os lançamentos da pessoa, não contra o mês | o rascunho; a resposta nova é `POST /api/entries/duplicate-check` |
| Detalhe | O lançamento do endereço, mesmo fora do mês | `entries` se já estiver na memória; senão `GET /api/entries/{id}` |
| Contas e importação | Catálogo de bancos, uma vez | `banks` e `bankCatalog`, agora em `GET /api/banks` |
| Importação | Lote técnico e pendências | `batches` com a conta, `occurrences` em estado pendente |
| Início | Não usa a lista. O mês do Início continua `booked_on` | `accounts`, `context` |

`mine()` também servia a duplicidade, o detalhe, a faixa do lote e o par de `linkId`. Um recorte sem o par mudaria `IsaCalc.summarize`. Um recorte sem os membros do lote ativo faria a faixa contar “fora da conta” o que estava só em outro mês. A faixa passou a usar `outsideAccount`, contado no servidor: membros cuja conta não é a conta em visualização. Com todas as contas, esse número é zero.

`workbatches.list_batches` já calculava `count`, `memberIds`, `totals` e `compositions`. O cartão do lote usa esses números. A lista do mês não precisa ter todos os membros na memória. A leitura dos membros, que era uma consulta por lançamento, passou a vir em blocos de 400.

Ocorrências: a tela usa as pendentes do mês na conferência e a conta do lote técnico na importação. A resposta traz só `state = pendente`. A conta do lote sai de uma linha por lote, não de todas as ocorrências incorporadas. Notas: as do mês, do período, ou todas quando a pessoa pede todos os meses. Nota sem data permanece.

Medição do 005T3, nesta máquina, com a área inteira: 14 consultas e 118,9 ms com 5.000 lançamentos; 610 KB com 2.000.

## Tabela de recortes

`GET /api/workspace` aceita o recorte na query ou no cabeçalho `X-ISA-Slice`. A query prevalece. Sem parâmetro, o mês corrente em `America/Sao_Paulo`.

| Parâmetro | O que volta |
|---|---|
| `month=YYYY-MM` | Lançamentos cuja data da lista cai no mês |
| `batch={id}` | Lançamentos ativos daquele lote, em qualquer mês |
| `from=YYYY-MM-DD&to=YYYY-MM-DD` | Período pela mesma data da lista |
| `scope=all` | Todos os meses, sem paginação nova |
| `archived=1` | Inclui os arquivados do recorte |

A data da lista é uma função só, `list_month`: pagamento ou recebimento, senão vencimento, senão documento. É a mesma ordem de `IsaLotes.monthOf`. A consulta usa `booked_on` ou `due_on` no intervalo, com os índices que já existiam, e filtra em seguida por essa função.

Também entram, marcados `outsideSlice`, o par de cada `linkId` do recorte e, no mês ou no período, os membros do lote ativo. A lista não os mostra. O cálculo do mês os encontra.

A resposta mantém o formato anterior, sem `banks` e sem `bankCatalog`, e ganha `slice` com o recorte efetivo.

Gravações que já devolviam `workspace` devolvem esse recorte. Trocar mês, lote, período ou “todos os meses” pede o recorte novo. Até a resposta chegar, a lista anterior permanece e o título já é o novo.

A 0.6.14 ignora os parâmetros e continua devolvendo tudo. A 0.6.15 sem parâmetro devolve o mês corrente. Um navegador antigo em cache, até recarregar, vê só o mês corrente. Isso fica aceito: recarregar a página traz o script novo.

## O que mudou

| Arquivo | Mudança |
|---|---|
| `server/store.py` | Recorte, mês da lista, duplicidade, leitura de um lançamento, catálogo com ETag, schema 11 |
| `server/workbatches.py` | `outsideAccount`; membros do lote em blocos |
| `server/wsgi_app.py` | Recorte nas respostas, `GET /api/banks`, duplicidade e detalhe |
| `server/serve.py` | O mesmo no laboratório |
| `prototype/lotes.js` | `inList`, `matchesQuick` e `reviewKind`, a mesma regra da lista |
| `prototype/app.js` | Cabeçalho do recorte, troca sem apagar a lista, duplicidade e detalhe no servidor, catálogo sob demanda, botão “Todos os meses” |
| `prototype/styles.css` | A barra do mês quebra a linha para o botão caber em 390 px |
| `server/test_recorte_005t4.py` | Equivalência, duplicidade, detalhe, bancos, isolamento, medição, cenário de 26/10 |
| `prototype/recorte.test.mjs` | A mesma lista, os totais e o cálculo, com as funções reais |
| Testes já existentes | Schema 11; ocorrência incorporada lida no SQL; linha antiga lida com `scope=all` |
| `scripts/dev/prova-recorte-005t4.py` | Prova de tela no laboratório isolado |
| `VERSION` | isa-piloto 0.6.15 |

O índice novo é `ledger_entry_owner_amount_idx` em `(owner_id, amount_cents)`, `CREATE INDEX IF NOT EXISTS`, migração 11. A duplicidade busca por esse valor e, para documento ou impressão com outro valor, por um trecho do JSON. A comparação final é a mesma de `calc.js`.

## Equivalência

Para Marina, Paulo, Eveline e uma pessoa sintética com 2.100 lançamentos, a área inteira filtrada pelas funções de `lotes.js` e `calc.js` foi comparada com o recorte do servidor. Mesmas linhas, na mesma ordem, as mesmas contagens, `IsaLotes.summarize`, `composition` e `IsaCalc.summarize`.

Coberto: mês, lote que atravessa meses, todos os meses, período, arquivados, realizados, previstos, a conferir, direção, categoria, situação, moeda, busca, resultado e consumo. O par com `linkId` em outro mês entra como `outsideSlice`. Sem ele, o cálculo do mês muda; com ele, fica igual ao da lista inteira. Aberto com vencimento em outro mês fica no mês do vencimento. Arquivado não aparece no mês, e aparece quando o recorte pede arquivados.

A duplicidade do servidor, nos mesmos rascunhos, devolve o mesmo tipo que `calc.js`, inclusive o aviso brando de mesmo valor e mesma data. Documento e impressão valem com outro valor. Lançamento de outra pessoa não entra. O detalhe da própria pessoa abre fora do mês. O de outra pessoa responde 404. A gravação com `X-ISA-Slice: month=2026-09` devolve setembro, não o mês corrente e não a lista inteira.

O cenário de 26/10 permanece: disponível R$ 1.200, falta R$ 150 em 28/10, fechamento R$ 1.350, reserva R$ 200, margem R$ 0, conta do Banco do Brasil R$ 1.000.

## Capturas

Laboratório isolado, Marina sintética, `scripts/dev/prova-recorte-005t4.py`. Não é a conta publicada. Não há captura de antes: a tela já estava em edição quando a prova rodou. A diferença visual nova é o botão “Todos os meses” / “Ver só este mês”, necessário para a pessoa escolher `scope=all`. O restante da lista, do lote, do detalhe e do aviso de duplicidade usa os mesmos textos.

| Tela | 1440 | 390 |
|---|---|---|
| Mês, só o Mercado Central de outubro; a faixa do lote continua com os 2 registros e R$ 150 | `documents/reviews/recorte-005t4/depois-mes-1440.png` | `depois-mes-390.png` |
| Todos os meses: Material, Fora do lote e Mercado; totais R$ 172 | `depois-todos-1440.png` | `depois-todos-390.png` |
| Lote que atravessa agosto e outubro | `depois-lote-1440.png` | `depois-lote-390.png` |
| Detalhe aberto a partir do lote | `depois-detalhe-lote-1440.png` | — |
| Detalhe de setembro, fora do recorte do mês, buscado no servidor | `depois-detalhe-fora-1440.png` | — |
| Registrar, possível duplicata pelo combinacao | `depois-duplicata-1440.png` | `depois-duplicata-390.png` |

Em 390 a barra do mês quebra a linha e o botão “Todos os meses” aparece. Não houve comparação de pixel com uma imagem anterior.

## Medição

SQLite nesta máquina, depois da mudança. O mês é outubro de 2026, um quarto dos lançamentos. O lote grande contém todos eles. `scope=all` é a lista inteira, sem as ocorrências já incorporadas.

| Lançamentos | Mês: consultas, ms, bytes, linhas | Lote: consultas, ms, bytes | Todos: consultas, ms, bytes |
|---|---|---|---|
| 0 | 12, 1,0 ms, 443 B, 0 | 11, 0,7 ms, 442 B | 11, 0,7 ms, 439 B |
| 2.000 | 16, 9,7 ms, 308 KB, 500 | 26, 51,6 ms, 1,29 MB | 21, 41,1 ms, 1,29 MB |
| 5.000 | 16, 59,5 ms, 767 KB, 1.250 | 42, 508 ms, 3,23 MB | 29, 221 ms, 3,23 MB |

`GET /api/banks`: 54.369 bytes. No 005T3 a área inteira com 5.000 lançamentos levava 14 consultas e 118,9 ms, e com 2.000 ocupava 610 KB. O mês agora leva 16 consultas e 59,5 ms com 5.000 na base, e 308 KB com 2.000 na base. O lote de 5.000 ainda lê os membros para o total do cartão; por isso fica mais lento que a lista do mês.

## Testes

`python -m unittest discover -s server -p "test_*.py"`: 104 testes, ok, SQLite e PostgreSQL local `127.0.0.1:5442`. `node prototype/calc.test.mjs`, `lotes.test.mjs`, `bb-statement.test.mjs` e `recorte.test.mjs`: ok.

## Publicação

A publicar neste commit, com cópia verificada antes da imagem. Serviço contínuo no mínimo 100 e no máximo 200. A 0.6.14 ignora o recorte. A 0.6.15 sem recorte devolve o mês corrente. Retorno: `isa-web:23`, isa-piloto 0.6.14. O hash, a imagem e a revisão da tarefa entram neste relatório quando a troca concluir.

## Limitações

O mês do Início e o mês da lista continuam diferentes. `scope=all` ainda devolve todos os lançamentos. O cartão de um lote grande lê os membros no servidor. O valor importado pode continuar com sinal na coluna. Cache de arquivo estático, saldo do extrato, recorrência, telas e cores não entram aqui. ActionFinance, Cognito, Spider e Hub não mudam.

## Critérios

| # | Resultado | Evidência |
|---|---|---|
| 1 | atendido | Investigação neste relatório |
| 2 | atendido | `GET /api/workspace` com `slice`; o formato segue, sem o catálogo |
| 3 | atendido | Par e lote ativo com `outsideSlice`; faixa e cartão usam o servidor |
| 4 | atendido | Duplicidade igual ao `calc.js`; detalhe 200 da própria pessoa e 404 da outra |
| 5 | atendido | Gravação com `month=2026-09` devolve esse mês |
| 6 | atendido | `GET /api/banks` com ETag, `max-age=86400` e 304; sem sessão, 401; a área de trabalho não traz o catálogo |
| 7 | parcial | Listas e totais idênticos no teste. Capturas do laboratório depois da mudança. Não há par antes/depois para comparar pixel |
| 8 | atendido | Tabela de medição acima, mais o tamanho de `/api/banks` |
| 9 | atendido | 104 testes e os quatro arquivos do protótipo; cenário de 26/10 igual |
| 10 | não atendido | A imagem `isa-web:24` ainda não foi publicada. O retorno previsto é `isa-web:23` |
