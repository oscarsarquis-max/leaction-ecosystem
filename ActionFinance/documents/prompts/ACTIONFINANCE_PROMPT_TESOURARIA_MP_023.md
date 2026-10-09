# Tesouraria e análise financeira com Mercado Pago

Documento independente para o Cursor. ACTIONFINANCE_PROMPT_TESOURARIA_MP_023. Data 09/10/2026. Concretiza a primeira etapa do projeto analítico 022, sem substituir as correções 019/020/021.

## Decisões confirmadas pelo proprietário

O Mercado Pago é o principal meio de recebimento e também será utilizado para pagar as despesas da empresa. O proprietário concordou com a sequência inicial: registrar obrigações no Finance, realizar pagamentos no MP e conciliá-los depois. Executar pagamentos diretamente pelo Finance não faz parte desta etapa.

O Finance deve ser uma plataforma de gestão e análise, não apenas uma listagem do Pay. O MP assume dois papéis distintos: processador de cobranças e conta financeira. ActionHub Pay não é a própria conta e seu endpoint de pagamentos não deve ser tratado como extrato completo.

## Primeiro resultado financeiro a entregar

Projetar uma visão que responda: qual é a posição de caixa, o que vence em seguida, quais valores devem entrar, quais saídas já ocorreram e quais diferenças precisam de conciliação.

Definir três bases separadas:

- Posição informada pelo MP, com conta, moeda, instante e disponibilidade conforme a fonte.
- Saldo gerencial do Finance, calculado de saldo inicial comprovado e movimentos válidos.
- Projeção, calculada a partir de um saldo-base declarado, compromissos restantes e hipóteses explícitas.

Nenhuma dessas bases pode ser chamada indistintamente de saldo disponível. Diferenças não conciliadas ficam visíveis. Ausência de extrato ou saldo inicial impede afirmar conciliação completa; não preencher saldo zero nem gerar ajuste para fechar a conta.

## Fontes e perímetro da conta

Verificar a conta MP efetivamente usada, sua titularidade/vínculo com a empresa e o período histórico acessível. Não supor que lojadepaes, empresa Finance, collector_id e conta MP sejam a mesma identidade. Se uma conta atender mais de uma aplicação/empresa ou contiver operações pessoais, demonstrar a separação e não atribuir todo o saldo à Loja automaticamente.

Investigar relatórios de Dinheiro em conta e Liberações, extrato e demais consultas oficiais disponíveis à conta. A API de Relatórios documenta geração e download, mas sua existência não prova acesso, configuração ou cobertura no ambiente do proprietário. Levantar amostra autorizada, campos, sinais, timezone, paginação, eventos e permissões antes de escolher o contrato.

Escolher integração pela Spider quando houver capacidade disponível; caso contrário, projetar importação de arquivo real com prévia e validação. Arquivo importado não é sincronização automática. Não usar scraping autenticado ou endpoint de cobranças como substituto silencioso de extrato. Não cadastrar relatório agendado, enviar e-mail ou alterar configuração do MP sem necessidade e autorização específica.

## Registro das despesas e compromissos

Reaproveitar a jornada existente de contas a pagar. A obrigação registra fornecedor, referência/documento, finalidade, categoria, competência, vencimento, valor/moeda, parcelas e vínculo com compra/Panne quando houver. A conta de pagamento prevista pode ser MP, sem torná-la baixa efetiva.

Após pagar no MP, o operador pode registrar a liquidação no Finance e conciliá-la com a movimentação, ou partir da movimentação importada para vinculá-la ao compromisso. As duas entradas da jornada devem terminar no mesmo fato financeiro, sem duplicação. Propor regras e confirmação explícitas para pagamentos sem título, parciais e agrupados; não criar obrigação fictícia automaticamente.

Uma compra de insumos, sua entrada em estoque, seu consumo e o pagamento são eventos diferentes. O extrato prova movimentação, não finalidade ou competência. Não classificar despesa somente pelo nome do favorecido.

Separar aportes, retiradas de sócios, empréstimos, amortizações, transferências próprias, tarifas, impostos, despesas operacionais e compras de ativos. Definir o tratamento gerencial com critérios documentados, sem apresentar toda saída como despesa de resultado ou toda entrada como receita.

