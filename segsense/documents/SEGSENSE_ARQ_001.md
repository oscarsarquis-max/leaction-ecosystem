# SEGSENSE_ARQ_001 — Proposta Inicial e Arquitetura de Referência

## Controle do documento

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_ARQ_001 |
| Título | Proposta Inicial e Arquitetura de Referência |
| Categoria | ARQ — Arquitetura |
| Versão | 0.4 |
| Status | Em elaboração |
| Data | 12/09/2026 |
| Plataforma subjacente | Spider |
| Integração inicial | Icatu Seguros |
| Stack definida | PostgreSQL, Java e React |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 0.1 | 04/09/2026 | Consolidação da proposta inicial, limites, arquitetura de referência e primeiro recorte funcional. |
| 0.2 | 04/09/2026 | Aderência ao SPIDER-ARCH-017 e formalização do SegSense como Insurance Reference Satellite. |
| 0.3 | 04/09/2026 | Esclarecimento da independência física e operacional entre SegSense, Spider e provedor mock. |
| 0.4 | 12/09/2026 | PRM_010: o ideal satélite permanece; o contrato externo executável está ausente (ramo B). |

## 1. Finalidade

Este documento apresenta a proposta inicial e a arquitetura de referência do SegSense, uma solução de distribuição contextual de seguros construída sobre a plataforma Spider.

O documento estabelece o problema de negócio, a proposta de valor, os atores, as responsabilidades sistêmicas, a jornada inicial, os limites regulatórios, o modelo conceitual, a arquitetura tecnológica e o escopo de uma primeira prova de valor.

O SegSense não criará uma arquitetura de execução paralela à Spider. As regras e interfaces específicas do domínio de seguros pertencerão ao SegSense; interpretação contextual, políticas, planejamento, resolução e execução continuarão sob responsabilidade da Spider.

## 2. Visão do produto

O SegSense será uma plataforma de distribuição contextual de seguros. Sua função será conectar situações percebidas em ambientes digitais a jornadas apropriadas de proteção, de forma governada, explicável, rastreável e integrável.

Um ambiente digital poderá ser um artigo, portal, aplicativo, marketplace, sistema empresarial ou outra experiência autorizada. Nesse ambiente, o SegSense permitirá publicar uma oportunidade contextual de proteção relacionada ao assunto, à situação ou ao objetivo apresentado.

Exemplo conceitual: em um artigo que trate de quebra de safra, uma chamada poderá permitir que o leitor conheça alternativas de proteção relacionadas ao contexto e, voluntariamente, inicie uma jornada de seguro.

Esse exemplo não pressupõe que a Icatu disponha atualmente de produto ou jornada para quebra de safra. A aderência ao portfólio, aos canais e aos contratos reais da seguradora deverá ser confirmada antes da disponibilização comercial.

## 3. Problema de negócio

Seguros são frequentemente apresentados de maneira genérica, desconectados do momento em que uma pessoa ou empresa percebe um risco real. Ao mesmo tempo, os ambientes digitais contêm sinais legítimos de contexto que podem ajudar o usuário a compreender uma necessidade de proteção.

Os participantes do ecossistema enfrentam dificuldades como:

- baixa contextualização da oferta;
- pouca interação cotidiana entre segurado e seguradora;
- linguagem técnica e baixa compreensão dos riscos;
- fragmentação de canais e sistemas;
- integrações custosas com plataformas tradicionais;
- necessidade de confiança, transparência e conformidade;
- dependência de dados históricos e sistemas legados;
- risco de confundir comunicação contextual com recomendação, elegibilidade ou contratação.

O desafio do SegSense é transformar um ponto de contato digital em uma entrada contextual governada para o ecossistema de seguros, sem assumir indevidamente funções reguladas e sem acoplar a experiência diretamente aos sistemas de uma seguradora.

## 4. Proposta de valor

O SegSense permitirá que canais digitais publiquem oportunidades de proteção:

- relacionadas ao conteúdo ou à situação apresentada;
- adaptadas ao canal e ao momento da jornada;
- conectadas a produtos e operações autorizados;
- rastreáveis desde a publicação até o resultado permitido;
- governadas por regras técnicas, comerciais e regulatórias;
- desacopladas das implementações específicas dos provedores.

O elemento publicado não será tratado como uma URL comercial isolada. Será uma entrada contextual identificada, versionada, governada e correlacionável com a jornada executada pela Spider.

