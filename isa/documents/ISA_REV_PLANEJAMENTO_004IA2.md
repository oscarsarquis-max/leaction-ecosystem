# ISA 0.6.2 — planejamento guiado

17/10/2026. Código `6a6308f4e5ab42d58028e7fe9a932deac48fb422`.

## O que a pessoa encontra

No Início, a frase diz qual informação falta e o botão se chama **Informar dinheiro disponível**. O toque abre a etapa do dinheiro, sem passar antes pelo cartão grande da ajuda.

A etapa mostra o cabeçalho com o logo, Voltar, o progresso Seu dinheiro → Próxima entrada → Contas a pagar, o título **Quanto você tem disponível?** e a explicação para não incluir limite do cartão nem cheque especial. Os campos são Dinheiro disponível, com R$ e entrada brasileira, e a data do valor. A reserva só aparece se a pessoa quiser separar uma parte, e esse valor continua dentro do disponível. A ação é **Salvar e continuar**.

Enquanto grava, a tela diz Salvando… e não avança antes da resposta do servidor. Em branco não vira zero. Zero informado permanece zero. Um erro fica junto do campo, com os valores ainda na tela. Ainda não sei guarda a pendência e oferece continuar ou voltar; o planejamento segue marcado como incompleto.

A entrada seguinte distingue o que já está confirmado do que ainda é incerto. As contas a pagar aparecem em lista, com espaço para outra e para seguir. Declarar que não há conta conhecida é diferente de ainda não ter preenchido a lista. No resumo, cada item tem Editar. Abrir a tela de novo não grava sozinho e não apaga o que já estava salvo.

A ajuda grande não entra acima do formulário. Durante o preenchimento ela fica atrás de **Preciso de ajuda para responder**. Quando já há informação salva, a ajuda volta depois do resumo e, se faltar algo, aponta o campo em vez de pedir o valor numa pergunta livre.

O material em `claude/2026-10-15-interface-gestao-financeira` foi lido. A hierarquia de uma ação por vez foi aproveitada. A marca e as cores daquele estudo não entraram na ISA.

## O que foi preservado

Não houve migration, reset, seed nem escrita na base publicada. O schema continua 4. Banco, identidades, permissões de IA, cópia diária e histórico permanecem. Os números 600,00 e 100,00 eram exemplos de campo, não saldo salvo; nenhum registro real foi alterado por causa deles.

A task anterior `isa-web:9`, versão 0.6.1, continua registrada para retorno. O Finance permanece em `actionfinance-web:27`. O ingresso continua o `paneldx-alb` existente.

## Verificação

No laboratório, com base temporária e a conta sintética de Paulo, a jornada foi percorrida no navegador: formulário aberto pelo botão, erro de campo vazio, falha de rede sem confirmação falsa, zero salvo e depois corrigido para 1.200,50, uma entrada e uma conta sem duplicar no retorno. Capturas em `documents/reviews/planejar-004ia2/`. Isso não é uma sessão da conta publicada e não é aceite do proprietário.

No host público, depois da troca da imagem, `/api/health` respondeu `isa-piloto 0.6.2`, `/api/ready` respondeu schema 4 e `/api/workspace` sem sessão respondeu 401. O arquivo `plan.js` servido contém o título e **Salvar e continuar**. Task `isa-web:10`, uma implantação concluída e um alvo saudável. A imagem é `sha256:b3b7d65e373bf7c1ac498134cc570e2ddc594253f0677f619ef7c57ee283f424`.

## Limite

A prova autenticada no host público não foi feita: não havia sessão autorizada da conta real, e a conta da Eveline não recebeu dados de teste. No celular, a ação principal fica abaixo dos campos e o menu inferior permanece fixo; na prova de 390 px ela pôde ser alcançada sem ficar coberta.