## Conciliação e invariantes

Identidade da conta/origem e identificador do evento devem sustentar deduplicação. Mesmo valor/data não basta para fundir registros. Manter origem, arquivo/lote, revisão, moeda, valores e data efetiva, com trilha de importação e correções.

Definir correspondências 1:1, parciais e agrupadas com limite de valor alocável. Sugestões não confirmam vínculo automaticamente nesta primeira etapa. Desfazer conciliação desfaz o vínculo, não o pagamento real; estorno financeiro exige seu próprio fato.

Demonstrar saldo inicial + créditos − débitos = saldo final para o recorte e a semântica do relatório escolhido. Explicar bloqueios/liberações e transferências sem contá-los novamente como venda. Relatórios distintos podem descrever o mesmo evento em etapas diferentes: não concatenar linhas e somar indiscriminadamente.

Representar bruto, tarifa e líquido sem dupla baixa ou cobrança duplicada da tarifa. Tratar reembolsos, contestação, reversão, antecipação e valores retidos apenas conforme dados e regras disponíveis. Preservar divergências com ação de resolução.

## Primeiro painel e fluxo projetado

Propor posição atual com data-base; compromissos próximos e vencidos; entradas previstas; movimentação realizada; diferenças e cobertura de conciliação. Todo total abre sua composição.

Projeção inicial determinística, diária no curto prazo e semanal até 13 semanas, como proposta analítica a validar. Saldo projetado = saldo-base selecionado + entradas futuras elegíveis − saídas futuras elegíveis. Excluir o que já ocorreu e não somar recebível, aprovação e liberação como três entradas. Datas de liberação não conhecidas devem permanecer incertas, com hipótese identificada quando usada em cenário.

Permitir cenário base e alterações explícitas de prazo/valor sem mudar o realizado. Exibir menor saldo projetado, data e compromissos que o explicam quando a cobertura permitir. Sem previsão estatística ou “IA preditiva” nesta etapa.

Projetar conforme as duas barras de navegação aprovadas, sem sidebar ou Mais. Telas novas só entram no produto quando houver jornada funcional. Preparar prévia visual com dados sintéticos claramente identificados, sem substituir provas reais por essa prévia.

## Trabalho imediato e entregáveis

Este pedido autoriza o projeto executivo deste recorte, inspeção das capacidades existentes e proposta de contrato. Não autoriza movimentar dinheiro, iniciar pagamentos, importar fatos em produção, novos serviços pagos ou alterar saldo inicial produtivo.

1. Confrontar títulos/baixas/contas atuais com este fluxo, preservando o que existe.
2. Entregar mapa MP → Spider → Finance e alternativa de arquivo, com cobertura comprovada e lacunas.
3. Definir métricas, regras de conciliação, alocação, deduplicação e projeção com exemplos sintéticos verificáveis.
4. Entregar plano de captura na origem: o que deve nascer no compromisso/compra, o que vem do MP e o que requer classificação do operador.
5. Apresentar primeiro recorte implementável, dependências, migrations propostas, testes, recuperação e prévia visual. Pedir apenas informação realmente indisponível depois da inspeção; nunca pedir credenciais pelo chat.

Criar ACTIONFINANCE_PROJETO_TESOURARIA_MP_023. As correções de recebimentos e Monitor já autorizadas continuam até sua prova pública. Este planejamento não deve atrasá-las. Aceite e implementação das novas capacidades de tesouraria serão decisões concretas sobre o projeto apresentado.

## Referências oficiais

- [Mercado Pago — API de Relatórios](https://www.mercadopago.com.br/developers/pt/reference/reports/overview): capacidades documentadas de configuração, geração e download; verificar disponibilidade efetiva.
- [Mercado Pago — Dinheiro em conta](https://www.mercadopago.com.br/developers/pt/docs/qr-code-ca/resources/reports/account-money/introduction?scope=prod): referência de histórico e eventos da conta.
- [Mercado Pago — Liberações](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/resources/reports/released-money/introduction): referência de disponibilidade e movimentos de liberação. Não equivale automaticamente ao contrato Pay atualmente integrado.
