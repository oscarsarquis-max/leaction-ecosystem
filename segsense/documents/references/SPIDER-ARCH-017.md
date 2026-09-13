# SPIDER-ARCH-017 — ARQUITETURA DE APLICAÇÕES SATÉLITE E SATELLITE CONTRACT

**Status:** PROPOSED / ARCHITECTURAL BASELINE  
**Projeto:** Spider  
**Classificação:** Arquitetura de Plataforma / Integração de Canais  
**Predecessores principais:** `SPIDER-ARCH-014`, `015`, `016`  
**Primeiro satélite de referência:** Seguros  
**Boundary atual do Spider:** `SIMULATED_INFRASTRUCTURE / MOCK_ONLY`

---

## 1. Objetivo

Este documento define a arquitetura padrão para aplicações externas que utilizem o Spider como plataforma contextual, de planejamento, composição e execução de capacidades empresariais.

Essas aplicações serão denominadas:

# SPIDER SATELLITES

Um Spider Satellite é uma aplicação orientada a um domínio ou experiência específica — por exemplo:

- Seguros;
- Crédito;
- Investimentos;
- Projetos;
- Atendimento;
- Cobrança;
- canais corporativos;
- portais;
- aplicativos móveis;
- plataformas externas.

O satélite **não incorpora o Core do Spider**.

Ele utiliza o Spider através de um contrato estável e governado.

---

# 2. Princípio arquitetural

A aplicação satélite é responsável por:

> **experiência de domínio, contexto do usuário e apresentação do resultado.**

O Spider é responsável por:

> **compreensão contextual, decisão determinística, planejamento, composição de capacidades, resolução, execução e auditabilidade.**

Portanto:

```text
SATÉLITE
   ↓
objetivo + contexto
   ↓
SPIDER
   ↓
Intent
   ↓
Policy
   ↓
Execution Plan
   ↓
Business Capabilities
   ↓
Capability Resolution
   ↓
Routes / Adapters
   ↓
Execução
   ↓
resultado + jornada
   ↓
SATÉLITE
```

---

# 3. Regra de separação

O satélite NÃO deve replicar:

- Context Interpreter;
- Intent Router;
- Context Guard;
- Execution Plan Resolver;
- Business Capability Catalog;
- Capability Resolver;
- Route Resolver;
- orchestration engine;
- retry/backpressure;
- runtime;
- observabilidade operacional.

Esses elementos pertencem ao Spider.

---

# 4. Responsabilidades do satélite

Uma aplicação satélite pode possuir:

### Experiência do usuário

- páginas;
- formulários;
- assistentes;
- cards de objetivos;
- dashboards;
- documentos;
- notificações;
- navegação do domínio.

### Contexto

- usuário autenticado;
- empresa;
- sessão;
- canal;
- produto;
- entidade atualmente selecionada;
- referências a documentos.

### Dados locais

Dados que pertencem exclusivamente à experiência do satélite e não precisam constituir estado operacional do Spider.

### Apresentação

Transformação da projeção retornada pelo Spider em linguagem adequada ao domínio.

---

# 5. Arquitetura de referência

```text
┌──────────────────────────────────────────┐
│          SPIDER SATELLITE                │
│                                          │
│  DOMAIN EXPERIENCE                       │
│  Forms / Cards / Objective Input         │
│  Documents / Results / Journey           │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│           SATELLITE BFF                  │
│                                          │
│  Authentication / Session                │
│  User Context                            │
│  Satellite Identity                      │
│  Spider Client                           │
│  Correlation                             │
│  Document References                     │
│  Domain Projection                       │
└──────────────────┬───────────────────────┘
                   │
          SPIDER SATELLITE CONTRACT
                   │
                   ▼
════════════════ SPIDER BOUNDARY ════════════════
                   │
                   ▼
┌──────────────────────────────────────────┐
│         SATELLITE INGRESS                │
│                                          │
│ Authentication                           │
│ Satellite Manifest                       │
│ Contract Validation                      │
│ Policy / Security                        │
│ Capacity / Admission                     │
└──────────────────┬───────────────────────┘
                   │
                   ▼
          CONTEXT INTELLIGENCE
                   │
                   ▼
             INTENT CONTRACT
                   │
                   ▼
              CONTEXT GUARD
                   │
                   ▼
             EXECUTION PLAN
                   │
                   ▼
          BUSINESS CAPABILITIES
                   │
                   ▼
          CAPABILITY RESOLVER
                   │
                   ▼
             ROUTES / ADAPTERS
                   │
                   ▼
               DATA PLANE
```

---

