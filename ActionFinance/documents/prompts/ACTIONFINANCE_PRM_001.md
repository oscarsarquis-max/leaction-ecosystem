# ACTIONFINANCE_PRM_001 — Fundação documental da arquitetura

Versão 0.2 · Prompt para copiar integralmente no Cursor

Cópia integral do prompt recebido. A execução e o fechamento de ressalvas estão em [`ACTIONFINANCE_PRM_001_EXEC.md`](ACTIONFINANCE_PRM_001_EXEC.md).

## Missão e papéis

Você é o desenvolvedor exclusivo do ActionFinance. O analista de negócio/TI desta iniciativa define arquitetura, UX e prompts; o proprietário aprova as decisões. Nesta tarefa, materialize e valide a arquitetura documental fornecida. **Não implemente a aplicação, não crie banco nem inicie infraestrutura.**

Projeto de destino: `C:\Projetos\ActionFinance`, dentro do monorepositório Git existente em `C:\Projetos`, o mesmo da Spider. Não criar repositório Git aninhado.

## Entradas obrigatórias

Leia integralmente a arquitetura preparada pelo analista:

`C:\Users\Oscar Sarquis\Documents\Codex\2026-09-25\files-pasted-by-the-user-documento\outputs\ACTIONFINANCE_ARQ_001.md`

Use como apoio o levantamento anterior, subordinado à arquitetura mais recente e às decisões abaixo:

`C:\Users\Oscar Sarquis\Documents\Codex\2026-09-25\files-pasted-by-the-user-documento\outputs\ActionFinance-levantamento-2026-09-25.md`

Se a arquitetura não estiver acessível, procure esse nome no projeto e nos arquivos fornecidos ao Cursor. Se não existir, informe o bloqueio de entrada antes de criar uma arquitetura substituta. Não peça ao usuário respostas que estejam nesses documentos ou no código local.

## Decisões de negócio que não podem ser reinterpretadas

1. ActionHub permanece responsável somente pelo recebimento dos pagamentos das assinaturas dos serviços do grupo. Não será executor financeiro genérico.
2. ActionFinance concentra toda a gestão financeira restante. Terá frontend, backend de domínio, regras e PostgreSQL próprios; não será apenas uma tela para o Hub.
3. Toda gestão física do estoque da padaria pertence ao Panne. ActionFinance recebe os dados financeiros necessários por integração governada; não replica estoque físico.
4. Spider governa integrações, correlação, policies e evidências. Não se torna ledger e não é banco de dados do ActionFinance.
5. ActionFinance segue a estrutura de um EXPERIENCE Satellite independente. Frontend chama apenas seu backend. BFF e domínio podem coexistir no mesmo backend modular inicial.
6. O mesmo monorepo não autoriza compartilhamento de entidades, banco, imports do core Spider ou deployment.
7. Primeira fatia funcional planejada: cadastrar e acompanhar obrigações fictícias de contas a pagar, sem executar pagamentos. Não a implemente neste prompt.
8. Produto comum ao grupo; referências à padaria são exemplos de contexto, não modelo exclusivo.
9. Backend, BFF e domínio obrigatoriamente em Java, **na mesma versão da Spider**. A leitura atual do `C:\Projetos\spider\backend\pom.xml` confirma Java 21. Não propor Node.js/Python para backend. Frontend React/TypeScript é proposta de UI separada, conforme os satélites existentes.

## Escopo autorizado

- Leitura dos projetos existentes para confirmar convenções e limites.
- Criação/atualização de documentação exclusivamente em `C:\Projetos\ActionFinance`.
- Materialização da arquitetura do analista, ADRs propostos, especificação conceitual de dados, UX e matriz de integração.
- Relatório de divergências entre proposta e código, com evidência de arquivo/linha quando possível.

Não é permitido neste incremento: código executável, scaffolding de frontend/backend, manifests de dependências, migrations SQL, Compose, `.env`, secrets, cadastro de satélite/provider, chamadas financeiras, criação de banco, testes que iniciem serviços, mudanças em produtos vizinhos, commit ou push. Não usar subagentes/desenvolvedores paralelos sem instrução expressa do responsável.

## Etapa 1 — Inspeção e preservação

1. Leia `C:\Projetos\AGENTS.md` e qualquer instrução aplicável no destino.
2. Confirme raiz Git e estado do working tree. Registre alterações preexistentes relevantes, sem limpar, resetar, mover ou sobrescrever trabalho alheio.
3. Se ActionFinance já existir, inventarie seu conteúdo e integre a documentação de forma conservadora. Não apague documentos para forçar a estrutura proposta.
4. Leia as fontes abaixo, priorizando código/configuração sobre afirmações históricas de README:
   - Spider: ARCH-017, Satellite Contract, schemas 1.0/1.1/1.2, parser, registry, serviço de interação e idempotência.
   - SegSense: README, estrutura de camadas, manifests frontend/backend, Compose, configuração de persistência, migrations e manifesto de satélite.
   - SpiderBank: estrutura e limitações declaradas de persistência.
