# SPIDER-ARCH-001 — Baseline e Princípios Arquiteturais

| Campo | Valor |
|---|---|
| Identificador | SPIDER-ARCH-001 |
| Status | Baseline inicial |
| Escopo | Passo 0 do projeto Spider |
| Próxima etapa obrigatória | SPIDER-ARCH-002 — Metamodelo Contextual |

## 1. Objetivo

Estabelecer a baseline arquitetural do Spider, separando o estado atual do repositório da arquitetura-alvo inicial. Este documento registra missão, limites, conceitos, princípios e decisões em aberto. Não define implementação detalhada nem autoriza integração com legados reais.

## 2. Missão

O Spider é uma plataforma de orquestração contextual entre canais ou sistemas originadores e capacidades oferecidas por produtos, serviços e sistemas internos. Deve:

- receber uma situação-problema expressa por um contexto;
- identificar a intenção correspondente;
- resolver as capacidades necessárias;
- relacioná-las a produtos ou serviços;
- selecionar e executar jornadas e rotas técnicas de forma determinística;
- adaptar contratos canônicos às interfaces dos sistemas de destino;
- aplicar resiliência técnica e manter rastreabilidade ponta a ponta.

O Spider desacopla a linguagem contextual dos canais da heterogeneidade dos sistemas internos, sem se tornar dono dos dados ou decisões de negócio desses sistemas.

## 3. Limites e não objetivos

O Spider:

- não é System of Record de clientes, contas, contratos, limites ou transações;
- não é ERP, CRM, core bancário ou motor de crédito;
- não contém regras bancárias de elegibilidade, concessão, precificação, risco ou aprovação;
- não substitui produtos, serviços ou legados em suas responsabilidades;
- não impõe REST/HTTP como tecnologia universal;
- não pode ter sua arquitetura condicionada pelos simuladores atuais.

Sua persistência é técnica e de controle: definições versionadas, rotas, configurações, idempotência, auditoria e traces. Ela não deve evoluir para repositório de dados de negócio.

## 4. Baseline atual

### 4.1 Stack observada

| Área | Baseline atual |
|---|---|
| Backend | Java 21, Spring Boot 3.4.2 e WebFlux |
| Persistência técnica | Spring Data JPA e PostgreSQL 16 |
| Integração HTTP | WebClient |
| Resiliência | Resilience4j: circuit breaker e retry |
| Segurança de transição | JWT/JWS via jjwt |
| Contratos de API | OpenAPI 3 / Swagger UI |
| Frontend operacional | React, Vite e TypeScript/JavaScript |
| Simuladores locais | Node.js/Express |

O backend expõe atualmente `POST /v1/products/orchestrate`. O fluxo resolve uma rota de produto, traduz o payload, chama o simulador financeiro, emite um JWT de transição, registra auditoria técnica e notifica o originador por callback.

### 4.2 Persistência atual

- `tb_product_routes`: definições versionadas de rotas por produto.
- `tb_audit_trace`: correlação, idempotência, status, tempos, erros e metadados técnicos.

Essas tabelas são uma baseline técnica, não o metamodelo contextual definitivo, que será definido no SPIDER-ARCH-002.

### 4.3 Simuladores atuais

| Componente | Porta | Papel atual |
|---|---:|---|
| `service-originador` | 8081 | Inicia teste e recebe callback |
| `service-legado-financeiro` | 8082 | Simula `POST /api/legado/processar` |
| `mock-sistema-cadastro` | 8091 | Stub opcional de cadastro |
| `mock-sistema-credito` | 8092 | Stub opcional de crédito |

São instrumentos locais de desenvolvimento e teste, não referências arquiteturais.

## 5. Banco Contextual

Banco Contextual é a capacidade de traduzir uma situação-problema em uma execução técnica rastreável:

```text
Contexto → Intenção → Capacidade → Produto/Serviço → Jornada → Rota → Adapter → Legado
```

| Elemento | Responsabilidade |
|---|---|
| Contexto | Situação-problema, atores, canal, circunstâncias e dados relevantes |
| Intenção | Resultado desejado, sem antecipar solução técnica |
| Capacidade | O que a organização precisa fazer para satisfazer a intenção |
| Produto/Serviço | Oferta ou domínio que realiza capacidades |
| Jornada | Etapas e estados necessários para alcançar o resultado |
| Rota | Execução técnica determinística e versionada da jornada |
| Adapter | Tradução entre contrato canônico e tecnologia/contrato do destino |
| Legado | Execução da responsabilidade de negócio do sistema de destino |

Cardinalidades, invariantes, estados, versionamento e representação persistente serão tratados no SPIDER-ARCH-002.