# 6. Backend for Frontend obrigatório

A arquitetura recomendada é:

```text
Browser / App
     ↓
Satellite BFF
     ↓
Spider
```

Evitar:

```text
Browser
     ↓
Spider diretamente
```

O BFF protege a fronteira técnica e mantém credenciais da plataforma fora do frontend.

---

# 7. Responsabilidades do BFF

O Satellite BFF deve tratar, no mínimo:

- autenticação do usuário;
- sessão;
- identidade do satélite;
- correlation IDs;
- contexto do canal;
- chamadas ao Spider;
- referências de documentos;
- projeções orientadas à experiência.

O BFF NÃO deve:

- escolher sistema;
- escolher route;
- construir Execution Plan;
- reproduzir Business Capability Resolver;
- executar orchestration empresarial própria quando a responsabilidade for do Spider.

---

# 8. Spider Satellite Contract

Criar um contrato estável entre Satélite e Spider.

Conceitualmente:

```text
SatelliteRequest
```

contendo:

```text
schemaVersion
requestId
applicationId
channel
actor
objective
context
constraints
references
correlation
```

---

# 9. Objective

O campo `objective` representa o objetivo declarado pelo usuário ou produzido por uma interação determinística da aplicação.

Exemplo:

```text
"Quero proteger minha empresa contra incêndio,
roubo e danos aos equipamentos."
```

O satélite não precisa converter essa declaração em route.

---

# 10. Context

O contexto pode conter informações explicitamente disponíveis ao satélite.

Exemplo:

```text
customerId
companyId
productId
policyId
claimId
selectedAssetId
```

Somente dados necessários devem ser enviados.

---

# 11. Actor

O Spider deve distinguir:

```text
usuário
≠
aplicação
≠
canal
```

Conceitualmente:

```text
actor:
  subjectId
  roles

origin:
  applicationId
  channel
```

Isso suporta:

- policy;
- autorização;
- auditabilidade;
- provenance.

---

# 12. Satellite Manifest

Cada aplicação satélite deve possuir manifesto próprio.

Exemplo:

```text
applicationId:
INSURANCE_PORTAL

domains:
INSURANCE
CUSTOMER

allowedOperationClasses:
READ
SIMULATE
REQUEST

mutationPolicy:
CONFIRMATION_REQUIRED
```

---

# 13. Satellite Manifest não define Route

O manifesto determina **o que o satélite está autorizado a solicitar**, não como a solicitação será executada.

Nunca:

```text
INSURANCE_PORTAL
→ SYSTEM_X
```

Correto:

```text
INSURANCE_PORTAL
→ allowed domain/capability class
→ Spider determines execution
```

---

# 14. Resposta de compreensão

Após receber o objetivo, o Spider pode retornar um objeto conceitualmente equivalente a:

```text
SpiderDecision
```

contendo:

```text
decisionId
intent
understanding
policyDecision
executionPlan
capabilities
missingContext
confirmationRequired
executionAvailability
```

---

# 15. Separar compreender de executar

Uma aplicação satélite deve suportar:

```text
OBJETIVO
   ↓
SPIDER ENTENDEU
   ↓
PREVIEW
   ↓
CONFIRMAÇÃO
   ↓
EXECUÇÃO
```

Especialmente quando houver:

- mutação;
- contratação;
- operação financeira;
- criação de registro;
- ação externa relevante.

---

# 16. Execução

Após confirmação, o Spider retorna ou disponibiliza:

```text
executionId
```

A aplicação acompanha o processamento utilizando projeções read-only do Spider.

---

# 17. Modelo assíncrono obrigatório

Uma aplicação satélite não deve assumir execução síncrona imediata.

Deve suportar:

```text
ACCEPTED
   ↓
PROCESSING
   ↓
WAITING
   ↓
RESUMED
   ↓
COMPLETED
```

ou:

```text
FAILED
PARTIAL
NOT_EXECUTABLE
```

conforme a execução real.

---

# 18. Jornada do satélite

O satélite NÃO deve inventar seu próprio estado operacional.

Ele deve receber projeção do Spider.

Exemplo orientado ao usuário:

```text
✓ Entendemos sua necessidade
✓ Verificamos as regras
✓ Definimos o plano
◉ Consultando coberturas
○ Obtendo propostas
○ Preparando opções
```

---

# 19. Duas projeções da mesma execução

A mesma execução pode possuir:

### Spider Console

Visão técnica:

- Intent;
- Policy;
- Plan;
- Capability;
- Route;
- Adapter;
- Worker;
- Operational Events;
- Interaction;
- Retry.

### Satellite Experience

