# ISA 0.6.7 — Lançamentos, lotes de trabalho e consulta

22/10/2026. A pessoa registra várias despesas num lote, vê o total mudar depois da gravação, sai e continua, e recupera o conjunto ou uma compra. Cartões continuam fora, na etapa 005. A publicação não é aceite do proprietário.

## O que a pessoa vê

Em Lançamentos, o título e a descrição ficam à esquerda; Importar extrato e Registrar, à direita. O mês aparece por extenso, com Anterior, Próximo e Mês atual. A data do mês usa o fuso de Brasília e, na lista, a data do pagamento, do recebimento ou do vencimento. A busca fica sempre visível. Filtros abre o restante. Lançamentos e Lotes são formas de consulta. Todos, Realizados, Previstos e A conferir contam registros; A conferir pode repetir um realizado e não é parcela de Todos. Dentro da conferência, a tela separa categoria pendente, natureza desconhecida e ocorrência de importação ainda não consolidada.

Um lote em andamento mostra o nome, a quantidade gravada, Ver registros e Lançar neste lote. Salvar e lançar outro confirma e prepara a linha seguinte. Salvar e concluir encerra a organização, sem pagar nem apagar. A capa pode ser completada depois. O fornecedor da capa não é copiado para as compras.

Na busca, o valor dos encontrados fica separado do valor do lote completo. Abrir lote completo avisa que o recorte da busca ficou para trás. Sem lote é uma seção, não um lote criado sozinho.

## Modelo

O lote de trabalho é capa, vínculo e histórico. Não é despesa, saldo, autorização nem a sessão. As tabelas novas são `work_batch`, `work_member`, `work_event` e `work_preference`. O lote técnico da importação continua na tabela `batch`. Um lançamento tem no máximo um lote de trabalho ativo e pode continuar no lote técnico de origem. Mover desativa o vínculo anterior e grava o evento; o lançamento não é clonado. Sair não apaga o lote. Entrar de novo não cria lote vazio. A preferência do lote em andamento fica na conta da pessoa.

O total é a soma inteira, em centavos, dos lançamentos ativos do lote, por moeda. Gastos pagos, gastos a pagar, ganhos recebidos, ganhos a receber, transferências/reembolsos/empréstimos, aplicações, BB Rende Fácil e natureza pendente ficam separados. Transferência não reduz o gasto. Natureza desconhecida fica fora do resultado. Categoria vazia em consumo entra em A categorizar e continua no gasto. A soma das categorias fecha com os gastos pagos da mesma moeda. Sugestão ainda não aplicada não vira categoria confirmada. Arquivar tira o registro do total vigente e não estorna. O valor de referência da capa só gera diferença quando todos os gastos registrados estão na mesma moeda; ele não vira lançamento. Não há conversão entre BRL, USD e EUR.

A gravação do lançamento e do vínculo ocorre na mesma transação. Repetir o mesmo identificador não cria outra linha. A capa usa versão: a segunda gravação com a versão antiga é recusada e a primeira permanece. Outra pessoa não lê nem grava o lote, mesmo conhecendo o identificador.

## Prova

Os dez cenários financeiros rodaram em SQLite temporário, com a pessoa sintética `pessoa-ensaio-lotes`, sem a conta publicada. Viagem paga 100,00 e 27,90 soma 127,90. O terceiro item de 25,90, repetido, permanece em três itens e 153,80. O item a pagar de 100,00 deixa os pagos em 153,80 e os gastos registrados em 253,80. O ganho de 50,00 e a transferência de 200,00 ficam fora do gasto. A busca por mercado devolve 100,00 encontrados e 153,80 no lote, na página 1 e na página 2. O lote de uma compra funciona. A referência de 250,00 contra 253,80 registrados mostra 3,80. Editar, mover, arquivar, restaurar e trocar a categoria preservam o identificador e a ocorrência de origem. USD e BRL não se somam. A composição de 100,00 em Alimentação e 27,90 a categorizar fecha 127,90; aplicar Transporte não muda o total.

No navegador de laboratório, com base descartável e a identidade sintética Marina, a jornada gravou Mercado Central 100,00 e Padaria 27,90. A busca mostrou 1 encontrado de 2, R$ 100,00 nos encontrados e R$ 127,90 no lote. Capturas em `documents/reviews/lancamentos-004ia5/`, em 1440, 1280, 768, 390 e 360 px. Não houve sessão autenticada na conta publicada. O zoom real de 200% não foi medido nesta rodada: a prova usou a largura da janela, não a escala do navegador.

## Publicação

https://isa.actionhub.com.br serve `isa-piloto 0.6.7`, baseline 1.3. A tarefa em execução `2b4f22c477fb430fbdb7606a964e6ff3` usa a definição `isa-web:16`, está HEALTHY e o rollout está COMPLETED. A imagem da tarefa é linux/amd64 `sha256:baa5a224cb8daeba0d467b00fe6b1bbd379318878eeafed4df9e1c557d045c13`. O índice da tag `0.6.7` é `sha256:ed4796469618f8d17d1d59746f747cf5a1897d4e6833957b3827a9140c039257` e não entra na tarefa.

`GET /api/health` responde 200 com versão `isa-piloto 0.6.7`, autenticação oidc e banco postgres. `GET /api/ready` responde schema 7. Sem sessão, `GET /api/workspace`, `POST /api/entries`, `POST /api/work-batches` e `POST /api/work-search` respondem 401. A página servida carrega `lotes.js` e `app.js`; o script traz “Lote em andamento”, “Salvar e lançar outro”, “Gastos do recorte” e “Gastos do lote”.

A cópia anterior à migration 7 está em `backups/20261023T122532+0000/`, tarefa `e63f535218734ca3909d31c97aa36bd4`, saída 0, 22 tabelas e upload verificado. Ela é do schema 6 e não contém as tabelas de lote de trabalho. O retorno compatível é `isa-web:15`, versão 0.6.6: abre o schema 7, continua lendo os lançamentos e não apaga os lotes. O ActionFinance permanece em `actionfinance-web:28`.

Não houve sessão autenticada na conta publicada. O zoom real de 200% não foi medido. Esta publicação não é aceite do proprietário.
