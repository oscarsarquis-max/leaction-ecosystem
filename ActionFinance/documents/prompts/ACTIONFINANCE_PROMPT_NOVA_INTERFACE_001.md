# ActionFinance implementação da interface aprovada

Data: 02/10/2026. Destinatário: Cursor, executor. Autor: analista de produto e UX.

## Mandato

Implementar a nova direção visual aprovada pelo proprietário: marca branca sobre azul, superfícies claras, navegação sem sidebar, recebimentos legíveis, detalhe orientado à conferência e acesso direto ao formulário Cognito com identidade consistente. Entregar uma interface funcional e verificável, preservando dados e comportamento financeiro. Não entregar apenas CSS ou imagens estáticas.

Este prompt é um recorte de interface. A aprovação visual não encerra PRM_009, as pendências da Spider, a canônica histórica, regressão Pay, APPLY histórico ou PRM_007. Não declarar novo aceite global nem abrir automaticamente um ciclo de evolução financeira. Identificar este documento pelo nome atual; compatibilizar sua numeração com o índice vigente sem sobrescrever prompts existentes.

O analista define e revisa a experiência; o Cursor implementa e produz evidências; o proprietário aceita o produto. Trabalhar no ActionFinance. Cognito somente no cliente/branding do Finance, após identificar o alcance da configuração. Não modificar Monitor, Hub, Panne ou outros clientes de autenticação como efeito colateral.

## Referências aprovadas e sua precedência

Abrir e inspecionar as três imagens, não trabalhar apenas pela descrição:

1. Lista e navegação: [referência desktop e mobile](../ux/interface-aprovada/01-recebimentos-desktop-mobile.png).
2. Detalhe: [referência desktop e mobile](../ux/interface-aprovada/02-detalhe-recebimento-desktop-mobile.png).
3. Acesso: [referência Cognito desktop e mobile](../ux/interface-aprovada/03-acesso-cognito-desktop-mobile.png).

Estas imagens são estudos gráficos aprovados, não capturas de recursos existentes. Não transportar seus textos indicativos, linhas, valores, eventos, avatares ou componentes inexistentes como dados do produto. Não incorporar a prancha como imagem da interface. Reutilizar os arquivos oficiais da marca; não extrair uma logo redesenhada pela geração de imagem.

Em divergência entre imagem e este texto, valem os requisitos deste texto e a integridade funcional. Na entrada, remover slogan e marca repetida no rodapé. Remover as anotações externas das pranchas, incluindo percentuais desktop/mobile. Na implementação, controles e texto corrente devem priorizar legibilidade; a tipografia da marca não obriga usar serifas em todos os campos.

Base funcional complementar: [retomada da gestão financeira](ACTIONFINANCE_RETOMADA_FUNCIONAL_001.md). Seu roadmap de conciliação, caixa e modelo financeiro permanece proposta futura; não implementá-lo inteiro neste prompt. Cópia estável no repositório: este arquivo e o diretório `documents/ux/interface-aprovada/`.

Os arquivos estão inicialmente na pasta outputs da área do analista. Ao registrar no repositório, copiar as referências para um diretório documental estável e ajustar links relativos. Não deixar o prompt depender apenas de arquivos temporários ou da pasta interna de imagens do Codex.

## Levantamento inicial obrigatório

Ler as instruções aplicáveis do repositório e os DOM, DAT, UX, INT atuais. Conferir código, rotas, autenticação, permissões e modelo efetivo. Documentação contém estados históricos; distinguir comportamento atual de proposta e registro antigo. Registrar versão inicial e alterações locais relevantes, sem incluir trabalho de outros produtos no commit.

Identificar quais telas, filtros e ações existem; quais campos são retornados pela API; quais recursos das imagens não existem. Realizar um levantamento curto, depois implementar o escopo viável. Não inventar endpoints, contas, clientes, situação bancária ou métricas para preencher o desenho.

## Identidade e estrutura visual

