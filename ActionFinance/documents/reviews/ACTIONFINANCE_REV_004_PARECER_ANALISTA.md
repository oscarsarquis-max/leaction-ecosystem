# ACTIONFINANCE_REV_004 — Parecer do analista

Data: 29/09/2026. **Resultado: entrega funcional parcial, aceite pendente de quatro ajustes e prova da jornada.** Sem PRM_005.

## Alcance

Revisão estática do relatório, serviços de baixa/contas, repositórios de contas/títulos, trechos das novas telas e nomes/cobertura dos testes de integração. Inspeção das capturas mobile de extrato e desktop de registro de recebimento. Não executei escritas no runtime, não li tokens e não modifiquei implementação. Os achados de comportamento abaixo são inferências diretas do código, não incidentes reproduzidos pelo analista.

Os XML Failsafe presentes confirmam 32 testes sem falhas/erros/skips. Os demais resultados de gates/backup são atribuídos ao relatório Cursor. Isso não equivale a uma validação ponta a ponta de toda a experiência.

## Aproveitado nesta entrega

A separação título/baixa/alocação/movimento/estorno foi materializada. Há registro transacional, idempotência persistida, locks de título/conta, restante calculado pelas alocações não estornadas e distinção entre controle financeiro e execução externa. O exemplo de saldo 250 + 50 − 100 = 200 está coerente. O mobile inspecionado não apresenta o corte lateral visto no ciclo anterior.

Não reabrir fundação/PRM_003, não redesenhar o domínio e não acrescentar integrações. Os ajustes abaixo pertencem às operações novas do PRM_004.

## R1 — Escritas de conta ainda escapam da recuperação segura

**Prioridade alta.** App.tsx/AccountCreateDialog faz POST com crypto.randomUUID() a cada submissão, usando request diretamente. Se o servidor criar a conta e sua abertura, mas a resposta se perder, a repetição usa outra chave e pode criar outra conta/abertura. AccountDetailPage também gera chave nova por tentativa de renomear/inativar/reativar, sem fluxo congelado e bloqueio consistente de envio.

Aplicar o mecanismo já existente freezeWrite/sendPending e classificação de resultado desconhecido a todas essas escritas novas, preservando rota, corpo, empresa/ator e chave. Não criar implementação paralela de retry. Bloquear repetição concorrente; resultado desconhecido oferece repetição segura. Rejeição definitiva permite correção de campos.

Prova exigida: criar conta pelo diálogo da baixa; simular resposta perdida após sucesso e repetir com mesma chave/corpo, obtendo uma única conta e um único movimento OPENING. Cobrir também atualização de conta, sem declarar criação duplicada resolvida apenas com teste da página dedicada.

## R2 — Conflito de baixa não atualiza versão; retry pode ficar travado

**Prioridade alta.** SettlementFormPage recebe VERSION_CONFLICT e exibe restante atual vindo do erro, mas não recarrega title/version. A tentativa seguinte usa a versão antiga novamente. Além disso, no handler do botão Tentar novamente, uma resposta definitiva limpa pending.current sem limpar unknownResult; o botão normal continua desabilitado e o retry retorna sem fazer nada porque pending é nulo.

Correção: em conflito, carregar versão/restante atuais, preservar os valores digitados e pedir revisão explícita do usuário antes de enviar uma operação nova. Não reduzir automaticamente o valor. Ao resolver um resultado desconhecido com erro definitivo, sair do estado pendente e devolver controles utilizáveis. Aplicar comportamento equivalente ao estorno quando houver conflito de versão.

Provas: duas sessões tentam baixar o mesmo título; a perdedora revê o restante, ajusta o pedido e conclui sem recarregar a aplicação. Outra prova: timeout seguido de 400/409 na repetição deixa o formulário recuperável, sem botões permanentemente bloqueados.

## R3 — Extrato não usa uma fotografia consistente

**Prioridade média, integridade da consulta.** AccountService.movements não possui transação de leitura consistente. JdbcAccountRepository.listMovements consulta contagem, saldo anterior, soma do período, saldo atual e linhas separadamente. Uma baixa concorrente pode entrar entre consultas e produzir uma resposta com saldos incompatíveis entre si.

Usar fotografia transacional consistente para toda a resposta do extrato, incluindo a leitura da conta, ou consulta equivalente. Preservar o cálculo acumulado antes da paginação e a ordenação da abertura. No frontend, cabeçalho e extrato devem usar saldo da mesma resposta ao exibir o mesmo conceito, evitando dois valores atuais divergentes obtidos em momentos distintos. Mudanças rápidas de período não devem permitir que resposta antiga substitua a consulta mais recente.

Prova: baixa/estorno concorrente durante consulta; saldo anterior + entradas − saídas = saldo final, linhas/saldo acumulado coerentes e total correto além da primeira página. Não basta validar os valores de seed sem concorrência.

## R4 — Extrato mobile omite o valor da movimentação

**Prioridade média de UX.** Os cartões em AccountDetailPage mostram data, descrição e balanceAfterMinor, mas omitem inflowMinor/outflowMinor e não rotulam o número destacado como saldo. Na captura, “Recebimento registrado” aparece com R$ 300,00, embora o recebimento seja R$ 50,00; 300 é o saldo posterior. A leitura pode atribuir ao recebimento um valor errado.

Cada cartão deve mostrar, separadamente: **Entrada R$ 50,00** ou **Saída R$ 100,00**, e **Saldo após R$ 300,00**. Abertura deve ter rótulo próprio. Manter moeda e sinal/texto sem depender só de cor. Disponibilizar acesso ao detalhe da baixa para referência, autor e instante; não limitar o mobile a uma descrição estática.

Prova visual: capturas de entrada, saída e estorno com valores distintos do saldo acumulado, em 360 px, sem corte ou ambiguidade. Não requer redesign completo da tela.

## Prova de entrega ainda necessária

O relatório declara que a jornada de escrita no browser não foi executada. A presença de seed e testes de serviço não substitui a jornada UX pedida. Após corrigir os quatro pontos, executar no navegador, com dados demonstrativos próprios: criar conta, baixar 50 de 150, baixar o restante, estornar 50, consultar título e extrato; percorrer também pagamento. Registrar capturas/resultados e o perfil de consulta sem escrita. Testes que simulam respostas devem ser identificados como mocks.

Completar evidência de rollback dos novos fatos e de estorno concorrente, prevista no prompt, se não estiver coberta por teste existente. Reutilizar cobertura já válida; não repetir testes da fundação sem motivo. Rodar gates pertinentes após as alterações e agrupar evidências da execução final.

## Identidade visual e limites

As três logos compactas estão aprovadas pelo proprietário, com dimensões/proporções/margens preservadas e prioridade à amarela. Sua aplicação e a evolução da paleta azul/amarelo serão direção visual própria; não são usadas para reprovar retroativamente esta fatia. Não gerar novamente nem recortar as versões aprovadas.

## Deliberação

Corrigir este conjunto no mesmo PRM_004 e retornar um relatório consolidado para aceite. A funcionalidade entregue é aproveitada. Sem novo ciclo exclusivo de infraestrutura, sem mudanças em outros produtos, sem PRM_005 e sem produção/piloto. Este documento é parecer do analista; não é encerramento aprovado.
