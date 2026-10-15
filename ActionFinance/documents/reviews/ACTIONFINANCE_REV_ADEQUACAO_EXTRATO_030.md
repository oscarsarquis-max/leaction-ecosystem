# REV 030 — Adequação do extrato T1

Data: 15/10/2026. Candidata **0.2.0**, parser **1**, schema **V21**. Não publicada. O produto no ar permanece **0.1.2**. O RDS público permanece Flyway **V20**, checksum V20 `-145522935`. A ISA permanece pausada. Nenhuma chamada ao Mercado Pago. Nenhuma imagem de produção foi construída.

O relato [029](ACTIONFINANCE_REV_EXTRATO_T1_029.md) descreve a fatia anterior, inclusive a hipótese antiga de assumir BRL e de classificar liberação como efeito só de disponibilidade. Este relato substitui essas duas regras. Não reescreve o 029.

## Formato real suportado

Nenhum. Não havia amostra da conta Mercado Pago no workspace nem em canal privado nesta rodada. O único CSV encontrado, `documents/data/samples/modelo-cadastros-011.csv`, é cadastro e não é extrato. A documentação pública de `settlement_report` não foi usada como substituto.

O perfil `mp-account-money-csv-1` continua hipótese de laboratório: UTF-8, vírgula, ponto decimal, data `yyyy-MM-dd` ou instante ISO no dia civil de America/Sao_Paulo, colunas obrigatórias `DATE`, `SOURCE_ID` e `RECORD_TYPE`. Ele não foi conferido contra a exportação desta conta. A exportação não foi editada, porque não chegou.

Validação que falta, e só ela fecha a compatibilidade:

- tipo e versão do relatório desta conta;
- identificador da conta no arquivo e o período coberto;
- separador, codificação e tipo de data;
- proveniência da moeda: coluna preenchida, ou ausência;
- semântica de cada coluna, em especial bruto, tarifa e líquido;
- efeito de `RELEASE`, `HOLD`, `UNBLOCK` e `INFO` sobre o saldo total e sobre o disponível;
- se `SOURCE_ID` + `RECORD_TYPE` distingue dois estornos parciais, duas tarifas ou duas ocorrências legítimas do mesmo tipo para o mesmo pagamento.

Enquanto isso, esses quatro tipos ficam em revisão e não entram. A chave não recebe a versão do parser. Identidade insuficiente permanece revisão: nada é fundido e nada é gravado por valor, data ou hash da linha.

## O que mudou na candidata

- Moeda ausente não vira BRL. A prévia abre, a confirmação fica bloqueada e a soma financeira dessa prévia não entra. O valor aparece como `10,00 · moeda não informada`. Célula vazia continua “Não informado”; zero escrito continua zero.
- `RELEASE`, `HOLD`, `UNBLOCK` e `INFO` ficam inelegíveis com o aviso de efeito ainda não lido. Não são rotulados como mudança de disponibilidade. A soma existente declara a base: líquido dos eventos de fluxo monetário confirmados neste perfil. Não é variação do saldo total nem do disponível. Não há painel de saldo.
- A mesma chave com o mesmo conteúdo não duplica. A mesma chave com conteúdo diferente fica `IDENTITY_INSUFFICIENT`: as duas linhas ficam de fora e a linha já gravada permanece. Dois estornos parciais do mesmo pagamento e do mesmo tipo não são importados até o arquivo real fornecer um identificador que os separe.
- A versão do parser fica no lote. A chave do evento é `MERCADOPAGO|mp-account-money-csv-1|{SOURCE_ID}|{RECORD_TYPE}`.
- Referência de conta igual ao vínculo gravado é correspondência de texto, não validação do Mercado Pago. Texto do operador é declaração do operador. Conta divergente bloqueia a confirmação.
- Bruto, tarifa e líquido divergentes são gravados como vieram. A tarifa da mesma linha não é somada de novo ao líquido.

## Contas e valores de controle

Laboratório, não produção. Empresa da semente local: **Padaria Exemplo**. Conta: **Conta demonstrativa Banco Exemplo**. Vínculo: `mp-conta-sintetica`, procedência “vinculo sintetico de laboratorio”. Isso não é a empresa publicada Loja de Pães.

| Controle | Valor | Onde foi provado |
|---|---|---|
| Liquidação `pay-sint-jornada` | bruto R$ 90,00, tarifa R$ 5,00, líquido R$ 85,00, BRL, efeito de fluxo | jornada com frontend e backend no banco isolado |
| Liberação do mesmo pagamento | inelegível, não gravada | mesma jornada |
| Reenvio do mesmo arquivo | criadas 0, inalteradas 1 | mesma jornada |
| Arquivo sem coluna `CURRENCY` | prévia aberta, confirmação desabilitada, nenhuma linha nova | mesma jornada |
| Composição divergente `pay-sint-composicao` | bruto 10000, tarifa 500, líquido 8000, sem ajuste | teste de integração, sintético |
| Dois estornos `pay-sint-estorno` | R$ 10,00 e R$ 4,00, ambos fora | teste de integração, sintético |
| Conta `mp-outra-conta` | confirmação recusada | teste de integração, sintético |
| Soma do primeiro arquivo sintético do teste | entradas de fluxo R$ 223,00, saídas R$ 3,50, líquidos ausentes 1, liberações gravadas 0 | teste de integração, sintético |

Nenhum desses identificadores é pagamento real.

## Rodada dirigida

