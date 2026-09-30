# ACTIONFINANCE_PRM_003 — Primeira entrega funcional: a receber e a pagar

Versão 0.3 — 28/09/2026 — produto autônomo, UX e modelo de dados detalhados

Esta versão substitui a 0.2 do mesmo prompt, não inicia outro ciclo. As seções 9–11 são especificação do analista e prevalecem sobre escolhas antes deixadas abertas. Cursor implementa e registra divergências justificadas; não redefine silenciosamente o produto.

## Resultado que você deve entregar

Implemente em C:\Projetos\ActionFinance uma aplicação local utilizável para **cadastrar, consultar e acompanhar títulos a receber e a pagar**, com PostgreSQL, API Java e interface em português. Ao abrir a aplicação, o proprietário deve conseguir percorrer os dois fluxos, ver compromissos por vencimento e consultar o histórico das alterações. Não entregar somente contratos, documentação ou endpoints sem telas.

Você é o único desenvolvedor. O analista definiu o recorte e a UX neste prompt; o proprietário retornará seu relatório para revisão. Pare após esta entrega, sem emitir/executar PRM_004.

## 1. Produto autônomo, contexto de negócio e fronteiras

**ActionFinance é um produto financeiro autônomo e integrável, não uma extensão exclusiva do grupo.** Deve permitir operação manual completa do recorte implementado sem Spider, ActionHub ou Panne disponíveis. Essa autonomia não transforma o ActionFinance em processador de pagamentos: gestão local e execução externa são responsabilidades diferentes.

A Spider será a camada de integração e interação com sistemas internos ou de terceiros, conforme capacidades, autorização e contratos efetivamente suportados. “Qualquer sistema” é uma direção de extensibilidade, não promessa de conector universal já implementado. Não restringir o domínio a seguros/crédito por limitações do contrato atual da Spider; não fingir que esse contrato já atende a esta integração.

Dois modos de uso do mesmo produto: autônomo, com entrada e gestão locais; conectado, combinando operação local e fatos externos através da Spider. Não criar forks, dependência de disponibilidade da Spider para CRUD local ou chamadas de rede obrigatórias no startup/readiness local.

Empresa/organização e autorização são conceitos próprios do produto. Não hardcodar “grupo”, “padaria”, ActionHub ou Panne em regras, nomes de tabelas ou permissões. Cadastros devem usar linguagem genérica (cliente, fornecedor, categoria). Exemplos de padaria pertencem somente à carga demonstrativa. Comercialização, onboarding corporativo, planos de assinatura do próprio ActionFinance e identidade de produção ficam para entregas próprias.

Primeiro cenário do proprietário, sem limitar os demais clientes do produto:

- ActionHub registra vendas, recebimentos e planos de subscrição. Continua sendo o módulo de pagamento existente, sem mudança de essência.
- Panne registra compras, entradas de mercadorias e estoque físico.
- ActionFinance administra as duas frentes financeiras e despesas próprias como aluguel, energia e folha, sem calcular folha.
- Integrações futuras passam pela Spider. Não implementar conectores neste ciclo.

Distinções obrigatórias: venda não é recebimento; compra/entrada de estoque não é pagamento; plano de subscrição não é uma única conta a receber. O título representa um compromisso com valor e vencimento. Não apresentar soma de títulos como saldo bancário, receita realizada, lucro ou caixa disponível.

Nesta entrega, dados são fictícios e operações locais. Registros digitados têm origem técnica MANUAL; a identificação de ambiente/dado demonstrativo é separada da origem de negócio. Não criar MANUAL_DEMO como conceito permanente do domínio. Pode haver uma referência informativa ao fato simulado (venda, parcela de subscrição ou compra), sempre identificada como demonstrativa. Nunca exibir dados como sincronizados/importados do Hub/Panne sem conexão real. Não gerar recorrências ou parcelas automaticamente, nem consultar sistemas externos.

