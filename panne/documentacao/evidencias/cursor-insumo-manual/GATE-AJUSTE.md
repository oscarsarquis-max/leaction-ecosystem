# Gate final do candidato — overflow e baseline de login

Ajuste sobre `27dbfcc`. Sem publicação.

## 1. overflow-x

`html { overflow-x: clip }` voltou a `visible`, como em `d0a3451`. Não há `overflow-x: clip` no CSS. Largura das rotas novas fica em `.manual-path` e `.estoque-util` (`max-width: min(…, 100%)`, `min-width: 0`, `overflow-wrap`). Em 390 px, `documentElement.scrollWidth === clientWidth` (390) em estoque, consolidar e abertura; smoke igual em `/entrar` e `/gestao/custos`. Ver `capturas-gate/`.

## 2. login-editorial 6/7 — pendência de `d0a3451`

`LoginPage.tsx`, `login-editorial.test.tsx` e `GlobalAssistant.tsx` são idênticos a `d0a3451` (diff vazio). Worktree destacado em `d0a3451`: o mesmo arquivo `login-editorial.test.tsx` deu **6 passed / 1 failed** — `ajuda pública não chama rede` procura heading `/Ajuda para entrar/` e a gaveta já titula `Gigio`. **Pendência preexistente. Login não foi alterado neste pacote.**

## 3. CLI de owner — não executado

`tests/test_onboarding_access.py::test_owner_without_bypass_can_issue_and_keeps_force` **não foi executado** neste candidato (papel Docker sem dono de `access_credential`). Não conta como aprovado. O código de onboarding não mudou em relação a `d0a3451`.
