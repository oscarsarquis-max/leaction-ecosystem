# PRM_009_ADENDO_002 — Importação de transações reais e rastreabilidade pública

Revisão 0.2 — incorpora fiscalização estrita, preservação do formato anterior do Monitor e da transação canônica original. Esta versão substitui integralmente a versão anterior deste mesmo prompt.

## Determinação expressa do proprietário

“O que eu quero é a importação das transações do ActionHub de produção com origem dos pagamentos e o registro da passagem disso pelo monitor. Não quero simulação.”

Esta determinação substitui as restrições anteriores que limitavam a entrega a quatro registros sintéticos e à empresa Padaria de teste público. A homologação realizada é evidência técnica preparatória, não entrega do objetivo de negócio nem aceite.

O analista reconhece o desvio de recorte. Cursor deve continuar o PRM_009 com este objetivo, sem iniciar PRM_010, sem pedir ao proprietário para repetir autorização de uso dos dados reais aqui explicitamente solicitada.

## 1. Escopo autorizado e fronteiras

Importar no ActionFinance público as transações existentes de cobrança/recebimento da Loja de Pães no ActionHub Pay de produção. Fluxo obrigatório: Finance → Spider → ActionHub Pay → Spider → Finance. Mostrar a passagem no Monitor público, mantendo fases e detalhes da experiência anterior e o fluxo canônico autorizado.

A origem é consultada somente para leitura. Autoriza-se persistir no Finance a representação externa real, configurar bindings e publicar as correções necessárias dentro da infraestrutura existente. Não criar cobranças, executar pagamento, payout, reembolso, estorno no processador, baixa automática, título ou movimento de conta. Não alterar fatos originais do Pay.

Não incluir transações de outras empresas/apps por conveniência. Confirmar no banco/contrato o app_id real da Loja de Pães: os relatos anteriores usam grafias diferentes. Não presumir que um slug inventado corresponda ao proprietário das transações. Empresa AF da Loja: 624023a4-57e3-415c-b7d0-925ca1acd3b7; validar tenant e membership existentes antes do binding.

Novos recursos faturáveis ou ampliação para outras empresas não estão autorizados por este adendo. Não enviar convites/mensagens nem expor dados financeiros em logs públicos.

## 2. Origem real e conteúdo da importação

Levantar a fonte operacional usada pelo módulo de pagamentos e seu vínculo com a Loja, somente leitura. Localizar os registros que o proprietário vê no painel de produção; a tela administrativa não substitui a API nem é fonte para scraping.

Importar histórico autorizado e atualizações posteriores: pendentes, aprovados, cancelados, reembolsados e demais estados existentes, mantendo status original e normalização documentada. Distinguir ordem de cobrança de transação/tentativa do processador; não deduplicar tentativas distintas sem comprovação de identidade.

Registrar e exibir a origem: ActionHub Pay, app/empresa, referência da ordem, referência do pagamento/processador quando disponível, canal/tipo de cobrança e meio de pagamento quando efetivamente informados. Ausência deve ser explícita; não inventar processador, moeda, cliente, data ou canal.

Separar valor cobrado, valor efetivamente pago e valores de taxas/líquido se a fonte os fornecer. Não substituir um pelo outro em um único campo sem semântica. Aprovado não é sinônimo de liquidação nem dinheiro disponível. Valor ausente não vira zero. Dados pessoais apenas quando necessários à identificação financeira e acessíveis pelo usuário autorizado.

O painel de produção antes mostrado tinha “Incluir testes” marcado. Estar no banco de produção não torna um registro real: usar evidência confiável para distinguir testes, não converter artificialmente sandbox/test_order em operação real. Itens comprovadamente de teste ficam fora da importação operacional; classificação ambígua vai para revisão segregada e fora de totais, com motivo. Demonstrar ao proprietário por que eventuais itens da tela não entraram.

## 3. Isolamento, contrato e base

Implementar modo explícito de leitura operacional autorizado por empresa/app, com defaults restritivos. Não apontar flag ISOLATED para public.orders nem renomear HOMOLOG para PRODUÇÃO mantendo a mesma fonte sintética. Não desativar filtros globalmente. Provar endpoint efetivo, relação consultada, ambiente e origem dos registros.

Evoluir contrato/adapter/registry se o atual só aceita HOMOLOG/SANDBOX. Preservar contratos antigos e EXPERIENCE sem EXECUTE_CAPABILITY. Credenciais do Pay permanecem fora do AF; acesso ao Pay limitado à leitura necessária. Ambiente e empresa são derivados e validados pelo binding confiável, não aceitos livremente do browser.

