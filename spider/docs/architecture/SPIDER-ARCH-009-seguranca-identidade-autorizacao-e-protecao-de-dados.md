# SPIDER-ARCH-009 — Segurança, Identidade, Autorização e Proteção de Dados

| Campo | Valor |
|---|---|
| Identificador | SPIDER-ARCH-009 |
| Título | Segurança, Identidade, Autorização e Proteção de Dados |
| Status | Proposta arquitetural inicial |
| Predecessor | SPIDER-ARCH-008 — Persistência Técnica, Idempotência, Evidências e Retenção |
| Escopo | Especificação lógica normativa, sem implementação |

## 1. Objetivo

Formalizar a arquitetura de segurança do Spider, abrangendo identidades de originadores, atores, workloads e operadores; autenticação; delegação; autorização contextual; confiança entre zonas; proteção de transporte e mensagem; gestão de credenciais e secrets; minimização; classificação; mascaramento; privacidade; prevenção de replay; não repúdio; auditoria e resposta a incidentes.

Os controles definidos são transversais ao Contexto, Control Plane, Data Plane, Engine, Adapters, persistência, callbacks, eventos, arquivos, operação e evidências.

Este documento não escolhe provedor de identidade, PKI, KMS, HSM, vault, API gateway, service mesh, WAF, SIEM, protocolo de token ou produto de segurança. Também não autoriza integração com legados reais, uso de identidades reais ou processamento de dados pessoais reais nesta fase.

## 2. Vocabulário normativo

Os termos “deve”, “não deve” e “somente” expressam requisitos arquiteturais. “Pode” expressa possibilidade admitida.

- **Principal**: identidade autenticável que solicita ou executa uma ação.
- **Originador**: sistema, canal ou componente que inicia uma solicitação ao Spider.
- **Ator**: pessoa ou entidade de negócio em cujo contexto uma ação é solicitada.
- **Workload**: componente técnico executável com identidade própria.
- **Operador**: identidade humana autorizada a realizar ações administrativas ou operacionais.
- **Delegação**: autorização limitada para um principal agir em nome de outro.
- **Security Context**: conjunto autenticado e validado de identidades, atributos, delegações, zona e evidências de confiança.
- **Policy Decision Point (PDP)**: capacidade lógica que avalia política de autorização.
- **Policy Enforcement Point (PEP)**: fronteira lógica que aplica a decisão.
- **Zona de confiança**: domínio com controles, owner e nível de confiança explicitamente definidos.
- **Secret**: material confidencial que permite autenticação, assinatura, criptografia ou acesso.
- **Dado pessoal**: informação relacionada a pessoa natural identificada ou identificável.
- **Dado sensível**: dado que exige proteção reforçada por classificação, contexto ou obrigação aplicável.

## 3. Decisões centrais

1. Segurança é transversal e aplicada em múltiplas fronteiras; não é responsabilidade isolada do gateway.
2. Toda chamada, mensagem, callback, arquivo ou ação administrativa possui principal autenticado ou é rejeitada.
3. Identidade do originador, identidade do ator, identidade do workload e identidade do operador são distintas.
4. Presença de identificador no payload não constitui autenticação.
5. Autorização é explícita, contextual, negada por padrão e reavaliada nas fronteiras relevantes.
6. Delegação possui cadeia, escopo, finalidade, prazo e evidência verificáveis.
7. A Engine recebe Security Context validado; não interpreta credenciais específicas de canal ou legado.
8. Secrets e credenciais nunca integram contratos, rotas, planos, logs ou evidências abertas.
9. Proteção de dados segue minimização, finalidade, necessidade, acesso mínimo e retenção limitada.
10. Nesta fase são permitidas apenas identidades de teste, dados sintéticos, Mocks e simuladores isolados.

## 4. Modelo de ameaças inicial

O modelo deve considerar, no mínimo:

- falsificação de originador, workload, callback ou operador;
- elevação de privilégio e uso indevido de delegação;
- replay de request, sinal, evento, arquivo ou callback;
- alteração de mensagem, rota, binding, policy ou evidência;
- exfiltração por payload, log, trace, erro, callback ou exportação;
- redirecionamento de Adapter para destino não autorizado;
- injeção em mapping, expressão, contrato ou configuração;
- confusão entre identidade técnica e identidade de ator;
- abuso de idempotência para consultar resultado alheio;
- enumeração por identificadores previsíveis;
- uso indevido de ferramentas operacionais;
- comprometimento de supply chain, runtime ou artefato publicado;
- negação de serviço e esgotamento de recursos;
- acesso persistente por secret não rotacionado;
- perda de integridade ou disponibilidade de trilhas de auditoria.

