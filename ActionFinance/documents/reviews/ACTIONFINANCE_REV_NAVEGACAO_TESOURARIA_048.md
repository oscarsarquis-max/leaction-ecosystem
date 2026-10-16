# REV 048 — Navegação da tesouraria

Data: 16/10/2026. Aceite do proprietário não atribuído.

## Candidata

| Peça | Valor |
|---|---|
| Código servido | `cb32cc0c3ea37c29dd1180079b9eb55c3a51f05d` em `feat/actionfinance-extrato-032` |
| Navegação | `cfcbe1227dee97859bf182cbb0b42b3718919384` |
| Versão | 0.2.7 |
| Task | `actionfinance-web:24`, PRIMARY COMPLETED, 1/1 |
| Imagem | Tag `0.2.7`. Índice OCI `sha256:486effcdef13dd64d5848c41fc3451b2b7a1f916f14f0c6c516cdff2efdfee40`, não registrado. linux/amd64 `sha256:5f08f2bb740fd960a2faf3044c3ae00d81735f5bf82c33a68394444adbbf84c0`, registrado. Atestação `sha256:e5c2808728acddfcd2558972b388d431eee1e601bdeb9195498cc5940f2f28fa`, não registrada |
| JAR | `sha256:3a25668099dd0ad54d18fc7909befb437cc82e55b6be0482f8d9b2e8d15a0b7d`, 67812761 bytes |
| SPA servida | `index-DjaGJHJZ.js`, CSS `index-B3W2Zc0w.css`. `index.html` `sha256:35e545c77b0c0ad32d2555fd31a77673d73c521e78749e94d989f62d66309ea2` |
| Host | `version=0.2.7`, health 200, linhas sem sessão 401. O bundle tem Tesouraria, Recebimentos integrados, a frase da conta vazia e «Confira seu relatório», e não tem «Gravar vínculo» nem «Transações importadas» |
| Schema | V23, sem migration |
| Baseline | AF-BL-023 1.3. Projeto `733E99A930B4BB6718BF7D87AB7DDD4A696FEF4CC507A70633CBC0D355956E39`. Plano `08FFA0E3E2E336F98607BD71D41F2B8182CC45463A35AD39F593C46524258CD8`. 1.0, 1.1 e 1.2 permanecem |
| Retorno | `actionfinance-web:23`, versão 0.2.6, SPA `index-BxJv9SOg.js`, `sha256:a3b0ee98d44f237979faff3eebfe5b7ef977372c08d61154ba0d8d9026e5b464` |

Flyway permanece falso, perfil production, demonstração desligada, prontidão `readinessState,db`. A prova local usou o laboratório isolado. A prova pública foi sem sessão: versão, saúde, 401 e o texto do bundle. A jornada autenticada no ar não foi feita. Publicação não é aceite.

A asserção de que uma sessão só com `titles:write` não vê Tesouraria está em `c009666e3e7ccfa94af26270433a069da47dbb85`. Esse commit não altera o bundle servido.

## Mapa

| Antes, 0.2.6 | Agora, 0.2.7 | URL |
|---|---|---|
| Área Contas, depois de Pagamentos | Área Tesouraria, primeira | `/financial-accounts` |
| Contas financeiras | Contas | `/financial-accounts` e o detalhe |
| Extrato | Extratos | `/financial-accounts/statement` |
| Recebimentos | Recebimentos | `/receivables` |
| Transações importadas | Recebimentos integrados | `/pay-receipts` |
| Pagamentos / A pagar | Igual | `/payables` |
| Cadastros / Clientes e fornecedores / Categorias | Igual | `/catalogs/counterparties` e `/catalogs/categories` |

A marca e as duas barras horizontais continuam. Não há sidebar nem menu «Mais». Visão geral, Conciliação, Fluxo de caixa, Análise e planejamento, Iniciativas e Rateios não têm página nesta entrega. O logo continua em `/receivables`. A troca de rótulo não mudou a primeira página de quem já entra por Recebimentos.

## Baseline 1.3 e o 047

