# SEGSENSE_ARQ_002 — Arquitetura lógica do Insurance Reference Satellite

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_ARQ_002 |
| Título | Arquitetura lógica e fronteiras de componentes |
| Categoria | ARQ — Arquitetura |
| Versão | 1.6 |
| Status | Vigente nesta etapa |
| Data | 12/09/2026 |
| Dependências | SEGSENSE_ARQ_001 v0.4; SPIDER-ARCH-017 (ideal); SEGSENSE_ADR_001; SEGSENSE_ADR_003; SEGSENSE_API_001; SEGSENSE_DOM_001 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Formalização do Satellite BFF, camadas internas, identidade local, manifesto preliminar e correlação HTTP. |
| 1.1 | 04/09/2026 | Fronteira de identidade e autorização deny-by-default, sem IdP. |
| 1.2 | 04/09/2026 | Independência física das três aplicações; catálogo local Publisher/Channel/Environment. |
| 1.3 | 04/09/2026 | Aggregate local `ContextualOpportunity` com revisões imutáveis; sem publicação nem Spider. |
| 1.4 | 04/09/2026 | Governança editorial local; PUBLISHED = autorização interna, sem link. |
| 1.5 | 11/09/2026 | Aggregate `PublishedContextLink`; resolução pública mínima; ainda sem jornada do usuário. |
| 1.6 | 12/09/2026 | Fronteira Spider bloqueada (PRM_010 ramo B); sem conexão operacional. |

## 1. Contexto e objetivo

Este documento descreve a arquitetura interna do SegSense após o `SEGSENSE_PRM_004`. O produto permanece o **Insurance Reference Satellite** da Spider no sentido de **padrão de integração**. Isso **não** incorpora código, banco, runtime ou deployment do SegSense à Spider.

Três aplicações são fisicamente independentes:

```text
SegSense (aplicação independente)
        ↓ contrato de integração (ideal; bloqueado — SEGSENSE_ADR_003)
Spider (plataforma independente; este projeto não a modifica)
        ↓ contrato de executor, quando aplicável
Insurance Provider Mock (aplicação independente futura)
```

O mock futuro terá runtime, configuração, endpoints e ciclo de vida próprios. Nenhum código, módulo, banco, runtime ou deployment do SegSense ou do mock pertence à Spider.

O objetivo desta etapa inclui o catálogo administrativo local, o rascunho versionado de oportunidade contextual e a governança editorial de autorização interna de publicação, além das convenções já existentes do Satellite BFF.

Não faz parte desta arquitetura: client ou mock da Spider/Icatu, submissão de objetivo, Intent Contract, execução assíncrona, jornada de seguros, autenticação de usuários junto a um IdP ou regras funcionais de seguros. O PRM_010 **não** implementa Satellite Contract; a fronteira operacional está em `SEGSENSE_ARQ_003`.

## 2. Diagrama de fronteira

```text
Browser
  └── React (segsense-frontend)
        └── somente HTTP local
              └── Satellite BFF (segsense-backend)
                    └── estado local (Postgres, health, catálogo, link, aviso, instância)

Spider (independente) — Satellite Contract externo AUSENTE
Insurance Provider Mock futuro — fora desta etapa
```

Caminhos proibidos:

```text
Browser → Spider
Browser → Icatu
SegSense BFF → Icatu (operações do plano Spider)
BFF → escolha de route / adapter / executor / Execution Plan
```

O frontend chama apenas o BFF SegSense. O BFF será a única fronteira futura com o Satellite Contract **quando este for publicado**. Credenciais técnicas da plataforma nunca chegam ao React. Operações exclusivamente locais não passam pela Spider. Nesta data não há seta operacional para a Spider.

## 3. Componentes e responsabilidades