## 5. Princípios

1. Contexto inicia uma avaliação; não determina sozinho uma recomendação.
2. A iniciativa do usuário deve ser voluntária, transparente e demonstrável.
3. O SegSense define regras e experiências do domínio de seguros.
4. A Spider interpreta, aplica políticas, planeja, resolve e executa.
5. Capabilities representam competências, não sistemas ou endpoints.
6. A Icatu é a primeira integração, não uma dependência estrutural do domínio.
7. Dados pessoais não devem ser transmitidos silenciosamente por URLs.
8. A interface deve apresentar estados e resultados reais.
9. Ausência de produto, elegibilidade ou integração deve ser exibida honestamente.
10. Toda decisão relevante deve ser rastreável e explicável.

## 6. Atores

### 6.1 Usuário

Pessoa física ou representante de pessoa jurídica que acessa o ambiente contextualizado e decide iniciar uma jornada.

### 6.2 Publicador

Organização responsável pelo site, aplicativo, portal ou outro ambiente que apresenta a chamada contextual.

### 6.3 Gestor do SegSense

Responsável por configurar publicadores, canais, ambientes, oportunidades, chamadas, vigência e regras de publicação.

### 6.4 Spider

Plataforma subjacente responsável por interpretação contextual, contratos de intenção, policies, planos, capabilities, resolução, execução, segurança operacional e continuidade.

### 6.5 Icatu Seguros

Primeiro provedor previsto para disponibilizar jornadas, produtos e operações de seguros conforme os contratos de integração que vierem a ser formalmente fornecidos.

### 6.6 Operação, segurança e compliance

Perfis responsáveis por monitoramento, auditoria, privacidade, conformidade e tratamento de exceções.

### 6.7 Participantes futuros

Corretoras, representantes, MGAs, seguradoras, resseguradoras, serviços atuariais e outros participantes poderão ser incorporados conforme o modelo operacional e regulatório aplicável.

## 7. Objeto central: oportunidade contextual

A oportunidade contextual de proteção será o principal agregado do domínio. Ela deverá representar:

- publicador e canal;
- ambiente e posição de publicação;
- assunto e contexto editorial;
- riscos ou necessidades percebidos;
- público pretendido, quando permitido;
- chamada apresentada ao usuário;
- finalidade da jornada;
- categorias ou produtos autorizados;
- vigência;
- regras comerciais e regulatórias;
- destino lógico;
- identificador de correlação;
- versão do contexto;
- situação de aprovação e publicação.

A oportunidade não deverá apontar diretamente para um endpoint técnico da Icatu. Ela deverá referenciar uma finalidade ou jornada lógica, posteriormente resolvida por meio da Spider.

## 8. Jornada inicial

1. O publicador e o ambiente digital são cadastrados.
2. Uma oportunidade contextual é criada e associada ao ambiente.
3. Conteúdo, finalidade, regras, vigência e chamada são revisados.
4. A oportunidade aprovada é publicada como link ou componente incorporável.
5. O usuário visualiza a chamada e manifesta interesse.
6. O SegSense recupera a versão exata do contexto e registra a origem.
7. A experiência explica sua finalidade e identifica os participantes relevantes.
8. O consentimento e as informações indispensáveis são obtidos progressivamente.
9. O SegSense apresenta à Spider um contrato funcional de intenção e contexto.
10. A Spider valida policies, determina o plano e resolve as capabilities.
11. A rota autorizada para a Icatu é selecionada quando disponível.
12. A jornada prossegue por redirecionamento, sessão integrada, API ou atendimento.
13. Callbacks ou consultas atualizam os estados permitidos.
14. O SegSense apresenta ao usuário e à operação somente resultados confirmados.

## 9. Fronteiras semânticas

As seguintes situações não são equivalentes:

- contexto identificado não significa perfil de risco confirmado;
- necessidade percebida não significa recomendação personalizada;
- clique não significa consentimento para compartilhar dados;
- encaminhamento não significa cotação;
- cotação não significa proposta;
- proposta não significa aceitação;
- aceitação não significa apólice emitida;
- pagamento não significa cobertura vigente sem confirmação;
- falha de retorno não significa falha ou sucesso do negócio.

Essas fronteiras deverão aparecer nos contratos, estados, eventos e interfaces.

## 10. Responsabilidades do SegSense