## 6. Fronteira probabilística e determinística

Uma LLM poderá futuramente atuar somente como interpretador semântico probabilístico, antes da fronteira determinística. Poderá transformar linguagem natural ou contexto não estruturado em candidatos estruturados de intenção, entidades e sinais de confiança.

A LLM não deve decidir políticas bancárias, chamar legados diretamente, escolher endpoints livremente, criar rotas fora de contratos aprovados, alterar o Control Plane sem governança ou substituir validação e autorização determinísticas.

```text
Entrada contextual
       ↓
Interpretação semântica opcional (probabilística)
       ↓ saída estruturada + confiança
Validação de contrato e políticas técnicas
       ↓
Spider Engine (determinística)
```

Ambiguidade ou baixa confiança deve produzir tratamento explícito: esclarecimento, encaminhamento assistido ou rejeição segura.

## 7. Engine determinística e ausência de regra bancária

A Engine executa definições versionadas e aprovadas. Para a mesma versão de contratos, catálogo, contexto validado e estado técnico relevante, a execução deve ser explicável e reproduzível.

São responsabilidades da Engine:

- validar contratos e precondições técnicas;
- resolver definições e rotas publicadas;
- sequenciar, paralelizar e coordenar etapas;
- aplicar timeout, retry, circuit breaker, idempotência e tratamento de falha;
- controlar estados técnicos;
- produzir auditoria e correlação;
- acionar adapters por interfaces definidas.

Regras bancárias permanecem nos domínios responsáveis. O Spider pode orquestrar análise de crédito, mas não calcula score nem decide aprovação.

## 8. Comunicação universal com legados

Universalidade significa uniformidade para o núcleo, não uma tecnologia única imposta aos destinos.

```text
Spider Engine
     ↓
Contrato canônico de integração
     ├── Adapter REST/HTTP ─────► API moderna
     ├── Adapter SOAP/XML ──────► Web service
     ├── Adapter mensageria ────► Fila, tópico ou barramento
     ├── Adapter arquivo ───────► Batch ou arquivos
     ├── Adapter de dados ──────► Integração controlada por dados
     └── Adapter específico ────► RPC ou protocolo proprietário
```

Princípios:

- a Engine conhece portas e contratos canônicos, não o transporte do legado;
- o adapter encapsula payload, protocolo, autenticação, erros e semântica técnica;
- contratos são explícitos, versionados, testáveis e evolutivos;
- REST/API é uma opção, não a premissa universal;
- particularidades externas não contaminam o modelo contextual;
- simulador e integração real devem permanecer atrás da mesma fronteira contratual sempre que possível.

## 9. Estratégia de simuladores e legados

Nenhum legado real será conectado antes da fase final. Até lá serão usados endpoints, mocks, stubs e simuladores controlados, capazes de representar sucesso, falhas, latência, timeout, indisponibilidade, respostas inválidas, idempotência, cenários síncronos e assíncronos, callbacks, eventos e versões de contrato.

> Nenhuma decisão arquitetural do Spider pode depender das características particulares dos simuladores atuais. Eles são instrumentos de teste, não referência arquitetural.

Cada integração real exigirá análise própria de contrato, segurança, rede, operação, dados, resiliência e adapter, sem alterar o núcleo para acomodar particularidades locais.

## 10. Data Plane e Control Plane

### 10.1 Data Plane

É o caminho de execução em tempo de operação: recepção, validação, identidade e correlação, resolução de versões publicadas, execução determinística de jornadas e rotas, chamadas a adapters, resiliência, idempotência, respostas/eventos e produção de telemetria.

Deve favorecer previsibilidade, baixa latência, isolamento de falhas e ausência de mudanças administrativas durante a execução.

### 10.2 Control Plane

Governa os artefatos consumidos pelo Data Plane: metamodelo, catálogos, intenções, capacidades, produtos/serviços, jornadas, rotas, adapters, schemas, políticas técnicas, versões, validação, aprovação, publicação, ativação e rollback.

Artefatos são promovidos ao Data Plane por ciclo governado e versionado. O painel React/Vite atual é operacional e não representa ainda a solução definitiva do Control Plane.

## 11. Rastreabilidade, contratos abertos e neutralidade

Cada execução deve correlacionar origem, contexto, intenção, versões utilizadas, jornada, rota, etapas, adapters, tentativas, tempos, falhas, interações externas e resultado técnico, sem armazenar indevidamente dados sensíveis. Logs, métricas, traces e auditoria são complementares e devem observar minimização, mascaramento, retenção e acesso.