O modelo de ameaças deve evoluir por fluxo, perfil de integração, classificação de dados e ambiente.

## 5. Arquitetura de confiança

```text
Canal / Originador
        ↓ autenticação + autorização de entrada
Fronteira de Ingress do Spider
        ↓ Security Context normalizado
Engine determinística
        ↓ autorização de capacidade e step
Porta Universal Engine–Adapter
        ↓ identidade de workload + perfil de segurança
Adapter
        ↓ credencial específica e proteção do perfil
Mock nesta fase / Legado real somente na fase final

Control Plane
        ↓ autoria, aprovação, assinatura e publicação segregadas
Snapshots íntegros
        ↓ validação pelo Data Plane
Execução com release e policies fixadas
```

Cada seta representa mudança de confiança e exige controles explícitos. Confiança não é transitiva por simples localização de rede.

## 6. Tipos de identidade

| Tipo | Exemplos lógicos | Regra |
|---|---|---|
| Originador | canal assistido, aplicação, parceiro ou serviço | Autenticado na entrada e autorizado por capability |
| Ator | cliente, colaborador, representante ou procurador | Referenciado e vinculado à delegação quando aplicável |
| Workload | Engine, Adapter, scheduler ou worker | Identidade própria, curta duração e menor privilégio |
| Operador | suporte, SRE, auditor ou administrador | Identidade individual, autenticação reforçada e ação auditada |
| Control Plane service | validador, publisher ou distributor | Separado do Data Plane e limitado ao ciclo administrativo |
| Destino | Mock ou, na fase final, legado | Identidade verificada pelo Adapter conforme perfil |

Uma identidade não pode ser reutilizada para tipos distintos apenas por conveniência operacional.

## 7. Principal Descriptor

```text
PrincipalDescriptor
├── principalId
├── principalType
├── issuerRef
├── authenticationMethodRef
├── assuranceLevel
├── authenticatedAt
├── validUntil
├── tenantOrDomainRef?
├── authorizedAttributeRefs[]
└── evidenceRef
```

`principalId` é referência opaca e estável dentro do issuer. A Engine não deve extrair organização, papel ou autorização do formato do identificador.

## 8. Security Context

```text
SecurityContext
├── contextId
├── originatorPrincipal
├── workloadPrincipal
├── actorRefs[]
├── delegationChainRef?
├── authenticatedAt
├── assuranceLevel
├── trustZoneRef
├── authorizationContextRef
├── consentOrPurposeRefs[]
├── dataClassificationCeiling
├── expiresAt
└── securityEvidenceRefs[]
```

O Security Context é produzido após autenticação e validação. Ele contém referências e atributos necessários, não credenciais brutas.

O contexto é imutável durante uma decisão específica. Mudança de principal, delegação, escopo ou assurance exige novo contexto e nova autorização.

## 9. Autenticação

### 9.1 Requisitos gerais

- validar emissor, destinatário, assinatura, validade e método;
- verificar revogação ou estado de credencial quando aplicável;
- impedir downgrade de método ou assurance;
- diferenciar autenticação humana, workload e sistema externo;
- associar a evidência ao Security Context;
- rejeitar credenciais ambíguas, expiradas ou fora de escopo;
- evitar credenciais de longa duração em workloads;
- aplicar autenticação reforçada a ações críticas.

### 9.2 Originadores

Cada originador deve ser registrado e possuir métodos, capabilities, ambientes, limites e owners aprovados. Canal não cadastrado ou incompatível com a operação deve ser rejeitado antes da resolução de rota.

### 9.3 Workloads

Workloads devem usar identidade própria e verificável. Secret compartilhado entre múltiplos componentes impede atribuição adequada e é proibido.

Credenciais devem ser emitidas por workload, ambiente e finalidade, preferencialmente com curta duração e rotação automatizada.

### 9.4 Operadores

Operadores devem usar identidade individual. Ações críticas exigem autenticação reforçada, sessão de curta duração, reautenticação quando aplicável e segregação de funções.

Conta genérica de suporte ou administração é proibida.

## 10. Delegação

### 10.1 Delegation Descriptor

```text
DelegationDescriptor
├── delegationId
├── delegatorRef
├── delegateRef
├── actorRef
├── purpose
├── allowedCapabilities[]
├── constraints[]
├── issuedAt
├── notBefore
├── expiresAt
├── issuerRef
├── chainRef?
└── evidenceRef
```