- administrar publicadores, canais e ambientes;
- criar, revisar, aprovar e publicar oportunidades contextuais;
- administrar chamadas e regras de exibição;
- associar contexto a finalidades de negócio;
- registrar manifestação de interesse e atribuição de origem;
- conduzir transparência e consentimento na experiência;
- coletar contexto adicional permitido;
- manter as interfaces administrativas e de usuário;
- manter os contratos funcionais com a Spider;
- acompanhar resultados comerciais permitidos;
- apresentar jornadas e falhas de maneira explicável.

## 11. Responsabilidades da Spider

- interpretar linguagem e contexto;
- produzir e validar o Intent Contract;
- aplicar Context Guard e policies determinísticas;
- selecionar o Execution Plan;
- decompor o plano em Business Capabilities;
- resolver routes e adapters;
- coordenar execução, espera, retomada, callbacks e signals;
- prover idempotência, envelopes, tokens e segurança operacional;
- emitir eventos operacionais;
- aplicar resiliência, controle de capacidade e observabilidade;
- manter a rastreabilidade da execução.

O SegSense não deverá reimplementar essas responsabilidades.

## 12. Integração inicial com a Icatu

A arquitetura deverá admitir, sem alterar o núcleo do domínio:

- redirecionamento para URL fornecida pela Icatu;
- deep link com parâmetros expressamente autorizados;
- criação de sessão no provedor;
- formulário hospedado pela Icatu;
- formulário hospedado pelo SegSense com transmissão consentida;
- operação por API;
- callback ou webhook;
- consulta de status;
- encaminhamento para atendimento humano.

A modalidade inicial dependerá da documentação técnica, dos produtos, dos ambientes, das credenciais e dos contratos efetivamente disponibilizados pela Icatu.

## 13. Capabilities candidatas

Os nomes deverão ser reconciliados com o catálogo canônico da Spider.

### 13.1 Domínio SegSense

- `REGISTER_CONTEXTUAL_ENVIRONMENT`
- `CREATE_CONTEXTUAL_OPPORTUNITY`
- `VALIDATE_PUBLICATION_CONTEXT`
- `APPROVE_CONTEXTUAL_OPPORTUNITY`
- `PUBLISH_CONTEXTUAL_ENTRY_POINT`
- `PAUSE_CONTEXTUAL_ENTRY_POINT`
- `REVOKE_CONTEXTUAL_ENTRY_POINT`

### 13.2 Jornada de seguro potencialmente reutilizável

- `RESOLVE_INSURANCE_NEED`
- `COLLECT_REQUIRED_CONTEXT`
- `CAPTURE_USER_CONSENT`
- `FIND_ELIGIBLE_INSURANCE_PRODUCTS`
- `START_INSURANCE_JOURNEY`
- `CREATE_PROVIDER_SESSION`
- `GENERATE_PROVIDER_REDIRECT`
- `GET_JOURNEY_STATUS`
- `RECEIVE_PROVIDER_CALLBACK`
- `RECORD_ATTRIBUTION`
- `PRESENT_JOURNEY_RESULT`

## 14. Link contextual

O formato externo deverá utilizar identificador opaco, por exemplo:

```text
https://<dominio-segsense>/j/<contextualEntryId>
```

O identificador será resolvido internamente para publicador, ambiente, oportunidade, versão, campanha, finalidade, vigência e regras.

O mecanismo deverá contemplar:

- assinatura ou validação equivalente;
- expiração quando aplicável;
- prevenção de adulteração;
- revogação;
- idempotência;
- rastreabilidade;
- correlação com a Spider;
- proibição de dados pessoais ou decisões sensíveis na URL.

## 15. Estados de negócio

### 15.1 Oportunidade contextual

```text
DRAFT
UNDER_REVIEW
APPROVED
PUBLISHED
PAUSED
EXPIRED
REVOKED
```

### 15.2 Jornada

```text
CONTEXT_LOADED
AWAITING_CONSENT
COLLECTING_INFORMATION
POLICY_EVALUATION
ELIGIBILITY_PENDING
PROVIDER_RESOLVED
REDIRECT_READY
JOURNEY_STARTED
AWAITING_PROVIDER
COMPLETED
NOT_ELIGIBLE
UNAVAILABLE
EXPIRED
FAILED
```

Os estados deverão ser refinados para distinguir o estado do SegSense, o estado da execução Spider e o estado declarado pelo provedor.

## 16. Interfaces

### 16.1 Console administrativo

