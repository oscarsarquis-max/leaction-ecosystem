# ACTIONFINANCE_SEC_001 — Identidade demo da fundação

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_SEC_001 |
| Versão | 0.2 |
| Data | 25/09/2026 |
| Prompt | PRM_002 v0.2 |
| Parecer do analista (PRM_001) | Aprovado, sem ressalvas abertas |
| Autorização desta fundação | Proprietário instruiu executar o PRM_002 |
| Aprovação de produção / identidade corporativa | Não concedida |

## O que esta identidade é

Instrumento temporário de teste da API técnica local. Não é login operacional, não é token Spider e não habilita ação financeira.

Habilitação somente com **os dois** controles:

1. perfil Spring `local-demo`
2. flag `ACTIONFINANCE_DEMO_AUTH_ENABLED=true`

Ausência de qualquer um deixa os endpoints protegidos em 401. Flag ativa com tokens ausentes, repetidos ou curtos impede a subida (`IllegalStateException`), sem imprimir os valores.

## Tokens

Gerados em `scripts/dev/setup-local.ps1`, gravados em `.local/demo-tokens.env` (ignorado pelo Git). Sem credencial padrão no código, frontend, URL, documentação ou resposta. Comparação por `MessageDigest.isEqual` no filtro Spring Security.

O frontend desta etapa **não** coleta, armazena nem envia token.

## Principais fictícios (UUIDs estáveis)

| Papel | actorId | Empresa autorizada |
|---|---|---|
| Operador empresa A | `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1` | `11111111-1111-4111-a111-111111111111` |
| Consulta empresa A | `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2` | `11111111-1111-4111-a111-111111111111` |
| Consulta empresa B | `bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2` | `22222222-2222-4222-a222-222222222222` |

Permissões técnicas atuais: `system:read`, `company-context:read`. Não existe papel aprovador de pagamento. Nomes de permissões financeiras futuras não habilitam endpoint.

O token determina o principal. Headers `X-Actor-Id`, `X-Company-Id`, `X-Role` e `X-Permissions` não promovem privilégio. A query `companyId` é validada contra os vínculos do principal: sem acesso → 403 com mensagem uniforme `Não foi possível atender esta consulta.`

## Cadeia HTTP

- Stateless Bearer; sem cookie, HTTP Basic ou formulário nesta etapa.
- CSRF desabilitado **somente** porque a cadeia é Bearer stateless. Sessão futura por cookie exige revisão explícita de CSRF.
- CORS: origens locais explícitas (`http://127.0.0.1:5179`, `http://localhost:5179`). Sem wildcard e sem `allowCredentials`.
- Listener do perfil demo em `127.0.0.1` (não público). Com demo habilitado, bind efetivo `0.0.0.0`, `::` ou não loopback impede a subida.
- Rotas não previstas: `denyAll` (401 anônimo, 403 autenticado). `/api/v1/access/me` exige `system:read`; `/context` exige `company-context:read`.
- Erro estável: `code`, `message`, `correlationId`. Correlação gerada no servidor ou aceita após validação `[A-Za-z0-9_-]{8,80}`; eco em `X-Correlation-Id`. Não é autorização nem idempotência.
- Actuator: só `health` (liveness/readiness). Sem `env`, `mappings` ou detalhes.

## Ambientes

| Ambiente | Demo auth |
|---|---|
| local-demo + flag + tokens válidos | Adapter temporário ativo |
| Sem perfil, sem flag, tokens incompletos | Negado / falha de startup |
| Produção futura | Fora desta etapa; migration e identidade corporativa terão desenho próprio |

## Acesso de produto (PRM_006)

OIDC Authorization Code + sessão JDBC. Identidade = issuer + subject. Autorização só no banco ActionFinance. Cookie `AFSESSION` host-only, HttpOnly, Secure em produção, SameSite=Lax, Path=/, sem Domain compartilhado. CSRF nas escritas e no logout. Reavaliação do vínculo a cada pedido. Perfil `production` recusa demo e falha se OIDC essencial faltar (sem imprimir segredos).

Sair do ActionFinance ≠ sair do provedor.

Comando `scripts/ops/access-admin.ps1` (dry-run disponível). Sem senhas. Sem cadastro público.

## Limitação

A identidade demo permanece só no perfil `local-demo`. O provedor OIDC **real** ainda não foi provisionado; o ensaio usa `mock-oauth2-server` descartável.
