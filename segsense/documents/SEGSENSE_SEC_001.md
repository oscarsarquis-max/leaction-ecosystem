# SEGSENSE_SEC_001 — Fundação de segurança e identidade

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_SEC_001 |
| Título | Fundação de segurança, ameaças e identidade futura |
| Categoria | SEC — segurança |
| Versão | 1.4 |
| Status | Vigente nesta etapa |
| Data | 11/09/2026 |
| Dependências | SEGSENSE_ARQ_002 v1.2; SEGSENSE_ADR_002; SEGSENSE_API_001 v1.2; SPIDER-ARCH-017 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Modelo de ameaça inicial, deny-by-default e contrato futuro OIDC/OAuth 2.0 sem implementação. |
| 1.1 | 04/09/2026 | Authorities de catálogo; CSRF isento em `/api/**` (STATELESS, sem cookie); publicadores sem PII. |
| 1.2 | 04/09/2026 | Authorities `segsense.opportunity.read` / `segsense.opportunity.write`; matchers de oportunidade antes do catálogo. |
| 1.3 | 04/09/2026 | `submit`, `review` e `publication.manage`; SOD por `subjectId`; matchers de governança antes do POST genérico. |
| 1.4 | 11/09/2026 | Authorities `segsense.link.read` / `segsense.link.manage`; GET público de resolução; ver `SEGSENSE_SEC_002`. |

## 1. Modelo de ameaça inicial

Ameaças consideradas nesta fundação:

| Ameaça | Mitigação atual |
|---|---|
| Chamada direta do browser à Spider ou Icatu | Frontend só chama o BFF |
| Enumeração de APIs ainda inexistentes | `/api/**` sem política → 401 anônimo, sem 404 revelador |
| Confiança em `X-User-Id` / `X-Subject-Id` / roles na query | Nenhum filtro de identidade lê headers ou query do navegador |
| Credencial padrão do Spring Boot | `UserDetailsServiceAutoConfiguration` excluída; sem usuário in-memory |
| Login HTML ou HTTP Basic acidentais | Form login e Basic desabilitados; 401 JSON |
| Exposição de Actuator | Somente health/readiness; detalhes ocultos |
| CSRF em mutações com cookie | CSRF **não** foi desabilitado globalmente; `/api/**` é isento enquanto a API for STATELESS e sem cookie de sessão |
| Vazamento de token em log | Token bruto só no 201; digest SHA-256 no banco; path público redigido no MDC `sanitizedPath` |

Fora desta etapa: phishing contra um IdP, sequestro de sessão, Guard/Policy da Spider.

## 2. Fronteiras de confiança

```text
Não confiável: browser, headers de identidade, query, payload de roles
Confiável no futuro: provedor OIDC/OAuth 2.0 com issuer, audience, assinatura e expiração validados
Local e não autenticador de usuário: applicationId=SEGSENSE
Não nesta etapa: Spider, Icatu, Guard, Policy
```

O BFF é a fronteira. Credenciais técnicas da plataforma nunca chegam ao React.

## 3. Endpoints públicos

Públicos, sem login:

- `GET /api/v1/system/info`
- `GET /actuator/health`
- `GET /actuator/health/readiness`
- `OPTIONS /api/**` (pré-voo CORS)

Qualquer outro `/api/**` é negado por padrão, salvo as rotas administrativas abaixo, que exigem autenticação real e authority:

- `GET …/opportunities` e sub-recursos (incl. `/governance` e `/governance/events`) — `segsense.opportunity.read`
- `POST …/opportunities` e `…/revisions` — `segsense.opportunity.write`
- `POST …/governance/submit` — `segsense.opportunity.submit`
- `POST …/governance/return-for-changes|approve|reject` — `segsense.opportunity.review`
- `POST …/publication/**` — `segsense.publication.manage`
- `GET /api/v1/admin/**` (demais) — `segsense.catalog.read`
- `POST` e `PATCH /api/v1/admin/**` (demais) — `segsense.catalog.write`

Sem IdP, essas rotas respondem **401** a chamadores reais. Demais endpoints Actuator não são expostos.

## 4. Deny-by-default

Não existe política implícita de “autenticado pode tudo”. `anyRequest().denyAll()` faz com que:

- anônimo receba 401 (`AUTHENTICATION_REQUIRED`);
- ator autenticado de teste sem política explícita receba 403 (`ACCESS_DENIED`).

Não há usuário, senha, JWT ou API key no runtime.

## 5. CSRF

CSRF permanece o default do Spring. A API `/api/**` é **isenta** (`ignoringRequestMatchers`) porque a sessão é `STATELESS` e não há cookie de sessão: um token CSRF de sessão não se aplica. Isso **não** é `csrf.disable()` global.

Quando a autenticação usar cookie de sessão, CSRF voltará a ser obrigatório nesses endpoints. Bearer/OIDC sem cookie poderá manter a isenção documentada por prefixo `/api/**`.

## 6. Identidade futura (não implementada)

O adapter futuro deverá converter identidade **já verificada** por um provedor confiável em `Actor`, garantindo:

- issuer e audience validados;
- assinatura e expiração validadas;
- `subject` estável mapeado para `subjectId`;
- roles mapeadas por configuração governada — nunca claims livres, query ou header do browser;
- nenhuma confiança em claims não autorizadas;
- separação entre autenticação do **usuário** no BFF e autenticação do **satélite** perante a Spider;
- no-enumeration nas respostas;
- trilha auditável sem tokens nos logs.

Nenhum fornecedor de identidade é escolhido nesta etapa.

## 7. Exclusões

Não existem nesta etapa: tela de login, cadastro de usuário, emissão de token, API key, Basic Auth, JWT próprio, IdP local, tenant, CPF, e-mail pessoal, integração Spider/Icatu, Guard ou Policy. Publicadores do catálogo são entidades técnicas locais, sem dados cadastrais pessoais. Justificativas de governança são texto administrativo e não devem conter dados pessoais.