Persistir origem, ambiente, IDs e revisões com unicidade e paginação segura. Não reclassificar os quatro registros sintéticos como reais nem copiá-los para a Loja. Preservar a trilha de testes separada, sem apagamento. Ajustes de schema são incrementais; documentar DAT e grants mínimos.

## 4. Defeito atual do Monitor — obrigatório resolver

A captura do proprietário mostra o link da sincronização afm-013a79b8-ffbd-4c82-bcfc-131e10144e1c abrindo zero correspondências, com “AMBIENTE NÃO AFIRMADO”. Não considerar isso rastreabilidade entregue.

Rastrear essa referência e identificar se houve ID errado, execução não registrada, projeção incompleta, filtro de empresa, engine distinta, retenção/restart ou outra causa. Não atribuir automaticamente a RAM. Não fabricar eventos nem abrir o acesso global para fazê-los aparecer.

Para cada nova sincronização operacional, ligar a execução raiz às páginas/tentativas e aos itens importados. O deep link deve resolver a execução correta, inclusive fora da lista dos últimos eventos quando ela ainda está dentro da retenção prometida. Ausência, expiração e acesso negado devem ser diferenciados sem vazar informação.

Preservar a apresentação anterior das fases, estados e detalhes. Demonstrar no Monitor público o fluxo canônico autorizado e o fluxo Finance: pedido, autorização, seleção de capacidade, despacho ao provider, resposta e retorno. Não reduzir a experiência a lista simples ou sucesso/erro. A Spider não afirma persistência no AF sem evidência desse fato.

### 4.1 Formato anterior como referência obrigatória

O proprietário exige o formato anterior do Monitor, da versão que exibia a transação canônica. Localizar essa versão em Git/artefatos e as capturas anteriores antes de alterar o layout. A referência visual inclui “Transação selecionada”, “DATA PLANE”, fases identificadas e expansíveis, estados de cada etapa, resultado e evidências. Inventariar as demais interações existentes na versão localizada e preservá-las.

Restaurar/preservar essa experiência no Monitor atual incorporando os controles de acesso corrigidos. Não fazer rollback cego de bundle que reintroduza falhas de autenticação, CSP ou isolamento. Não substituir o formato por outro painel, uma tabela simplificada, logs ou somente seis rótulos fixos. O Finance deve usar a mesma linguagem visual e de navegação, com as fases realmente observadas em sua execução; não preencher fases inexistentes para imitar o fluxo canônico.

Apresentar comparação antes/depois com a mesma largura e fases expandidas: transação canônica e importação real do Finance. Confirmar busca, seleção, expansão de detalhes, status, resultado e evidências. A inspeção visual e funcional é obrigatória; “sem overflow” sozinho não comprova preservação.

### 4.2 Preservar a transação canônica original, não apenas a capacidade de criar outra

A referência do proprietário é a execução anteriormente exibida como [ENTRADA CANÔNICA], “demo-success multi step”, SUCCEEDED, data apresentada 28/09/2026 às 15:20:33. O ID aparece truncado na captura; localizar o identificador completo por evidência, sem adivinhar. Registrar o fuso e distinguir essa execução histórica de uma nova demonstração.

Antes de restart, deploy ou limpeza que possa eliminar eventos em RAM, inventariar e preservar os registros disponíveis de forma protegida. Investigar stores, arquivos, logs, backups e artefatos já existentes para localizar a execução original e seus eventos. Não presumir perda nem recuperabilidade.

Preservar identificador, origem, horários, estados, eventos, detalhes e evidências originais, acessíveis no Monitor aos usuários autorizados. A transação canônica originalmente demonstrativa deve continuar classificada como demonstração canônica; não a apresentar como pagamento real do Hub.

Se existir material original recuperável, restaurar/reexibir com proveniência e trilha explícitas. Uma representação histórica reconstruída de evidência parcial deve declarar sua condição e lacunas; não fabricar timestamps, eventos ou etapas faltantes, nem apresentá-la como recuperação integral. Corrigir a retenção necessária para que novo deploy não elimine novamente a referência preservada, dentro da infraestrutura autorizada; custo novo exige decisão específica.

Se o original não puder ser recuperado, entregar diagnóstico de perda, fontes verificadas e conteúdo efetivamente disponível. Uma nova execução canônica pode testar funcionalidade, mas não satisfaz a preservação da anterior e não pode reutilizar seu ID para fingir continuidade. O requisito permanece não atendido até decisão explícita do proprietário; não dar aceite automático em seu lugar.

Retenção/topologia devem permitir ao proprietário abrir o resultado após sincronizar. Se o desenho atual não garante isso, corrigir dentro do escopo e documentar o comportamento; necessidade de custo novo deve ser apresentada concretamente antes de contratar.