Contratos devem adotar especificações públicas e formatos interoperáveis quando adequados, como OpenAPI, AsyncAPI, JSON Schema, CloudEvents ou equivalentes. “Aberto” significa documentado, portável, versionado e independente de fornecedor, não exposição pública irrestrita.

Modelos centrais não dependem de frameworks, infraestrutura, protocolos ou fornecedores. A stack atual é baseline de execução, não restrição conceitual perpétua.

## 12. Arquitetura-alvo inicial

```text
Canais / Originadores
        ↓
Entrada e contratos contextuais
(segurança, validação, idempotência, correlação)
        ↓
Interpretador semântico opcional e probabilístico
        ↓ fronteira validada
Data Plane determinístico
Contexto → Intenção → Capacidade → Produto/Serviço → Jornada → Rota
        ↓ contrato canônico
Adapters: REST | SOAP | Mensageria | Arquivo | Dados | Específico
        ↓
Simuladores no desenvolvimento → Legados reais somente na fase final

Control Plane
(catálogos, metamodelo, contratos, versões, aprovação, publicação e rollback)
        └──────── publica versões imutáveis para o Data Plane

Segurança, governança e rastreabilidade são transversais.
```

Os blocos não implicam serviços físicos separados. Limites de implantação serão definidos por requisitos, riscos e evidências operacionais.

## 13. Princípios consolidados

1. Contexto expressa a situação-problema; intenção expressa o resultado desejado.
2. Intenção, capacidade, produto/serviço, jornada e rota têm responsabilidades separadas.
3. A Engine é determinística, explicável e orientada por versões aprovadas.
4. O Spider não implementa regras bancárias nem se torna System of Record.
5. Componentes probabilísticos são opcionais e anteriores à fronteira determinística.
6. A comunicação universal usa contrato canônico e adapters, sem impor REST.
7. Legados reais somente na fase final; antes disso, simuladores contratuais.
8. Simuladores atuais não condicionam a arquitetura.
9. Data Plane e Control Plane possuem responsabilidades e ciclos distintos.
10. Execuções e mudanças administrativas relevantes são rastreáveis.
11. Contratos são explícitos, abertos, versionados e testáveis.
12. O núcleo preserva neutralidade tecnológica.
13. Segurança, privacidade, minimização e observabilidade são transversais.
14. Mudanças admitem validação, aprovação, publicação e rollback.

## 14. Decisões em aberto

| Tema | Questão a decidir |
|---|---|
| Metamodelo | Entidades, atributos, relações, cardinalidades, invariantes e taxonomias |
| Resolução | Algoritmo, prioridades e conflitos entre contexto, intenção, capacidade e jornada |
| Semântica probabilística | Confiança, ambiguidade, explicabilidade e eventual revisão humana |
| Contrato canônico | Envelope, schemas, erros, comandos, consultas, eventos e versões |
| Jornadas e rotas | Linguagem, máquina de estados, compensação e falha parcial |
| Execução | Síncrono, assíncrono, eventos, callbacks e processos longos |
| Adapters | Portas internas, framework, capacidades e testes de conformidade |
| Control Plane | Aprovação, segregação, publicação, rollback e ambientes |
| Persistência | Modelo definitivo, histórico, retenção, cache e consistência |
| Segurança | Identidade, autorização, credenciais, secrets e não repúdio |
| Observabilidade | Trace, métricas, logs, auditoria, mascaramento e retenção |
| Idempotência | Escopo, janela, replay e garantias por integração |
| Resiliência | Políticas, backpressure, rate limit, timeout e bulkhead |
| Topologia | Monólito modular versus serviços e critérios de decomposição |
| Dados | Classificação, minimização, LGPD, residência e descarte |
| Integração final | Inventário, priorização e certificação dos legados reais |

## 15. Organização documental e próximos artefatos

Documentos arquiteturais seguem `SPIDER-ARCH-NNN` em `docs/architecture/`.

Prompts futuros para o Cursor serão documentos separados, com sequência própria: `SPIDER-PROMPT-001`, `SPIDER-PROMPT-002` etc. Serão armazenados em estrutura documental específica quando criados. Um prompt não substitui decisão arquitetural e não deve ser incorporado a este documento.

Antes de qualquer implementação futura, a próxima etapa obrigatória é:

> **SPIDER-ARCH-002 — Metamodelo Contextual**

O SPIDER-ARCH-002 detalhará semântica, relações, cardinalidades, estados, versionamento e invariantes da cadeia Contexto → Intenção → Capacidade → Produto/Serviço → Jornada → Rota, preservando Adapter e Legado como fronteira de integração.
