---
title: SDD Autenticacao e Sessao
tipo: SDD
---

# Arquitetura de autenticacao

Este SDD define login, sessao e controle de acesso da plataforma. O objetivo e
autenticar usuarios com seguranca, emitir tokens de sessao e aplicar RBAC por tenant.

## Fluxo de login

Usuario informa e-mail e senha (ou SSO OIDC). A API valida credenciais, cria sessao
server-side, emite access token JWT de curta duracao e refresh token rotativo em cookie
HttpOnly. Logout invalida a sessao no servidor.

### Sessao e renovacao

Refresh tokens ficam em store Redis com TTL. Rotacao a cada uso evita reuso. Dispositivos
confiaveis podem manter sessao estendida com reautenticacao para acoes sensiveis.

## Componentes

Auth service (Flask), identity store em Postgres, gateway com middleware de JWT,
Action Hub como IdP opcional. Contratos: `/login`, `/refresh`, `/logout`, `/me`.