Banco descartável Postgres 17.6 em `127.0.0.1:5441`, container `af-extrato-030`, Flyway até V21 só nesse banco. Backend `0.2.0` em modo demonstração em `127.0.0.1:8091`. Frontend em `127.0.0.1:5179` apontando para esse backend. O Postgres de `127.0.0.1:5439` e o RDS público não foram usados. O container foi removido ao fim.

Jornada na tela, com a sessão caindo no recarregamento e exigindo novo acesso:

1. vínculo da conta de demonstração;
2. prévia de `jornada.csv`, período 01/10/2026–01/10/2026, liquidação marcada e liberação desmarcada;
3. confirmação: criadas 1, enriquecidas 0, inalteradas 0, não importadas 1;
4. lista com a base do fluxo e detalhe bruto R$ 90,00, tarifa R$ 5,00, líquido R$ 85,00, “Não classificada”, “Não atribuída”;
5. recarga do navegador, novo acesso, a mesma linha ainda na lista;
6. reenvio: criadas 0, inalteradas 1;
7. `sem-moeda.csv`: diagnóstico de moeda não presumida, valor sem símbolo de real, botão de confirmar desabilitado.

No banco isolado, depois disso: 1 linha, chave `MERCADOPAGO|mp-account-money-csv-1|pay-sint-jornada|SETTLEMENT`, `currency_assumed` falso. Dois lotes `jornada.csv` confirmados (1 criada e depois 0 criada / 1 inalterada). Duas prévias `sem-moeda.csv` sem linha. A prévia grava o lote em estado `PREVIEW` para o token; não grava observação.

Títulos, baixas e movimentos de caixa desse banco são os da semente: 14 títulos, o mais novo em 15/09/2026, anteriores à linha de extrato de 15/10/2026 17:02 UTC; 3 baixas; movimentos `OPENING` 3, `SETTLEMENT` 3 e `REVERSAL` 1. A confirmação da jornada não acrescentou movimento.

O teste `StatementObservationIT` é sintético e não é prova do arquivo real. Nele, a repetição da mesma chave de confirmação devolve o resultado já gravado e a contagem permanece 7; o arquivo sobreposto cria 0 e deixa 1 inalterada; a declaração do operador sobe a contagem para 8; a composição divergente sobe para 9. Empresa B recebe 403 na leitura. Perfil só de leitura recebe 403 na prévia. Título, baixa, movimento e o pago do recebimento `pay-sint-100` permanecem os de antes da importação.

Capturas em `documents/reviews/screenshots/extrato-030/`: `jornada-previa.png`, `jornada-lista.png`, `jornada-detalhe.png`, `jornada-recarga.png`, `jornada-sem-moeda.png`. Largura útil 1280, sem rolagem horizontal. São a jornada desta rodada, não as capturas 029 de API simulada.

`MpAccountMoneyCsvParserTest` e `StatementObservationIT` passaram juntos. `StatementPage.test.tsx`: 2 testes, incluindo a prévia sem moeda.

Menu: `CounterpartiesPages.tsx` e `AppShell.tsx` não estão no diff de trabalho. A falha antiga de Cadastros, em que a lista de partes lê `data.items` indefinido, não foi alterada e não entra nesta publicação. A jornada abriu Contas → Extrato com as duas barras.

## Versão, manifesto, rollback

| Peça | Estado |
|---|---|
| Produto | 0.2.0 candidata. Servido: 0.1.2 |
| Parser | 1, gravado no lote, fora da chave do evento |
| Schema | V21 no repositório. Origin: V20. V21 foi aplicada neste Postgres descartável e no Postgres efêmero do teste |
| Manifesto | [AF-0.2.0](../versioning/manifests/AF-0.2.0-extrato-t1-029.md) |
| Rollback | `actionfinance-web:16`, `sha256:bcf11a54e4017cd5d4e64efce860ee1e47cfc716f77698980f8c3c33fbb34dec`, SPA `index-B0699gCh.js`, produto 0.1.2. Voltar a imagem não desfaz V21 nem apaga observação. Não dropar as tabelas. A imagem 0.1.2 não lê essas tabelas |

## Condições para a primeira carga produtiva

1. Receber a exportação real por canal privado, sem senha, cookie, token ou credencial.
2. Registrar tipo, versão, conta, período, separador, codificação, moeda, datas e colunas sem alterar o arquivo para caber no parser.
3. Derivar fixture sanitizada e repetir a jornada dirigida com ela.
4. Só então decidir se o perfil cobre o arquivo e se a chave distingue ocorrências repetidas do mesmo tipo.
5. Publicação continua outro ato: aplicar V21 no banco isolado de publicação, construir a imagem e receber autorização explícita. Este prompt não autoriza nenhum dos dois.

## Decisão

Não publicar a 0.2.0 e não importar extrato produtivo.

| Campo | Decisão |
|---|---|
| Fonte | Amostra real ausente. Perfil hipotético `mp-account-money-csv-1`, parser 1 |
| Conta | Nenhuma conta produtiva. O laboratório usou a conta demonstrativa da Padaria Exemplo, vínculo `mp-conta-sintetica` |
| Período | Nenhum período real. A jornada sintética cobre 01/10/2026 |
| Linhas elegíveis | Do arquivo real: não contadas. Da jornada: 1 liquidação em 2 linhas |
| Exclusões | Do arquivo real: não avaliadas. Da jornada: 1 liberação, por efeito não comprovado |
| Efeito previsto | Nenhum no RDS e nenhum título, baixa ou movimento novo. No laboratório ficou uma observação de R$ 85,00 líquidos, com bruto R$ 90,00 e tarifa R$ 5,00 preservados |
