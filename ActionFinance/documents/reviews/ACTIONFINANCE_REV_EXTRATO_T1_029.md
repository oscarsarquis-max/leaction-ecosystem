# REV 029 — Extrato T1, candidata de laboratório

Data: 15/10/2026. Estado: **candidata 0.2.0**, não publicada. O produto no ar permanece **0.1.2**.

## O que esta entrega é

Uma linha de extrato gravada aqui é observação externa. Confirmar a importação não concilia, não quita recebimento, não cria título, baixa nem movimento de caixa. A sugestão de vínculo continua sugestão.

A jornada fica em Contas → Extrato. As duas barras permanecem. Recebimentos não foi redesenhado. A empresa exibida continua Loja de Pães. Nenhuma iniciativa recebe o extrato inteiro: a linha fica “Não atribuída” e “Não classificada”.

## Perfil do arquivo

Um único perfil, `mp-account-money-csv-1`, parser versão 1.

| Peça | Regra |
|---|---|
| Codificação | UTF-8. BOM é removido. UTF-8 inválido é recusado |
| Separador | Vírgula. Cabeçalho só com ponto e vírgula é recusado, sem tentativa de adivinhar |
| Dinheiro | Ponto decimal, até dois decimais, sem milhar e sem sinal. Crédito e débito são colunas distintas |
| Data | `yyyy-MM-dd`, ou instante ISO convertido para o dia civil em America/Sao_Paulo |
| Colunas obrigatórias | `DATE`, `SOURCE_ID`, `RECORD_TYPE` |
| Colunas conhecidas | `EXTERNAL_REFERENCE`, `DESCRIPTION`, `NET_CREDIT_AMOUNT`, `NET_DEBIT_AMOUNT`, `GROSS_AMOUNT`, `MP_FEE_AMOUNT`, `FINANCING_FEE_AMOUNT`, `SHIPPING_FEE_AMOUNT`, `TAXES_AMOUNT`, `CURRENCY`, `ACCOUNT_EXTERNAL_REF` |
| Moeda | Coluna ausente: assume BRL e avisa. Coluna em branco ou diferente de BRL: a linha não entra e não há conversão |

A chave do evento é `MERCADOPAGO|mp-account-money-csv-1|{SOURCE_ID}|{RECORD_TYPE}`. `SOURCE_ID` sozinho identifica o pagamento e pode repetir em liquidação, tarifa, liberação e estorno. O hash do arquivo identifica o lote. O número da linha identifica a posição naquele arquivo. Valor e data iguais não fundem eventos.

Mesmo evento, mesma revisão de conteúdo: não duplica. Conteúdo divergente: as duas apresentações ficam inelegíveis e o valor já gravado permanece. Omissão não apaga dado conhecido. Campo antes vazio pode ser preenchido. Repetir a confirmação com a mesma chave não grava de novo.

Tarifa na mesma linha compõe o evento e não é somada outra vez ao líquido. Liberação, bloqueio e desbloqueio são efeito só de disponibilidade e ficam fora da soma de entradas e saídas. Célula vazia não vira zero. Zero escrito no arquivo permanece zero.

O arquivo sintético prova o parser e o fluxo. Não prova acesso ao Mercado Pago nem compatibilidade com toda exportação real.

## O que foi executado

Banco isolado Postgres 17.6, Flyway até V21, só dentro do teste. O RDS público não foi migrado.

`StatementObservationIT` percorreu, numa rodada:

- arquivo válido, prévia, confirmação, repetição da mesma chave e arquivo sobreposto sem segunda linha;
- o mesmo pagamento em liquidação e liberação, preservados como eventos diferentes;
- o mesmo valor e a mesma data com identificadores diferentes, preservados;
- conflito do mesmo evento, com o líquido já gravado de R$ 85,00 mantido;
- linha sem identidade e moeda USD fora da gravação; confirmação só das elegíveis;
- prévia obsoleta respondida com conflito e sem gravação;
- arquivo sem conta exigindo evidência de origem; evidência curta recusada;
- separador por ponto e vírgula diagnosticado e não interpretado;
- sugestão qualificada pela referência do processador, sugestão fraca por data e valor quando há um único recebimento, e ausência de sugestão quando há dois candidatos pelo mesmo valor;
- identificador de pedido igual ao `SOURCE_ID` sem sugestão, porque namespaces diferentes não são comparados;
- empresa B e perfil só de leitura sem acesso de escrita;
- nenhuma criação de título, baixa ou `cash_movement`; o pago do recebimento sintético permaneceu R$ 85,00.