## 5. Jornada e aceite

Na empresa Loja de Pães, mostrar “Recebimentos do ActionHub Pay” com identificação inequívoca de origem operacional e última sincronização. Remover dessa jornada textos que afirmam importar apenas testes, sem apagar a área separada de homologação. Exibir referências e estados compreensíveis; UUID completo pode ficar no detalhe/copiar. Não executar redesign geral neste reparo.

Validar primeiro as alterações com testes pertinentes e depois publicar o candidato identificado. Conferir acesso por empresa, CSRF, contrato, paginação, precisão monetária, atualizações e idempotência. Manter plano de reversão e dados preservados.

Executar uma importação pública real da Loja dentro deste escopo autorizado, com sessão legítima. Se a única dependência restante for intervenção humana de login, solicitar somente isso na aba correta, sem credenciais no chat.

Provar:

1. Inventário inicial autorizado na origem, número de registros elegíveis e exclusões/revisões justificadas. Não presumir quatro itens nem contagem fixa da captura antiga.
2. Correspondência entre IDs, origem, valores e status de registros reais no Hub e no Finance; evidência sanitizada em documentos, dados completos somente nas telas autorizadas.
3. Repetição sem duplicação e atualização correta; nenhuma escrita nos fatos Pay ou criação de baixa/título/movimento AF pela importação.
4. Mesma execução aberta no Monitor público com fases reais, origem operacional e link funcional, preservando o percurso canônico.
5. Negação de acesso cruzado entre empresas e separação dos registros sintéticos.
6. Formato anterior preservado com comparação visual e funcional, e transação canônica original acessível com identidade e eventos comprovados. Se houver perda ou recuperação parcial, declarar requisito pendente; não substituir essa prova por uma execução nova.

### Fiscalização estrita e evidência verificável pelo analista

Não pedir aceite baseado apenas no relatório do executor, em screenshots, contagem ou HTTP 200. Entregar evidências que permitam ao analista conferir independentemente:

- Configuração e versão efetivas de cada componente, origem operacional consultada e binding autorizado da Loja, sem divulgar credenciais.
- Inventário da leitura na origem com instante/limite da janela, IDs estáveis e classificação real/teste/indeterminada. Não alterar um registro de produção para produzir prova de atualização; se ainda não houve mudança legítima observável, declarar essa limitação e separar o teste controlado da evidência operacional.
- Correspondência item a item entre resposta real do Hub, passagem pelo provider/Spider e persistência no Finance: referência, origem do pagamento, valores com semântica, moeda, status e revisão/datas disponíveis. IDs comparáveis em arquivo de evidência restrito; versão redigida nos documentos destinados ao Git.
- Correlação real entre execução raiz e páginas/tentativas no AF, Spider e provider. Eventos devem ser emitidos pela execução; não inserir eventos manualmente para preencher o Monitor.
- Reexecução sem duplicação, rejeições por empresa, comparação de integridade antes/depois e acesso efetivo ao deep link público.
- Identificação completa da transação canônica preservada, fonte da recuperação quando houver, e comparação com a referência anterior.

É proibido usar seed, fixture, simulador, arquivo fabricado ou INSERT direto no Finance como substituto da importação e declarar isso sincronização. Ferramentas administrativas podem configurar o binding, mas os recebimentos operacionais devem entrar exclusivamente pelo fluxo implementado. Não renomear os quatro registros sintéticos como reais. Se a origem não tiver itens reais elegíveis, informar o fato com evidência; não inventar dados para satisfazer uma quantidade esperada.

O analista deve registrar separadamente inspeção de código, evidência do executor e execução observada. O executor não pode atribuir fiscalização ou aceite ao analista antes de sua revisão. Evidência ausente mantém o requisito pendente.

## 6. Entrega e parada

Salvar este adendo integral em documents/prompts/ACTIONFINANCE_PRM_009_ADENDO_002_TRANSACOES_REAIS.md. Atualizar pacote, INT/DAT/UX, guia e relatório, registrando que o proprietário ampliou expressamente o recorte para dados reais da Loja e que a homologação não constituiu aceite.

Não devolver apenas “pronto para testar” com health 200. Entregar jornada real executada ou impedimento específico com evidência e insumo necessário. No relatório final, apresentar estados separados para importação real, rastreabilidade pública, restauração do formato anterior e preservação da transação canônica original. O aceite depende do cumprimento desses requisitos e da validação do proprietário; nenhuma prova de homologação os substitui. PRM_007 separado, sem PRM_010, sem novas cobranças ou movimentação de dinheiro.