| Componente | Responsabilidade | Não faz |
|---|---|---|
| React | Apresentar o estado real do BFF; enviar `X-Correlation-ID` por chamada técnica | Chamar Spider/Icatu; guardar credenciais; rastrear usuário pelo correlation id |
| Satellite BFF | Identidade local, manifesto preliminar, HTTP `/api/v1`, correlação, erros, health | Interpretar intent; escolher plano, capability, route, adapter ou executor |
| Camada `domain` | Tipos locais (`SystemInfo`, identidade, catálogo, `ContextualOpportunity`) | Spring, JPA, servlet, HTTP, Spring Security |
| Camada `application` | Casos de uso e portas | Controllers e adapters concretos |
| Camada `inbound/http` | Adaptar HTTP aos casos de uso | Regras de seguros; clients externos |
| Camada `infrastructure` | Configuração, CORS, manifesto YAML, health via DataSource | Orquestração Spider |
| PostgreSQL | Persistência técnica local, catálogo V2/V3 e oportunidade V4 | Fonte de projeções operacionais da Spider |
| `services/spider-integration` | Limite documental do contrato | Client |
| `services/icatu-integration` | Limite documental: executor potencial | Integração operacional |

Health e readiness são componentes técnicos locais. Não são domínio de seguros.

## 4. Dependências permitidas e proibidas

Permitidas:

```text
domain ← application ← inbound | infrastructure
```

- `domain` não depende de Spring, JPA, servlet, HTTP ou infraestrutura.
- `application` não depende de `inbound` nem de implementações em `infrastructure`.
- `inbound/http` e `infrastructure` dependem de `application`/`domain`.
- Controllers REST residem em `inbound.http`.

Proibidas:

- dependência de `br.com.spider..` ou `com.icatu..`;
- `IntentRouter`, `ContextGuard`, `ExecutionPlan`, `CapabilityResolver`, `RouteResolver`;
- client HTTP, mock ou payload inventado da Spider/Icatu;
- envio do manifesto a qualquer sistema.

As regras são verificadas por ArchUnit.

## 5. Estado local versus projeção Spider

| Estado local (existente) | Projeção Spider (inexistente nesta etapa) |
|---|---|
| `operationalState` do banco local | `requestId`, `decisionId`, `planId`, `executionId`, `interactionId` |
| Flyway V1–V4, health, readiness, catálogo e oportunidade locais | Journey Projection |
| Página de ambiente | Progresso operacional de jornada |
| Manifesto `DRAFT` em classpath | Manifesto certificado / contrato executável |

O SegSense não mantém máquina de estados operacional paralela. Quando houver execução na Spider, a UI deverá projetar o estado real da plataforma, sem colapsar os identificadores canônicos em um único campo.

## 6. Identidade `SEGSENSE`

O `applicationId` único do satélite é `SEGSENSE`. Ele vive em configuração externa tipada (`segsense.satellite.application-id` / `SEGSENSE_APPLICATION_ID`) e na porta `SatelliteSettings`. Não é literal espalhado pelo código de negócio.

A identidade é **local**. Não declara autenticação junto à Spider nem registro aceito pela plataforma. `GET /api/v1/system/info` a expõe junto com `name`, `version` e `operationalState`. `applicationId=SEGSENSE` **não** autentica um usuário.

## 6.1 Fronteira de identidade (usuário, aplicação, canal)

Três identidades permanecem distintas:

| Identidade | Tipo | Papel |
|---|---|---|
| Usuário ou serviço autenticado | `Actor` (`subjectId`, `ActorType`, roles) | Só existirá após um provedor confiável verificar a identidade |
| Satélite | `ApplicationIdentity` | Identifica a aplicação `SEGSENSE` |
| Canal | `ChannelContext` | Contexto do canal quando legitimamente conhecido; não autoriza sozinho |

Regras vigentes:

- `subjectId` e roles não são aceitos de header, query string ou payload do navegador.
- Ausência de autenticação não gera ator anônimo privilegiado.
- Os tipos são puros, imutáveis e validados; não há adapter de autenticação em runtime nesta etapa (`SEGSENSE_ADR_002`).
- Autenticação do usuário no BFF é distinta da autenticação futura do satélite perante a Spider.

## 7. Manifesto preliminar

Arquivo: `backend/src/main/resources/satellite-manifest.yaml`.

Classificação: `DRAFT / NOT_CERTIFIED`. `schemaVersionKind: PRELIMINARY`. `status: DRAFT`. `executable: false`. `acceptedBySpider: false`.

Contém apenas identidade, domínio `INSURANCE`, classes pretendidas `READ`, `SIMULATE`, `REQUEST` e `mutationPolicy: CONFIRMATION_REQUIRED`. Não contém routes, adapters, URLs, credenciais, produto Icatu, capabilities inventadas nem permissões tratadas como concedidas.

