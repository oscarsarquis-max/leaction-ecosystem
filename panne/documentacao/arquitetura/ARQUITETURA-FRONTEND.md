# Arquitetura frontend

```
src/auth          AuthProvider (OIDC PKCE ou fake)
src/session       organização ativa e ApiClient
src/api           cliente tipado, erros, fixtures
src/components    shell, estados, permissão
src/pages         quadro, planos, ordens, rastreio, ficha
src/styles        tokens, app, impressão
```

Dependências novas: `react-router-dom`. Dev: ESLint, jsx-a11y, user-event, axe-core, vitest-axe.

Tipos em `src/api/types.ts` acompanham o OpenAPI de produção (decimais como string). Sem biblioteca de estado global.

Cache em memória no `ApiClient`, invalidado na troca de organização e no logout.