- gestão de publicadores;
- canais e ambientes;
- oportunidades e versões;
- editor de chamadas;
- regras de publicação;
- aprovação, vigência e revogação;
- integrações;
- jornadas;
- auditoria;
- indicadores.

### 16.2 Experiência contextual do usuário

- chamada incorporada ao ambiente;
- página intermediária contextual;
- identificação da finalidade e dos participantes;
- coleta progressiva de informações;
- consentimento;
- continuidade para a Icatu;
- apresentação verdadeira do estado.

### 16.3 Visão operacional

- origem e versão do contexto;
- intent reconhecida;
- policy aplicada;
- plano selecionado;
- capabilities requeridas;
- resolução para rota e adapter;
- execução Spider;
- resposta da Icatu;
- falhas e possibilidades de retomada.

## 17. Arquitetura tecnológica

### 17.1 Tecnologias obrigatórias

- PostgreSQL para persistência;
- Java para backend e serviços de integração;
- React para interfaces web.

Frameworks, versões e bibliotecas deverão ser definidos em decisão técnica posterior.

### 17.2 Estrutura do repositório

```text
segsense/
├── frontend/
│   ├── administrative-console/
│   └── contextual-experience/
├── backend/
│   ├── domain/
│   ├── application/
│   ├── api/
│   └── infrastructure/
├── services/
│   ├── spider-integration/
│   ├── icatu-integration/
│   └── contextual-link/
├── database/
│   ├── migrations/
│   ├── seeds/
│   └── documentation/
└── README.md
```

A divisão em pastas expressa responsabilidades lógicas e não obriga a adoção imediata de microserviços. A solução poderá começar como aplicação modular, preservando fronteiras que permitam evolução posterior.

## 18. Persistência conceitual

Entidades candidatas:

- `publishers`
- `channels`
- `contextual_environments`
- `contextual_opportunities`
- `opportunity_versions`
- `placements`
- `contextual_links`
- `publication_rules`
- `journeys`
- `journey_contexts`
- `consents`
- `spider_executions`
- `provider_integrations`
- `provider_sessions`
- `provider_callbacks`
- `attributions`
- `audit_events`

Contextos, versões, consentimentos e eventos relevantes deverão preservar histórico. O desenho físico, relacionamentos, cardinalidades, índices e políticas de retenção serão definidos em documento específico.

## 19. Segurança, privacidade e conformidade

O projeto deverá contemplar desde o início:

- minimização de dados;
- finalidade explícita;
- transparência;
- consentimento quando aplicável;
- segregação entre publicadores;
- controle de acesso por função;
- proteção de credenciais e segredos;
- trilha de auditoria;
- retenção e descarte governados;
- prevenção de vazamento por URLs, logs e telemetria;
- validação de callbacks;
- proteção contra adulteração e repetição;
- revisão jurídica das jornadas, textos e papéis dos participantes.

As obrigações legais e regulatórias específicas deverão ser validadas por especialistas competentes antes de uso em produção.

## 20. Requisitos não funcionais

- rastreabilidade ponta a ponta;
- versionamento de contexto e regras;
- idempotência;
- acessibilidade;
- responsividade;
- tolerância a indisponibilidade da Spider e da Icatu;
- observabilidade sem exposição indevida de dados;
- nenhuma apresentação falsa de cotação, elegibilidade ou contratação;
- capacidade de adicionar provedores sem alterar o núcleo do domínio;
- documentação dos contratos e decisões;
- testabilidade das políticas, estados e integrações.

## 21. Primeiro recorte funcional

O primeiro ciclo deverá demonstrar:

1. cadastro de publicador;
2. cadastro de ambiente contextualizado;
3. criação, revisão e aprovação de oportunidade;
4. geração de link contextual;
5. incorporação do link em ambiente de demonstração;
6. abertura da experiência pelo usuário;
7. registro da manifestação de interesse;
8. transparência e consentimento;
9. formação do contrato com a Spider;
10. resolução da integração com a Icatu;
11. início ou redirecionamento da jornada;
12. recepção ou consulta de status, quando suportada;
13. visualização operacional ponta a ponta;
14. tratamento explícito de indisponibilidade e ausência de produto compatível.

## 22. Fora do escopo inicial

- motor atuarial próprio;
- subscrição própria;
- emissão própria de apólice;
- recebimento de prêmio;
- regulação de sinistro;
- recomendação autônoma de produto;
- marketplace com múltiplas seguradoras;
- assunção automática de papel de corretora, representante ou seguradora;
- inferência sensível ou compartilhamento oculto de dados.