O BFF carrega o YAML na inicialização como configuração local. Se o `applicationId` do manifesto divergir da configuração, a aplicação falha. O manifesto não é publicado em endpoint e não é enviado à Spider.

## 8. Correlação local e IDs Spider futuros

Para `/api/**`:

- header `X-Correlation-ID`;
- aceita somente UUID válido; caso contrário gera UUID;
- devolve o identificador efetivo no response;
- disponibiliza o valor durante a requisição (`CorrelationContext`) e no MDC `correlationId`;
- remove o MDC ao final;
- inclui `correlationId` no corpo padronizado de erros.

Este identificador **não** é `requestId`, `decisionId`, `planId`, `executionId` nem `interactionId`. O mapeamento futuro para a correlação da Spider dependerá do Satellite Contract executável. Até lá, os IDs canônicos da Spider, quando existirem, serão campos distintos.

## 9. Segurança da fronteira

- Origem CORS explícita (`SEGSENSE_FRONTEND_ORIGIN`); sem curinga.
- Headers permitidos e expostos incluem `X-Correlation-ID`.
- Credenciais técnicas não seguem para o frontend.
- Spring Security deny-by-default: públicos são `GET /api/v1/system/info`, `GET /api/v1/public/context-links/*`, health e readiness. Links exigem `segsense.link.read` / `segsense.link.manage` **antes** dos matchers de oportunidade. Oportunidades exigem `segsense.opportunity.*` e `segsense.publication.manage`; demais `/api/v1/admin/**` exigem authorities de catálogo; anônimo recebe 401.
- 401 e 403 padronizados, correlacionados, sem Basic Auth, form login ou página HTML de autenticação.
- CSRF permanece o default do Spring fora da API. `/api/**` é isento enquanto a sessão for STATELESS e sem cookie (`SEGSENSE_SEC_001`). Não é `csrf.disable()` global.
- Respostas de erro não incluem stack trace, classe interna, SQL ou segredo.
- Health não revela componentes internos.

## 10. Tratamento de indisponibilidade

Se o banco local não responde, `operationalState` é `DEGRADED` e o frontend não inventa sucesso. Falha de rede ou payload inválido resulta em “Backend indisponível”. Readiness do Actuator permanece a sonda de infraestrutura. Ausência da Spider não é simulada como jornada.

## 11. Consequências e limitações

- O satélite ainda não é certificável (SAT-03 ausente; SAT-01/02/04/05/08 parciais).
- Não há IdP, sessão de usuário, token nem autenticação de satélite perante a Spider. O catálogo administrativo existe, mas o runtime o recusa a chamadores anônimos.
- Não há preview, confirmação nem execução.
- A Icatu permanece executor potencial resolvido pela Spider (`SEGSENSE_ADR_001`). O mock futuro, quando existir, será aplicação independente.

## 12. Mapa SAT-01 a SAT-10 após esta etapa

| ID | Situação | Comentário |
|---|---|---|
| SAT-01 | PARCIAL | `applicationId=SEGSENSE` local, centralizado e validado; sem registro aceito pela Spider |
| SAT-02 | PARCIAL | Manifesto `DRAFT / NOT_CERTIFIED`; não é contrato executável |
| SAT-03 | NÃO IMPLEMENTADO | Satellite Contract não existe e não foi inventado |
| SAT-04 | PARCIAL | Browser → React → BFF imposto; sem client Spider e sem sessão de usuário |
| SAT-05 | PARCIAL | Correlação HTTP local; sem IDs canônicos da Spider |
| SAT-06 | NÃO APLICÁVEL NESTA ETAPA | Sem submissão de objetivo |
| SAT-07 | NÃO APLICÁVEL NESTA ETAPA | Sem execução para projetar |
| SAT-08 | PARCIAL | Deny-by-default, 401/403, CORS; sem IdP, Guard, Policy nem autenticação do satélite |
| SAT-09 | ATENDIDO | Sem knowledge de routes/adapters |
| SAT-10 | ATENDIDO | Operações locais (catálogo, oportunidade, autorização interna, links) não usam a Spider |