- Substituir o bloco amarelo da marca pela composição branca sobre azul, integrada ao cabeçalho. Conferir o arquivo original logoazul e os assets compactos oficiais. Preservar proporção e legibilidade, sem distorção, moldura amarela ou recorte das letras. Eliminar margem externa excessiva somente por tratamento adequado do asset/container, sem redesenhar a marca.
- Base clara, texto escuro, divisórias discretas; azul para navegação, seleção e ações. Amarelo deixa de ser preenchimento predominante de marca/botões; âmbar pode sinalizar pendência, acompanhado de texto. Não misturar cor institucional com estado financeiro.
- Não criar grandes cartões vazios, avisos técnicos dominantes ou grandes espaços sem função. Aumentar área útil de leitura e alinhar valores monetários com numerais tabulares.
- Aplicar o shell e os componentes compartilhados às telas existentes: títulos, formulários, cadastros, contas, movimentos e diálogos, além de recebimentos. Evitar duas identidades visuais no mesmo produto.

## Navegação sem sidebar

Desktop: cabeçalho compacto com marca, contexto de empresa e acesso do usuário; navegação horizontal abaixo. Áreas principais: Recebimentos, Pagamentos, Contas e caixa e Mais. Visão geral aparece somente se houver destino funcional, sem dashboard fictício. Dentro das áreas, manter acesso inequívoco a A receber, A pagar, registros existentes e recebimentos externos. O operador não pode perder funções atuais durante a reorganização.

Mobile: barra inferior com até cinco destinos, ícone acompanhado de rótulo; acesso a Receber, Pagar, Contas e Mais. Início só se tiver destino funcional definido, podendo ser a página operacional inicial. Não criar menu lateral persistente. Mais abre uma superfície acessível de navegação para cadastros, integrações disponíveis e demais destinos. Contexto de empresa permanece visível e alterável.

Navegação adicional: busca de registros na área atual, filtros e atalhos para destinos existentes. Se houver “Buscar ou ir para” global, deve ser um localizador funcional de páginas/ações autorizadas; não sugerir pesquisa global de transações sem implementá-la. Atalhos e visões salvas só aparecem se funcionarem; preferir presets reais a um botão “Personalizar” sem ação. Indicar diferenças necessárias em relação à prancha.

Preservar URLs antigas e deep links por compatibilidade/redirecionamento. Voltar/Avançar devem manter contexto coerente. Não alternar empresa implicitamente. Manter proteção de formulário sujo, foco, Escape, retorno ao acionador e estados de sessão.

## Lista de recebimentos

Recebimentos é um domínio amplo. ActionHub Pay aparece como origem, não como toda a definição de recebimento. A navegação precisa dar acesso ao registro manual existente, inclusive pagamentos/recebimentos feitos fora das aplicações. Se ainda não houver API consolidada de liquidações, organizar entradas funcionais claramente separadas; não simular uma união nem limitar a visão a Pay sob um rótulo enganoso. Especificar esse gap e reaproveitar as jornadas existentes. Não criar título fictício para viabilizar recebimento avulso.

Filtros iniciais sobre dados realmente disponíveis: busca por referência, período com semântica da data explícita, situação na origem e pendência. Origem comercial, estabelecimento, sistema de origem, processador e método são dimensões diferentes. Oferecer filtros dessas dimensões apenas quando tiverem informação e contrato suficientes; caso contrário registrar lacuna, sem deduzir unidade a partir do app_id. Nunca mostrar filtro inerte.

Se a API retorna coleção parcial/paginada, filtrar e contar o conjunto correto no servidor; não apresentar filtro local de uma página como pesquisa completa. Pequenos ajustes de leitura da API para filtros são admissíveis com autorização por empresa e testes pertinentes; alteração de modelo financeiro/migration não é implícita neste recorte.

Lista: origem/referência legível, contraparte quando disponível, data claramente definida, cobrado, pago e situação. Referência curta com copiar/ver referência completa no detalhe. Não ocupar a tabela com UUIDs quebrados. Mobile usa cartões compactos com o mesmo significado, sem duplicação de tabela e cartão visíveis.

Separar contagem da última sincronização do total atual de registros/pendências. “Concluído sem novidades” não deve minimizar pendências existentes. Usar “Sincronização concluída”, resultado da consulta e pendências atuais em blocos semanticamente distintos. Ausência de valor é “Não informado”, nunca zero. Aprovado na origem não equivale a baixa, conciliação ou saldo disponível.

