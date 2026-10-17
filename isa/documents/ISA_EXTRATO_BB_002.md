# ISA — extrato do Banco do Brasil

Adendo 002A, conferido em 16/10/2026. O protótipo 0.2.0 lê esse perfil. Isso não é a importação persistente do produto e não publica o extrato de ninguém.

O arquivo `ISA_PROMPT_IMPORTACAO_BB_E_CATEGORIZACAO_002.md` não está nesta pasta. Ele não foi reescrito. O que segue é o perfil que o adendo fechou.

## Leitura local do arquivo real

O CSV informado pelo proprietário foi lido só nesta máquina. Não foi editado, não entrou no Git, não foi copiado para Marina ou Paulo e o conteúdo não foi enviado a um provedor.

| Conferência | Resultado |
| --- | --- |
| Tamanho | 5.217 bytes |
| BOM | ausente |
| UTF-8 estrito | não |
| Decodificação usada | Windows-1252 |
| Movimentações | 53 |
| Observações de saldo | 11 |
| Entradas | 10 |
| Saídas | 43 |
| Controle de saldo | fechou, na ordem do arquivo, a partir do saldo anterior |

A prévia não trata os 64 registros como 64 gastos. As linhas de saldo ficam fora da soma de entradas e saídas.

O nome do arquivo indica o mês e não prova que outubro inteiro tenha sido exportado. As movimentações lidas vão do dia 1º ao dia 16. O saldo anterior está na véspera. Esses limites não são valores.

## Perfil

Separador vírgula, campos entre aspas. O leitor não fatia a linha num split simples, porque o valor também tem vírgula.

Cabeçalho, nesta ordem: Data, Lançamento, Detalhes, N° documento (com o sinal de grau), Valor, Tipo Lançamento.

- Data civil `dd/MM/aaaa`, sem hora e sem mudança de dia por fuso.
- Lançamento preservado.
- Detalhes pode vir vazio. Pode ter dado pessoal e não entra em log integral.
- N° documento é texto, com zeros e pontuação. Não é único e não é chave global.
- Valor brasileiro, em centavos inteiros. Saída desta amostra vem negativa. Zero é valor, não ausência.
- Tipo Entrada, Saída ou vazio. O vazio, nos rótulos conhecidos, é observação de saldo. O sinal tem de combinar com o tipo.

Política de codificação, testada: UTF-8 válido, com ou sem BOM, é lido como UTF-8. Se a sequência não for UTF-8 estrito, a leitura usa Windows-1252. Não há substituição silenciosa por caractere de erro. Outra estrutura de coluna devolve erro e não importa nada.

Rótulos de saldo, depois de normalizar espaços e caixa, e só por igualdade: Saldo Anterior, Saldo do dia, e `S A L D O` com espaços entre as letras. Uma busca pela substring `saldo` não acha esse último rótulo. Uma descrição que apenas mencione saldo continua movimentação.

`S A L D O` é saldo informado no extrato, na data da linha. Não é saldo disponível, não prova investimento e não prova limite.

## Conta e moeda

O CSV não traz agência, conta, titular, moeda nem período num cabeçalho extra. A prévia pergunta: em qual conta você quer importar este extrato? A demonstração oferece o nome já declarado Conta BB, em Real, ou um nome novo. O vínculo é declaração da pessoa. O banco não é consultado. Outra moeda não entra neste perfil. O nome do arquivo não identifica a conta.

## Repetição

O número do documento se repete na amostra, em grupos de duas e de nove ocorrências, sem linha exatamente igual nos seis campos. A repetição do número não é duplicata da operação.

A identidade do lote é a do texto exato. Reenviar o mesmo arquivo não funde nem descarta linha. Arquivos sobrepostos comparam a assinatura dos seis campos, com a quantidade de linhas iguais, sem usar o número da linha. Se a quantidade igual deixa dúvida entre operação legítima repetida e reenvio, a conferência aparece e a pessoa escolhe. Nada é fundido sozinho.

## BB Rende Fácil e meios

Há nove movimentações com o histórico BB Rende Fácil na amostra. Entrada dessa família não vira salário. Saída não vira consumo. O arquivo não separa principal e rendimento. A linha permanece no extrato, com natureza de aplicação, sem posição de investimento inventada. Isso é regra de leitura, não uso de IA.

Pix, transferência e compra com cartão nomeiam o meio. Não recebem categoria de consumo. A categoria não é obrigatória para guardar a prévia.

## O que o protótipo guarda

Só o exemplo sintético em `prototype/fixtures/`. A validação do arquivo real é o script `prototype/validate-bb-local.mjs`, que imprime contagens e se o saldo fechou, sem linhas nem valores. A gravação vista na demonstração fica no navegador e está marcada como exemplo.