## 23. Critérios de sucesso

- o publicador consegue inserir a entrada sem conhecer detalhes da integração;
- o usuário recebe experiência coerente com o contexto de origem;
- dados pessoais não são compartilhados sem fundamento e transparência;
- a Spider governa resolução e execução;
- a integração com a Icatu não contamina o núcleo do domínio;
- decisões relevantes são explicáveis e auditáveis;
- falhas não são exibidas como sucesso;
- origem, interesse e continuidade podem ser medidos;
- a solução preserva as fronteiras regulatórias definidas;
- o fluxo pode evoluir para novos canais, produtos e provedores.

## 24. Questões em aberto

1. Quais produtos e jornadas a Icatu disponibilizará?
2. Quais ambientes de homologação e produção existirão?
3. A integração inicial será redirect, sessão, API ou modelo híbrido?
4. Quais dados poderão ser recebidos e devolvidos?
5. Quais callbacks e estados serão suportados?
6. Qual participante será responsável pela distribuição e intermediação?
7. Como serão definidos remuneração, atribuição e conciliação?
8. Quais textos e chamadas precisarão de aprovação prévia?
9. Quais dados do ambiente poderão compor o contexto?
10. Quais capabilities já existem no catálogo da Spider?
11. Qual será o contrato exato entre SegSense e Spider?
12. Quais indicadores poderão ser compartilhados com cada ator?

## 25. Próximos documentos sugeridos

| Identificador sugerido | Documento |
|---|---|
| SEGSENSE_ARQ_002 | Arquitetura lógica e fronteiras de componentes |
| SEGSENSE_ARQ_003 | Contrato de integração SegSense–Spider |
| SEGSENSE_INT_001 | Integração inicial com a Icatu |

## 26. Adendo normativo — SPIDER-ARCH-017

O documento `SPIDER-ARCH-017 — Arquitetura de Aplicações Satélite e Satellite Contract` passa a ser baseline normativa do SegSense. Em caso de conflito, este adendo e o SPIDER-ARCH-017 prevalecem sobre formulações anteriores deste documento.

### 26.1 Classificação

O SegSense é o **Insurance Reference Satellite** da Spider. Ele é proprietário da experiência de domínio, do contexto legitimamente disponível, dos dados exclusivamente locais e da apresentação orientada a seguros.

### 26.2 BFF obrigatório

O backend Java/Spring Boot do SegSense exercerá o papel de **Satellite BFF**. O frontend React não poderá chamar a Spider diretamente nem armazenar credenciais técnicas da plataforma.

O BFF será responsável por autenticação e sessão do usuário, identidade do satélite, contexto do canal, correlation IDs, referências documentais, Spider Client e projeção de domínio. Ele não poderá escolher route, adapter, sistema executor ou Execution Plan, nem reproduzir a engine da Spider.

### 26.3 Contrato e manifesto

O SegSense deverá possuir `applicationId` único, Satellite Manifest e Spider Satellite Contract versionado. Conceitualmente, a requisição deverá comportar `schemaVersion`, `requestId`, `applicationId`, `channel`, `actor`, `objective`, `context`, `constraints`, `references` e `correlation`.

Este parágrafo descreve o **ideal** do padrão satélite. Em 12/09/2026 (`SEGSENSE_PRM_010`, ramo B) **não** existe Satellite Contract público, versionado e executável. SAT-03 permanece não implementado. A implementação executável está bloqueada até a Spider publicar o contrato externo (`SEGSENSE_INT_001`, `SEGSENSE_ADR_003`, `SEGSENSE_REQ_002`).

O manifesto limitará o que o SegSense pode solicitar, nunca como ou onde a operação será executada.

### 26.4 Compreensão, confirmação e execução

As jornadas deverão separar compreensão de execução:

```text
OBJETIVO → COMPREENSÃO → PREVIEW → CONFIRMAÇÃO → EXECUÇÃO
```

Contratação, mutações e ações externas relevantes exigirão confirmação conforme policies da Spider.

### 26.5 Assincronia e projeção

O SegSense deverá suportar execução assíncrona e projeções read-only da Spider. Não manterá uma segunda máquina de estados operacionais. Estados locais serão admitidos apenas para UI e dados exclusivamente pertencentes ao satélite.

Toda jornada deverá propagar, quando existentes, `requestId`, `decisionId`, `planId`, `executionId` e `interactionId`.