Retirar “Empresa autorizada · ambiente PRODUCTION” do conteúdo principal. Configuração de conexão fica em detalhes técnicos. Preservar a identificação inequívoca de dados de teste e a separação dos totais; não remover controles de ambiente nem reinterpretar registros indeterminados. Explicar pendências em linguagem operacional, sem expor nomes de campos como live_mode na primeira leitura.

## Detalhe do recebimento

Página dedicada com retorno à lista preservando filtros. Primeiro nível: origem identificável, valor cobrado, valor pago informado, situação na origem e pendência. Segundo nível: empresa, contraparte, datas com semântica correta, método e conta de destino se conhecidos. Não inventar cliente ausente nem reclassificar “revisão da origem” como data do pagamento.

Separar nome do processador de ID da transação no processador. Distinguir pedido, transação e referência comercial mesmo que a origem atualmente use o mesmo ID. Mostrar de onde veio cada informação relevante.

Pendências: o que falta, consequência financeira e ação realmente disponível. “Atualizar da origem” usa a operação suportada via Spider. Se só houver sync por empresa, explicitar esse alcance e não fingir consulta individual. Não oferecer “aprovar como real” para compensar falta de evidência. Não escrever pagamento presumido.

Histórico contém apenas revisões reais, com data, mudanças e fonte quando existentes. Referências e rastreio ficam em área secundária expansível, com link da execução remota quando conhecido. Evitar duas entradas redundantes para o mesmo painel, como abas e disclosure duplicados da prancha. No celular, conteúdo em página inteira e seções expansíveis; barra inferior não cobre controles ou última linha.

## Acesso direto ao Cognito

Entrada sem sessão deve encaminhar diretamente ao fluxo OIDC do Finance e apresentar o formulário Cognito personalizado, sem página intermediária exigindo outro clique em Entrar. Sessão válida continua levando ao destino autorizado. Evitar loops em falha, expiração, logout e ausência de vínculo; uma página de erro/reentrada explícita pode ser necessária nesses casos.

Antes de alterar: identificar o tipo atual de interface Cognito, versão de branding, domínio, app client, recursos suportados e eventual impacto em plano/custo. Conferir documentação oficial atual. O mockup expressa intenção visual, não comprova que qualquer HTML/CSS é aceito. Preferir branding nativo suportado. Não criar formulário que receba senha no backend do Finance, iframe ou bypass OIDC para imitar a prancha.

Adaptar marca, azul, superfícies claras, campos, botão e tipografia dentro das capacidades verificadas. Usuário não é necessariamente endereço de caixa postal. Manter a configuração existente de login/recuperação e os destinos de contato; não criar convites, provedores sociais ou cadastro público.

Manter Authorization Code, state/nonce, sessão servidor, cookie seguro, CSRF, logout, recuperação e desafios MFA existentes. Preservar somente destino interno permitido para retorno ao recurso solicitado, sem open redirect. Não extrair cookies nem pedir senha/MFA no chat. Não alterar branding compartilhado com outros clientes sem delimitar e resolver o impacto.

Se a aproximação exata exigir mudança de plano, custo ou arquitetura, entregar a alternativa nativa concreta e apontar diferença para decisão. Não bloquear os demais trabalhos de interface por isso e não declarar personalização concluída apenas com uma tela local fictícia.

## Preservação funcional e dados

Sem reparo histórico, importação fabricada, seed em produção, baixa automática, alteração de saldo, nova cobrança ou execução de pagamento. Não alterar contratos da Spider/Pay para fins estéticos. Toda consulta integrada continua AF → Spider → Pay → Spider → AF, sem fallback direto.

Preservar idempotência, retry de resultado desconhecido, chave/rota/corpo congelados, conflito de versão, escopo de empresa, autorização de viewer/operator e prevenção de duplo envio. Não substituir estado financeiro por estado de carregamento. Atualização visual não pode misturar respostas de empresas ou registros diferentes.

Novas conciliações, fluxo de caixa, transferências, centros de custo, liquidações em lote e consolidação multiempresa ficam no roadmap. Não criar links vazios para elas nem anunciá-las como disponíveis.

## Verificação e evidências