5. Registre versões observadas sem classificá-las como verificadas por build. Não instale dependências.
6. Não leia/imprima secrets, dumps, dados de produção ou conteúdo financeiro real. Não execute scripts de inicialização, migração, simulação ou deploy para “validar arquitetura”.

## Etapa 2 — Materialização documental

Criar os seguintes documentos. Documentos derivados devem referenciar a arquitetura principal e não introduzir decisões contraditórias.

| Arquivo no projeto | Conteúdo obrigatório |
|---|---|
| `README.md` | Propósito, limites, caminho do projeto, estado DOCUMENTATION_ONLY, ausência de aplicação executável e link para índice |
| `documents/README.md` | Índice navegável, status de cada documento, convenção de identificadores e próximos gates |
| `documents/architecture/ACTIONFINANCE_ARQ_001.md` | Arquitetura do analista, preservada como baseline v0.2; correções factuais registradas, não silenciosas |
| `documents/domain/ACTIONFINANCE_DOM_001.md` | Módulos, ownership, glossário de obrigação/tentativa/movimento/recebível, primeira fatia e fora de escopo |
| `documents/data/ACTIONFINANCE_DAT_001.md` | Modelo conceitual PostgreSQL, relações, dinheiro, empresa, concorrência, idempotência, histórico e evolução |
| `documents/integrations/ACTIONFINANCE_INT_001.md` | Matriz de compatibilidade Spider, identidades, limitações atuais e contratos a evoluir |
| `documents/ux/ACTIONFINANCE_UX_001.md` | Jornada, shell, navegação progressiva, lista, formulário, detalhe e estados de tela definidos pelo analista |
| `documents/adr/AF-ADR-001.md` a `AF-ADR-010.md` | Um registro por decisão técnica da seção 11, com contexto, decisão, consequências e status PROPOSED |
| `documents/prompts/ACTIONFINANCE_PRM_001.md` | Cópia deste prompt para rastreabilidade |
| `documents/reviews/ACTIONFINANCE_REV_001.md` | Evidências, divergências, validação documental e pendências por etapa |

Não criar diretórios vazios de runtime. A árvore alvo de frontend/backend/database é documentação para PRM_002, não instrução para implementar agora.

### Arquitetura e dados: verificações obrigatórias

- Java 21 é obrigatório e deve manter paridade com a Spider. Confirmar a propriedade `java.version` no POM atual da Spider e registrar evidência. Spring Boot observado na Spider é 3.4.2, enquanto SegSense usa 4.1.1: não copiar o POM ou starters do SegSense para outra versão major. A proposta é alinhar também Spring Boot à baseline da Spider, com resolução de dependências a validar na fundação. Não atualizar a Spider nem escolher “latest”. React/TypeScript/Vite é a proposta de UI; PostgreSQL próprio e Flyway compõem a persistência. Uma mudança posterior de Java na Spider deve ser registrada e refletida na baseline antes de implementar, mantendo a instrução de paridade.
- Banco e schema candidatos `actionfinance`, credencial exclusiva, sem compartilhamento de tabelas com Spider/Panne/Hub. Migrations canônicas em `database/migrations` e cópia de build conforme referência SegSense, a implementar depois.
- Camadas: interfaces HTTP, application, domain, infrastructure e configuration. Backend único com módulos; evitar serviços separados sem necessidade demonstrada.
- Tabelas conceituais da primeira fatia: company, business_unit, counterparty, financial_category, cost_center, payable, payable_history e request_idempotency. Não gerar DDL.
- Invariantes empresariais e relacionamentos entre empresas, dinheiro inteiro exato, datas de negócio versus instantes UTC, estado e condições derivadas documentados.
- Proposta monetária: minor units exatas; `numeric(19,0)` no PostgreSQL; representação de inteiro como string decimal na API para evitar perda em JavaScript. BRL apenas na primeira fatia; não inventar teto de negócio.
- Situações locais DRAFT, OPEN e CANCELLED conforme arquitetura. Vencida é condição derivada. Nenhuma delas representa pagamento bancário realizado.
- Idempotência persistida com escopo empresa/operação, fingerprint semântico e atomicidade; concorrência otimista; correções auditadas.
- Receita, recebível, tentativa de pagamento e movimento de caixa separados; sem saldo bancário inventado e sem novo ledger contábil implícito.