### 10.2 Regras

1. Delegação é explícita e negada por padrão.
2. Escopo delegado não pode exceder autoridade do delegador.
3. Cadeia deve ser limitada, verificável e livre de ciclos.
4. Finalidade e prazo são obrigatórios.
5. Subdelegação somente ocorre quando expressamente permitida.
6. Revogação deve ser observável dentro do risco e SLA definidos.
7. A Engine não cria delegação a partir de campo livre do payload.
8. Evidência da delegação acompanha decisões sem expor documento sensível completo.

## 11. Autorização

### 11.1 Princípios

- deny by default;
- menor privilégio;
- separação entre autenticação e autorização;
- avaliação por capability e operation, não por endpoint físico;
- contexto, finalidade, ambiente e classificação considerados;
- decisão determinística, versionada e auditável;
- resultado limitado a `PERMIT`, `DENY`, `NOT_APPLICABLE` ou `INDETERMINATE`;
- `INDETERMINATE` falha de modo seguro.

### 11.2 Authorization Request

```text
AuthorizationRequest
├── subjectRefs[]
├── originatorRef
├── workloadRef
├── action
│   ├── capabilityCode
│   └── operationCode
├── resourceRefs[]
├── environment
├── purposeRefs[]
├── dataClassifications[]
├── delegationRef?
├── routeAndStepRefs?
└── policySetRef
```

### 11.3 Authorization Decision

```text
AuthorizationDecision
├── decisionId
├── result
├── policySetRef
├── evaluatedAt
├── expiresAt
├── obligations[]
├── advice[]
├── reasonCode
└── evidenceRef
```

Obligations são controles obrigatórios, como mascarar campo, limitar output, exigir callback protegido ou registrar evidência reforçada. Advice não pode ser usado para contornar obrigação.

## 12. Pontos de decisão e enforcement

| Fronteira | Enforcement mínimo |
|---|---|
| Ingress | Autenticar originador, validar Security Context e autorizar capability |
| Resolução | Restringir catálogos, jornadas e rotas ao escopo autorizado |
| Planejamento | Fixar policies e bindings compatíveis com classificação |
| Step | Confirmar autorização de operação e obligations |
| Adapter | Aplicar credencial, destino e proteção do binding |
| Callback/sinal | Autenticar peer, validar contrato, correlação e replay |
| Evidência | Autorizar consulta, exportação e dados revelados |
| Control Plane | Autorizar autoria, aprovação, ativação e rollback |
| Operação | Autorizar intervenção, reconciliação e cancelamento |

Uma decisão na entrada não elimina enforcement posterior quando recurso, step, destino ou classificação se tornam conhecidos.

## 13. Autorização contextual sem regra bancária

Políticas do Spider controlam quem pode solicitar e executar uma capability técnica, em qual ambiente, com qual finalidade e classificação. Elas não decidem elegibilidade bancária, crédito, limite, preço, risco ou aprovação.

Exemplo permitido: originador X pode acionar a capability `CONSULTAR_LANCAMENTO` em ambiente Y para finalidade Z.

Exemplo proibido: cliente com renda maior que valor definido é elegível ao produto. Essa decisão pertence ao domínio de negócio responsável.

## 14. Zonas de confiança

```text
TrustZone
├── zoneCode
├── ownerRef
├── environmentClass
├── assuranceRequirements
├── acceptedIssuerRefs[]
├── networkPolicyRef
├── traceTrustPolicyRef
├── dataClassificationLimit
├── ingressProfileRefs[]
├── egressProfileRefs[]
└── monitoringPolicyRef
```

Mudança de zona exige autenticação e autorização novas ou validação explícita da continuidade. Presença em rede interna não concede confiança automática.

O fluxo entre Control Plane, Data Plane, Adapters, simuladores e stores deve possuir zonas declaradas e owners.

## 15. Segurança de transporte

Todo transporte deve proteger confidencialidade, integridade e identidade dos peers conforme risco.

Requisitos lógicos:

- protocolos e algoritmos aprovados;
- autenticação unilateral ou mútua conforme perfil;
- validação de certificado ou identidade equivalente;
- hostname ou endpoint identity verificada quando aplicável;
- prevenção de downgrade;
- renovação e rotação;
- revogação e expiração;
- limites de payload e conexão;
- proteção contra redirecionamento indevido;
- evidência de falha sem expor material criptográfico.

