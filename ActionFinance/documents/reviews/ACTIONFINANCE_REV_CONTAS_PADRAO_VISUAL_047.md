# REV 047 — Contas financeiras no padrão visual aprovado

Data: 16/10/2026. Aceite do proprietário não atribuído.

## Candidata

| Peça | Valor |
|---|---|
| Código | `e4cb456b` em `feat/actionfinance-extrato-032` |
| Versão | 0.2.6 |
| Task | `actionfinance-web:23`, PRIMARY COMPLETED, 1/1 |
| Imagem | Tag `0.2.6`. Índice OCI `sha256:02a11ffaa0c528b8463da0de646a8d2191b2b918fb0411c4a7200d864003e148`, não registrado. linux/amd64 `sha256:a3b0ee98d44f237979faff3eebfe5b7ef977372c08d61154ba0d8d9026e5b464`, registrado. Atestação `sha256:3452e9ca76520af319bbef64d3042d69a22a43014fbad31faa23066ed0ffe08c`, não registrada |
| JAR | `sha256:7d945f54701f0a7ca906966983a97c70b4936b407ddf9566e769a9b70b6de0df`, 67705082 bytes |
| SPA servida | `index-BxJv9SOg.js`, CSS `index-B3W2Zc0w.css` |
| Host | `version=0.2.6`, health 200, linhas sem sessão 401. O bundle tem a frase da conta vazia, «Confira seu relatório» e «Confirmar importação», e não tem «Gravar vínculo» |
| Schema | V23, sem migration |
| Retorno | `actionfinance-web:22`, versão 0.2.5, SPA `index-2pCvF-Zh.js`, `sha256:745260497f81fbee9a2b99bfbbceaab2861cd069a370327e9f84db5fcfa0a052` |

Flyway permanece falso, perfil production, demonstração desligada. A prova local usou o laboratório isolado. A prova pública foi sem sessão: versão, saúde, 401 e o texto do bundle. A jornada autenticada no ar não foi feita.

## Antes e depois

O detalhe antigo espalhava instituição, moeda, situação e posição numa faixa, repetia «Não apurado» três vezes, abria o período inteiro e mantinha tabela e paginação vazias. «Instituição: Não informada» era um literal da tela. O modelo de conta não tem coluna de instituição; o nome da conta não foi usado para preencher «Mercado Pago». O literal saiu do destaque. A lacuna fica registrada: instituição, titularidade e vínculo externo não são dados da conta.

O detalhe agora cabe numa faixa: nome, empresa, Real e situação, com «Ver extrato» como ação principal e «Gerenciar conta» secundário. Em 1440 a consulta mede cerca de 904 px e a análise 452 px, alinhadas no topo. Sem movimentos, o cartão diz que ainda não há registros no Finance e aponta o extrato, sem paginação. Sem saldo inicial, «Não apurada» aparece uma vez. Com saldo zero informado, a posição permanece R$ 0,00. A lista mostra tipo, situação e posição, e leva ao detalhe e ao extrato. Conta inativa fica identificada.

## Fontes e totais

Entradas, saídas, diferença e barras vêm de `cash_movement` da mesma empresa, conta, período e busca, excluindo o saldo inicial, no conjunto inteiro e não na página visível. A posição anterior, a do fim do período e a atual só aparecem quando existe saldo inicial. O gráfico não transforma fluxo em saldo.

No ensaio «Ensaio 047 com fluxo»: saldo inicial 20000, onze entradas de 1500 e dez saídas de 700. A consulta devolveu entradas 16500, saídas 7000, posição 29500 e 21 dias, iguais na página 1 (20 itens) e na página 2 (2 itens). O clique numa barra filtrou a lista e «Limpar filtros» restaurou as duas páginas. Os títulos do ensaio foram criados e baixados pela API, identificados como ensaio, no banco isolado.

O relatório confirmado é um lote `CONFIRMED`. Uma prévia aberta não entra. No ensaio, o lote sanitizado ficou em revisão com 18 linhas e o período 02/10/2026 a 14/10/2026, separado dos movimentos do Finance. Agenda, categorias e investimentos não foram atribuídos à conta: o título não tem vínculo de conta até a baixa, e não há posição de investimento datada.

## Prova

Laboratório Postgres em `127.0.0.1:5448`, encerrado ao final. Estados: lista vazia por resposta local `[]`, porque as empresas de demonstração já nascem com conta; conta ativa sem saldo e sem movimento; saldo inicial zero; conta com fluxo; filtro sem resultado; erro 500 seguido de nova tentativa; conta inativa; relatório confirmado com revisão. A empresa B não viu os nomes do ensaio. A consulta da conta A com o token da empresa B respondeu 403.

A prévia aprovada continuou com «Confira seu relatório», abas e «Confirmar importação». Capturas em `documents/reviews/evidence/contas-047/`: 1440, 1280, 768 e 390. Em 390, depois do ajuste dos filtros, `scrollWidth` igualou a largura da janela. O zoom de 200% mudou `visualViewport.scale` para 2 com a janela ainda em 1440; a captura `17-zoom-200.png` mostra o tipo ampliado e o lado direito cortado. Não foi usada uma janela de 720 px como se fosse zoom.

Testes: `App.test.tsx` e `StatementPage.test.tsx` passaram; `SettlementOperationsIT` passou e confere os totais do período com os movimentos que não são saldo inicial quando a página contém o conjunto inteiro. As duas falhas de `AppShell.test.tsx` («Clientes e fornecedores») já existiam em `95545ab5`: os arquivos do cadastro não mudaram desde a 0.2.4, e a causa continua `data.items.length` quando o dublê devolve `[]`. No laboratório, a rota real de clientes e fornecedores abriu o título.

## Telas restantes

| Tela | Estado visto | Desvio | Prioridade | Dependência |
|---|---|---|---|---|
| Recebimentos | Lista renderizada | Resumo largo, fora da composição 045 | Seguinte | Não mexer no contrato de título neste recorte |
| Pagamentos | Lista renderizada | Mesma composição antiga | Seguinte | Igual a recebimentos |
| Clientes e fornecedores | Lista renderizada no laboratório | Densidade anterior; o teste de casca falha no dublê `[]` | Média | Corrigir o dublê ou a leitura de página vazia |
| Categorias | Título renderizado | Não recompor agora | Baixa | Cadastros |
| Contas | Este recorte | Instituição ainda não é dado | Feito neste ciclo | Sem migration só para o rótulo |
| Extrato | Prévia e lista conferidas | Composição 0.2.5 preservada | Feito | Não regressar a confirmação |
| Transações importadas, formulário de título, baixa e estorno | Não verificados nesta rodada | — | Não abrir junto | Visitar na próxima fatia |

O arquivo real do Mercado Pago não foi importado. Nenhuma conta produtiva foi recriada.
