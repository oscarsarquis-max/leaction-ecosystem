# ACTIONFINANCE_REV_CORRECAO_LOGOUT_009 — Correção do comando Sair

Versão 0.1 — 05/10/2026. Recorte de sessão. Aceite: **NÃO**. Não reabre nem substitui ACTIONFINANCE_PRM_009 de integração. Não encerra prova Spider, canónica, Pay, APPLY nem PRM_007.

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_CORRECAO_LOGOUT_009 |
| Prompt | [ACTIONFINANCE_PROMPT_CORRECAO_LOGOUT_009](../prompts/ACTIONFINANCE_PROMPT_CORRECAO_LOGOUT_009.md) |
| Evidência do incidente | Captura do proprietário em `/receivables` após Sair — Oscar Sarquis, Loja de Pães, UI autenticada. Favicon 404 e aviso de inicialização do console **não** são a causa. |
| Produto | ActionFinance apenas |
| Modelo | Sem mudança |

## Reprodução

1. Origin público `https://actionfinance.actionhub.com.br/receivables` com sessão AF autenticada (web:9, `index-DtMFC6jP.js`).
2. Clique em **Sair** (botão `type=button` visível no cabeçalho; sem overlay interceptando).
3. A lista autenticada reaparece. O operador permanece identificado.

O clique chega ao handler. Em lista, `dirtyRef` é falso, portanto não há diálogo silencioso. Não foi observado GET mutável no lugar do POST. O 404 de `/favicon.ico` é irrelevante.

## Causa (caso 4)

Fronteira: SPA `App.tsx` + `api.ts` `signOut`. Servidor POST `/logout` (CSRF + invalidação de `AFSESSION`) **não** foi alterado e já devolve 204 com `Accept: application/json`.

1. `requestSignOut` chamava `navigate("/", true)` após logout confirmado.
2. `pathOf()` lê só `pathname`. `/?logout=1` tem path `/`.
3. O efeito `path === "/"` redirecionava para `/receivables`, apagando `logout=1`.
4. Sem hold, o efeito OIDC chamava `startOidcLogin()` e a sessão ainda válida no Cognito recriava a sessão AF.
5. Havia corrida: `signOut` zera a sessão em memória **antes** da navegação para o hold.
6. `signOut` aceitava qualquer `response.ok` (um follow de 302→200 HTML poderia parecer confirmação).

Casos 1–3 não explicam a captura: o controle dispara, o servidor já invalida cookie AF, e a UI volta autenticada — típico de reentrada OIDC, não de clique morto nem de estado local órfão.

## Correção

- Hold explícito `/?logout=1` e `logoutHoldRef` **antes** do POST, para o efeito OIDC não disparar quando a sessão some.
- `/` só vira `/receivables` se **não** houver `logout=1` / `login=failed`.
- `signOut` confirma só com **204**, ou 401 de `/logout` **e** 401 de `/api/v1/access/me`. 200/403/rede não encerram sessão válida.
- Após confirmação: limpa `af.returnPath`, filtros transitórios e estado em memória; mostra saída com **Entrar novamente**.
- **Sair** permanece `type=button`, com `Saindo…` / `aria-busy` / sem clique duplo.
- Rascunho sujo: `window.confirm` visível; recusa mantém a página.
- Ao voltar à aba, revalida `/access/me`. 401 oculta dados e vai ao hold. Falha de transporte **não** finge logout.

## Semântica AF / Cognito

| Sessão | O que Sair faz |
|---|---|
| ActionFinance | POST `/logout` autenticado + CSRF. Invalida HTTP session, limpa `AFSESSION` e `X-XSRF-TOKEN`. Resposta JSON: 204. |
| Cognito | **Não** é encerrada. Não há logout do provedor, não há alteração de pool, client ou URLs permitidas. |

