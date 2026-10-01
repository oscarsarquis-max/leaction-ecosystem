# ACTIONFINANCE_PRM_009 — Sincronização de recebimentos com passagem visível pela Spider

## 1. Objetivo e autorização

Implementar e demonstrar, em ambiente controlado, a sincronização manual de transações de recebimento da Loja de Pães originadas no ActionHub Pay. Usar o código real do serviço Pay com banco descartável e dados de teste, obrigatoriamente pelo percurso ActionFinance → Spider → provider ActionHub Pay → Spider → ActionFinance.

O proprietário precisa enxergar a execução na Spider. Resultado exibido apenas no Finance, logs desconectados ou simulador substituindo o Hub não satisfazem o aceite.

Cursor é o executor. Ler AGENTS/regras aplicáveis e os contratos atuais antes de alterar. Registrar o encerramento do PRM_008 já emitido pelo analista. Não reabrir seus corretivos nem iniciar PRM_010. Este prompt autoriza alterações necessárias em AF, Spider e na superfície de integração do Pay, com diffs separados por produto. Não autoriza deploy, mudança em AWS/DNS, acesso de escrita a dados de produção, commit ou push.

PRM_007 e sua pendência de invalidação de sessões restauradas permanecem separados.

## 2. Levantamento obrigatório e execução

Rastrear a página /dashboard/admin/payments até API, consultas e tabelas. Identificar pedido, transação do processador e tentativa de pagamento; uma venda pode ter múltiplas tentativas. Documentar os IDs e cardinalidades, sem presumir que orderId seja paymentId.

Localizar valor efetivo, moeda, status original, datas de criação/alteração, app/empresa e identificação de teste. A captura do proprietário mostra aprovados com valor “—” e receita R$ 0,00. Determinar a causa no código; não deduzir valor zero nem situação financeira a partir do resumo visual.

O adaptador individual atual lê amount_cents do payload e pode retornar null. Validar a origem correta para checkout avulso e assinaturas, precisão e ausência de dados. Não obter valores por scraping da página administrativa.

Após o levantamento, implementar a fatia sem pedir aprovação de escolhas rotineiras. Se faltar dependência externa, concluir tudo que independe dela e registrar o impedimento concreto; não substituir silenciosamente o Pay por fixture HTTP. Dados de teste no banco do Hub real são permitidos e devem ser rotulados como tais. Isso não prova sandbox vivo do processador nem leitura de produção.

## 3. Responsabilidades e contrato

- Pay: fonte das transações de cobrança/recebimento e de seus estados originais; endpoint de leitura com empresa/app, ambiente e paginação autorizados.
- Spider: autenticar o satélite, validar finalidade e binding de empresa, selecionar capacidade/provider no registry, despachar e devolver contrato comum com rastreabilidade.
- Adaptador do provider: traduzir contrato comum para a API do Pay e normalizar a resposta; credenciais do Pay só nessa fronteira.
- Finance: armazenar representação externa, controlar a sincronização e apresentar os dados. Não conhecer URL ou credencial do Pay.

Adicionar capacidade de listagem, por exemplo LIST_PAYMENT_TRANSACTIONS, com nome final alinhado ao catálogo existente. Reutilizar o mecanismo satélite aprovado quando apropriado. EXPERIENCE continua sem EXECUTE_CAPABILITY; a Spider decide a capacidade. Versionar mudanças incompatíveis e manter regressão 1.0–1.3. Não forçar contratos antigos a aceitar campos novos sem regra explícita.

Contrato de item: identidade estável, referência de pedido quando distinta, empresa/binding, origem, ambiente, status original e normalizado, valor em unidades mínimas como string ou ausência explícita, moeda, datas e revisão da origem quando disponível. Pagamento aprovado, liquidação e dinheiro disponível são conceitos distintos.

Valores ausentes/inconsistentes exigem revisão e ficam fora de somas; nunca converter null em zero, inventar BRL ou timestamp da origem. Não transportar payload bruto, tokens, dados de cartão ou dados pessoais desnecessários.

## 4. Paginação e retomada

Primeira sincronização traz o histórico autorizado; seguintes buscam registros novos e alterados, incluindo cancelamentos e reembolsos. Não filtrar apenas por created_at ou apenas aprovados.

Projetar ordenação estável, desempate por ID, limite superior da janela e cursor opaco validado por escopo. Explicar como alterações durante paginação são recuperadas sem perdas: snapshot apropriado ou janela sobreposta com deduplicação e semântica documentada. Datas iguais e atualizações de registros antigos devem ter testes próprios.

No AF, persistir os itens da página e seu checkpoint na mesma transação curta. Avançar o marco global somente após concluir a janela; falha parcial deve permitir retomada/reprocessamento seguro. Não manter transação durante HTTP. Impedir duas sincronizações concorrentes da mesma origem/empresa/ambiente ou coordená-las explicitamente.

Não introduzir entrega automática de eventos neste ciclo. Push com persistência e recuperação é evolução futura; polling agendado também fica fora. Agora a ação é manual: “Sincronizar recebimentos”.

## 5. Base de dados e regras financeiras