Documentar o vínculo futuro com fonte externa em termos genéricos: organização/empresa, instância da conexão, sistema de origem, tipo e ID externo do objeto, parcela/componente quando aplicável, versão/evento e correlação de integração. A deduplicação deverá considerar esse contexto, não só o ID externo global. Isso é desenho para evolução: não criar agora conectores vazios, tabelas de inbox/outbox sem uso ou APIs que aceitem origem externa declarada pelo usuário. Nenhuma enumeração fechada HUB/PANNE pode definir todos os sistemas permitidos.

Documentar a separação entre o fato operacional, mantido pela origem, e os dados/decisões gerenciais mantidos pelo ActionFinance. Futuras atualizações externas precisarão tratar duplicidade, correção e conflito com edição local sem sobrescrita silenciosa. Não implementar essa política de sincronização sem contrato específico.

As definições a seguir são decisões de implementação do recorte local, não aprovação retroativa de todos os ADRs nem autorização de uso real.

## 2. Ler e preservar

Ler instruções aplicáveis, ARQ_001, ARQ_002/diretrizes de integração, DOM_001, DAT_001, UX_001, parecer de encerramento da fundação e código atual. Este prompt atualiza o recorte anterior: recebíveis entram agora e a UX operacional básica também, sem esperar um prompt posterior só de telas. Documentar essa mudança explicitamente.

Preservar Java 21, Boot 3.4.2, PostgreSQL 17.6, Flyway 11.10.1, testes Testcontainers, perfis e isolamento existentes. Não editar V1 aplicada, seu checksum, outros produtos, regras globais, configurações globais de máquina ou volumes preservados. Sem nested Git, commit/push/deploy, DNS ou contas reais.

Antes de reutilizar os scripts de parada, resolver R1 do parecer: metadados incompletos devem recusar encerramento; PID/data de criação/executável devem coincidir; checkout deve ser o caminho canônico exato desta execução, não Contains/prefixo de outra pasta. Filhos devem provir de árvore previamente comprovada; launchId é correlação, não prova isolada. Não adotar processos desconhecidos pela porta/texto. Provar com processos descartáveis que caminho semelhante e registro sem data são recusados, mantendo o caso de wrapper ausente. Completar ensaio start/stop sem resíduos próprios. Não ampliar o trabalho para um gerenciador genérico de processos.

Resolver R2 com npm ci bem-sucedido a partir do lockfile, com frontend próprio parado com segurança. Aproveitar as correções existentes. Estas duas tarefas acompanham a entrega funcional e não a substituem.

## 3. Funcionalidade desta fatia

Dois destinos visíveis: **A receber** e **A pagar**, com comportamento consistente. Cadastros de apoio mínimos: contrapartes e categorias. Não construir ERP de clientes/fornecedores. Contraparte pode ser cliente, fornecedor ou ambos; sem CPF, dados bancários ou endereço obrigatório no demo.

Um título contém (nomes físicos, nulabilidade e relacionamentos na seção 10):

| Campo | Regra desta entrega |
| --- | --- |
| ID/referência interna | Gerados pelo servidor; estáveis e distintos da referência de origem |
| Empresa | Do contexto autorizado; não escolhida livremente no corpo |
| Direção | RECEIVABLE ou PAYABLE na API/banco; “A receber” ou “A pagar” na UI; imutável após criação |
| Contraparte | Obrigatória para confirmar; da mesma empresa |
| Descrição | Obrigatória para confirmar, até 200 caracteres |
| Valor/moeda | BRL; positivo; inteiro de centavos na persistência/API |
| Competência e vencimento | Datas de negócio obrigatórias para confirmar; podem diferir |
| Categoria | Obrigatória para confirmar; compatível com direção e empresa |
| Unidade/centro de custo | Fora desta implementação; evolução definida na seção 11 |
| Referência do fato simulado | Opcional, até 100 caracteres; não é chave canônica externa nem prova de sincronização |
| Situação | DRAFT, OPEN ou CANCELLED |
| Controle | version, ator e instantes de criação/alteração; origem MANUAL, com identificação demo separada |

