# ACTIONFINANCE — Agenda financeira com calendário — 052

Data: 16/10/2026. Candidata 0.2.9 sobre a 0.2.8 publicada. Aceite não atribuído. Nenhuma carga produtiva.

## Antes e depois

A agenda da 0.2.8 abria em faixas (vencidos, hoje, 7 dias, 8º ao 30º, sem data) e numa lista. A 0.2.9 abre, sem parâmetros, num calendário mensal. A lista permanece quando o endereço traz `vista=lista`, `vista=dia` ou `faixa`.

O mês mostra a grade de segunda a domingo, com os dias vizinhos em tom mais claro. Em cada data com compromisso há duas sínteses: entrada azul “A receber” e saída laranja “A pagar”, com quantidade e restante. A legenda fica no cartão da grade: entrada, saída, vencido, hoje e dia selecionado. O painel traz o resumo do mês e o dia escolhido. A diferença prevista é a receber menos a pagar no mês consultado; o texto diz que não é saldo bancário nem posição da conta.

## Consulta

`GET /api/v1/treasury/calendar` devolve o intervalo pedido, a cobertura `MONTH_AND_ADJACENT_DAYS`, a data de referência, o fuso, a moeda BRL, os agregados de cada dia da grade, os totais só do mês principal, os vencidos fora desse mês e o detalhe paginado do foco. Os dias vizinhos são consultados e não entram no total do mês. O valor é o residual dos títulos abertos em real. Rascunho e cancelado ficam de fora. A consulta não grava título, baixa nem movimento.

No ensaio `TreasuryAgendaIT`, o dia 20/01/2031 ficou com 3 recebimentos e restante 120000, 2 pagamentos e restante 45000, diferença 75000. A página 2 do detalhe não alterou esse total. O vizinho da grade, de 1000, ficou fora do mês. Fevereiro de 2032 contém o dia 29. Junho de 2032, além de trinta dias, devolveu o título daquela data. Um vencido de agosto de 2026 não foi movido para hoje nem somado em janeiro de 2031.

## O que foi visto renderizado

Laboratório isolado, Postgres próprio na porta 5441, perfil local-demo, empresa Padaria Exemplo. Edge headless em 1440, 1280, 768 e 390. Não houve rolagem horizontal da página.

- Outubro de 2026, mês corrente, com grade, legenda, hoje no dia 16 e vencidos fora do mês numa faixa própria.
- Setembro de 2026 preenchido. O dia 14 abriu o recebimento vencido de R$ 32,00, com “Conta ainda não definida”, sem trocar a direção.
- O clique nesse título foi para o recebível e o Voltar restaurou `vista=calendario&mes=2026-09&dia=2026-09-14`.
- Março de 2027, além de trinta dias e depois da virada do ano, manteve a grade vazia, a frase “Nenhum vencimento neste mês” e os atalhos Novo recebimento e Novo pagamento. Os vencidos de outros meses continuaram na faixa de fora e não entraram no zero do mês.
- A seta do teclado saiu de 15/09/2026 para o foco `cal-day-2026-09-16`.
- Em 390 px a grade ficou em sete colunas, com ícone e quantidade na célula e o valor no painel abaixo. Em 768 px o resumo foi para baixo da grade. Em 1280 e 1440 ficaram lado a lado.
- O zoom CSS de 200% no Chromium reflowou controles e células sem rolagem horizontal da página.
- No mesmo laboratório, o dia 20/11/2026, identificado como ensaio-052, mostrou “A receber · 2 · R$ 1.200,00” e “A pagar · 1 · R$ 450,00”. O painel listou os três compromissos, um deles “Parcialmente recebido”, e a diferença prevista de R$ 750,00 com a frase de que não é saldo bancário.

Um desvio visto na primeira captura — as células saíam como botão azul da marca — foi corrigido antes desta leitura. A regra que pintava todo botão do fluxo passou a excluir o dia, o compromisso e a faixa auxiliar.

## O que esta rodada não fechou

A conciliação do laboratório foi aberta e está vazia: não há lote confirmado para classificar, ratear, relacionar e desfazer. Iniciativas também foi aberta e está vazia. Não houve estorno de baixa acompanhado na agenda. Essa pendência do relato 051 continua. Menu e tipo de teste não a substituem.

A publicação desta candidata ainda não foi feita. A imagem de retorno permanece a 0.2.8, task `actionfinance-web:25`, bundle `index-BgQocLZy.js`. Schema V24 não foi reaplicado nem editado. Flyway do site continua desligado. Nenhum título, baixa ou arquivo real foi criado em produção.

## Pendências

Posição informada pela fonte, conta prevista no compromisso, fluxo de caixa projetado e análise continuam fora. O aceite do proprietário não está atribuído.
