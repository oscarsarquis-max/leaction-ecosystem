# ISA — fechamento da importação local

Data: 16/10/2026. Protótipo **0.4.0**. Baseline proposta **1.1**, a mesma da etapa anterior. Não publicada, não aceita e sem commit desta etapa.

Os Prompts 001, 002 e o Adendo 002A permanecem. O leitor do Banco do Brasil e a separação entre movimentação e saldo continuam. Esta correção não abre Open Finance, não contrata IA e não mexe no ActionFinance.

## Comportamento

A prévia começa pelo arquivo e pelo intervalo encontrado, segue para a conta em Real, mostra novas, já importadas e a conferir, e só então oferece **Importar N movimentações**. A lista, a codificação, a ausência de moeda no CSV e os saldos ficam em seções recolhidas. O saldo final datado aparece dentro dos saldos. No celular a ação fica acima da consulta e acima do menu. No desktop a decisão fica ao lado da consulta. Os botões de reenvio e de sobreposição estão numa área chamada Demonstração.

Cada linha lida vira uma ocorrência, com origem e estado. Confirmar as novas cria movimentos só para elas. As correspondências ficam numa fila, fora dos totais de ganhos e gastos, até a pessoa decidir. Reenviar o mesmo arquivo reabre o resultado e não cria ocorrência. Uma carga nova aponta para decisões já tomadas quando elas cobrem a quantidade recebida. A lista de assinaturas do lote não entra na conta de movimentos.

A assinatura dos seis campos é candidata, não identidade bancária. A pessoa pode marcar uma ocorrência como a mesma operação ou como outra. Não há mais o botão que guardava todas as dúvidas de uma vez. Repetir a decisão não cria outro movimento. Duas compras iguais no mesmo arquivo continuam duas.

O Início separa o que já tem natureza de consumo do que ainda é só entrada ou saída de extrato. Com natureza pendente, o cartão diz **Resultado identificado até agora** e a quantidade sem natureza. Não diz que o mês não teve gasto. Um gasto com natureza de consumo e categoria vazia entra no total e aparece em **A categorizar**. BB Rende Fácil aparece como **Movimentação BB Rende Fácil**. O extrato não vira rendimento nem patrimônio investido.

O exemplo sintético grava origem `exemplo-sintetico`. Um CSV escolhido no seletor grava `arquivo-teste` e não fica marcado como simulação. Antes da escolha, a tela diz que o seletor é de teste e que o aplicativo não descobre sozinho se o arquivo é real. O extrato verdadeiro não entra na demonstração nem nas fixtures.

## Testes

Cálculo e leitor, em Node: `prototype/calc.test.mjs` e `prototype/bb-statement.test.mjs`. O segundo cobre candidata, duas operações iguais, reuso da pendência numa terceira leitura e a terceira fixture sintética com saldo fechado.

No navegador, só com fixtures sintéticas, em 390×844 e 1280×800, emulação no Edge, não um aparelho físico:

- lote inicial: 8 movimentos, duas compras de R$ 40,00, duas movimentações BB Rende Fácil, seis ainda sem natureza;
- reenvio: continuou 8 ocorrências;
- sobreposição: entrou 1 e ficaram 2 para conferir;
- saída e volta à fila;
- uma ocorrência marcada como a mesma e outra como nova; a soma das compras ficou R$ 120,00;
- repetir a decisão não aumentou os movimentos;
- terceira carga: a compra incorporada continuou 3, o Pix já importado continuou 1, e só a linha nova entrou;
- Início com natureza pendente mostra cobertura parcial; o gasto de R$ 27,90 sem categoria entra no total e em A categorizar;
- a conta, a quantidade nova e Importar 8 movimentações aparecem sem abrir a lista;
- no desktop, decisão e consulta ficam lado a lado;
- Paulo, com o mesmo CSV sintético escolhido no seletor, gravou `arquivo-teste` sem o rótulo de simulação.

A jornada anterior de lançamento manual, duplicata e isolamento entre Marina e Paulo foi repetida e passou. Não houve rolagem horizontal da página.

Capturas: `documents/prototipo/390-importar-decisao.png`, `1280-importar-decisao.png`, `390-pendencias.png`, `390-inicio-parcial.png`, `390-inicio-categorizar.png`.

## Limitações

A demonstração vive no navegador, separada por pessoa, sem senha e sem dono no servidor. Isso não protege um extrato real. Não houve câmera de aparelho nem teclado virtual; o foco de um campo sobe acima do menu. A classificação continua demonstrativa e não escolhe categoria. Nenhuma descrição foi enviada a um provedor. O arquivo real usado na conferência do leitor não foi copiado para cá. A emulação de tela não prova um celular.

## Git e a próxima etapa

O diretório `isa/` segue não rastreado. Não houve commit. O ActionFinance permanece na versão já publicada, 0.2.10; os arquivos sujos dessa frente não foram alterados nesta correção.

A próxima etapa é acesso individual e persistência. A categorização real espera o provedor definido e não precisa existir para a importação funcionar.