Rascunho exige descrição não vazia; demais campos podem estar ausentes. Campos preenchidos sempre devem ser válidos. Confirmar exige todos os obrigatórios. Valores não usam double/float: manter numeric(19,0) e string de inteiro de centavos na API, com validação de limites de representação; não inventar limite comercial. Usar BigInteger/BigDecimal de forma coerente no Java, sem converter todo numeric(19,0) para long. Na UI, formatar e converter decimal brasileiro sem aritmética monetária de ponto flutuante nem perda acima de Number.MAX_SAFE_INTEGER.

Competência/vencimento não sofrem conversão de fuso. A data de negócio vem do backend, America/Sao_Paulo neste demo, com Clock injetável. Vencido é OPEN com vencimento anterior à data de negócio, derivado e não persistido. Hoje não é vencido. Valores negativos/zero são recusados quando preenchidos; outras moedas também.

Transições:

- Criar DRAFT; editar DRAFT; confirmar DRAFT → OPEN.
- Oferecer também “Registrar” no formulário para criar OPEN atomicamente, após validação completa.
- OPEN: valor, contraparte, descrição, classificação e datas podem ser corrigidos com motivo obrigatório e histórico de antes/depois. Direção/empresa/origem técnica imutáveis.
- DRAFT ou OPEN → CANCELLED com motivo; cancelado é somente leitura. Sem exclusão física e sem reabertura nesta fatia.

Não há estados pago/recebido, baixa parcial, execução de cobrança, transferência, conciliação ou liquidação. Isso é um recorte de acompanhamento de compromissos; não uma implementação completa da gestão financeira. Não colocar botões sem funcionalidade para esses recursos.

## 4. Persistência, auditoria e autorização

Reutilizar a arquitetura modular existente. Domínio e casos de uso independem de DTOs/clientes da Spider ou de fornecedores externos. Adaptadores futuros traduzem contratos externos na borda; o modo manual utiliza os mesmos casos de uso locais. Decisão do analista: financial_title compartilhado com direção e invariantes comuns, mantendo casos de uso distinguíveis. Modelo definido na seção 10; não criar abstração genérica de ERP.

Novas migrations incrementais; grants mínimos de runtime; Hibernate sem criação automática. Integridade de referências por empresa também no banco, por exemplo com chaves compostas. Uma empresa nunca referencia contraparte/categoria da outra. Não confiar em ocultação da UI.

Persistir histórico local append-only por aplicação, na mesma transação da alteração: empresa, título, ação, ator do principal, instante UTC, campos alterados e motivo quando exigido. Sem dados secretos nos eventos. Não chamar esse histórico de ledger ou auditoria criptograficamente imutável.

Concorrência otimista em alteração/confirmação/cancelamento. Versão desatualizada → 409, preservando dados atuais; interface explica e permite recarregar sem sobrescrever silenciosamente.

Idempotência persistente e transacional nas criações/ações: escopo por empresa, ator, operação e chave, fingerprint do pedido, resultado seguro. Repetição idêntica retorna o mesmo resultado; chave reutilizada com conteúdo diferente → 409. Impedir duplicidade mesmo em requisições simultâneas; não implementar só mapa em RAM. Documentar retenção local sem expurgo automático nesta fatia. Autorizar antes de devolver resultado idempotente.

Permissões explícitas de leitura/escrita para títulos e cadastros; consulta não altera. Reutilizar o resolvedor de contexto e identidade demo do backend. Nada de aceitar actor/role/authority fornecido pelo corpo ou header arbitrário. Rotas novas devem ser explicitamente permitidas e o restante permanece denyAll.

Identidade demo: acesso apenas local-demo/loopback, token não embarcado no frontend, não salvo em localStorage, não logado. Pode usar entrada local de token em memória com instrução simples; reaproveitar solução segura existente se houver. Limpar dados ao sair/trocar contexto; bloquear resultados assíncronos atrasados de empresa anterior.

## 5. Contratos de consulta

Antes de implementar, fixar contratos no documento técnico e cumprir nas telas. API sob /api/v1, seguindo convenções existentes; separar ou filtrar explicitamente as duas direções. Expor criar, listar, detalhe/histórico, corrigir, confirmar e cancelar. Cadastros de apoio com listar/criar/editar/inativar; inativo permanece consultável nos títulos existentes e não pode ser usado em novos registros.