Atualizar DAT com modelo físico: entidades, colunas/tipos, PK/FK, unicidade, índices, estados, retenção e permissões. Reutilizar estruturas somente se a semântica for adequada; não transformar a consulta individual em lote por conveniência.

Persistir execução de sincronização, páginas/tentativas/checkpoint, transação externa e histórico necessário para explicar alterações. Unicidade inclui tenant, empresa, origem, ambiente e identificador da transação; separar testes de operação real. Preservar valor/status anteriores e não deixar resposta antiga sobrescrever revisão nova.

Importação registra transações externas. Não cria automaticamente títulos, recebimentos, baixas, movimentos de conta ou saldo; esses vínculos exigem um recorte posterior. Repetir sincronização não duplica registros. Permissões de leitura/escrita respeitam empresa; somente perfil autorizado inicia sincronização.

Migrations incrementais após V11, sem alterar checksums anteriores, com grants mínimos e sem dados reais em seeds. Documentar eventual vínculo futuro com título, sem inserir FK ou correspondência fictícia.

## 6. UX do Finance

Adicionar área funcional “Recebimentos do Pay” na navegação existente, com filtro de empresa autorizada e ambiente visível. Manter logos, dimensões, azul/ouro/branco e padrões responsivos aprovados.

Exibir última sincronização, resultado, quantidade importada/atualizada/em revisão e ação manual. Lista desktop e cartões mobile com data, referência, valor ou “Valor não informado”, situação na origem e identificação de teste. Não chamar soma de aprovados de saldo ou dinheiro disponível. Testes não entram em totais operacionais.

Detalhe: dados de origem, histórico de atualização e rastreio. Oferecer “Ver execução na Spider” com link autenticado real para a execução correspondente. Mostrar claramente que importar não movimenta dinheiro nem baixa título.

Estados: vazio, carregando, concluído sem novidades, sucesso, parcial, indisponível, revisão de dados e acesso negado. Preservar itens já importados na falha; indicar retomada. Mensagens de indisponibilidade não devem usar aparência de sucesso. Navegação por teclado e foco acessíveis; 360/768/1280 sem overflow.

## 7. UX e rastreabilidade na Spider — requisito central

Inspecionar o monitor existente e estendê-lo, sem criar um painel paralelo se ele já atende. Para uma execução mostrar explicitamente:

Finance solicitou → empresa autorizada → capacidade selecionada no registry → provider ActionHub Pay acionado → resposta recebida → resultado devolvido.

Exibir execução raiz e correlações das páginas/tentativas, horários/duração, origem/destino, ambiente, quantidade de itens e erros. Instrumentar fatos reais; não animar etapas inferidas ou fabricar eventos. A conclusão da importação é fato do AF: não afirmar na Spider que o AF persistiu só porque ela devolveu a resposta.

O usuário deve conseguir acompanhar a mesma execução entre telas do AF e Spider. Controle de acesso no monitor deve impedir exposição de outras empresas e segredos. A durabilidade atual da Spider é limitada: declarar retenção e comportamento após restart; não afirmar histórico persistente se houver apenas RAM. AF mantém seu histórico próprio durável.

## 8. Provas para aceite

Executar com AF, Spider, provider e código real do Hub, usando Postgres descartável do Hub com transações conhecidas. Provar:

1. Mais de uma página, IDs/datas coincidentes, valor válido e valor ausente, pendente/aprovado/reembolsado. Primeiro lote, repetição sem duplicatas e alteração de transação antiga.
2. Falha entre páginas e reinício do AF: retomada consistente, sem perda do checkpoint confirmado nem duplicação. Disputa de dois acionamentos.
3. Empresa errada, cursor de outra empresa e ambiente incompatível recusados; credenciais não aparecem em navegador/logs.
4. Spider interrompida com Hub saudável: nenhuma nova chamada ao provider; AF mantém importados e informa falha. Após religar, retomada pela Spider.
5. Navegador real nas larguras propostas: sincronizar no AF, abrir execução na Spider e conferir resultado no AF. Capturas de viewport e fullPage normalizado no topo, com valores de teste. Evidência da mesma correlação nas três fronteiras.
6. Antes/depois no banco: nenhuma baixa, título ou movimento financeiro criado pela sincronização. Integridade após backup/restore isolado das novas estruturas, sem tocar RDS.

Rodar verify integral do AF após migrations; testes afetados e regressão contratual da Spider; testes do endpoint/adaptador Hub; lint/test/build dos frontends alterados. Guardar logs por execução, evitando somar XML antigos de target. Não classificar teste simulado como integração real nem substituir asserções por capturas.

## 9. Entrega e parada

Salvar prompt integral em documents/prompts/ACTIONFINANCE_PRM_009.md. Entregar ACTIONFINANCE_REV_009.md, modelo físico atualizado, contrato/matriz INT, UX, guia curto para o proprietário acompanhar as duas telas e índice. Documentar cada alteração por produto e o que é dado de teste.

Classificar separadamente: Hub real local com banco descartável; simulador; sandbox do processador; produção. Se só a primeira estiver exercitada, declarar exatamente isso.

Apresentar gates, caminhos das evidências, limitações e estado final dos serviços. Sem deploy, commit/push, dinheiro real, payout, baixa automática, Panne ou PRM_010. Parar para revisão do analista.