TLS e mTLS são possibilidades adequadas para vários perfis, não abstrações universais para mensageria, arquivo ou protocolo proprietário.

## 16. Segurança de mensagem

Quando proteção de transporte não for suficiente, mensagens podem exigir assinatura, criptografia, autenticação de origem, timestamp e nonce.

```text
MessageSecurityDescriptor
├── securityProfileRef
├── signerRef?
├── recipientRef?
├── signatureAlgorithmRef?
├── encryptionAlgorithmRef?
├── keyRef?
├── issuedAt
├── expiresAt
├── nonce?
└── canonicalizationRef
```

A representação assinada deve ser canônica e versionada. Re-serialização não pode invalidar ou alterar significado silenciosamente.

## 17. Prevenção de replay

Replay deve ser controlado por combinação apropriada de:

- identidade de mensagem ou request;
- idempotency key;
- timestamp e janela aceitável;
- nonce ou sequence;
- audience e finalidade;
- binding ou canal esperado;
- Inbox e deduplicação;
- assinatura ou MAC quando aplicável.

Mensagem válida fora da janela é rejeitada ou encaminhada para reconciliação. A mesma mensagem recebida em binding diferente não é automaticamente equivalente.

Replay de callback ou sinal nunca reabre execução terminal.

## 18. Gestão de secrets

### 18.1 Ciclo de vida

```text
Solicitação → Aprovação → Emissão → Distribuição controlada
→ Uso → Rotação → Revogação → Destruição → Evidência
```

### 18.2 Regras

- secrets somente em store ou mecanismo autorizado;
- referência, nunca valor, em binding e configuração;
- menor privilégio por workload, operação e ambiente;
- exposição apenas no instante necessário;
- ausência em variável, arquivo ou log não protegido quando houver alternativa segura;
- rotação automatizável e testada;
- revogação emergencial;
- inventário, owner, validade e último uso;
- detecção de secret em código, artefato ou evidência;
- proibição de copiar secret de ambiente real para simulação.

## 19. Chaves e certificados

Chaves de assinatura, criptografia e autenticação possuem finalidades separadas quando o risco exigir. O modelo deve registrar owner, algoritmo, tamanho, validade, ambiente, uso permitido, rotação, revogação e evidência.

Chave privada não deve ser exportável quando a tecnologia permitir proteção mais forte. Backup e recuperação de chave devem ser coerentes com disponibilidade e não repúdio.

Certificado expirado ou revogado deve falhar seguro. Renovação não altera contrato canônico ou identidade lógica do binding.

## 20. Segurança dos perfis de integração

### 20.1 REST/HTTP

- autenticação de peer e originador;
- TLS/mTLS quando aplicável;
- proteção e audience de token;
- allowlist de destinos e redirects;
- limites de header, body e decompression;
- validação de content type;
- prevenção de SSRF e request smuggling;
- assinatura de mensagem quando exigida;
- idempotency key e replay controlados.

### 20.2 SOAP/XML

- validação estrita de XML e schema;
- proteção contra external entities e expansão;
- WS-Security ou equivalente quando aplicável;
- assinatura, criptografia e canonicalização;
- prevenção de wrapping de assinatura;
- timestamp, nonce e replay;
- trust de WSDL/XSD governado.

### 20.3 Mensageria e eventos

- identidade de producer e consumer;
- ACL por destino lógico e operação;
- proteção de mensagem quando atravessa zonas;
- schema e origem validados;
- deduplicação, ordering e replay;
- dead-letter com mesma classificação;
- retenção e acesso mínimos;
- prevenção de confused deputy entre tópicos ou filas.

### 20.4 Arquivo e batch

- canal de transferência autenticado;
- assinatura, checksum e manifesto;
- criptografia quando aplicável;
- staging e publicação atômica;
- proteção contra path traversal, filename injection e arquivo incompleto;
- malware scanning conforme classe;
- identidade de lote e item;
- retenção e descarte coordenados.

### 20.5 Dados controlados

- credencial de menor privilégio;
- allowlist de operações;
- proibição de query construída por input livre;
- read-only por padrão;
- limites de volume e tempo;
- mascaramento e row/column security quando aplicáveis;
- trilha de acesso;
- isolamento da Engine de schema físico.

### 20.6 Protocolo específico

O Adapter deve encapsular autenticação, sessão, framing, integridade, criptografia, replay e limites. Garantias ausentes devem ser declaradas e compensadas por controles adicionais ou pela rejeição da integração.

## 21. Segurança do Control Plane