Listagem paginada no servidor, ordem estável vencimento crescente e ID para desempate; datas ausentes por último. Filtros: busca por referência/descrição/contraparte, situação, intervalo inclusivo de vencimento, categoria e somente vencidos. Validar intervalos e limitar tamanho de página. Parâmetros e ordenação permitidos por lista explícita.

Resumo no backend para todo o filtro, independente da página: quantidade/valor de OPEN, quantidade/valor de OPEN vencidos, quantidade de rascunhos. Rascunhos/cancelados não entram no total aberto. Somar cada direção separadamente. Não compensar receber contra pagar nem chamar a diferença de saldo.

Preservar respostas uniformes existentes para empresa/objeto inacessível, sem revelar sua existência. Validação 400, não autenticado 401, falta de permissão 403, conflito 409 conforme convenções compatíveis do projeto.

## 6. UX a implementar

Ferramenta de trabalho em português, fundo cinza-claro, superfícies brancas, texto grafite, azul-petróleo nas ações. Tipografia de sistema, valores tabulares alinhados à direita, espaçamento consistente de 4/8 px. Não acrescentar biblioteca visual grande só para esta fatia.

Shell desktop: navegação lateral com A receber, A pagar e Cadastros; topo com empresa ativa, identificação “Demonstração local” e usuário/perfil. Abrir em A receber; manter última direção dentro da sessão. Sem menus de módulos futuros, sem indicador de integração ativa. Status técnico da fundação pode ficar em área secundária, não na tela principal.

Cada direção contém:

1. Título “Contas a receber”/“Contas a pagar” e ação “Novo recebível”/“Nova conta a pagar”.
2. Resumo do filtro: Em aberto, Vencidos e Rascunhos, com rótulos claros; não usar verde de sucesso para pendências.
3. Busca e filtros. Diferenciar sem registros de sem resultados; oferecer limpar filtros.
4. Tabela com referência, cliente/fornecedor, descrição curta, vencimento, valor, situação e categoria. Abrir detalhe pela referência. Paginação e indicação de total filtrado.

Formulário em página dedicada, empresa fixa e seções Identificação, Valor e datas, Classificação. Labels persistentes, BRL explícito, entrada brasileira (1.234,56), campos obrigatórios identificados. Ações Salvar rascunho e Registrar; sucesso “Recebível registrado”/“Conta a pagar registrada”, com esclarecimento discreto de que não houve movimentação financeira. Desabilitar duplo envio e preservar a chave para repetição após timeout.

Detalhe com referência/situação, dados principais, ações permitidas e histórico legível. Correção de OPEN exige motivo; cancelamento usa diálogo com motivo e consequência clara. Não pedir confirmação para simples salvamento. Troca de empresa/saída com edição pendente pede decisão; não perder formulário silenciosamente.

360 px: menu recolhível, lista em cartões, sem scroll horizontal da página. Desktop 1280 px: tabela legível. Teclado, foco visível, rótulos, mensagens de erro associadas aos campos, contraste e status além de cor. Carregamento não exibe zeros inventados; falha preserva formulário; timeout distingue resultado desconhecido de operação rejeitada. Conflito permite recarregar e informa que outra alteração ocorreu.

## 7. Dados demonstrativos e verificações

Criar carga demo explícita, repetível e exclusiva de local-demo; nunca migration com seed corporativo. Duas empresas fictícias para provar isolamento. Exemplos a receber: venda demonstrativa e parcela demonstrativa de subscrição; a pagar: compra de insumos e aluguel. Incluir OPEN a vencer/hoje/vencido, DRAFT e CANCELLED. Datas relativas à data de negócio da carga, sem atualização silenciosa a cada reinício. Nenhuma pessoa/credencial real.

Testes proporcionais às regras:

- PostgreSQL/Testcontainers: isolamento de empresa/referências, dinheiro exato/limites, validação, transições, concorrência, idempotência concorrente e rollback do histórico.
- Autorização: leitor não escreve; operator só na empresa permitida; origem/ator não forjáveis; denyAll continua fora das rotas implementadas. Atualizar o teste antigo de /payables negado: se a rota agora existir, testar uma rota realmente não permitida, sem perder cobertura.
- Autonomia: aplicação e CRUD das duas frentes funcionam com nenhum cliente/serviço externo configurado; nenhuma chamada para Spider, Hub ou Panne é exigida. Usar também um exemplo fictício de empresa fora do ramo de padaria para verificar ausência de regras específicas desse negócio.
- Datas com Clock fixo: ontem/hoje/amanhã; resumo correto além da primeira página e excluindo cancelados/rascunhos.
- UI/navegador: cadastrar cada direção, confirmar, corrigir com motivo, cancelar, consultar histórico, filtros, conflito, erro de API, troca de empresa e consulta sem escrita; 360/1280 px e teclado. Capturas dos dois fluxos.
- mvnw.cmd clean verify completo, zero skips/falhas/erros; npm ci, lint, testes, build e audit, com resultado real registrado.

A nova persistência exige adaptar o ensaio de backup que atualmente só aceita V1: comparar conjunto completo de migrations/checksums e restaurar dados fictícios/grants das novas tabelas. Testar em container descartável, conferir títulos/histórico e acesso runtime após restauração. Não editar V1 nem conceder DDL ao runtime.

## 8. Entrega

Salvar este prompt integral em documents/prompts/ACTIONFINANCE_PRM_003.md. Atualizar ARQ, DOM/DAT/UX e índice com o recorte realmente implementado e a diretriz de produto autônomo/integrável, preservando histórico e distinguindo propostas futuras. Produzir documents/reviews/ACTIONFINANCE_REV_003.md.

Relatório deve trazer: como abrir e percorrer as duas frentes; telas/capturas; contratos e migrations; testes e seus resultados; ressalvas R1/R2; mudanças de documentação; estado final de serviços; limitações funcionais explícitas. Sem dizer que integração ou recebimento/pagamento foi executado.

Se houver problema em uma frente, declarar a entrega parcial; não substituí-la por cartões estáticos ou dados hardcoded. Resolver erros dentro deste escopo e então parar para revisão do analista. Nenhuma autorização de produção decorre deste prompt.

## 9. Especificação de UX do analista

### 9.1 Estrutura e medidas

Desktop a partir de 1024 px: barra lateral de 224 px, cabeçalho de 64 px, conteúdo com 24 px de margem e largura máxima de 1440 px. De 768 a 1023 px, navegação recolhida em menu. Abaixo de 768 px, margem de 16 px, uma coluna, tabela substituída por cartões. Alvos de interação com pelo menos 44 px; texto de campos 16 px. Títulos 24 px, texto principal 16 px e texto auxiliar 14 px. Bordas discretas de 1 px, raio de 8 px; nada de gradientes ou decoração de landing page.

Tokens iniciais: fundo #F4F6F8, superfície #FFFFFF, texto #172B3A, texto secundário #465968, ação #075985 e foco #1D4ED8. Estados têm texto/ícone e cor; testar contraste real nas combinações utilizadas e ajustar se necessário. Rascunho neutro, Em aberto azul, Vencido âmbar escuro, Cancelado cinza. Sucesso transitório pode ser verde; pendência não.

Topo: marca ActionFinance, empresa ativa, “Demonstração local” e perfil. Organização contratante é contexto de isolamento, sem seletor livre de tenant. Se o usuário tiver uma única empresa, mostrar seu nome sem controle que prometa alternativas. Navegação: A receber, A pagar, Cadastros. Cadastros abre abas Contrapartes e Categorias. Não usar “Cliente” no menu para designar simultaneamente contratante do produto e devedor.

### 9.2 Mapa de telas e caminhos