### 26.6 Icatu e executores

A Icatu é um executor futuro potencial de capabilities resolvidas pela Spider. Para operações pertencentes ao plano Spider, o SegSense não implementará integração direta, não escolherá a Icatu e não conhecerá sua route ou adapter.

Qualquer redirect, sessão, API ou callback da Icatu deverá ser modelado na fronteira definida pela Spider. Uma funcionalidade puramente local somente poderá permanecer no SegSense quando não exigir contexto, decisão, composição, capability empresarial, integração ou governança compartilhada.

### 26.7 Boundary atual

O boundary informado pelo SPIDER-ARCH-017 é:

```text
Runtime: SIMULATED_INFRASTRUCTURE
Integrações: MOCK_ONLY
Produção: FORA DE ESCOPO
```

Portanto, o SegSense não poderá declarar integração real com Spider ou Icatu enquanto essa fronteira não for formalmente alterada e os contratos correspondentes não forem disponibilizados.

### 26.8 Certificação mínima

Antes de ser considerado compatível, o SegSense deverá demonstrar os requisitos SAT-01 a SAT-10: identidade da aplicação, manifesto, contrato, BFF, correlação, assincronia, projeção da jornada, segurança, ausência de conhecimento de routes e independência para operações locais.

### 26.9 Independência física e de ciclo de vida

SegSense e Spider são projetos independentes. A classificação do SegSense como Spider Satellite define um padrão de integração, não incorporação de código, módulos, banco, runtime ou deployment.

```text
SegSense (aplicação independente)
        ↓ contrato de integração (ideal; não executável nesta data)
Spider (plataforma independente e inalterada pelo SegSense)
        ↓ contrato de executor, quando aplicável
Insurance Provider Mock (aplicação independente)
```

O provedor mock também deverá possuir processo, configuração, endpoints, persistência e ciclo de vida próprios. Ele não será incorporado à Spider nem tratado como módulo interno do SegSense. A integração futura deverá ocorrer somente pelas interfaces públicas e contratos aprovados de cada aplicação. A seta “contrato de integração” é o **norte arquitetural**; o runtime atual do SegSense **não** a realiza (`SEGSENSE_ARQ_003`).

### 26.10 Realidade executável após o PRM_010

A cópia `documents/references/SPIDER-ARCH-017.md` permanece `PROPOSED / ARCHITECTURAL BASELINE`. O texto vigente na Spider (`spider/docs/architecture/SPIDER-ARCH-017-satellite-architecture.md`, commit `4ba112d`, 2026-09-09) descreve o Satellite Contract como ideal **não implementado** e distingue Contextual Link e SpiderBank desse contrato. São artefatos distintos; a cópia PROPOSED **não** foi aceita pela Spider e **não** foi editada neste PRM.

Intent Contract (`intent-contract-v1.schema.json`) e schemas canônicos do Data Plane são `INTERNAL_ONLY`. Não substituem o contrato externo Satellite → Spider.

Uma futura seção comercial dedicada à Icatu Seguros deverá identificar claramente a simulação. O mock, quando houver, será aplicação independente (PRM_012/013), jamais incorporada ao SegSense ou à Spider. Isso é planejamento, não implementação desta etapa.

| SEGSENSE_FUN_001 | Jornada de publicação contextual |
| SEGSENSE_FUN_002 | Jornada do usuário e consentimento |
| SEGSENSE_DAT_001 | Modelo conceitual e governança de dados |
| SEGSENSE_UX_001 | Arquitetura de informação e experiência inicial |
| SEGSENSE_SEC_001 | Segurança, privacidade e auditoria |
| SEGSENSE_REQ_001 | Requisitos e critérios de aceite do primeiro ciclo |

## 26. Convenção documental inicial

Os documentos do SegSense deverão utilizar o padrão:

```text
SEGSENSE_<CATEGORIA>_<SEQUENCIAL>
```

Categorias iniciais:

- `ARQ`: arquitetura;
- `INT`: integrações;
- `FUN`: análise funcional e jornadas;
- `DAT`: dados;
- `UX`: experiência e interfaces;
- `SEC`: segurança e conformidade;
- `REQ`: requisitos;
- `PRM`: prompts de desenvolvimento;
- `ADR`: registros de decisão arquitetural.

Cada documento deverá conter identificação, versão, status, data, histórico de alterações, dependências e questões em aberto.
