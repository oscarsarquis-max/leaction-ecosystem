# ISA 005T5 — Regras únicas do lançamento

Data: 26/10/2026. Base de partida: isa-piloto 0.6.15, schema 11, commit `89bdb4ac`. Este recorte muda os números de propósito. A regra de foto idêntica do 005T3 deixa de valer para lançamento aberto, arquivado e valor com sinal. O cenário de 26/10/2026, que usa saldo e compromissos, permanece.

## Investigação

### Onde o mês, o realizado, o aberto, o arquivado e o valor eram calculados

| Ponto | O que fazia | O que passou a fazer |
|---|---|---|
| `entry_columns` / `write_entry` | Se existia movimentação com o mesmo id, copiava `amount_cents`, `direction`, `booked_on` e `nature`. A data, sem movimentação, era `statusDate` ou `noteDate`. | O valor da coluna é sempre absoluto. `booked_on` segue a data única. A movimentação não é mais lida. |
| `backfill_entry_columns` | Só preenchia coluna nula. | Recalcula valor e data de todas as linhas, sem reescrever o JSON. Pode repetir. |
| `_month_state` | Não olha a situação. Data até hoje vira realizado, salvo transferência e aplicação. | Continua valendo para o que já está realizado. O aberto não passa por aqui. |
| `month_picture` | Arquivado importado continuava no mês. `a_conferir` ia para `pendingNatureCents` com o inteiro da coluna, inclusive negativo. Aberto com data até hoje entrava no realizado. | Arquivado fica de fora. Incorporado ou `pago`/`recebido` é realizado. `a_pagar`/`a_receber` é em aberto ou previsto e só entra no previsto se não houver `link_row`. |
| Recorte do `workspace` | Mês e período usavam `booked_on` ou `due_on` e depois filtravam em Python com `statusDate` ou `dueDate` ou `noteDate`. | Filtra por `booked_on`. A coluna já guarda a data única, então o `OR` e o filtro em Python saíram. |
| `person_presence` | Conta linhas. Não soma o mês. | Sem mudança. |
| `ai.py` | Gasto pago de consumo no mês de `statusDate`. | Usa a mesma data do realizado (`statusDate` ou `noteDate`). |
| `workbatches.py` | Busca e ordenação por `statusDate` ou `dueDate` ou `noteDate`. | Usa a data única. |
| `calc.js` | Já ignorava arquivado. Realizado por situação e data de pagamento. Aberto por vencimento ou documento. | O realizado sem data de pagamento passa a usar o documento. O extrato incorporado continua na faixa "a conferir" da lista; no Início ele entra no realizado. |
| `lotes.js` | `statusDate` ou `dueDate` ou `noteDate`. | A mesma tabela de `fact_date`. |
| `home.js` | Já mostra "em aberto" e "previsto". | Sem mudança de tela. O Início passa a emitir esses estados para o lançamento aberto. |
| `engine.py` | Lê saldo, compromisso e entrada prevista. Não lê lançamento. | Continua sem lançamento aberto. |

### Sinal da saída importada

O leitor `prototype/bb-statement.js` exige centavos negativos na saída. `import_batch` grava esse inteiro em `movement.amount_cents`. O escritor copiava esse inteiro para `ledger_entry.amount_cents`. O JSON já guardava o absoluto (`amountMinor`).

Com a natureza padrão do extrato, `a_conferir`, o mês não jogava esse inteiro em `realizedOut`. Jogava em `pendingNatureCents`. Na pessoa sintética, Farmácia (−50,00) e Padaria (−30,00) deixavam essa faixa em −80,00 e a linha aparecia como realizado negativo. Não reduziam a saída realizada.

Quando a natureza conta no mês, o mesmo inteiro negativo reduzia `realizedOut`. O caso de teste importa uma saída de consumo de 18,00 com sinal no arquivo: a movimentação permanece −1800 e a coluna do lançamento fica 1800. O realizado do mês soma 1800. A soma antiga dessa coluna seria −1800.

`movement.amount_cents` não é recalculado e nenhum cálculo novo o lê.

### Testes que só passavam com a regra antiga