### Integração: verificações obrigatórias

Documente em tabela, para cada item: capacidade observada, fonte, requisito ActionFinance, gap, proposta, projeto que será alterado e gate.

Itens mínimos: identidade EXPERIENCE; nome técnico minúsculo; autenticação; finalidade financeira; contexto de empresa; contrato financeiro; idempotência durável; resposta síncrona; entrega assíncrona; deduplicação; correlação; observabilidade; persistência; dados proibidos.

Confirme que o contrato atual não é automaticamente compatível com o domínio financeiro. Não publicar versão futura presumida, inventar endpoint de callback, colocar pagamento em workingCapitalParameters nem escolher provider no BFF.

Operações locais continuam no ActionFinance; não precisam criar execução canônica. A integração financeira futura é entrega separada que exigirá prompt explícito na Spider. Inbox/outbox ficam especificadas como evolução, não como capacidade já existente.

### UX: verificações obrigatórias

Preserve o desenho de UX da arquitetura. Não redesenhe o produto por conta própria nem copie a homepage de outro satélite.

- Primeira navegação: Contas a pagar e cadastros necessários; módulos futuros só na documentação.
- Empresa ativa visível; troca segura de contexto e checagem de permissão no backend.
- Lista com filtros, retorno preservado, valores alinhados, paginação e total filtrado real.
- Cadastro em página dedicada; salvar rascunho e registrar obrigação, sem botão Pagar.
- Detalhe com situação, classificação e histórico; integração técnica recolhida somente quando existir.
- Estados vazio, filtrado, erro, conflito, sem permissão, carregando e resultado desconhecido.
- Acessibilidade, teclado, foco, responsividade e mensagens de negócio.
- Sem frontend, protótipo interativo, imagem gerada ou design system implementado neste prompt.

## Etapa 3 — Divergências e decisões

Classifique cada informação como:

- CONFIRMED_BY_OWNER: fronteiras de negócio e instruções explícitas do proprietário.
- OBSERVED_IN_CODE: comprovada no working tree, com fonte.
- PROPOSED: decisão técnica/UX ainda em revisão.
- EXTERNAL_CONTRACT_PENDING: depende de contrato ou provider ainda não confirmado.
- NOT_VERIFIED: exige execução ou inspeção fora do alcance desta etapa.

Não marcar ADR como ACCEPTED, arquitetura como aprovada, sistema como integrado ou ambiente como pronto pelo simples fato de produzir documentos. A divergência de cobrança avulsa no Hub deve constar como achado fora do escopo; não remover nem expandir esse código.

Se houver conflito técnico real entre a proposta e a referência, apresente evidência, impacto e alternativa recomendada no REV_001. Preserve as decisões de negócio. Não interrompa a documentação independente por lacunas que pertencem à integração futura.

## Etapa 4 — Verificação documental

1. Verificar existência dos documentos, índice, links internos e referências.
2. Conferir que todos os diagramas distinguem arquitetura alvo de fluxo implementado.
3. Conferir consistência dos nomes, estados, responsabilidades e status.
4. Demonstrar que não houve alteração em Spider, Panne, Hub, SegSense ou outros diretórios fora de ActionFinance.
5. Revisar diff e arquivos novos; não incluir secrets, payloads protegidos nem conteúdo não relacionado.
6. Não rodar build/testes de runtime para um incremento exclusivamente documental. Informar claramente que não foram executados.

## Critérios de aceite

- Documentação completa e coerente nos destinos previstos, sem aplicação criada.
- Arquitetura do analista preservada e divergências rastreadas.
- PostgreSQL próprio e estrutura de satélite independente inequívocos.
- Limites entre gestão local, integração Spider, estoque Panne e assinaturas Hub explícitos.
- Lacunas do contrato financeiro não disfarçadas como suporte existente.
- UX inicial suficientemente descrita para receber prompt visual posterior.
- Nenhum Git aninhado, commit, push, serviço iniciado, migration executada ou mudança em outros produtos.

## Resposta final esperada do Cursor

Entregue:

1. Resultado: DOCUMENTATION_ONLY, pronto para revisão arquitetural, sem alegar aprovação.
2. Relação dos arquivos criados/alterados e links.
3. Evidências do padrão de satélite adotado e divergências encontradas.
4. Decisões que permanecem PROPOSED e contratos pendentes.
5. Resultado das verificações documentais; informar que não houve testes de runtime.
6. Insumos necessários ao PRM_002, sem implementá-lo nem escrever prompts substitutos do analista.

Pare ao concluir esta entrega. Não avance automaticamente para fundação, domínio, UX executável ou integração.