1. Gates frontend: instalação reprodutível, lint, testes pertinentes, build e auditoria. Verificar backend apenas conforme alterações e gates exigidos; não declarar backend validado por teste de CSS.
2. Browser real em 360, 768 e 1280 px: entrada, lista, detalhe, filtros, navegação, títulos, registro manual existente, contas e diálogos. Conferir ausência de overflow, teclado, foco, contraste, zoom 200%, rótulos e áreas de toque. Capturas devem incluir estados preenchido, vazio, falha e pendência, não só a tela favorável.
3. Regressão financeira em ambiente controlado: criar título, baixa parcial, conclusão, estorno e extrato; conflito e retry; viewer sem escrita e troca de empresa. Fixtures somente nesse ambiente e identificadas. Em produção, evitar gravações financeiras para teste; consulta/sync autorizada deve preservar invariantes.
4. Cognito real do ambiente avaliado: acesso direto, login, retorno ao deep link, logout sem loop, reentrada e erro. Recuperação/MFA conforme configuração e com interação humana quando necessária; marcar o que não foi exercitado. Não afirmar prova com mock. Preparar uma sessão acompanhada, sem transformar o proprietário no executor da suíte.
5. Comparação visual lado a lado com as três pranchas e explicação das diferenças. Verificar estabilidade ao atualizar lista, voltar à página e trocar de aba; não regredir o percurso para a Spider.

Dados das imagens aprovadas não são fixture de produção. Relatórios/capturas não incluem senha, token, cookie, cartão ou dados pessoais desnecessários. Registrar ambiente, versão e quais ações foram reais ou controladas.

## Entrega e publicação

Entregar implementação revisável, referências copiadas, relatório único ACTIONFINANCE_REV_NOVA_INTERFACE_001.md, atualização de UX/índice e matriz requisito → alteração → evidência → limitação. DAT somente se necessário para registrar que não houve mudança de modelo; não inventar versão física nova.

Separar implementado local, validado, publicado e aceito. Preparar plano de publicação e reversão para imagem frontend/AF e branding Cognito, incluindo preservação da configuração anterior. Aplicar somente dentro da autorização de publicação vigente e comprovadamente aplicável; não inferir custo novo ou alteração em outro produto da aprovação gráfica. Se for necessária decisão adicional, apresentar o pacote pronto e a razão específica, não pedir autorização genérica antes de concluir o trabalho.

Não reiniciar engine Spider para publicar uma alteração de interface do Finance. Não perder eventos/evidências da integração por esse trabalho. A conclusão do executor não é aceite do analista/proprietário. Não declarar “pronto, falta você testar”: produzir as provas ao alcance do executor e identificar somente dependências humanas reais.

## Adendo de continuidade do acesso e publicação conjunta

02/10/2026. O proprietário pediu continuidade após a correção local do cabeçalho. Esta instrução integra o mesmo prompt e deve ser copiada para sua versão no repositório, sem abrir outro ciclo. O analista inspecionou 1280-cabecalho-marca-azul.png: o topo está alinhado à direção visual; esse recorte não comprova lista, detalhe, mobile, autenticação ou aceite integral.

Concluir a personalização do próprio formulário hospedado no Cognito do ActionFinance. Redirecionar para /oauth2/authorization/actionfinance, por si só, não entrega a prancha de acesso aprovada. Não substituir o formulário real por uma página intermediária decorativa ou um formulário de senha no backend Finance.

Usar a marca oficial branca horizontal integrada ao azul de referência RGB(22, 3, 173), #1603AD, superfícies claras e controles coerentes com o produto, dentro das capacidades verificadas do Hosted UI clássico. Preparar logo e CSS compatíveis, delimitados ao app client Finance. Não prometer faixa ou composição idênticas se o Cognito clássico não as permitir: apresentar a aproximação nativa e a diferença concreta. Não trocar plano/versão de login nem gerar custo novo automaticamente.

Entregar o pacote concreto de branding: identificação do cliente alvo, configuração anterior recuperável, assets/CSS prontos, procedimento de aplicação, verificação e reversão. Conferir alcance antes de aplicar; preservar demais clientes, URLs de callback, autenticação, MFA, recuperação e regras de sessão. Não deixar a preparação incompleta sob a justificativa genérica de que AWS exige autorização separada. Para a aplicação, observar a autorização vigente e os limites de publicação já definidos neste prompt; se houver decisão realmente ausente, explicar o ponto exato com o pacote pronto.