- A foto `assert_same_picture` comparava o mês com a função antiga. No conjunto sintético grande isso dependia do sinal, do arquivado importado e de tratar tudo com data até hoje como realizado.
- `mov-1` exigia `ledger_entry.amount_cents = -1800`, igual à movimentação.
- `assert_coherent` exigia a coluna igual ao inteiro da movimentação, com sinal.
- Os casos de mês sem situação tratavam vencimento como data da lista mesmo quando o lançamento não estava em aberto.
- As suítes afirmavam schema 11.

O cenário de 26/10 e as pessoas de demonstração, que não têm lançamento aberto nem saída negativa, continuam iguais à função antiga.

### O que a lista já fazia

`IsaCalc.summarize` já deixava arquivado de fora e não tratava `a_pagar`/`a_receber` como realizado. A data do aberto já era vencimento ou documento. Faltava, no realizado sem data de pagamento, cair no documento. `IsaLotes.monthOf` ainda usava a data antiga da lista. Os dois lados agora leem `prototype/regras-mes.json`.

## As quatro regras

R1. `ledger_entry.amount_cents` é o valor absoluto. `direction` é `entrada` ou `saida`.

R2. Arquivado, importado ou manual, fica fora do realizado, do previsto e das contagens do mês. O filtro de arquivados da lista continua mostrando a linha.

R3. Realizado é `pago`, `recebido` ou ocorrência de extrato incorporada. `a_pagar` e `a_receber` são em aberto (vencimento até hoje) ou previsto (depois de hoje). Entram no previsto do mês só se não houver `link_row` para aquele lançamento. Não entram no motor de projeção.

R4. Realizado usa a data de pagamento ou recebimento; se ela faltar, a do documento. Em aberto usa o vencimento; se faltar, o documento. `booked_on` guarda essa data. Pagar uma conta aberta muda o mês quando o pagamento cai em outro mês.

O recorte da lista ficou só em `booked_on`. A data única cabe numa coluna, então o `OR due_on` e o filtro em Python não são mais necessários.

## Pessoa sintética, antes × depois

Outubro de 2026, hoje 26/10/2026, sem saldo. O compromisso do aluguel permanece com restante de 1.000,00. O vínculo foi gravado em `link_row` sem baixar esse restante, porque o lançamento continua `a_pagar`: o vínculo impede a soma dupla e o compromisso segue a regra atual, que conta o restante.

O "antes" é a função antiga aplicada aos mesmos registros, não uma segunda execução da 0.6.15.

| | Antes | Depois |
|---|---|---|
| Realizado saída | 390,00 (Mercado, Luz e Internet) | 150,00 (Mercado e Farmácia) |
| Realizado entrada | 500,00 (Freela tratado como realizado) | 0 |
| Previsto saída | 1.000,00 (só o compromisso) | 1.200,00 (Luz 200,00 + compromisso 1.000,00) |
| Previsto entrada | 0 | 500,00 (Freela) |
| Faixa de natureza pendente | −80,00 | 0 |
| Internet | Outubro, como realizado | Novembro, como previsto, 90,00 |
| Padaria arquivada | No mês, linha negativa | Fora de todo total |
| Aluguel em aberto | Sem data de coluna, invisível no mês | Na tabela, em aberto, sem entrar de novo no previsto |

A lista de outubro, sem filtro, traz Mercado, Luz, Farmácia, Freela e Aluguel. Internet aparece em novembro. Padaria só com o filtro de arquivados. Na lista, gastos pagos 100,00 e saída de extrato a conferir 50,00 somam os mesmos 150,00 do realizado. A pagar na lista é Luz mais Aluguel, 1.200,00, o mesmo previsto do Início, sem somar o aluguel duas vezes.

Lançamentos em aberto que não entram no motor, neste laboratório: Luz, Internet, Freela e Aluguel, quatro. O compromisso do aluguel continua no motor. O cenário de 26/10 não tem lançamento aberto e não mudou: disponível 1.200,00, falta 150,00 em 28/10, fechamento 1.350,00, reserva 200,00, margem 0, conta BB 1.000,00.

## Testes alterados

