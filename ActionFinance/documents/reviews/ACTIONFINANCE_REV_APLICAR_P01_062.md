# ACTIONFINANCE_REV_APLICAR_P01_062

10/11/2026. O patch P01 de identidade foi aplicado sobre a 0.2.14 e publicado como 0.2.15. Spider, Loja e Hub não foram alterados. Não houve mudança de banco.

A cópia do prompt está em [ACTIONFINANCE_PROMPT_APLICAR_P01_062.md](../prompts/ACTIONFINANCE_PROMPT_APLICAR_P01_062.md).

## Patch

`git am -3` de `P01-identidade-loja-gestao.patch` sobre `446c6124`, sem conflito. O commit aplicado é `9fd3fc549a48cb250d5e04bcdb917700069ca079`. Só entra em `ActionFinance/frontend/src`: faixa marrom, ação verde, DM Sans, Playfair e o logo `af-logo-vazado-branco`.

As cores `#1603ad`, `#1800ad`, `#24219b` e `#14143d` não restam em `.css` nem em `.tsx`. As cores fixas que o Início do 058B ainda tinha (superfície, borda, sucesso e aviso) passaram a usar os tokens.

## SSH

Os security groups `actionfinance-svc` e `actionfinance-db` continuam sem regra na porta 22. O serviço roda em Fargate, sem SSH. Nenhuma regra foi aberta.

## Publicação 0.2.15

| Item | Valor |
|---|---|
| Versão | 0.2.15 |
| Banco | sem migração |
| Task web | `actionfinance-web:32`. Copiada da `:31`; só a imagem mudou |
| Flyway na web | `false` |
| Perfil | `production`. Sincronização de recebimentos ligada |
| Imagem na task | `sha256:14dc23c13ebfafae492f415b86770f44c589b7f89addac2c83a9c58e0b932516` (linux/amd64) |
| Tag `0.2.15` no ECR | índice `sha256:2cc84feb04ec155b62887436188886c862a6b72942a54c7825bfbb8a464a9698`. A task usa o digest amd64, não o índice |
| Rollout | `COMPLETED`, desired 1, running 1, em 2026-11-10T14:59:45-03 |
| Health | `GET /actuator/health` 200, `{"status":"UP","groups":["liveness","readiness"]}` |
| SPA | `index-Ce_dW76n.js` contém `af-logo-vazado-branco`; `index-DdyZWOF5.css` contém `DM Sans` |

Retorno da aplicação: `actionfinance-web:31`, a task do 058B, versão 0.2.14. Reverter a task não mexe no banco.

## Testes

Não rodei a suíte inteira.

`App.test.tsx`, `HomePage.test.tsx` e `AppShell.test.tsx`: 39 testes, 0 falhas. O teste do menu entrou porque o patch troca o logo da faixa.

## Capturas

Não havia sessão autenticada de produção, o mesmo limite do 058B. Não redefini senha para fabricar uma sessão. A prova pública é o pacote no ar, com o logo vazado e a DM Sans.
