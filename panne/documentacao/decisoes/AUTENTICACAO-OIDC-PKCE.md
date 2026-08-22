# Autenticação OIDC / PKCE

`AuthProvider` é a abstração.

Runtime real:

- Authorization Code + PKCE (S256)
- alvo Cognito User Pools
- issuer, client ID, redirect URI e scopes via `VITE_OIDC_*`
- sem client secret no navegador
- access token só em memória
- `code_verifier` e `state` no `sessionStorage` apenas durante o fluxo
- callback em `/callback`; logout limpa a sessão e, se configurado, redireciona ao logout do IdP

Desenvolvimento e testes:

- `VITE_AUTH_PROVIDER=fake` explícito
- proibido em `vite build` de produção e no construtor do fake quando `PROD`
- nenhum token real nos testes

Autorização visual: permissões de `/api/v1/me`. Claims e grupos do IdP não autorizam.