| Teste | Motivo |
|---|---|
| `mov-1` em `test_lancamento_005t3` | A coluna passa a 1800. A movimentação continua −1800. |
| `assert_coherent` | Compara o absoluto da movimentação, não o sinal. |
| Foto do conjunto sintético grande | Deixa de exigir igualdade com a função antiga. Passa a exigir valor absoluto, data igual à regra e arquivado fora do mês. |
| Foto das pessoas de demonstração e do 26/10 | Mantida. Esses dados não usam as regras que mudaram. |
| Casos de mês em `test_recorte_005t4` e `recorte.test.mjs` | O caso em aberto agora declara a situação, para o vencimento mandar. Sem situação, a data é a do documento. |
| Schema em lançamento, recorte, contas, trabalho, conexão e Postgres | A versão passou a 12. |
| `rewind_ledger` | Apaga também a versão 12, senão a migração 10 não reaplicava. |

## Testes novos

`server/test_regras_005t5.py` e `prototype/regras-mes.test.mjs`, os dois lendo `prototype/regras-mes.json`.

1. Pessoa sintética no Início e na lista, em SQLite e em PostgreSQL isolado.
2. A tabela de mês igual nos dois lados.
3. Backfill duas vezes, JSON e `updated_at` intactos, uma só linha de schema 12.
4. Arquivado fora de todos os totais.
5. Compromisso vinculado uma vez só.
6. Isolamento entre pessoas.
7. Cenário de 26/10 inalterado.
8. Saída de consumo com sinal no arquivo: antes reduziria o realizado; agora soma 18,00.
9. Pagar a conta de novembro em 26/10 muda o mês para outubro.

Suítes: 113 testes Python em SQLite e PostgreSQL isolado, OK. `prototype/*.test.mjs`, OK.

## Publicação

Commit `85797ca6`, enviado sem force-push. Imagem `sha256:bc2311513683851af6fba4293eba0a73b824f57caaca0c69581271775d83b9e5`. Tarefa `isa-web:25`. Retorno: `isa-web:24`, isa-piloto 0.6.15. O Financeiro permanece `actionfinance-web:28`.

Cópia antes da imagem: `backups/20261027T000022+0000/`, `verifiedUpload` true, 31 tabelas. Tarefa de cópia `4168f263d7b74d4d9fd9b3e55275e736`.

A 0.6.15 sobe em cima do schema 12: a migração 12 não cria nem apaga coluna, só registra a versão. O código antigo, ao ver a versão 12, não tenta refazer o índice da versão 11. Uma convivência deixaria a 0.6.15 gravar `booked_on` pela data antiga e copiar o sinal da movimentação, e o backfill da 0.6.16 só corre na subida do processo.

A parada com máximo 100 foi recusada enquanto o rebalanceamento de zona estava ligado. Com o rebalanceamento desligado e máximo 100, a tarefa 24 parou e a 25 não chegou a ser colocada. O rebalanceamento foi religado e o serviço voltou a mínimo 100 e máximo 200. A tarefa 25 subiu com a 24 já encerrada, então as duas versões não atenderam ao mesmo tempo. Houve um intervalo sem tarefa. O rollout de `isa-web:25` concluiu com uma tarefa em execução, nesses percentuais.

`/api/health` responde `isa-piloto 0.6.16`, postgres, oidc. `/api/ready` responde schema 12. `/api/banks`, `/api/workspace` e `/api/home` sem sessão respondem 401. A contagem somente leitura, com transação só de leitura, está em zero para movimentação, ocorrência, lançamento, nota, saldo, compromisso, entrada, vínculo e conta, schema 12. O log da tarefa nova mostra `/api/ready` 200 e, neste intervalo, `/api/banks`, `/api/workspace` e `/api/home` em 401. Não houve sessão autenticada.

A base publicada não tem lançamento. Recalcular as colunas não altera número que alguém já tenha visto.

## Limitações

- Lançamento em aberto não vira compromisso e não entra no motor. São quatro casos na pessoa sintética.
- `link_movement`, quando confirma o valor inteiro, baixa o restante do compromisso a zero e o compromisso sai do previsto. O caso do aluguel não usa esse caminho: o restante continua 1.000,00 e o vínculo só evita a segunda soma.
- Na lista, o extrato incorporado continua na faixa a conferir. No Início ele entra no realizado. Os 150,00 fecham somando as duas faixas da lista.
- `movement.amount_cents` guarda o sinal do arquivo.
- Membros do lote ativo continuam podendo aparecer fora do mês, como no 005T4.
- Telas, orçamento, saldo do extrato e a unificação de conta a pagar com compromisso ficam fora. A tela do Início não foi aberta no navegador. Os testes conferem o payload que essa tela já desenha com os estados "em aberto" e "previsto".