| Tela | Caminho de interface | Objetivo |
| --- | --- | --- |
| Lista a receber | /receivables | Priorizar e localizar recebíveis |
| Lista a pagar | /payables | Priorizar e localizar obrigações |
| Novo título | /receivables/new ou /payables/new | Digitar e salvar/registrar |
| Detalhe | /receivables/:id ou /payables/:id | Entender título e histórico |
| Edição | mesmo caminho + /edit | Editar rascunho ou corrigir aberto |
| Cadastros | /catalogs/counterparties e /catalogs/categories | Manter dados de apoio |

Links diretos e recarga devem funcionar. O detalhe valida direção; ID de conta a pagar não aparece como recebível por trocar a URL. Voltar preserva filtros/página da lista na sessão; não guardar tokens junto deles. Após criação, abrir detalhe; após cancelamento, permanecer no detalhe atualizado. Ao cancelar edição, voltar à origem preservando o estado anterior.

### 9.3 Lista: hierarquia visual definida

Padrão de entrada: situação Em aberto, sem intervalo de data; 20 itens por página, opções 20/50. Ordenação vencimento crescente e ID. Busca com atraso curto de 300 ms, descarte de resposta obsoleta e paginação reiniciada após mudar filtro. Alteração de empresa limpa filtros e seleção da empresa anterior. Filtro Situação permite Em aberto, Rascunho, Cancelado e Todas; “Vencidos” é condição adicional, não estado da máquina.

Resumo acompanha exatamente os filtros, inclusive situação; mostrar zero verdadeiro quando, por exemplo, a consulta só contém cancelados. Sem dados ainda: explicar “Nenhum recebível cadastrado nesta empresa” e oferecer cadastro apenas ao operador. Sem resultado de filtro: “Nenhum resultado para estes filtros”, com Limpar filtros. Falha de API: mensagem e Tentar novamente, preservando filtros; não converter erro em lista vazia.

No cartão mobile: referência e situação no topo; contraparte e descrição; vencimento e valor em destaque; categoria secundária. Item inteiro pode abrir detalhe, mas deve ser link acessível, sem ações sobrepostas. Sem seleção em massa nesta etapa.

### 9.4 Formulário, detalhe e cadastros

Formulário com largura máxima de 880 px. Ordem: descrição; contraparte; referência informativa; valor; competência; vencimento; categoria. Desktop: valor/competência/vencimento em linha; mobile: campos empilhados. Empresa e direção são texto contextual, não campos editáveis. Campos inicialmente vazios; não inferir valor ou vencimento. Usar labels “Cliente / pagador” a receber e “Fornecedor / favorecido” a pagar, mantendo suporte a contrapartes BOTH.

Seletores de contraparte/categoria com busca e estado vazio explicativo. Ação “Cadastrar contraparte”/“Cadastrar categoria” abre diálogo curto, sem perder o formulário; depois de salvar, seleciona o cadastro criado. Leitor não vê ação de criação. Autocomplete só lista ativos e compatíveis. Detalhe antigo continua exibindo cadastro inativo com indicação, sem apagar seu vínculo.

Rodapé: Cancelar edição, Salvar rascunho, Registrar. Para OPEN, substituir por Cancelar edição e Salvar correção, com motivo obrigatório no próprio formulário. Mostrar validação junto do campo e resumo focável no topo após tentativa inválida. Não apagar entradas no erro. Valor vazio não vira zero; máximo de duas casas, sem arredondamento silencioso.

Detalhe: título/referência, situação, contraparte, valor, datas, categoria, origem “Manual” e referência informativa. Abaixo, histórico cronológico mais recente primeiro: ação, autor, data/hora local, motivo e alterações com rótulos humanos, nunca JSON bruto. Campos ausentes no rascunho aparecem como “Não informado”. Origem manual e badge demo têm significados separados.

Cancelamento: diálogo “Cancelar este título?”, valor/referência, motivo obrigatório de 3–500 caracteres, botões Voltar e Cancelar título. Explicar que retira o compromisso das previsões e não desfaz movimentação bancária. Após cancelar, todas as ações de alteração desaparecem. Foco retorna ao cabeçalho do detalhe; diálogo possui escape, foco contido e retorno adequado ao fechar.

