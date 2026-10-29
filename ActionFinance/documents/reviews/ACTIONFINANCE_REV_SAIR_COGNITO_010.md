# ACTIONFINANCE_REV_SAIR_COGNITO_010 — Sair direto ao formulário Cognito

Versão 0.1 — 05/10/2026. Recorte de sessão. Aceite: **NÃO**. Não é o ciclo financeiro PRM_010. Histórico: [ACTIONFINANCE_REV_CORRECAO_LOGOUT_009](ACTIONFINANCE_REV_CORRECAO_LOGOUT_009.md) (não modificado). Esta orientação substitui só a tela intermediária de saída.

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_SAIR_COGNITO_010 |
| Prompt | [ACTIONFINANCE_PROMPT_SAIR_COGNITO_010](../prompts/ACTIONFINANCE_PROMPT_SAIR_COGNITO_010.md) |
| Produto | ActionFinance apenas |
| Modelo | Sem mudança |

## Sequência implementada

1. `POST /logout` AF autenticado + CSRF. Confirmação só com 204 (ou 401+/me 401). Invalida sessão e cookies `AFSESSION` / `XSRF-TOKEN`.
2. Navegador vai a `GET /access/cognito-logout` (rota interna, destino **não** vem de parâmetro do usuário).
3. Backend redireciona ao Hosted UI clássico: `https://actionfinance-253137917703.auth.us-east-2.amazoncognito.com/logout?client_id=<client Finance>&logout_uri=<origem>/oauth2/authorization/actionfinance`.
4. Cognito encerra a sessão de navegador deste domínio e devolve à rota Spring `/oauth2/authorization/actionfinance`.
5. Spring cria **nova** requisição OIDC (state/nonce novos) e abre o formulário personalizado.

A SPA não inventa `state`, não monta `/login` do Cognito e não reutiliza callback. `af.returnPath` é apagado no Sair explícito. Deep link anônimo continua podendo gravar destino interno autorizado.

Falha CSRF/rede: aviso recuperável, sessão AF preservada se o POST não confirmou. Se o POST confirmou e o provedor falhar, `/access/cognito-logout` pode ser repetido; `/<login=failed>` permanece só como falha, com **Entrar novamente**.

## Alcance da saída

| Peça | Observado |
|---|---|
| Pool | `us-east-2_GYIa11WvX` / `actionfinance-operators` |
| Client | único: `actionfinance-confidential` / `275ig9d7lfi0j7if9rqe374rqc` |
| Domínio Hosted UI | `actionfinance-253137917703.auth.us-east-2.amazoncognito.com` · Managed Login clássico |
| Outros pools | Panne, Monitor e Qmind são pools distintos. Este `GET /logout` não os atinge. |
| GlobalSignOut / devices | Não usados |
| IdP externo | AWS documenta que `/logout` **não** encerra sessão de IdP social/OIDC externo. O Finance usa o Hosted UI do próprio pool. |

Não há isolamento “por client_id” a reivindicar: o pool Finance tem um client só, e o cookie do Hosted UI vive neste domínio.

## Configurações alteradas

| Antes | Depois | Rollback |
|---|---|---|
| LogoutURLs: `https://actionfinance.actionhub.com.br` | + `https://actionfinance.actionhub.com.br/oauth2/authorization/actionfinance` | Remover essa URL; snapshot `ops/aws/cognito-hosted-ui/logout-urls-before-010.json` |
| Callbacks | Inalterados: só `/login/oauth2/code/actionfinance` | — |
| Branding CSS/logo | Não reaplicado | — |

`actionfinance.oidc.hosted-ui-origin` no JAR de produção (domínio público do Hosted UI). Sem curingas.

## Evidências

- Unidade: URL Cognito fixa; origem Hosted UI fora da AWS recusada; produção rejeita Hosted UI não-Cognito.
- `OidcAuthorizationCodeIT`: `GET /access/cognito-logout?logout_uri=https://evil.example` → 302 para o `/logout` Cognito com `logout_uri` interno `/oauth2/authorization/actionfinance`. POST `/logout` JSON 204 e `/me` 401 permanecem.
- Frontend 61/61: Sair confirma POST+CSRF e chama `/access/cognito-logout`; sem “Você saiu” / “Entrar novamente” no sucesso; rascunho recusado; teclado; aba 401.
- Referência AWS `/logout` (05/10/2026): `logout_uri` + `client_id` para destino permitido; `redirect_uri`+state só se o app já tivesse state OIDC — evitado de propósito.

Prova pública do percurso sem sessão AF (05/10/2026): `GET /access/cognito-logout?logout_uri=https://evil.example` → 302 Cognito `/logout` → 302 `/oauth2/authorization/actionfinance` → 302 `/oauth2/authorize` → 200 `/login` no domínio Finance. Formulário real com senha; zero “Entrar novamente”; `/api/v1/access/me` 401. Captura `screenshots/sair-cognito-010/1280-cognito-form.png`. Log `evidence/sair-cognito-010/public-form.json`.

Sair autenticado no origin (POST `/logout` 204 + 401 da API financeira **antes** da nova autenticação) ainda precisa de um login humano agrupado. Sem senha/MFA/cookies neste relatório.

## Publicação

| Peça | Valor |
|---|---|
| Commit isolado | `4e556ecd` Send ActionFinance Sair through Cognito logout to the Hosted UI form. |
| Worktree | `C:\Projetos\.wt-af-ui` detached |
| JAR | sha256 `79dd27b0bb00a349cf596d6fe22a6ed417da747f8ff0addabf72d41d32302830` |
| Tag local | `actionfinance:sair-cognito-010-4e556ecd` |
| Digest ECR | `sha256:06e067e772f65d37a0cf43c53022e32d9e0a76eb9841cfebaf75d684b28f953c` |
| Tarefa | `actionfinance-web:11` · desired=1 · running=1 · COMPLETED |
| Origin | HTML 200 · health UP · SPA `index-BE46S7oG.js` |
| Rollback imagem | `actionfinance-web:10` · `sha256:38cbf68dad17f9482567b501fabeb519c6a1614b1f87ebca2d6c30d525be54a2` |
| Rollback Cognito | LogoutURLs só `https://actionfinance.actionhub.com.br` |
| Spider / Hub / Pay / Panne | Não alterados |

## Limitações

Não se afirma aceite de segurança ou do produto. Recarregar/Voltar pode mostrar HTML antigo; API protegida deve responder 401 até nova autenticação. Aceite com analista/proprietário.