Visão de negócio:

- necessidade compreendida;
- avaliação em andamento;
- informações necessárias;
- opções encontradas;
- resultado.

Ambas derivam do mesmo estado.

---

# 20. Regra de não duplicação

O satélite não mantém uma segunda máquina de estados da execução.

Pode manter estado local de UI, mas não reproduzir a verdade operacional do Spider.

---

# 21. Business Cards

Um satélite pode possuir atalhos determinísticos.

Exemplo Seguros:

```text
Comunicar sinistro
Renovar apólice
Comparar coberturas
Proteger minha empresa
```

O card pode produzir uma intenção conhecida.

Mas ainda deve convergir para os contratos do Spider.

---

# 22. Linguagem natural

Quando o usuário declarar livremente:

> "Bateram no carro da empresa e quero saber o que faço."

o satélite envia o objetivo ao Context Intelligence Plane.

Não deve executar interpretação independente se o Spider for responsável pelo Context Plane.

---

# 23. Documentos

Documentos não devem ser transportados indiscriminadamente dentro do Intent Contract.

Preferir referências:

```text
DocumentReference

documentId
type
classification
owner
source
```

O acesso ao conteúdo é governado separadamente.

---

# 24. Segurança

São requisitos obrigatórios:

- autenticação do satélite;
- autenticação/identidade do usuário;
- autorização;
- Satellite Manifest;
- policy;
- correlation;
- redaction;
- minimização de dados;
- mutation safety;
- no-enumeration quando aplicável;
- auditabilidade.

---

# 25. Confiança Zero na fronteira

O Spider não considera uma requisição confiável apenas porque veio de um satélite conhecido.

Toda solicitação continua sujeita a:

```text
Authentication
→ Contract Validation
→ Policy
→ Guard
→ Plan
→ Capability Resolution
```

---

# 26. Observabilidade

Toda solicitação satélite deve poder ser correlacionada através de:

```text
requestId
decisionId
planId
executionId
interactionId
```

quando os respectivos objetos existirem.

---

# 27. Falha do Spider

O satélite deve tratar indisponibilidade da plataforma de forma explícita.

Não apresentar sucesso quando:

- Context Plane indisponível;
- Intent rejeitado;
- plano não executável;
- capability indisponível;
- execução falhar.

---

# 28. Funcionalidades locais

Nem toda ação de um satélite precisa passar pelo Spider.

Exemplos:

- preferências de interface;
- navegação;
- conteúdo institucional;
- ajuda;
- cache de UX;
- dados exclusivamente locais.

Regra:

> Use o Spider quando houver necessidade de contexto, decisão, composição, capacidade empresarial, integração, execução ou governança compartilhada.

---

# 29. Primeiro satélite de referência — Seguros

Cenário:

> "Tenho uma pequena empresa e quero proteger o negócio contra incêndio, roubo e danos a equipamentos, mas não sei qual seguro preciso."

Fluxo:

```text
Insurance Satellite
        ↓
Objective
        ↓
Spider
        ↓
ASSESS_BUSINESS_INSURANCE_NEEDS
        ↓
BUSINESS_INSURANCE_ASSESSMENT_V1
        ↓
Business Capabilities
```

---

# 30. Capabilities conceituais de Seguros

Exemplo inicial:

```text
IDENTIFY_CUSTOMER
GET_CUSTOMER_PROFILE
IDENTIFY_BUSINESS_PROFILE
ASSESS_RISK_EXPOSURE
IDENTIFY_REQUIRED_COVERAGES
FIND_ELIGIBLE_INSURANCE_PRODUCTS
GET_INSURANCE_QUOTES
COMPARE_COVERAGES
PRESENT_OPTIONS
```

Essas capabilities não implicam existência atual de integrações reais.

---

# 31. Sistemas de Seguros

Uma capability futura pode resolver para diferentes executores:

```text
GET_INSURANCE_QUOTES
        ↓
Capability Resolver
        ├── Insurer A
        ├── Insurer B
        ├── Broker
        ├── Internal System
        └── Marketplace
```

A aplicação satélite não conhece essa seleção.

---

# 32. ServiceNow

ServiceNow pode participar futuramente como:

- satélite;
- origem de objetivo;
- executor de capability;
- target através de adapter;
- superfície operacional.

Ele não substitui o Spider Core.

---

# 33. Requisitos mínimos de certificação de um Spider Satellite

Uma aplicação só deve ser considerada compatível com o padrão Spider Satellite quando atender a:

### SAT-01 — Application Identity

Possuir `applicationId` único.

### SAT-02 — Manifest

