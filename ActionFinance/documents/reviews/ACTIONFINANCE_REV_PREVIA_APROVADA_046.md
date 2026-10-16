# REV 046 — Prévia aprovada do extrato

Data: 16/10/2026. A base efetiva era a **0.2.4** já publicada (`actionfinance-web:21`, SPA `index-Dg2CBQGA.js`). A prancha `ACTIONFINANCE_PREVIA_EXEMPLO_045.html` foi implementada na prévia real. A lista depois da importação permanece a da 0.2.4. Schema permanece V23. A conta produtiva não foi recriada e o arquivo real não foi importado. Aceite do produto continua com o proprietário. A aprovação da prancha não é aceite desta publicação.

## Comparação com a prancha

A prancha e a prévia implementada foram vistas na mesma largura de 1440 px, com 22 linhas, 4 prontas e 18 em revisão. As capturas estão em `documents/reviews/evidence/extrato-046/`.

| Peça | Prancha 045 | Prévia implementada |
|---|---|---|
| Marca e barras | Letreiro indicativo e faixa de demonstração | Marca e barras já publicadas. Sem faixa de estudo |
| Título | Confira seu relatório | O mesmo, com «Revise as movimentações antes de importar.» e «Voltar ao extrato» |
| Composição | Dois terços de linhas e um terço de decisão, alinhados no topo | Razão medida 2,00, topos alinhados, sem overflow horizontal |
| Lista | Abas, busca, quatro colunas e paginação de 8 | Todas, Prontas e Em revisão com contagens da resposta. Busca, paginação e checkbox de seleção |
| Decisão | Total de entradas, um aviso e confirmar | O total vem das linhas elegíveis selecionadas. Um aviso âmbar. «Confirmar importação» |
| Detalhe | Substitui o cartão de decisão | «Voltar ao resumo» devolve o cartão. A confirmação não fica no detalhe |
| 768 e 390 | Resumo abaixo | Resumo abaixo. Em 390 a linha quebra em data, valor, descrição e conferência, sem corte |
| 1280 | Largura intermediária da prancha ainda em duas colunas, porque a quebra da prancha é 1100 px | Duas colunas, razão preservada, sem overflow |

O zoom por teclado no Chrome sem interface não alterou a largura de layout (permaneceu 1440). A prova de 200% usou a largura de layout de 720 px, que é 1440 visto a 200%, também sem overflow horizontal.

## Contagens e regras

A fixture sanitizada já versionada, `settlement-v2-sanitizado-022.csv`, devolveu 22 linhas. Pronta é `eligible = true`: 4. Em revisão é a negação: 18. As duas contagens não se repetem. As 18 em revisão também não estão liberadas; a causa de ficarem fora da confirmação é a identidade ambígua, e o aviso único diz isso em linguagem comum. O detalhe da linha não mostra o nome da coluna.

O total destacado soma só as entradas elegíveis selecionadas que entram no fluxo. Nesta fixture a API devolveu 25100 centavos, apresentados como R$ 251,00. Esse número não está escrito na interface. Saídas elegíveis foram zero e a diferença parcial repetiu o total. O texto ao lado diz que isso não é saldo da conta. Valor ausente aparece como «Não informado» na linha, e não como zero.

A seleção por linha continua. Desmarcar uma pronta reduz o total e a quantidade de eventos. A confirmação guarda todas as ocorrências e consolida só as selecionadas. O endpoint de confirmação não mudou.

## Prova

Laboratório isolado, descartado ao fim. Jornada por clique: conta nova sem vínculo, leitura, confirmação da conta, prévia, abas, busca, paginação, detalhe e retorno, erro de confirmação com recuperação, confirmação real e resultado. A repetição da confirmação respondeu 409. A outra empresa recebeu 403 na conta da prova e não viu as linhas. Também passaram arquivo irreconhecível, valor ausente, arquivo sem pendência e identidade divergente sem troca do vínculo.

Testes de interface da página e do aplicativo: 38 passaram. Dois testes antigos de cadastro de clientes falham por lista indefinida; não fazem parte deste recorte.

## Publicação

| Peça | Valor |
|---|---|
| Commit | `6b3decf3f8bbdc6f284b7340fd2cff3b4db56fa1` |
| Versão | 0.2.5 |
| Task | `actionfinance-web:22`, rollout PRIMARY concluído, 1/1 |
| Imagem registrada | linux/amd64 `sha256:745260497f81fbee9a2b99bfbbceaab2861cd069a370327e9f84db5fcfa0a052` |
| Não registradas | índice OCI `sha256:1ae19eb2e0e43fa0958e03ea1f37dcd975157005d42642e307fcf92a26ee1dc7`; atestação `sha256:fa63bb79b36af86bdf8b79be9449c053d168d46745e81b8f815e331afec499df` |
| JAR | `sha256:5941b6d439ad8ac54c8f9f7a0b6487c299bb11e93c13bd20968d30d1f2970b10`, 67585095 bytes |
| SPA | `index-2pCvF-Zh.js`, CSS `index-CXVUE0WH.css` |
| Host | `version=0.2.5`, health 200, linhas sem sessão 401. O bundle tem «Confira seu relatório» e «Confirmar importação», e não tem «Gravar vínculo» |
| Flyway | `false` na revisão 22 |
| Retorno | `actionfinance-web:21`, produto 0.2.4, SPA `index-Dg2CBQGA.js`, `sha256:6e47b9eaa1658e78254cbc087e995a25a87a2e87575310b90138d544baa24f1d` |

A prova pública autenticada não foi feita. Inspeção local, publicação e aceite do proprietário são fatos separados.