A revisão 1.3 separa o que está publicado, o que foi provado em laboratório, o que ainda não tem uso real, o que permanece pendente e o que está planejado. Saíram do estado atual as frases superadas da 1.2: extrato inexistente, V21 ainda não escrita e extrato sob Recebimentos.

O 047 está publicado na 0.2.6 e foi incorporado. A lista, o cadastro, o detalhe, a prévia e os totais do período não foram refeitos. Instituição continua fora do modelo; a tela não usa o literal «Não informada» nem deduz a instituição do nome.

Registrado como entregue, com a verificação dos ciclos anteriores: leitura manual do arquivo, vínculo da conta depois da leitura, prévia, preservação das ocorrências, consolidação do que é elegível, revisão das ambiguidades e a apresentação aprovada. Limites que continuam: a importação real não foi comprovada, os nove pares ambíguos seguem sem explicação externa, a soma parcial não é posição de caixa, e classificação, conciliação, posição calculada e projeção estão especificadas na 1.3 e não fazem parte desta publicação. O 409 de uma segunda confirmação não é reenvio do arquivo. Uma sugestão de vínculo não é conciliação concluída.

## Prova

Laboratório Postgres em `127.0.0.1:5449`, encerrado ao final. Capturas em `documents/reviews/evidence/navegacao-048/`.

O clique em Tesouraria abre «Contas financeiras» com Contas atual. O detalhe e a prévia mantêm Tesouraria atual; a prévia marca Extratos. A prévia continua «Confira seu relatório», com abas e «Confirmar importação». A conta sem saldo mostra «Não apurada» e «Ainda não há movimentos registrados no Finance para esta conta.» A conta demonstrativa com saldo informado mostra a posição e as entradas e saídas do livro. Os totais de mais de uma página continuam os do ensaio 047: entradas 16500, saídas 7000, posição 29500, 22 itens e 21 dias, iguais nas duas páginas. Esse ensaio não foi repetido.

Em 1440, 1280, 768 e 390 a largura de rolagem igualou a janela. Em 390 os rótulos curtos são Receber e Pagar; Tesouraria, Contas, Extratos e Cadastros permanecem legíveis. Em repouso, a faixa da marca termina em 56 px e a segunda barra começa em 117. Com a janela em 640 px de altura e rolagem 280, a marca permanece em 56, a segunda barra sai para −163 e o título fica em −45, sem cobrir a marca. O zoom de 200% deixou `visualViewport.scale` em 2 com a janela ainda em 1440. Não foi usada uma janela de 720 px como zoom.

A volta do extrato restaurou `de`, `ate`, `q` e `pagina`, com Extratos atual. Recusar «Há alterações não salvas. Descartar e sair?» manteve o rascunho da conta. A empresa B não viu Padaria Exemplo, o ensaio nem a conta demonstrativa da empresa A. Uma sessão só com `titles:write` não recebe o botão Tesouraria; a URL direta continua sujeita ao servidor.

No laboratório local a integração não está ligada, então «Recebimentos integrados» fica fora do menu. A rota `/pay-receipts` mostrou o título «Recebimentos ActionHub Pay» e o texto de que são informações recebidas, não o extrato nem valores já conciliados. No ar, `receiptSyncEnabled` é verdadeiro, e o bundle servido contém o rótulo.

As duas falhas de «Clientes e fornecedores» do REV_046 já estavam em `95545ab5`: o dublê devolve `[]` e a lista lia `data.items.length`. Não foram introduzidas por este menu. A lista agora só pagina um objeto com `items`. O título abre e os testes da casca e do cadastro passam.

## Pendências

Classificação e conciliação, posição e compromissos, e fluxo e planejamento estão descritos na revisão 1.3 e não foram implementados. Os nove pares do relatório real continuam na investigação operacional, com proveniência, sem estorno, parcela ou compensação inventados. O detalhe autenticado de R$ 90 do 027 e a repetição idempotente continuam abertos. O arquivo real não foi importado. Nenhuma conta produtiva foi recriada. A empresa Loja de Pães não foi renomeada.
