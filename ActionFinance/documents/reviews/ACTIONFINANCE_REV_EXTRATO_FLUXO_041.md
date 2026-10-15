# ACTIONFINANCE_REV_EXTRATO_FLUXO_041

Data: 15/10/2026. Recorte único do extrato, Prompts 036 a 041. Produto **0.2.2** publicado. Schema permanece V23, sem migration. O arquivo real de liquidação não foi importado e nenhuma conta produtiva foi criada. A sessão autenticada do host público não percorreu a tela. Aceite visual e financeiro continuam com o proprietário.

## Arquivos da referência abertos

Pasta `C:\Projetos\claude\2026-10-15-interface-gestao-financeira`.

| Arquivo | Uso nesta entrega |
|---|---|
| `referencia\png\Lancamentos.png` | Tabela, chip de revisão e painel de detalhe ao lado da lista |
| `referencia\png\Fundamentos.png` | Sinal com seta, chip de atenção, dígitos alinhados |
| `referencia\png\Dashboard.png` | Fila de próximas ações e hierarquia dos indicadores |
| `referencia\png\MobileContas.png` | Cartão compacto no celular |
| `notas.md` | Contexto, no trecho anterior do mesmo ciclo |

Não abertos: `referencia\html\`, `design\*.dc.html`, `design\canvas.json`, `Lancamentos-390px.png`, `MobileInicio.png`, `Main.png`, `Planejamento.png`, `MobileInsights.png`, `MobileLancar.png`, `log-conversa.md`. O runtime `support.js` não foi reconstruído.

## Causa da conta vazia em produção

Consulta somente leitura no banco publicado, empresa cujo nome confere com Loja de Pães: `financial_account` 0, ativas 0, inativas 0, títulos 0, linhas de extrato 0, lotes 0. A lista vazia é ausência de cadastro, não filtro de inativa nem erro apresentado como lista vazia. A resposta do produto é o convite de cadastro. Nenhuma conta foi gravada em produção para fazer o botão funcionar.

## Capturas

Ensaio isolado em `127.0.0.1:5179`, backend de demonstração em `127.0.0.1:8091`, Postgres descartável. Empresa Padaria Exemplo. Fixture sanitizada de 22 ocorrências. Os valores abaixo são desse ensaio, não os números da prancha Fluxo.

| Implementação | Referência observada | O que a captura mostra |
|---|---|---|
| [com dados, 1440](evidence/extrato-041/05-com-dados-1440.png) | `Lancamentos.png`, `Dashboard.png` | Lista à esquerda, análise à direita. Entradas ↑ + R$ 251,00, saídas ↓ − R$ 0,00, diferença ↑ + R$ 251,00. Quatro barras nos dias 06, 08, 10 e 12/10 |
| [revisão, 1440](evidence/extrato-041/06-revisao-1440.png) | `Lancamentos.png` | 18 ocorrências em pares de datas, chip «Identificação ambígua», totais ainda em R$ 251,00 |
| [detalhe, 1440](evidence/extrato-041/07-detalhe-1440.png) | `Lancamentos.png` | Painel direito vira o detalhe da linha de R$ 25,00. A lista e os filtros permanecem. «Voltar à análise» |
| [com dados, 390](evidence/extrato-041/08-com-dados-390.png) | `MobileContas.png` | Cartões com data, descrição e líquido. O detalhe aparece abaixo porque a tela foi redimensionada depois de aberto no desktop |
| [sem conta, 1440](evidence/extrato-041/09-sem-conta-1440.png) | — | «Vamos cadastrar suas contas financeiras», importação desabilitada |
| [sem conta, 390](evidence/extrato-041/10-sem-conta-390.png) | `MobileContas.png` | O mesmo convite, sem barra inferior |
| [conta sem extrato, 1440](evidence/extrato-041/01-conta-sem-extrato-1440.png) | — | «Importe seu primeiro relatório» e o formulário de referência exigido pela prévia |
| [conta sem extrato, 390](evidence/extrato-041/02-conta-sem-extrato-390.png) | — | O mesmo estado empilhado |
| [prévia, 1440](evidence/extrato-041/04-previa-1440.png) | — | Arquivo, conta e contagens antes da confirmação |
| [zoom 200% em 390](evidence/extrato-041/03-zoom-200-390.png) | — | Captura visual. A medida numérica de rolagem não foi gravada |

Diferenças em relação à prancha, por regra deste recorte: faixa #1603AD, duas barras horizontais e o nome ActionFinance; sem sidebar, sem navegação inferior, sem seletor PJ/PF, sem chat, sem «Aceitar sugestões», sem «Por que Fornecedores?», sem calendário de vencimentos e sem curva de saldo projetado. Entrada em #0F766E. A prancha pinta a entrada de azul #1F5FA8. As descrições «Sem descrição» vêm da fixture sanitizada. O seletor de conta permanece porque a demonstração tem duas contas. A frase de saídas em R$ 0,00 é a soma das saídas elegíveis desta fixture, que são zero; não é saldo. A tarifa R$ 0,00 do detalhe é o valor gravado da linha.

Na captura do detalhe, a descrição aberta aparece com um realce escuro. A folha de estilo pinta a linha selecionada em #F4F6F8 e o link com fundo transparente. O chip âmbar fica só na coluna Situação da vista de revisão.

## Estados cobertos

| Estado | Prova |
|---|---|
| Sem conta | Capturas 09 e 10. Importação desabilitada, motivo «Cadastre uma conta para importar o relatório.» |
| Erro de consulta, sem permissão, duas contas, reenvio do mesmo arquivo, resposta tardia de outra empresa | Testes de `StatementPage.test.tsx`, 8 aprovados neste ciclo. Sem captura de tela do erro |
| Conta existente, uma vez | Captura 01. A demonstração lista a conta bancária e a conta caixa; nenhuma foi duplicada |
| Conta sem extrato e prévia | Capturas 01 e 04. O vínculo externo continua obrigatório no servidor antes da prévia |
| Confirmação da fixture | Captura 05. 22 preservadas, 4 linhas no total, 18 em revisão. Gravação só no banco isolado |
| Detalhe no desktop | Captura 07 |
| Detalhe em página própria no celular | Código em largura até 1099 px abre `/financial-accounts/statement/{id}`. A captura 08 não percorreu esse clique; mostra o painel empilhado após redimensionar |
| Cadastro e retorno ao extrato | Implementado em `?return=statement`. O clique de salvar e voltar não foi fotografado |
| Seleção de uma barra e «Limpar período» | Implementado. Sem captura |
| Zoom 200% | Captura 03. Em 390 px sem zoom, `scrollWidth` e `innerWidth` mediram 390 |

## Fórmulas e fontes

A soma ocorre no servidor sobre o conjunto filtrado, antes da paginação de 20 ou 50 linhas. A busca por descrição ou referência entra no mesmo filtro. A vista Todas, Identificadas ou Em revisão não altera a elegibilidade.

| Indicador | Fórmula | Fonte |
|---|---|---|
| Entradas identificadas | Soma de `net_minor` das linhas `ACTIVE`, efeito `AFFECTS`, líquido presente, direção `IN` | `statement_line` da conta e do período |
| Saídas identificadas | A mesma regra, direção `OUT`. O líquido de saída já está em magnitude positiva | idem |
| Diferença no período | entradas − saídas, em inteiro | as duas somas |
| Barras | Os mesmos líquidos, por dia de `effective_on`. Acima de 14 dias, por semana. Data nula entra no total e fica fora do gráfico | o mesmo laço |
| Contagem Identificadas | quantidade dessas linhas | idem |
| Em revisão | ocorrências `IN_REVIEW` da conta, até 200, fora das somas e das barras | `statement_occurrence` |
| Todas | linhas da consulta. A unidade da revisão é ocorrência | as duas listas, sem fundir |
| Saldo | «Saldo da conta não apurado.» Não há posição comprovada neste recorte | ausência |
| Agenda | «Nenhum título registrado.» quando a empresa tem zero títulos. «Informação indisponível.» quando há títulos e o vínculo de conta não está provado. A demonstração cai neste segundo texto | contagem de `financial_title` |
| Investimentos | «Investimentos indisponíveis.» | ausência de fonte |

No ensaio: 25 + 50 + 76 + 100 = 251. As 18 ocorrências em revisão, com pares de valores diferentes na mesma data, não entram nessa soma. Data exibida: data de aprovação do perfil `mp-settlement-v2-csv-1`, com a frase «Não é data de caixa.» A última importação diz «manual».

## Critérios de aceite

| # | Critério | Resultado | Evidência |
|---|---|---|---|
| 1 | Navegação de duas barras, Contas › Extrato | Atendido | Capturas 05 e 09 |
| 2 | Conta pelo nome, período com o tipo de data, «Importar relatório» | Atendido | Captura 05 |
| 3 | Sem conta, sem extrato, importando, prévia e erro | Parcial | 01, 04, 09 e testes. Falta captura do erro e do retorno do cadastro |
| 4 | Vistas com contagem e unidade | Atendido | Captura 06: 4 linhas e 18 ocorrências |
| 5 | Chip âmbar, linha inteira sem âmbar | Atendido | Captura 06. O realce escuro da descrição aberta está na captura 07 |
| 6 | Entradas, saídas e diferença no conjunto filtrado | Atendido | 251 = 25+50+76+100, revisão fora. A busca também filtra o total no servidor |
| 7 | Barras, legenda, unidade, data e seleção que filtra | Parcial | Captura 05 tem barras, legenda e data. A seleção e a limpeza não foram fotografadas |
| 8 | Detalhe no painel; no celular, página própria | Parcial | Desktop na captura 07. Celular: rota existe; a captura 08 é o painel empilhado |
| 9 | Ambiguidades sem fusão | Atendido | Captura 06, pares separados |
| 10 | Saldo, compromissos e investimentos sem zero presumido | Atendido | Captura 05. O zero das saídas é soma elegível |
| 11 | Entrada #0F766E com sinal e seta; contraste | Parcial | Cor, sinal e seta na captura 05. O contraste citado no prompt é sobre branco. O fundo da página é #F3F5FB e não foi remensurado |
| 12 | Dígitos tabulares, indicador em uma linha a 1440 | Atendido | `tabular-nums` e `nowrap`. Captura 05 |
| 13 | 200% e 390 px sem rolagem horizontal da página | Parcial | 390 px sem zoom mediu 390. O zoom tem captura e não tem a medida |
| 14 | Testes dirigidos e capturas ao lado da referência | Parcial | Testes de estado e as capturas desta seção. Falta a foto da barra, do erro e da página móvel de detalhe |
| 15 | Commit, push, build e publicação, com rollback | Atendido | Seção seguinte. A prova autenticada do host não entra neste item |

## Publicação

Código da imagem: `1e6d048206772427a463205974a69d7c65222083`, branch `feat/actionfinance-extrato-032`. Esse commit já está no remoto. O relato e as capturas entram num commit posterior e não estão dentro da imagem.

| Peça | Valor |
|---|---|
| Versão | 0.2.2 |
| Task | `actionfinance-web:19` |
| Índice OCI | `sha256:f2fafcfc8d99cd6b4ee4ff838829619317331922a9dbe399497bca7947eb181e` |
| Imagem linux/amd64 | `sha256:98942e11efae9774fb5df8244fb830a26fa10a1ec968dc1b56c3fded07b69611` |
| JAR | `sha256:e8c136a83400fd220ad8e5a7ad2918225e6834ba177d56bc60879cabc04f72fc` |
| Bundle servido | `/assets/index-CbYwmC0n.js`, CSS `index-DlGWfexE.css` |
| Rollout | `COMPLETED`, desejada 1, Flyway da task `false` |
| Health e readiness | `status=UP` |
| `system/info` | `version=0.2.2`, `demoEnvironment=false`, `accessMode=OIDC` |
| Extrato sem sessão | shell 200; linhas 401 |
| Bundle | contém «Extrato da conta» e «Importe seu primeiro relatório»; não contém «CSV da conta» |

Rollback: `actionfinance-web:18`, `sha256:e6b0e865e8e56fff213c8bb1a86fe1a73cfa328697e1ea1dcfaaf637cee403b8`, produto 0.2.1, bundle `index-JjqQdVrO.js`. Voltar a imagem não apaga o schema.

A disponibilidade funcional publicada é o shell 0.2.2 com health UP e a API de linhas recusando sessão ausente. Isso não é aceite do proprietário nem prova autenticada da jornada em `https://actionfinance.actionhub.com.br/financial-accounts/statement`.