Concluir também os ajustes e provas locais pendentes do parecer ACTIONFINANCE_REV_NOVA_INTERFACE_001_PARECER_ANALISTA.md. Validar o conjunto: Finance e formulário real de acesso coerentes em desktop/mobile, login e retorno ao destino, logout/reentrada sem loop e recuperação/MFA conforme configuração. Intervenção humana limita-se à autenticação ou desafio necessário; executor conduz e registra os demais testes. Não enviar mensagem de recuperação, convite ou alterar credenciais sem a autorização aplicável.

A publicação deste recorte deve contemplar interface Finance e personalização do acesso, com ordem e rollback documentados, sem afirmar atomicidade entre imagem e configuração Cognito. Não declarar entrega integral publicando somente o frontend e deixando o formulário antigo sem explicação. Se um componente estiver impedido, registrar precisamente a entrega parcial e a dependência restante. Não reiniciar Spider nem modificar Pay para esse trabalho.

Atualizar o relatório único separando preparado, aplicado, validado e aceito. O cabeçalho alinhado não encerra o recorte, nem as pendências financeiras ou da Spider. O aceite permanece com analista/proprietário.

## Continuidade autorizada da publicação da interface

02/10/2026. Após o relato de branding Cognito aplicado e imagem Finance ainda antiga, o proprietário determinou “vamos em frente”. Prosseguir com a publicação da nova interface ActionFinance pelo canal existente, concluindo antes os checks pendentes do parecer. Não solicitar novamente autorização genérica para este mesmo recorte. Esta continuidade não autoriza custos novos, mudanças em outros produtos ou escrita financeira de teste em produção.

1. Conferir o estado atual do cliente Cognito Finance e preservar o branding já aplicado. O relato do executor informa Hosted UI clássico personalizado exclusivamente neste app client; verificar o estado sem reaplicar configurações desnecessariamente. Registrar as limitações nativas de composição e rótulos em inglês, sem declarar tradução inexistente.
2. Resolver os pontos pendentes do parecer, comparar com as três referências e executar a regressão controlada pertinente. Registrar provas locais com ambiente explícito, sem chamar mocks de jornada real.
3. Gerar e publicar a imagem que efetivamente entrega a SPA no serviço Finance existente. Não presumir que deploy separado de frontend basta se a SPA estiver embutida no artefato backend. Registrar commit/conjunto de alterações, build, digest, tarefa e versão observada publicamente. Preservar a imagem anterior e o procedimento de reversão; excluir alterações alheias ao recorte.
4. Verificar no host público as telas alinhadas às referências em desktop e celular: navegação sem sidebar, recebimentos, filtros disponíveis, detalhe e demais jornadas existentes. Não fabricar transações ou alterar títulos, baixas e movimentos para produzir capturas de produção.
5. Validar entrada direta no Cognito personalizado, login e retorno ao destino interno solicitado, inclusive deep link, navegação e logout/reentrada sem loop. O teste local de sessionStorage não comprova o retorno público. Conferir rejeição de destinos externos e comportamento ao trocar empresa ou revogar acesso.
6. Se faltar sessão humana, preparar as abas acessíveis ao executor e pedir somente autenticação/desafio. Não pedir senha, MFA ou cookies no chat. Continuar imediatamente após a intervenção e conduzir o restante da prova; não transferir a suíte ao proprietário. Recuperação não deve disparar e-mail sem autorização aplicável.
7. Atualizar o relatório único com matriz implementado/publicado/verificado/pendente, capturas sanitizadas, versões e rollback. Registrar qualquer limitação concreta. Publicação não é aceite; permanecem separados PRM_009, Spider, canônica histórica, Pay, APPLY e PRM_007.

Não reiniciar a Spider, modificar Pay/Hub/Panne ou ampliar permissões para esta publicação. Este adendo integra o mesmo prompt; copiar a versão atualizada para o repositório e manter seu rastreio.

## Forma de entrega das próximas instruções

Por determinação do proprietário, toda instrução que ele deva encaminhar ao Cursor será consolidada em documento de prompt apresentado na área lateral. Mensagens resumidas do chat não substituem o documento. Manter um prompt por recorte, incorporando corretivos/adendos no mesmo arquivo quando aplicável, com referências e critérios verificáveis.