- autenticação reforçada para operadores;
- segregação entre author, reviewer, approver, release manager e operator;
- assinatura ou integridade de artefatos, bundles e releases;
- proteção contra publicação de secret ou endpoint real nesta fase;
- verificação de proveniência e supply chain;
- sessão curta para ações críticas;
- aprovação dual quando exigida;
- rollback e revogação auditados;
- acesso administrativo fora do caminho do Data Plane;
- backup e recuperação protegidos.

Comprometimento de uma conta de autoria não deve ser suficiente para ativar conteúdo no Data Plane.

## 22. Segurança do Data Plane

O Data Plane deve:

- validar integridade e compatibilidade do snapshot;
- executar somente versões publicadas;
- usar identidade de workload própria;
- aplicar policies fixadas no Execution Plan;
- impedir alteração administrativa durante execução;
- isolar payload e estado entre execuções;
- limitar concorrência e recursos por domínio/originador;
- proteger caches e memória transitória;
- encerrar credenciais e buffers ao final do uso;
- produzir evidências sem dados excessivos.

## 23. Segurança da Engine e do scheduler

- nenhuma execução de script arbitrário em condição ou mapping;
- interpretadores versionados e restritos;
- limites de CPU, memória, profundidade e tamanho;
- rejeição de grafo, mapping ou expressão maliciosos;
- isolamento entre executions;
- proteção contra step injection;
- estado persistido antes de efeito externo quando requerido;
- autorização antes de agendar step;
- prevenção de starvation e abuso de prioridade;
- fencing contra worker atrasado.

## 24. Segurança de Adapters

Adapters devem:

- aceitar somente operações declaradas;
- validar binding, contrato e Security Context;
- resolver destino por configuração governada;
- bloquear endpoint ou path livre no payload;
- proteger secret em memória e descarte;
- normalizar erros sem vazar topologia;
- limitar resposta, decompression e parsing;
- verificar peer e contrato externo;
- registrar interação e certainty;
- operar exclusivamente contra Mocks nesta fase.

Um Adapter não deve ser usado como proxy genérico.

## 25. Supply chain e runtime

Artefatos executáveis e dependências devem possuir proveniência, integridade, inventário e processo de correção. Requisitos:

- fontes e builds autorizados;
- dependências fixadas e verificadas;
- análise de vulnerabilidades;
- SBOM ou inventário equivalente;
- assinatura de artefato quando aplicável;
- ambientes de build isolados;
- menor privilégio de runtime;
- imagens e componentes mínimos;
- atualização e rollback testados;
- bloqueio de componente revogado.

A decisão de produto ou ferramenta permanece em aberto.

## 26. Classificação de dados

### 26.1 Data Classification Descriptor

```text
DataClassificationDescriptor
├── classificationCode
├── sensitivityLevel
├── personalDataCategories[]
├── allowedPurposes[]
├── allowedZones[]
├── maskingPolicyRef
├── encryptionPolicyRef
├── retentionPolicyRef
├── exportPolicyRef
└── ownerRef
```

### 26.2 Classes iniciais

| Classe | Exemplo | Tratamento |
|---|---|---|
| Pública | documentação aprovada para divulgação | Integridade e publicação controladas |
| Interna | configuração não sensível e catálogos | Acesso organizacional limitado |
| Confidencial | topologia, contratos externos e evidência técnica | Acesso por função e criptografia |
| Restrita | dado pessoal, credencial, segredo ou evidência sensível | Controles reforçados e menor exposição |

Taxonomia definitiva deve ser alinhada à organização. Payload sem classificação conhecida deve ser rejeitado ou tratado pela classe mais restritiva aplicável.

## 27. Minimização e finalidade

Cada campo deve possuir finalidade, owner, classificação e retenção. O Spider deve preferir referências a cópias e buscar dados somente quando necessários a um step autorizado.

São proibidos:

- copiar Contexto completo para cada step;
- registrar payload integral por padrão;
- manter dado “para uso futuro” sem finalidade;
- ampliar output além do autorizado;
- usar dado de execução para analytics não declarado;
- reter identificador direto quando hash ou referência opaca bastar;
- compartilhar dado entre originadores por correlação comum.

## 28. LGPD e direitos dos titulares

A arquitetura deve suportar princípios e obrigações aplicáveis, incluindo finalidade, adequação, necessidade, livre acesso quando devido, qualidade, transparência, segurança, prevenção, não discriminação e responsabilização.

O modelo deve permitir:

- localizar dados por subjectRefs autorizados;
- explicar finalidade e origem;
- corrigir referência técnica quando apropriado sem reescrever auditoria;
- aplicar retenção, bloqueio, anonimização ou descarte conforme base e obrigação;
- preservar legal hold e requisitos regulatórios;
- registrar atendimento e decisões;
- impedir que evidência técnica se torne perfil de negócio paralelo.

O documento não define bases legais ou prazos específicos; eles exigem validação jurídica e de privacidade por caso.

## 29. Consentimento e base de tratamento

Consentimento, quando aplicável, é referência governada com escopo, finalidade, versão, instante e revogação. Não deve ser representado por booleano genérico no payload.

Nem todo tratamento depende de consentimento. A base aplicável deve ser declarada pelo owner e refletida em policy, sem a Engine inferir justificativa jurídica.

Revogação de consentimento afeta novos usos conforme regra aplicável, mas não apaga automaticamente evidências que devam ser preservadas por obrigação legítima.

## 30. Mascaramento e tokenização

Mascaramento deve ser aplicado conforme usuário, finalidade, canal e campo. Não é apenas transformação visual; deve limitar o dado revelado antes de log, callback, evidência ou exportação.

Tokenização ou pseudonimização pode reduzir exposição, mas o dado permanece pessoal quando reversível ou correlacionável. Chaves e tabelas de reversão exigem proteção separada.

Dados mascarados não devem ser usados para decisões que exijam valor original sem autorização explícita.

## 31. Criptografia de dados

- criptografia em trânsito e repouso conforme classe;
- separação de chaves por ambiente, finalidade e domínio quando requerido;
- proteção de campos ou objetos para dados restritos;
- rotação sem perda de acesso autorizado;
- destruição criptográfica compatível com retenção;
- algoritmo e versão registrados em evidência;
- proibição de chave em payload, código ou configuração publicada;
- autorização e auditoria de decrypt.

Criptografia não substitui minimização, autorização ou descarte.

## 32. Logs, traces, métricas e erros

Telemetria deve operar com dados mínimos:

- correlation, execution, step e attempt IDs opacos;
- códigos canônicos em vez de payload;
- allowlist de atributos registráveis;
- mascaramento antes da emissão;
- proibição de tokens, secrets e credenciais;
- baggage limitado e classificado;
- stack trace restrita a ambiente e acesso autorizados;
- mensagens públicas sem topologia ou detalhe explorável;
- métricas sem labels de alta cardinalidade sensível.

Falha de mascaramento deve impedir registro do campo, não liberar valor original.

## 33. Evidências e não repúdio

Não repúdio pode exigir combinação de identidade forte, assinatura, timestamp confiável, integridade, sequência e cadeia de custódia.

Nem toda interação necessita não repúdio formal. A exigência deve ser definida por criticidade, efeito, obrigação e capacidade do destino.

O Spider não deve alegar não repúdio ponta a ponta quando algum trecho possui apenas autenticação fraca ou evidência não verificável.

## 34. Exportação e compartilhamento

Exportar evidência, resultado ou auditoria é ação distinta de consultar. Deve exigir:

- finalidade e destinatário;
- escopo mínimo;
- autorização reforçada conforme classe;
- mascaramento ou pseudonimização;
- formato e canal protegidos;
- prazo e condições de uso;
- marca de classificação;
- evidência de exportação;
- revogação ou expiração quando tecnicamente aplicável.

Link ou arquivo exportado não pode permanecer público ou sem prazo por padrão.

## 35. Ambientes

Ambientes devem ser isolados por identidade, rede, secrets, chaves, stores, dados e bindings.

É proibido:

- reutilizar credencial de produção em teste;
- copiar payload real para desenvolvimento sem processo aprovado;
- conectar simulador a dependência real;
- promover secret junto com artefato;
- permitir rota de rede de ambiente simulado para legado;
- compartilhar chave criptográfica entre classes incompatíveis de ambiente.

## 36. Mock-first e segurança desta fase

Nesta fase:

- principals são identidades de teste;
- certificados, tokens e secrets são exclusivos de simulação;
- dados são sintéticos ou anonimizados por processo aprovado;
- bindings alcançam somente Mocks, stubs e simuladores;
- zonas de rede impedem acesso a legados;
- callback, replay, fraude, expiração e rotação são simuláveis;
- testes de autorização incluem negação, ambiguidade e elevação;
- evidências não contêm dado real.

Simulador pode emular método de autenticação, mas não define a tecnologia final do legado.

