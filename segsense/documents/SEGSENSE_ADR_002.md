# SEGSENSE_ADR_002 — Autenticação desacoplada de provedor e ausência de identidade fictícia

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_ADR_002 |
| Título | Autenticação desacoplada de provedor e ausência de identidade fictícia |
| Categoria | ADR — decisão arquitetural |
| Versão | 1.0 |
| Status | Aceita |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_SEC_001; SEGSENSE_ARQ_002 v1.1; SPIDER-ARCH-017 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Registro da decisão. |

## Contexto

O BFF precisa de uma fundação de autorização deny-by-default antes de existir contrato com um provedor de identidade. Alternativas comuns — usuário `admin/admin`, JWT HS256 local, IdP embutido, header `X-User-Id` — criariam identidade fictícia e um contrato difícil de desfazer.

O SPIDER-ARCH-017 distingue usuário, aplicação e canal. O `applicationId=SEGSENSE` já identifica o satélite e não deve autenticar pessoas.

## Decisão

A autenticação permanece **desacoplada de provedor**. O domínio define `Actor`, `ActorType`, `ApplicationIdentity` e `ChannelContext` sem Spring Security. Nenhum adapter de autenticação roda até existir contrato real (OIDC/OAuth 2.0 com issuer e JWKS).

É **proibido** nesta etapa:

- login, cadastro, token, API key, Basic Auth, JWT próprio ou IdP local;
- usuário, tenant, publicador ou organização fictícios;
- Resource Server OAuth sem issuer;
- confiar em headers, query string ou payload enviados pelo navegador como identidade.

O Spring Security protege a superfície HTTP. Testes podem usar `@WithMockUser` / `user()` **somente no classpath de teste**.

## Alternativas rejeitadas

1. **Usuário em memória para desenvolvimento.** Introduz credencial fictícia e aparece em logs.
2. **JWT assinado pelo próprio SegSense.** Inventa um IdP e um formato que pode colidir com o contrato futuro.
3. **Header `X-User-Id` “temporário”.** O browser não é fonte de confiança.
4. **OAuth Resource Server com issuer inventado.** A aplicação deixaria de subir sem IdP.

## Consequências

- Endpoints não públicos respondem 401 ou 403 padronizados, sem Basic nem HTML de login.
- Integração OIDC/OAuth 2.0 fica documentada em `SEGSENSE_SEC_001` e só será implementada com contrato.
- SAT-08 permanece **parcial** até IdP, autenticação do satélite, Guard e Policy reais.
