# Plano de entrega — tesouraria AF-BL-023 revisão 1.3

Data: 16/10/2026. Projeto: [PROJETO_TESOURARIA_MP_023_R1_3](ACTIONFINANCE_PROJETO_TESOURARIA_MP_023_R1_3.md). A revisão 1.2 permanece como histórico. Esta revisão não é versão de produto e não reserva números de versão antigos. Aceite não atribuído.

O plano 1.2 dizia que nada dele estava implantado, que V21 ainda não estava escrita e que o extrato entraria sob Recebimentos. O extrato foi publicado de 0.2.0 a 0.2.5, as contas na composição aprovada em 0.2.6, e o schema está em V23. A navegação deste incremento coloca Contas e Extratos em Tesouraria.

## 1. Incremento atual — navegação

O usuário encontra Tesouraria, Recebimentos, Pagamentos e Cadastros, nesta ordem. Em Tesouraria: Contas e Extratos. Em Recebimentos: A receber e Recebimentos integrados, com o título interno ActionHub Pay e o texto de que são informações da origem, não extrato e não valores conciliados. Em Pagamentos: A pagar. Em Cadastros: Clientes e fornecedores e Categorias.

Não há página para Visão geral, Análise e planejamento, Conciliação, Fluxo de caixa, Iniciativas ou Rateios. As URLs atuais permanecem. Quem não lê contas não vê Tesouraria. O destino inicial de quem já entra em Recebimentos não muda só porque a ordem visual mudou.

## 2. Entregas seguintes, em cadeia

Não há versão de produto já reservada para elas. O número sai na hora da publicação.

### Classificação e conciliação

O usuário classifica, rateia com regra vigente e confirma ou desfaz vínculo com a evidência à vista. Depende do extrato e das categorias já publicados. A fórmula e as exceções estão na seção 6 do projeto 1.3. Termina quando a cobertura é explicável sem código e a linha ambígua continua fora do total elegível.

### Posição e compromissos

O usuário vê saldo informado, saldo gerencial e a diferença de conferência, além da agenda ligada à conta. Depende de saldo inicial datado para a posição calculada. Sem esse saldo, a agenda continua e a posição não é apresentada como conhecida. Seção 7 do projeto 1.3.

### Fluxo e planejamento

O usuário vê até 13 semanas, o menor saldo do cenário e o que é hipótese. Realizado e previsto do mesmo fato não se somam. A Visão geral só nasce com o que já for utilizável. Seção 8 do projeto 1.3.

## 3. Pendência paralela

Os nove pares ambíguos do relatório real seguem pela operação na conta ou por relatório correspondente, com proveniência. Não se inventa estorno, parcela ou compensação para liberá-los. Isso não trava a navegação nem a classificação das linhas elegíveis.

## 4. Provas que continuam abertas

O detalhe autenticado citado no 027 e a repetição sem gravação nova continuam sem sessão do operador. A importação do arquivo real não está comprovada. A soma parcial do extrato não é posição de caixa. A segunda confirmação com conflito não é o reenvio do arquivo.

## 5. Fora deste plano

Spider, Hub, Cognito, cliente direto ao Mercado Pago, execução de pagamento e ISA.