Entrada anônima normal continua a abrir o Hosted UI. Depois de **Sair explícito**, essa regra **não** reinicia sozinha. **Entrar novamente** é ação do operador e usa `/oauth2/authorization/actionfinance` (não reutiliza callback antigo). `sanitizeReturnPath` rejeita `logout=1`.

Não é logout global de Hub, Monitor, Panne ou outros clients.

## Evidências

### Antes

SPA pública web:9 redirecionava `/` → `/receivables` mesmo com `logout=1`. Teste novo reproduz a regressão: sem hold, `startOidcLogin` seria chamado após Sair.

### Depois (controlado)

`npm test` 60/60, incluindo:

- Sair OIDC → hold `/` + `?logout=1`, POST `/logout` JSON+CSRF, sem `startOidcLogin`, sem `af.returnPath`.
- Recarga de `/?logout=1` sem loop.
- Recusa de rascunho sujo.
- Teclado (Enter) e estado **Saindo…**.
- Aba visível com `/access/me` 401 não mantém dados.
- 200 HTML, CSRF 403 e 401 de logout com `/me` ainda 200 **não** confirmam saída.

Capturas locais (API simulada): `documents/reviews/screenshots/correcao-logout-009/`. Log sanitizado: `documents/reviews/evidence/correcao-logout-009/local-logout.json`.

### Pública — hold sem sessão (origin web:10)

`prove-public-logout-hold-009.mjs` em 05/10/2026: `https://actionfinance.actionhub.com.br/?logout=1` mostrou **Entrar novamente**, recarga manteve `logout=1`, `/api/v1/access/me` 401, nenhum arranque OIDC. SPA `index-DjW5pNjQ.js`. Evidência: `evidence/correcao-logout-009/public-hold.json`.

### Pública autenticada

POST `/logout` com sessão real no origin ainda depende de um login humano agrupado. Sem senha/MFA/cookies neste relatório. O hold público **não** substitui essa prova. **Não** se afirma “logout autenticado passou” só pelo hold ou pela ausência visual de dados.

## Gates

| Gate | Resultado |
|---|---|
| `npm test` | 60/60 |
| `npm run lint` | ok |
| `npm run build` | `index-DjW5pNjQ.js` / `index-4KjDmnSk.css` |
| Java / security | Sem alteração. POST `/logout` + CSRF + `invalidateHttpSession` preservados. |
| Favicon | 404 permanece; fora da causa. |

## Publicação

| Peça | Valor |
|---|---|
| Commit isolado | `b2ced277` Hold ActionFinance signed-out state after Sair so OIDC does not restart. |
| Worktree | `C:\Projetos\.wt-af-ui` detached |
| JAR | sha256 `34215d905dfa8bf79d054f50609f712aa141334131ae5820e87564fdfb4afe96` |
| Tag local | `actionfinance:logout-009-b2ced277` |
| Digest ECR | `sha256:38cbf68dad17f9482567b501fabeb519c6a1614b1f87ebca2d6c30d525be54a2` |
| Tarefa | `actionfinance-web:10` · desired=1 · running=1 · COMPLETED |
| Origin | `https://actionfinance.actionhub.com.br` HTML 200 · health UP |
| SPA pública | `/assets/index-DjW5pNjQ.js` · `/assets/index-4KjDmnSk.css` |
| Rollback | `actionfinance-web:9` · `sha256:fec29234a5b003e1fddbe57efaa480f65ee8fe4bbfa36e7897b74c55043cfe49` |
| Cognito / Spider / Hub / Pay / Panne | Não alterados |

Sem `terraform apply`. Sem restart da Spider. Sem reaplicar branding Cognito.

## Limitações

- Conteúdo já desenhado em outra aba pode permanecer visível até a aba voltar a ficar visível; o acesso servidor da sessão AF encerrada responde 401.
- Sessão Cognito continua válida: **Entrar novamente** pode autenticar sem novo desafio se o provedor ainda reconhecer o operador.
- Aceite continua com analista/proprietário.