Possuir Satellite Manifest.

### SAT-03 — Contract

Usar Spider Satellite Contract.

### SAT-04 — BFF

Proteger comunicação técnica atrás de backend controlado.

### SAT-05 — Correlation

Propagar correlação ponta a ponta.

### SAT-06 — Async

Suportar execução assíncrona.

### SAT-07 — Journey Projection

Projetar estado real do Spider.

### SAT-08 — Security

Respeitar Guard/Policy/permissions.

### SAT-09 — No Route Knowledge

Não acoplar frontend a routes/adapters internos.

### SAT-10 — Independence

Não utilizar o Spider para operações puramente locais sem necessidade.

---

# 34. Stack de referência

A arquitetura não obriga tecnologia específica.

Baseline recomendado para satélites web:

```text
Frontend
React / TypeScript

BFF
Java / Spring Boot
ou
Node
ou
Python

Communication
HTTPS / canonical Spider Satellite Contract
```

A stack pode variar desde que o contrato seja preservado.

---

# 35. Deployment

O satélite deve possuir ciclo de deployment independente do Spider.

```text
Satellite Deployment
        ≠
Spider Deployment
```

Uma atualização visual do satélite não deve exigir deploy do Spider.

Uma evolução interna do Spider que preserve o contrato não deve exigir deploy do satélite.

---

# 36. Versionamento

O Satellite Contract deve ser versionado.

Mudanças incompatíveis exigem nova versão.

Não quebrar satélites existentes silenciosamente.

---

# 37. Anti-patterns

São proibidos:

### Satélite chamando legados diretamente para operações pertencentes ao plano Spider

### Satélite implementando seu próprio Intent Router

### Satélite duplicando Context Guard

### Satélite escolhendo ServiceNow/SAP/Mainframe diretamente com base no Intent

### Frontend armazenando credenciais técnicas do Spider

### Satélite inventando progresso operacional

### BFF transformando-se em segunda engine

---

# 38. Modelo final

```text
                EXPERIENCE ECOSYSTEM

   Seguros
      │
   Crédito
      │
   Projetos
      │
   Investimentos
      │
   ServiceNow
      │
   Outros Canais
      │
      ▼
┌──────────────────────────────┐
│ SPIDER SATELLITE CONTRACT    │
│                              │
│ Objective                    │
│ Context                      │
│ Actor                        │
│ Constraints                  │
│ Correlation                  │
└──────────────┬───────────────┘
               │
               ▼
       CONTEXT INTELLIGENCE
               │
               ▼
          INTENT CONTRACT
               │
               ▼
             GUARD
               │
               ▼
        EXECUTION PLAN
               │
               ▼
     BUSINESS CAPABILITIES
               │
               ▼
      CAPABILITY RESOLUTION
               │
               ▼
        ROUTES / ADAPTERS
               │
               ▼
           DATA PLANE
```

---

# 39. Decisão arquitetural

Fica estabelecido:

> **Aplicações satélite utilizam o Spider como plataforma compartilhada de inteligência contextual, planejamento, composição, resolução e execução de capacidades empresariais.**

> **O satélite é proprietário da experiência de domínio. O Spider é proprietário da decisão e execução contextual compartilhada.**

---

# 40. Impacto no Espelho Funcional

Atualizar o `SPIDER-ARCH-014` futuramente para acrescentar uma camada anterior ao Experience Plane:

```text
DOMAIN SATELLITES
        ↓
SATELLITE CONTRACT
        ↓
SPIDER EXPERIENCE / CONTEXT
        ↓
SPIDER CORE
```

---

# 41. Boundary atual

Este documento define arquitetura.

Não declara aplicações satélite reais em produção.

Estado atual permanece:

```text
Runtime: SIMULATED_INFRASTRUCTURE
Integrações: MOCK_ONLY
Produção: FORA DE ESCOPO
```

---

# 42. Próxima etapa recomendada

O primeiro uso desta arquitetura deve ser a construção de um:

# INSURANCE REFERENCE SATELLITE

como implementação de referência do padrão definido neste documento.

Antes de implementar integrações reais, validar:

- Satellite Contract;
- BFF;
- Satellite Manifest;
- Objective submission;
- Context preview;
- execution confirmation;
- async journey;
- result projection;
- security;
- correlation.

---

# 43. Regra de governança

A partir deste documento:

> Novas aplicações de domínio não devem criar integração ad hoc com o Spider.

Toda nova aplicação deve avaliar aderência ao padrão:

`SPIDER SATELLITE ARCHITECTURE`.

---

**Fim — SPIDER-ARCH-017**