## 37. Detecção e monitoramento de segurança

Devem ser detectáveis:

- falhas e anomalias de autenticação;
- negações e elevações de autorização;
- replay e conflito idempotente suspeito;
- uso de secret expirado ou fora de escopo;
- acesso incomum a evidência;
- exportação e operação privilegiada;
- alteração de binding, policy ou release;
- divergência de snapshot;
- Adapter acessando destino não permitido;
- volume, latência ou payload anômalos;
- tentativa de injeção e contrato inválido;
- violação da barreira Mock-first.

Alertas devem possuir owner, severidade, deduplicação, runbook e retenção. Detecção não pode expor os mesmos dados que pretende proteger.

## 38. Resposta a incidentes

### 38.1 Security Incident Record

```text
SecurityIncidentRecord
├── incidentId
├── category
├── severity
├── detectedAt
├── affectedScopes[]
├── dataClassifications[]
├── state
├── ownerRef
├── containmentActions[]
├── evidenceRefs[]
├── notificationRefs[]
└── closureSummary?
```

### 38.2 Ciclo

```text
Detecção → Triagem → Contenção → Preservação de evidência
→ Erradicação → Recuperação → Notificação aplicável
→ Revisão e ações corretivas
```

Contenção pode revogar principal, secret, binding, artefato ou release. Execuções em andamento seguem decisão explícita; não são alteradas silenciosamente.

## 39. Break-glass

Acesso emergencial deve ser excepcional, temporário, individual, justificado, reforçadamente autenticado e monitorado.

Requisitos:

- escopo e prazo mínimos;
- aprovação prévia ou revisão imediata conforme emergência;
- credencial distinta da operação cotidiana;
- sessão integralmente auditada;
- proibição de apagar evidência;
- revogação automática;
- revisão posterior obrigatória;
- incapacidade de autorizar legado real antes da fase final.

Break-glass não autoriza alteração direta de estado histórico ou regra bancária.

## 40. Vulnerabilidades e correções

Vulnerabilidades devem possuir severidade, owner, exposição, prazo, compensating controls e evidência de correção.

Correção pode exigir:

- atualização de runtime ou dependência;
- rotação de secret ou chave;
- revogação de artefato;
- desativação de binding;
- restrição de capability;
- nova release;
- reconciliação de execução afetada;
- investigação de acesso a dado.

Patch emergencial não pode ignorar integridade, aprovação e rollback, embora o fluxo possa ser acelerado de modo governado.

## 41. Testes de segurança

Devem ser automatizáveis, no mínimo:

- autenticação válida, inválida, expirada e com issuer/audience incorretos;
- workload ou originador não cadastrado;
- delegação ausente, expirada, excessiva e encadeada indevidamente;
- permit, deny, not applicable e indeterminate;
- obrigação de masking e output reduzido;
- replay dentro e fora da janela;
- callback falsificado, duplicado e em binding errado;
- rotação e revogação de secret;
- certificado inválido e peer não confiável;
- SSRF, redirect, XML injection, path traversal e payload excessivo conforme perfil;
- acesso indevido a evidência e exportação;
- leakage em logs, traces e erros;
- integridade de release e snapshot;
- ação privilegiada e break-glass;
- isolamento entre ambientes;
- impossibilidade de acesso a legado real;
- uso exclusivo de identidades de teste e dados sintéticos.

## 42. Decisões arquiteturais consolidadas

1. Segurança é transversal ao Spider.
2. Toda interação possui principal autenticado ou é rejeitada.
3. Originador, ator, workload e operador são identidades distintas.
4. Security Context transporta referências e evidências, não credenciais brutas.
5. Autorização é contextual, versionada, auditável e negada por padrão.
6. Delegação é limitada por escopo, finalidade, cadeia e prazo.
7. A Engine opera sobre capability e operation, não endpoint ou credencial.
8. Trust de rede não substitui autenticação.
9. Proteção de transporte e mensagem são aplicadas conforme perfil e risco.
10. Replay é controlado por identidade, tempo, audience, deduplicação e integridade.
11. Secrets possuem ciclo completo e nunca entram em artefatos publicados.
12. Cada perfil de integração encapsula controles tecnológicos no Adapter.
13. Control Plane e Data Plane possuem identidades e permissões separadas.
14. Dados são classificados, minimizados, mascarados e retidos por finalidade.
15. LGPD e direitos são suportados sem transformar o Spider em cadastro mestre.
16. Evidências e não repúdio refletem somente garantias demonstráveis.
17. Resposta a incidentes pode revogar acessos e releases de modo governado.
18. Nesta fase, somente identidades de teste, dados sintéticos e Mocks são permitidos.

