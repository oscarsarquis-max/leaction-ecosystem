# ISA 0.6.3 — Início financeiro

17/10/2026. Código `f3dbd5d55369d6cb141d3d2b867fc5a406e7f30d` e correção `013dd06f91127371655c2fb3aafec9cba8de37d3`. A imagem servida é a segunda.

## O que a pessoa encontra

O Início responde, com o que já estiver salvo:

- Quanto tenho: o disponível informado, com a data e a parte protegida dentro desse valor. Se a data não é a de hoje, o número não vira saldo atual. Uma projeção para a data de referência, quando existe e difere do informado, aparece com esse nome.
- Quanto falta pagar: a soma do que resta nos compromissos do planejamento, no período dito na própria frase. Sem entrada confirmada, o período é os próximos 30 dias. Vencidos entram uma vez, como parte dessa soma. Conta sem valor ou data fica contada à parte, fora da soma.
- Quando recebo: a próxima entrada confirmada, com valor, data e contagem de dias. Entrada incerta aparece como incerta e não sustenta a frase principal.
- O dinheiro chega: uma frase. Falta de dinheiro usa a primeira data em que o saldo fica negativo. Se o menor valor do período cai em outro dia, esse dia é dito à parte. Uso da reserva não é chamado de saldo negativo. Se os compromissos informados cabem, a frase diz até quando e mostra a margem. Se ainda não dá para calcular, a frase aponta o que falta e o restante da tela continua.
- Quanto cabe gastar: a margem do motor, com o período. Sem cálculo, a tela diz que ainda não foi calculado. Zero de margem só aparece quando o cálculo mostra que não há folga.

A barra é azul `#1800ad`, a cor lida no fundo de `images/logoisantrans.png`. O logo continua o arquivo opaco, sem borda nem placa. No desktop, a mesma barra leva a Início, Lançamentos, Planejar, Perfil e Registrar. No celular, a barra fica com a marca e a navegação principal vai para a base, com ícone e nome. Sair continua no Perfil. Importar extrato segue em Início e em Lançamentos.

O gráfico só aparece quando a trajetória está completa. O calendário marca entrada, saída e alerta com texto, além da cor. Escolher um dia não muda vencimento nem chama a IA. Embaixo, o mês de lançamentos continua sendo ganhos recebidos, gastos pagos e resultado. Não é o disponível nem a projeção.

Um aviso de encargo mostra o valor em reais, a base e a data. Sem condição registrada, a frase é: ainda não sei os encargos desse atraso. A leitura por IA só começa em **Pedir a leitura de hoje**. Abrir o Início não grava conta, movimento nem chamada.

Para completar o que falta, o cartão abre a etapa correspondente do planejamento. Depois de salvar, a pessoa volta ao Início. A jornada **Salvar e continuar**, sem esse retorno, segue para a etapa seguinte.

## De onde vêm os números

O disponível informado é a disponibilidade ativa. O que falta pagar soma `remaining_cents` dos compromissos do planejamento dentro do período; a cobertura escrita na tela é “Compromissos do planejamento”. Lançamentos do extrato não entram nessa soma. Reserva não é somada de novo. A situação, a margem, a próxima entrada confirmada e a série do gráfico vêm do motor já existente: a primeira falta é `first_insufficiency`; o mínimo é outro campo e só entra na frase quando a data é outra. Encargos usam somente condições gravadas no compromisso, em centavos, com arredondamento half-up. Juros simples só entram com taxa, período e regime registrados. Fatura só é chamada de fatura quando o registro traz `kind` igual a fatura. Não há módulo de cartão.

Não houve migration. O schema continua 4.

## Verificação

Laboratório, base temporária, Paulo e Marina sintéticos. Não é a conta publicada.

A conta vazia não mostra zero no disponível. A conta parcial grava 1.500,00 em 16/10/2026, com 200,00 protegidos, e volta ao Início. A conta com falta mostra R$ 300,00 em 18/10/2026, a soma de R$ 2.890,00 até a entrada de 05/11/2026, e o encargo do condomínio: multa R$ 20,00, juros R$ 10,00, encargos R$ 30,00, total estimado R$ 1.030,00, para pagamento em 16/10/2026. A internet vencida, sem condições, permanece como encargo desconhecido. Marina, com dinheiro suficiente, não vê os compromissos de Paulo. Abrir o Início não criou leitura de IA. A jornada de 0.6.2 foi refeita no mesmo laboratório: o formulário abre, o servidor confirma antes de avançar, e a ajuda grande não cobre os campos.

Capturas em `documents/reviews/inicio-004ia3/`: incompleto e preenchido em 1280 px, falta em 1280 e 390 px, conta suficiente em 1280 e 390 px, e o retorno parcial em 390 px. A barra medida no navegador é `rgb(24, 0, 173)`, igual à amostra do arquivo. No viewport de 640 px, equivalente à largura útil de 200% numa janela de 1280 px, a página fica em uma coluna e sem rolagem horizontal. O comando de zoom do navegador em si não foi acionado. Em 390 px, a ação principal pôde ser levada para cima do menu inferior.

No host público, `/api/health` respondeu `isa-piloto 0.6.3`, `/api/ready` respondeu schema 4 e `/api/workspace` sem sessão respondeu 401. `home.js` respondeu 200 e contém o Início. Task `isa-web:12`, uma implantação concluída, uma tarefa em execução. A imagem é `sha256:d01e7d1843e2bb6ed2fd38b5197a1d280f3ffa7afa0396f9d43b66955eb3c20b`. O manifesto linux/amd64 é `sha256:ee1dd7bf83201c92067bd047f30190f5038e6970ff7c8190b336849c2b1b6cc1`.

A primeira imagem desta entrega, task `isa-web:11`, não publicava `home.js`. Foi substituída antes deste relato. O retorno da aplicação é `isa-web:10`, versão 0.6.2. O Finance permanece em `actionfinance-web:27`. O ingresso continua o `paneldx-alb` existente. Banco, Cognito, permissões de IA e cópia diária não foram alterados.

## Limite

Não houve sessão autenticada na conta publicada, e a conta real não foi preenchida para obter captura. Isto não é aceite do proprietário. Compromisso vencido antes da data do disponível informado continua na soma a pagar e no calendário, e não é descontado de novo da trajetória. A tela de entrada do provedor não foi reestilizada. Gestão de cartão, rotativo e parcelamento não foram implementados.
