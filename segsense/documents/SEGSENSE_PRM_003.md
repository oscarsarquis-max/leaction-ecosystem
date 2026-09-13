# SEGSENSE_PRM_003

Cópia integral do prompt de execução da etapa `SEGSENSE_PRM_003`.

---

Implemente o `SEGSENSE_PRM_003` em `C:\Projetos\segsense`, no monorepo Git existente `leaction-ecosystem`.

Leia integralmente os documentos indexados, especialmente `SEGSENSE_ARQ_001`, `SEGSENSE_ARQ_002`, `SEGSENSE_ADR_001`, `SEGSENSE_API_001`, `SEGSENSE_REV_002` e `SPIDER-ARCH-017`, além de todo o código e testes atuais.

Preserve alterações existentes. Não execute `git init`, não altere remotes ou outros produtos e não faça commit, push ou deploy.

## 1. Objetivo

Criar uma fundação segura e neutra de identidade e autorização para o Satellite BFF, sem inventar provedor de identidade, login, usuários, organizações, publicadores ou credenciais.

Esta etapa deverá:

- aplicar segurança web deny-by-default;
- preservar acesso público somente aos endpoints técnicos autorizados;
- distinguir conceitualmente usuário, aplicação e canal;
- definir o contrato interno mínimo de ator autenticado;
- padronizar respostas 401 e 403 com correlação;
- impedir confiança em headers de identidade fornecidos pelo navegador;
- documentar a futura integração OIDC/OAuth 2.0 sem implementá-la antes de existir contrato.

Não crie tela de login, cadastro de usuário, emissão de token, API key, Basic Auth, JWT próprio, IdP local, tenant fictício, publicador fictício ou integração Spider/Icatu.

## 2. Segurança web

Adicione Spring Security e configure cadeias explícitas:

- `GET /api/v1/system/info`: público;
- `GET /actuator/health`: público;
- `GET /actuator/health/readiness`: público;
- demais endpoints Actuator: indisponíveis;
- qualquer outro `/api/**`: negar por padrão enquanto não houver política explícita;
- form login: desabilitado;
- HTTP Basic: desabilitado;
- logout do framework: desabilitado enquanto não houver sessão;
- request cache: desabilitado;
- nenhuma página HTML de autenticação gerada pelo Spring;
- CORS: preservar origem explícita e headers atuais;
- CSRF: não desabilitar globalmente sem justificativa.

Como existem apenas GETs públicos nesta etapa, mantenha uma postura segura para CSRF e documente a decisão futura conforme o mecanismo de autenticação.

Não habilite OAuth Resource Server sem issuer, JWKS ou contrato real. A aplicação deve continuar iniciando sem IdP.

## 3. Respostas de segurança

Crie handlers de autenticação e acesso negado que retornem o formato definido em `SEGSENSE_API_001`.

Resposta 401:

```json
{
  "code": "AUTHENTICATION_REQUIRED",
  "message": "Autenticação necessária.",
  "timestamp": "<UTC>",
  "correlationId": "<UUID>"
}
```

Resposta 403:

```json
{
  "code": "ACCESS_DENIED",
  "message": "Acesso não autorizado para esta operação.",
  "timestamp": "<UTC>",
  "correlationId": "<UUID>"
}
```

Use:

- 401 quando não houver autenticação válida;
- 403 quando um ator autenticado não possuir autorização.

Não revele regras internas, roles esperadas, stack ou detalhes técnicos.

Garanta que o filtro de correlação execute antes da decisão de segurança para rotas protegidas. O mesmo UUID deve aparecer no response header e no corpo.

## 4. Modelo interno de identidade

Defina tipos puros, sem Spring Security no domínio, para representar futuramente:

- `Actor`: `subjectId`, conjunto de roles e tipo;
- `ActorType`: inicialmente `USER` e `SERVICE`;
- `ApplicationIdentity`: `applicationId`;
- `ChannelContext`: identificador do canal quando legitimamente conhecido.

Regras:

- usuário, aplicação e canal são identidades distintas;
- `applicationId=SEGSENSE` não autentica o usuário;
- `subjectId` nunca deve ser aceito de header arbitrário do navegador;
- roles não podem vir de query string ou payload;
- canal não concede autorização sozinho;
- ausência de identidade autenticada não gera ator anônimo privilegiado;
- os tipos devem validar campos vazios, normalização e imutabilidade;
- não adicionar CPF, e-mail, nome, seguradora, publicador ou organização.

Os tipos podem permanecer sem adapter de autenticação até existir contrato real. Não crie implementação falsa para utilizá-los em runtime. Use-os em testes unitários e na documentação.

## 5. Contrato futuro de autenticação

Documente, sem implementar, que o adapter futuro deverá converter identidade verificada por provedor confiável em `Actor`, garantindo:

- issuer e audience validados;
- assinatura e expiração validadas;
- subject estável;
- roles mapeadas por configuração governada;
- nenhuma confiança direta em claims não autorizadas;
- separação entre autenticação do usuário e autenticação do satélite perante a Spider;
- no-enumeration;
- trilha auditável sem tokens nos logs.

Não escolha fornecedor de identidade nesta etapa.

## 6. Comprovação sem endpoint fictício

Não crie endpoint funcional de identidade.

Para testar 401 e 403 sem inventar recurso de negócio, use apenas controllers ou rotas de fixture no escopo de testes, que não sejam empacotados na aplicação final.

Os endpoints reais devem continuar limitados a system info e Actuator.

## 7. Frontend

Preserve a página técnica e sua consulta real ao BFF.

- Não criar login.
- Não armazenar token.
- Não simular usuário autenticado.
- Prepare tipos de erro capazes de distinguir respostas 401 e 403, mas somente a partir de respostas reais.
- Preserve `X-Correlation-ID` por chamada.
- Atualize testes sem criar sessão fictícia.

## 8. Testes arquiteturais e de segurança

Amplie os testes para comprovar:

- tipos de identidade do domínio não dependem de Spring Security;
- domínio não conhece JWT, OAuth, servlet ou headers;
- frontend não contém segredo, token fixo ou chamada Spider/Icatu;
- application não depende de implementações de segurança;
- endpoints públicos respondem sem login;
- rota protegida de fixture retorna 401 para anônimo;
- ator autenticado de teste sem permissão recebe 403;
- handlers retornam código, mensagem, timestamp e correlationId;
- header e corpo possuem a mesma correlação;
- form login e Basic Auth não são oferecidos;
- endpoints Actuator não autorizados não ficam expostos;
- CORS continua restrito;
- manifesto, system info, Flyway, health e readiness não regrediram.

Use mecanismos do Spring Security somente no escopo de testes. Não crie credenciais de desenvolvimento no runtime.

## 9. Documentação

Crie:

- `documents/SEGSENSE_SEC_001.md`: modelo de ameaça inicial, fronteiras de confiança, endpoints públicos, deny-by-default, identidade futura e exclusões;
- `documents/SEGSENSE_ADR_002.md`: decisão “Autenticação desacoplada de provedor e ausência de identidade fictícia”;
- `documents/SEGSENSE_REV_003.md`: evidências, riscos e mapa SAT-01 a SAT-10;
- `documents/SEGSENSE_PRM_003.md`: cópia integral deste prompt.

Atualize:

- `SEGSENSE_API_001` para documentar 401, 403 e política de exposição;
- `SEGSENSE_ARQ_002` para incluir a fronteira de identidade;
- `README.md` raiz com a situação real da segurança;
- `documents/README.md` com documentos e versões corretas.

Não marque SAT-08 como atendido integralmente sem IdP, autenticação do satélite, Guard e Policy reais.

## 10. Validações

Execute:

1. `backend\mvnw.cmd verify`;
2. `npm ci`, lint, testes e build do frontend;
3. validação do Compose sem remover volumes;
4. inicialização controlada do backend;
5. chamadas reais aos três endpoints públicos;
6. comprovação automatizada de 401 e 403 por fixtures de teste;
7. verificação de ausência de `WWW-Authenticate: Basic` e página de login;
8. verificação de correlação nos erros de segurança;
9. inspeção de segredos, tokens e credenciais;
10. estado Git limitado a `segsense/`.

Não altere ou apague dados existentes.

## 11. Critérios de aceite

- Endpoints públicos autorizados continuam funcionando.
- Demais APIs são negadas por padrão.
- Não existe login ou credencial fictícia.
- 401 e 403 são distintos, padronizados e correlacionados.
- Modelo de ator é puro, mínimo e imutável.
- Usuário, satélite e canal permanecem distintos.
- Identidade do navegador não é confiada por header.
- Frontend não armazena token nem simula autenticação.
- Testes e builds passam.
- Documentação e índice estão atualizados.
- Nenhuma integração ou regra de seguros foi antecipada.
- Nenhum outro produto foi alterado.

## 12. Devolutiva obrigatória

Apresente:

1. arquivos criados e alterados;
2. matriz de exposição dos endpoints;
3. arquitetura da segurança;
4. modelo interno de identidade;
5. evidências de 200, 401 e 403;
6. correlação nos erros;
7. testes e builds;
8. situação SAT-01 a SAT-10;
9. inspeção de segredos;
10. estado Git restrito a `segsense/`;
11. riscos e itens deliberadamente não implementados;
12. confirmação de ausência de IdP, usuário, token ou integração fictícios.

Não faça commit, push ou deploy.