## 43. Invariantes arquiteturais

1. Nenhum identificador do payload é tratado como identidade autenticada.
2. Nenhum principal atua fora de escopo autorizado.
3. Nenhuma delegação amplia a autoridade original.
4. Nenhuma decisão `INDETERMINATE` resulta em permit.
5. Nenhum step executa antes do enforcement aplicável.
6. Nenhum Adapter recebe endpoint ou secret livre da Engine.
7. Nenhum secret é persistido em contrato, rota, plano, log ou evidência aberta.
8. Nenhum callback altera estado antes de autenticação, correlação e deduplicação.
9. Nenhuma mensagem expirada ou reproduzida é aceita silenciosamente.
10. Nenhuma zona interna é implicitamente confiável.
11. Nenhum dado é enviado além do mínimo autorizado.
12. Nenhum payload integral é registrado por padrão.
13. Nenhuma referência concede acesso por conhecimento do identificador.
14. Nenhuma exportação ocorre sem finalidade e evidência.
15. Nenhuma evidência é alterada para ocultar incidente.
16. Nenhum break-glass permanece ativo indefinidamente.
17. Nenhuma decisão de segurança implementa regra bancária.
18. Nenhum ambiente simulado usa credencial ou dado real.
19. Nenhum binding desta fase alcança legado real.
20. A futura troca de Mock por legado não altera o modelo central de segurança.

## 44. Pontos ainda abertos

| Tema | Questão a decidir |
|---|---|
| Identity providers | Provedores, federação, realms e disponibilidade |
| Protocolos | OAuth, OIDC, SAML, mTLS, assinatura ou combinações |
| Workload identity | Emissão, attestation e rotação |
| Autorização | Linguagem, PDP/PEP, cache e revogação |
| Delegação | Modelo jurídico e técnico por canal |
| Assurance | Níveis e métodos aceitos por operação |
| PKI | Hierarquia, certificados, revogação e automação |
| Secrets | Vault/KMS/HSM, rotação e recuperação |
| Message security | Canonicalização, assinatura e criptografia por perfil |
| Classificação | Taxonomia organizacional definitiva |
| LGPD | Bases, owners, direitos e prazos por fluxo |
| Mascaramento | Policies por campo, papel, canal e finalidade |
| SIEM/SOC | Integração, eventos, alertas e retenção |
| DLP | Cobertura de payload, logs, arquivos e exports |
| Supply chain | SBOM, assinatura, policy gates e attestation |
| Break-glass | Autoridade, monitoramento e revisão |
| Fase final | Perfil de segurança e certificação individual de cada legado |

## 45. Critérios de aceite

O SPIDER-ARCH-009 é considerado apto a orientar a próxima etapa quando:

1. tipos de principal e Security Context estiverem separados;
2. autenticação, delegação e autorização estiverem semanticamente definidas;
3. pontos de decisão e enforcement estiverem identificados;
4. trust zones e mudanças de confiança estiverem explícitos;
5. proteção de transporte, mensagem e replay estiver formalizada;
6. ciclo de secrets, chaves e certificados estiver definido;
7. controles por perfil de integração estiverem isolados em Adapters;
8. Control Plane, Data Plane, Engine e Adapter possuírem responsabilidades claras;
9. classificação, minimização, LGPD, masking e criptografia estiverem cobertos;
10. telemetria, evidências, exportação e não repúdio estiverem limitados;
11. detecção, incidentes, break-glass e vulnerabilidades estiverem governados;
12. identidades de teste, dados sintéticos e Mocks permanecerem exclusivos nesta fase.

## 46. Próxima etapa recomendada

Antes de implementar, recomenda-se criar:

> **SPIDER-ARCH-010 — Observabilidade, SLOs, Operação e Resposta a Falhas**

Esse documento deverá formalizar logs, métricas, traces, auditoria operacional, sinais dourados, SLIs/SLOs, budgets, alertas, dashboards, saúde, capacidade, backpressure, operação de processos longos, reconciliação, incidentes, runbooks, continuidade e critérios de prontidão.

A especificação continuará neutra a ferramenta e fornecedor, usando somente Mocks e cenários de falha simulados nesta fase. Prompts de implementação permanecem separados em `SPIDER-PROMPT-NNN`. Legados reais continuam fora de escopo até a fase final.
