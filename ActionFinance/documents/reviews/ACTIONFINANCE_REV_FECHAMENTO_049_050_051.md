# Fechamento 049 e 050 — Prompt 051

Data: 16/10/2026. Aceite do proprietário não atribuído.

## O que foi publicado

A candidata 0.2.8 reúne a classificação e a conciliação do 049 com o resumo, a agenda e a revisão visual do 050. O produto que estava no ar antes desta entrega era o 0.2.7.

| Peça | Valor conferido |
|---|---|
| Commit | `4b38c8c8` em `feat/actionfinance-extrato-032`, enviado a `origin` |
| Versão | `0.2.8` em `GET /api/v1/system/info` |
| Task | `actionfinance-web:25`, rollout COMPLETED, 1/1 |
| Imagem registrada | linux/amd64 `sha256:94598b7bc3da11c90745770dc583628c8e7041412e44673f8d7384ebeb785567` |
| Índice OCI | `sha256:ce7d801fbda5e8d2ee7460f1db31938e47203a031ef3b80d6ddd33312654b5f1`, não registrado na task |
| Atestação | `sha256:5b1cd19f95f1c045f462b779f2f8757610b5f7481d992a9f7898177b1ff78df1`, não registrada |
| JAR | `sha256:4c278c78dd89ed5da15ab2dafdf5c26ae539b4d4b02229bf5a4dea4c381fbd35` |
| SPA | `index-BgQocLZy.js` |
| CSS | `index-BSrtXlJP.css` |
| Schema | V24 aplicada pela task `actionfinance-migrate:6` antes da troca do site. O site permanece com Flyway falso |
| Saúde pública | health 200, linhas do extrato 401, resumo da tesouraria 401 |
| Retorno | `actionfinance-web:24`, imagem `sha256:5f08f2bb740fd960a2faf3044c3ae00d81735f5bf82c33a68394444adbbf84c0`, produto 0.2.7. Essa imagem continuou saudável depois da V24 e antes da troca |

## Correções desta rodada

| Defeito | Correção | Prova |
|---|---|---|
| Posição de hoje somava movimento futuro e qualquer saldo inicial | A soma usa fatos com data efetiva até o dia. Saldo inicial posterior não cobre a conta | `TreasuryAgendaIT`: movimento futuro não muda o valor conhecido; o cadastro recusa conta com início futuro; a moeda diferente de real é recusada pelo banco |
| Nenhuma conta coberta aparecia como R$ 0,00 | Sem conta ativa apurada, `known` fica falso e o valor some. Zero informado continua zero | Empresa Gama sem contas; conta de caixa da demonstração com saldo inicial zero continua na soma |
| Conta inativa sumia da empresa | A soma é só das contas ativas apuradas. A inativa com valor fica numa exclusão própria, com o valor | Conta inativa de R$ 42,42 listada à parte, fora da soma |
| Carregamento virava zero | A tela separa carregando, erro com nova tentativa, sem permissão e zero real | Vitest do resumo e da agenda |
| Conferência abria uma rota genérica | Parcial abre a fila `PARCIAL`, diferença abre `DIVERGENCIA`, ocorrência em revisão abre o lote confirmado | A contagem de revisão ignora lote retirado e declara a unidade como ocorrência, não evento único |
| Agenda não voltava ao recorte | Faixa, direção, página e vista ficam na URL. O título recebe um retorno interno | Vitest: resposta atrasada não troca a faixa; o clique leva o retorno |

## O que a prova local cobriu

Postgres isolado: `TreasuryAgendaIT` e, na construção do 049, `ClassificationIT` com `AllocationMathTest`. As consultas novas não gravam título, baixa nem movimento. Empresa vizinha recebe recusa. A posição, a agenda e a conferência foram exercitadas com título em aberto, baixa futura inserida só como fixture, lote confirmado e lote retirado.

Frontend: 18 testes de tesouraria, menu e recebimentos integrados. A checagem de tipos do build de produção passou.

## O que não foi percorrido no navegador

Não houve captura em 1440, 1280, 768 e 390 px, nem zoom real de 200%, nem o clique completo de classificação, rateio, conciliação e estorno na interface. Teste de menu e tipo não substituem essa jornada. A publicação não apaga essa lacuna.

A prova pública foi sem sessão: versão, saúde, 401 e os rótulos do bundle (`Resumo da tesouraria`, `Conciliação`, `Registrar recebimento`). Não houve sessão autenticada no ar e nenhuma operação financeira produtiva.

## O que a tesouraria ainda não faz

Posição informada pela fonte, conta prevista no compromisso, fluxo de caixa projetado, análise e planejamento. Essas capacidades não foram anunciadas como prontas.
