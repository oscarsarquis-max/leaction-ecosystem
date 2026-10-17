# ISA — importação do extrato e categorização

Proposta de baseline 1.1. Protótipo 0.3.0. Não é produção e não está aceita. O Prompt 002 permanece no arquivo original; este texto registra o contrato implementado na demonstração.

## O que a pessoa faz

No Início ou em Lançamentos, escolhe Importar extrato. Pode escolher um CSV ou usar o exemplo inventado. A tela diz Lendo extrato. Se o arquivo não servir, a frase é: Não consegui ler este arquivo. Escolha outro extrato. Cancelar a seleção não grava nada.

A prévia separa movimentações e observações de saldo. O botão principal é Importar N movimentações. Ler não grava. Confirmar grava uma vez e abre Lançamentos, com o intervalo das datas encontradas. Categoria não é pedida.

A conta de destino é um nome declarado, em Real. O CSV do Banco do Brasil conferido não traz agência nem conta. O banco não é consultado. O mesmo arquivo já vinculado a uma conta não muda de conta em silêncio.

## Saldo e resultado

Linha de saldo não é entrada nem saída. Saldo informado no extrato tem data própria e não é saldo disponível, investimento ou limite. O resultado do mês continua sendo recebidos menos pagos. Um extrato parcial não inventa saldo inicial nem saldo atual. Aplicação e o que ainda não tem natureza ficam fora desse resultado, com aviso. Dois registros vinculados contam uma vez; os dois continuam guardados.

## Repetição

O reenvio do mesmo texto é outro caso do que um período sobreposto. Sem identificador bancário estável, a assinatura é a dos seis campos, com a quantidade de linhas iguais. Data, descrição e valor iguais, sozinhos, não apagam uma linha. Dúvida fica para conferência. A pessoa pode guardar só as novas ou também as que pedem conferência. Nada é fundido sozinho.

Um gasto manual com o mesmo valor e a mesma data de uma linha do extrato gera uma sugestão de vínculo, não uma fusão. Desfazer o vínculo não apaga os registros. A nota não marca nada como pago.

## Agente

Fronteira da demonstração: a entrada é a descrição; a saída seria categoria, frase curta e se precisa de ajuda. Nesta entrega não há provedor. O botão diz classificação demonstrativa e não chama IA. Estados: A categorizar, Categorizado e Precisa de ajuda. Falha da classificação não refaz a importação. A categoria escolhida pela pessoa prevalece. O agente demonstrativo não altera valor, data, conta nem situação.

Pix, transferência, cartão e BB Rende Fácil não recebem categoria de consumo por essa regra local.

## Antes do uso real

A separação de Marina e Paulo no navegador não protege extrato real. Uso persistente de movimentação real espera a fatia de acesso individual, com dono verificado no servidor. A jornada sintética não espera essa fatia. Conexão automática e Open Finance ficam para depois.