Cadastros: lista simples de nome, papel/natureza e situação; criar/editar em diálogo. Inativar explica que títulos anteriores permanecem vinculados. Nomes duplicados são permitidos para contraparte e diferenciados por código; categorias usam código único. Não pedir dados fiscais/bancários.

### 9.5 Comportamentos críticos

| Situação | Resposta da experiência |
| --- | --- |
| Perfil consulta | Pode listar/ver histórico; botões de alteração ausentes; servidor mantém bloqueio |
| Sessão inválida | Limpar dados protegidos em memória e pedir nova identificação local, sem logar token |
| 403 | “Você não tem permissão para esta ação”; não sugerir trocar cabeçalhos |
| 409 por versão | “Este título foi alterado por outra pessoa”; manter valores digitados em memória e oferecer ver versão atual; não reenviar automaticamente |
| Timeout em escrita | “Não foi possível confirmar o resultado”; repetir com a mesma chave/payload, sem criar novo título |
| Troca de empresa com edição | Ficar nesta empresa ou Descartar alterações e trocar; sem autosave invisível |
| Carregamento | Estrutura estável e indicação de progresso; sem totais ou dados fictícios |

Critério de aceite UX: o proprietário percorre criar → registrar → localizar → corrigir → cancelar → consultar histórico nas duas direções sem terminal, edição SQL ou conhecimento de códigos técnicos. Somente a obtenção inicial do token demo segue a instrução local de teste; autenticação de produto será uma entrega própria.

## 10. Modelo de dados definido pelo analista — implementar nesta fatia

### 10.1 Isolamento e convenções

**Tenant é a organização cliente do produto; company é a empresa administrada.** Um tenant pode possuir várias empresas. Contraparte é quem paga/recebe, não é tenant. Introduzir essa separação agora evita fixar o produto a um único grupo. Não construir cadastro comercial/onboarding/IAM: tenants/empresas são provisionados apenas pela carga local explícita nesta etapa.

O principal atual contém authorizedCompanyIds. Preservar esse contrato e resolver tenant_id pela company autorizada no servidor; não aceitar tenant enviado como autoridade pelo cliente. Novos acessos ao banco recebem contexto autorizado contendo os dois IDs. Empresa desativada não admite escrita. Seed deve manter os UUIDs COMPANY_A/B já usados nos testes de fundação. Acrescentar terceira empresa fictícia para testar duas empresas no mesmo tenant e uma em tenant diferente, sem ampliar permissões dos usuários existentes. Ator multempresa só em fixture/demo explícito e separado.

Schema actionfinance. IDs UUID; instantes timestamptz UTC; datas date; version bigint não negativo; enums text/varchar com CHECK nomeado, sem ordinais Java. Texto limitado e validado após trim. Auditoria usa actor_id UUID do principal atual; sem FK a tabela de usuário inexistente. Não armazenar token. Actor_display_name pode ser snapshot de até 160 caracteres. Mudança futura de IdP exigirá mapeamento explícito, não substituição automática por e-mail.

### 10.2 Entidades e campos

Tabelas físicas: tenant, company, counterparty, financial_category, financial_title, financial_title_history, request_idempotency — conforme especificação do analista (PK UUID, FKs compostas tenant+company, CHECKs nomeados, UNIQUE de código/referência por empresa).

### 10.3 Invariantes adicionais

Conforme prompt: amount_minor positivo quando preenchido; OPEN completo; CANCELLED com motivo; histórico append-only; direção/empresa/origem imutáveis; idempotência transacional; runtime sem DELETE nesta fatia.

### 10.4 Índices e evolução de schema

Índices de consulta definidos pelo analista. Sem seed nas migrations. Toda consulta nova escopada por tenant/company.

## 11. Estrutura de dados do produto — evolução, sem implementar agora

Registrar no documento de dados a decomposição conceitual FUTURE/PROPOSED: estrutura gerencial, integração, parcelas/recorrência, tesouraria, execução externa, conciliação, custos e planejamento, produto e acesso. Não criar estas tabelas vazias, serviços fictícios ou menus agora.
