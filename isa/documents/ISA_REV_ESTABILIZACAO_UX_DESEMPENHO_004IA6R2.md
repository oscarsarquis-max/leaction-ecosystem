# ISA — Estabilização do Início

26/10/2026. A referência aprovada é `ISA_INICIO_REFERENCIA_004IA6R2.html`. O aceite é desse desenho, não desta publicação. Os relatos 004IA6 e 004IA6R1 permanecem.

## O que a pessoa passa a encontrar

O Início mostra a situação financeira na composição da referência: disponível com data e origem, o que ainda entra e o que ainda falta pagar, uma decisão, a tabela de realizado e previsto, a evolução quando há base, a agenda do mesmo mês e a leitura da ISA. Não há botão, convite nem atalho de importar extrato em nenhum estado do Início. Importar continua em Lançamentos e em Contas.

Uma pessoa sem conta e sem registro vê um convite só: **Sua visão financeira começa pelas contas**, com **Cadastrar primeira conta**. Um mês sem lançamento, havendo histórico, diz **Nenhum lançamento neste mês** e mantém o saldo conhecido. A consulta que falha continua com **Não conseguimos atualizar suas informações agora** e **Tentar novamente**.

## Estados

O servidor passa a informar `presence`: contas, movimentos, compromissos, entradas, lançamentos, saldos e se a pessoa está vazia. O Início só usa primeiro acesso quando `emptyPerson` é verdadeiro depois de uma leitura bem-sucedida. `null`, erro e mês vazio não viram esse convite.

## Cliques

Voltar ao Início com a mesma identidade, conta, moeda e período redesenha o último resultado válido e revalida em seguida, sem apagar a tela. Trocar o mês atualiza o título na hora e mantém o conteúdo até a resposta. A navegação entre Início e Lançamentos, no laboratório local, em 40 medições (20 idas e 20 voltas), ficou em p50 90 ms e p95 162 ms, máximo 165 ms. Isso é SQLite nesta máquina, pessoa sintética, sem a rede publicada. Não é a medida do host nem do celular do proprietário.

O zoom real não se aplicou: `visualViewport.scale` ficou 1 e o H1 ficou em 28 px. Não se usou zoom de CSS.

## Prova

PostgreSQL isolado, pelo mesmo HTTP da aplicação: mês inválido continua 400; o cenário de 26/10/2026 continua com disponível R$ 1.200, falta de R$ 150 em 28/10, fechamento de R$ 1.350, reserva de R$ 200 e margem de hoje R$ 0; a conta do Banco do Brasil isolada continua em R$ 1.000. Um movimento em setembro não torna a pessoa nova em outubro.

No navegador de laboratório, a tela preenchida, o mês vazio com histórico e o primeiro acesso foram capturados em `documents/reviews/inicio-004ia6r2/`, ao lado da referência em 1440 px, e a implementação também em 1280, 768, 390 e 360. Não aparece Importar. Marina não viu o saldo de Paulo.

Pendências: sessão autenticada no host publicado; tempos de rede, PostgreSQL de produção e celular; zoom real de 200%; importação percorrida de ponta a ponta nos dois destinos nesta rodada. A prova de importação existente nesses destinos não foi refilmada aqui.

## Publicação

A cópia anterior à imagem está em `backups/20261026T160249+0000/`, tarefa `72dcd5327ba64e508e35192050fc05ed`, saída 0, 31 tabelas, upload verificado. Não houve migration nem escrita na base publicada.

| Exigência | Evidência |
|---|---|
| Importação fora do Início | Capturas preenchida, mês vazio e primeiro acesso sem a palavra Importar. O botão do primeiro acesso abre Contas. |
| Primeiro acesso correto | Teste de presença com movimento em outro mês; captura de Marina sem contas; captura de outubro com histórico e novembro vazio. |
| Fidelidade visual | `referencia-1440.png` e `inicio-preenchido-1440.png` na mesma largura. A composição principal está na tela, mas não é o mesmo desenho: o controle do mês fica aberto na linha inteira, as legendas sob “Ainda vai entrar” e “Ainda falta pagar” não aparecem, e o laboratório usa 16/10/2026 como hoje. Isso não é aceite visual. |
| Cliques ágeis | 40 trocas locais Início/Lançamentos, p50 90 ms, p95 162 ms. Sem medida publicada. |
| Dados e IA preservados | Cenário financeiro revalidado por HTTP em PostgreSQL. Leitura manual permanece; a automática continua depois dos números, uma vez por contexto. |
| Entrega efetiva | Host em 26/10/2026 16:06 UTC: `isa-piloto 0.6.11`, schema 9, task `isa-web:20`, imagem `sha256:9fed4d9a3291b0892912273f9fea4bac065a8538d973eafd67b569ec15436ae4`. `/api/home` e `/api/workspace` sem sessão respondem 401. O `home.js` servido traz o convite de contas e não traz Importar, “Vamos reunir” nem “Nenhum valor foi gravado”. ActionFinance permanece em `actionfinance-web:28`. |

O retorno da aplicação, se esta imagem precisar sair, é `isa-web:19`, versão 0.6.10. Não se volta à 0.6.9. O ActionFinance não foi alterado.
