# ISA — relato da importação do extrato

Protótipo 0.3.0. Baseline proposta 1.1, não aceita e não publicada. ActionFinance permanece 0.2.10. Nada disto foi commitado.

## Versão e arquivos

A pasta `isa/` segue sem commit. Entram o leitor `prototype/bb-statement.js`, as fixtures sintéticas, os testes, a jornada no `app.js` e os documentos `ISA_EXTRATO_BB_002.md`, `ISA_PROJETO_IMPORTACAO_BB_002.md` e este relato. O Prompt 002 original não foi reescrito; ele está fora do repositório, em Documentos.

## O que foi conferido

O CSV real, só nesta máquina: 5.217 bytes, sem BOM, não é UTF-8, lido em Windows-1252. 53 movimentações, 11 observações de saldo, 10 entradas, 43 saídas. O controle de saldo fechou. Nenhuma linha pessoal foi copiada para a demonstração.

Testes sintéticos: formato, arquivo vazio, sinal incoerente, saldo zero, documento repetido, duas linhas iguais, reenvio, sobreposição, Windows-1252 e vínculo que conta uma vez.

No navegador, com o exemplo inventado, em 390 e 1280: escolher o exemplo, ver a prévia, importar 8 movimentações, achar a lista, reenviar sem duplicar e guardar só a linha nova do arquivo sobreposto. A jornada anterior de gasto manual, foto simulada e duplicata de comprovante continuou passando, sem rolagem horizontal.

## Limites

Não há câmera de celular provada, teclado virtual, IA real nem gravação fora do navegador. A classificação demonstrativa não escolhe categoria. O arquivo real não alimenta Marina nem Paulo.
