# Matriz de capacidades e riscos

29/10/2026. Implementação: existente, parcial, não encontrada no escopo, não aplicável. Evidência: confirmada, indício, não avaliada. P0 é risco atual demonstrável. P1 bloqueia parceiro, kit ou repasse. P2 é visibilidade ou robustez. P3 é adiável.

A tabela completa dos achados está neste arquivo. Os outros documentos linkam o ID.

| ID | Capacidade | Implementação | Evidência | Prioridade | Impacto no cenário |
|---|---|---|---|---|---|
| F01 | Várias organizações e papéis | Não encontrada | Confirmada no código: `AdminPrincipal` sem organização (`admin_auth.py:75`); login preso a `settings.admin_username` (`:168`) | P1 expansão | Parceiro não pode receber acesso sem ver a operação inteira |
| F02 | Listagem de produtos sem escrita | Parcial | Confirmada no código: `GET` chama `fill_empty_showcase_slots` (`products.py:63`, `showcase.py:78`) e a sessão confirma (`session.py:42`) | P2 operação atual | Abrir o catálogo pode mudar a vitrine. Impede auditoria autenticada em produção até haver leitura sem efeito |
| F03 | Pedido com tarefa por produtor | Não encontrada | Confirmada: `Order`/`OrderItem` não têm produtor nem tarefa (`orders.py:36`, `:149`) | P1 kit | Não dá para saber se o pão está pronto e o componente do parceiro não |
| F04 | Composição versionada de kit | Não encontrada | Confirmada no catálogo e no item: há produto, variante e snapshot de preço; não há versão de composição | P1 kit | Mudança posterior de receita ou fornecedor pode deixar de identificar o que foi vendido |
| F05 | Rendimento e perda | Parcial | Confirmada: `physical_units` reserva unidades (`storefront_orders.py:147`). Não há rendimento de um pão para vários kits nem perda | P1 kit | Reservar um pão por kit superestima a fornada se a receita render mais de uma porção |
| F06 | Lote sanitário e validade | Não encontrada | Confirmada: `ProductionBatch` é janela e capacidade (`production.py:20`) | P1 rastreabilidade | Ocorrência de qualidade não localiza os kits afetados por lote |
| F07 | Repasse e participação econômica | Não encontrada | Confirmada no modelo de pagamento e na ausência de rotas de split no checkout da Loja | P1 expansão | Dinheiro aprovado não gera obrigação de parceiro. Não é falha da venda atual de pães |
| F08 | Split no provedor da conta | Não avaliada na conta | Indício documental: pré-requisito oficial de carteira assessorada para 1:N. Hashes do Hub conferidos; a conta não foi consultada | P1 expansão | Não prometer vários recebedores nesta conta |
| F09 | Cobrança única, estados separados, reconciliação | Existente | Confirmada no código e em teste isolado (36 testes, 29/10/2026). Produção da imagem não reinspecionada | Reaproveitar | Base da compra atual. Preservar na expansão |
| F10 | Aceite antes da cobrança quando há avaliação | Existente | Confirmada: `start_checkout` (`storefront_orders.py:1076`). Autoaceite só no pão regular com data (`:743`) | Reaproveitar, com regra nova para kit | Kit não pode herdar o autoaceite do pão e liberar a parte do parceiro |
| F11 | Produção sem quitação só por exceção | Existente | Confirmada: `orders.py:333–372` | Reaproveitar | A exceção é explícita e registrada |
| F12 | Worker financeiro no processo da API | Existente | Confirmada no código (`main.py:76–83`) e em teste isolado. Sem medição de réplicas em produção | P2 escala | Mais processos podem duplicar ciclo se a eleição não for provada no SQL real |
| F13 | Acompanhamentos como marketplace de vendedores | Não aplicável ao kit | Confirmada: `AccompanimentItem.hub_source` padrão `mercadolivre` (`accompaniments.py:32`) | P2 clareza | Oferta externa não é parceiro, embalagem nem repasse |
| F14 | Inventário da execução | Parcial | Hub confirmado em 29/10. Loja: saúde pública confirmada; imagem não reinspecionada. `current-state.md` descreve 27/10 | P2 operação | Decisão de publicação futura não pode usar só a página “estado atual” |
| F15 | Segundo fator, várias contas operacionais | Não encontrada | Confirmada a ausência de MFA no login lido. Sessão, CSRF, limite e revogação existem | P2 antes de multiplicar operadores | Mais senhas no mesmo usuário configurado não segregam dados |
| F16 | Estorno e contestação como mesa | Parcial | Estado `refunded` / `partially_refunded` existe no registro. Não há fila administrativa de contestação nem regra depois de repasse | P1 quando houver repasse | Hoje o prejuízo fica na Loja porque não há repasse. Com parceiro, a lacuna passa a ser de responsabilidade |
| F17 | Isolamento de alerta por organização | Não encontrada | Confirmada: push e e-mail operacional são da Loja (`web_push.py`, `payment_alerts.py`) | P1 quando houver parceiro | Dispositivo administrativo receberia ocorrência de outra organização |
| F18 | Concorrência de edição do pedido | Parcial | Há bloqueio de linha em transições (`_lock_order` em `orders.py`) e na aplicação do pagamento. Não há versão apresentada ao operador nem prova visual de conflito | P2 | Dois operadores podem não ver que o outro gravou |
| F19 | Backup com restauração ensaiada | Não avaliada | O relatório 105A cita arquivos de backup. Esta auditoria não restaurou nada e não deve fazê-lo em produção | P2 | Existir arquivo não prova retorno |
| F20 | Capacidade medida em produção | Não avaliada | Teste isolado mediu ciclo com espera injetada. Não há amostra p50/p95 de produção nem pedidos/dia desta auditoria | P2 | Não fixar número de parceiros nem prazo de engenharia |

## Achados que não são P0

Não foi encontrado, nesta leitura, incidente financeiro ativo não tratado. A auditoria não reconsultou os pedidos de 27/10 em produção. O relatório 105A descreve a correção publicada até `prod-20261028c`; a imagem não foi reinspecionada hoje (F14). Se uma leitura futura achar divergência aberta, ela passa à frente do marketplace e não se corrige dentro desta fase.

## Condição de encerramento de cada achado

- F01, F03, F04, F05, F06, F07, F16, F17: encerram só depois de decisão ratificada e de prova no piloto, não por tela.
- F02: encerrar quando a listagem administrativa não gravar vitrine, com teste de que slots permanecem iguais após o `GET`.
- F08: encerrar com evidência da conta, ou com decisão explícita de não usar split.
- F09–F11: encerram como regressão contínua, não como item a apagar. Ver [matriz-regressoes-e-validacao.md](matriz-regressoes-e-validacao.md).
- F12, F18, F19, F20: encerram com medição ou ensaio fora de produção, no lote que os tocar.
- F13: encerrar quando a interface e a documentação deixarem de chamar essa área de marketplace de vendedores.
- F14: encerrar quando a imagem em execução, o Alembic e o documento de estado forem lidos na mesma data, por consulta sem escrita.
- F15: encerrar antes de criar o segundo operador humano, com papéis no servidor.

Detalhe de fluxo: [fluxos-kit-e-estados.md](fluxos-kit-e-estados.md). Dinheiro: [financeiro-conciliacao-repasses.md](financeiro-conciliacao-repasses.md).