Soma conferida depois da primeira confirmação: entradas que afetam disponibilidade R$ 223,00; saídas R$ 3,50; uma liberação fora da soma; um líquido ausente. A tarifa de R$ 5,00 da liquidação não entrou de novo nessa soma.

`MpAccountMoneyCsvParserTest`: perfil, duplicata, conflito, zero explícito, ausência, moeda sem conversão e separador recusado.

Frontend: `StatementPage.test.tsx` e `PayReceiptsPage.test.tsx`, 8 testes. A suíte do menu que já falhava em Clientes e fornecedores não foi tratada neste ciclo.

Telas inspecionadas, sem rolagem horizontal, em `documents/reviews/screenshots/extrato-029/`:

- `vazio-1280.png` — duas barras, Extrato corrente, “Extrato não importado.”, ação Importar arquivo;
- `previa-1280.png` e `previa-390.png` — motivo da moeda não suportada em linha própria, descrição longa, R$ 85,00 e “Não informado” sem virar zero;
- `lista-1280.png` e `lista-390.png` — cartão no celular, valor ao lado da data, descrição quebrada sem comprimir o valor;
- `detalhe-1280.png` — bruto, tarifa e líquido separados, “Não classificada”, “Não atribuída” e sugestão com divergência.

Essas capturas usam a tela real com a API simulada, para ver layout. O efeito financeiro foi o teste de integração, não a captura.

## Limitações

- Não há amostra real desta conta. O perfil pode não coincidir com o CSV que o Mercado Pago entregar.
- A correspondência entre a conta Mercado Pago e a empresa Loja de Pães não está demonstrada. O vínculo do laboratório é sintético e não guarda segredo.
- Não há chamada nova ao Mercado Pago nem à Spider.
- Categoria, iniciativa, rateio, conciliação, saldo e gráfico ficam de fora. Valor não atribuído permanece visível.
- Não há expurgo automático. O texto original fica restrito à empresa, sem URL pública. Retirar a importação não apaga essa evidência, não apaga o pagamento externo e não é estorno.
- O detalhe autenticado de R$ 90 e a repetição idempotente do 027 continuam sem prova. Esta entrega não os encerra.
- Aceite visual do proprietário não está atribuído.

## Pacote para decidir publicação e a primeira importação real

Não publicar, não migrar o RDS e não importar arquivo real a partir deste ciclo.

| Decisão | Conteúdo |
|---|---|
| Conta e fonte | Gravar, na empresa titular, o vínculo da referência que o relatório identificar. Sem essa referência no arquivo, a confirmação exige evidência de origem escrita pelo operador. Uma única conta na tela não prova a titularidade |
| Escopo | Só o perfil `mp-account-money-csv-1`. Aplicar V21 no banco isolado de publicação antes de subir a aplicação. A aplicação recusa operar se `statement_batch` não existir |
| Riscos | Arquivo real com outras colunas ou outro separador será recusado. A chave `SOURCE_ID` + `RECORD_TYPE` ainda não foi conferida num arquivo desta conta. Moeda diferente de BRL não é convertida |
| Recuperação | Artefato anterior: `actionfinance-web:16`, `sha256:bcf11a54e4017cd5d4e64efce860ee1e47cfc716f77698980f8c3c33fbb34dec`, SPA `index-B0699gCh.js`, produto 0.1.2. Voltar a imagem não desfaz V21 nem apaga observação. Não dropar as tabelas. A imagem 0.1.2 não lê essas tabelas |

## Como reproduzir o laboratório

```text
cd ActionFinance/backend
mvn "-Dtest=MpAccountMoneyCsvParserTest,StatementObservationIT" test

cd ActionFinance/frontend
npx vitest run src/StatementPage.test.tsx
```

O backend não foi iniciado contra o Postgres de `127.0.0.1:5439`, para não aplicar V21 fora do banco efêmero do teste.
