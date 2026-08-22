# Autenticação e autorização

Ciclo de origem: CURSOR-010.

## Autenticação (Cognito / OIDC)

O provedor-alvo é Amazon Cognito User Pools. O backend permanece desacoplado pela porta `AccessTokenVerifier`.

- `CognitoAccessTokenVerifier` valida access tokens.
- `FakeAccessTokenVerifier` cobre testes comuns, sem rede.
- Configuração: emissor (`PANNE_OIDC_ISSUER`), app client (`PANNE_OIDC_CLIENT_ID`), audiência opcional e escopos.
- `sub` é string opaca. Não é forçado a UUID.
- Grupos do Cognito **não** são autorização canônica da Panne.
- Refresh token não é armazenado.
- Claim obtida só por decode, sem verificação criptográfica, é ignorada.

Validações: RS256, `kid`, emissor, expiração, `token_use=access`, `client_id`, `aud` quando presente, escopos exigidos e formato estrutural. Falha fechada.

## JWKS

Cache em memória por `kid`. `kid` desconhecido provoca uma atualização controlada. Timeout de rede configurável (`PANNE_JWKS_TIMEOUT_SECONDS`). Sem cache válido e JWKS indisponível → falha fechada (HTTP 503 sanitizado).

## Autorização interna

Associação à organização não libera todas as ações. A autorização é por permissão explícita no catálogo `permission` / `role_permission`.

Papéis aceitos (existentes + candidatos do ciclo, sem quebrar 001–009):

| Papel persistido | Equivalência |
|---|---|
| `owner` | `organization_owner` |
| `administrator` | `organization_admin` |
| `production` | `production_manager` |
| `technical_responsible` | — |
| `commercial` | — |
| `viewer` | — |
| `baker_operator` | novo |
| `regulatory_reviewer` | novo |
| `restricted` | sem permissões (teste e contenção) |

Permissões atuais: `identity.read_me`, `organization.read`, `membership.read`, `compliance.review`.

Não há senha local, autocadastro nem entrada automática em organização.

## Bootstrap do primeiro proprietário

Somente sessão administrativa, função `bootstrap_first_owner`. Sem endpoint HTTP. Passos: criar organização, `app_user` ativo, associação `owner` e vínculo `issuer+subject` em `auth_identity`. Documentado em [BOOTSTRAP-PRIMEIRO-PROPRIETARIO.md](../produto/BOOTSTRAP-PRIMEIRO-PROPRIETARIO.md).
