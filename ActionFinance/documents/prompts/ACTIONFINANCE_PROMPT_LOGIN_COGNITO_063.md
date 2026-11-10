# ACTIONFINANCE — Prompt 063 · Tela de login (Cognito) na identidade nova

A tela de login do Finance (Hosted UI clássico do Cognito) continua azul. O Claude entregou o patch **P02** com o CSS e o logo novos. Este prompt aplica o patch e atualiza o Cognito.

## Regras
- Mexer só no app client `actionfinance-confidential` do pool do Finance, com os scripts que já existem em `ActionFinance/ops/aws/cognito-hosted-ui/`. Não tocar em outros clients ou pools (Hub, Monitor, Panne, Spider).
- Sem deploy da aplicação, então sem passo 0. Sem testes.
- **Não** rodar `make-logo.py`: ele recria o logo azul antigo.

## Passos
1. **Aplicar o patch** na branch `feat/actionfinance-extrato-032`:
   `git am -3 "C:\Projetos\claude\2026-11-09-actionfinance-corporate-analyser\patches\P02-login-cognito-identidade.patch"`
   O patch parte de `11c7ac4` e só toca em `ops/aws/cognito-hosted-ui/` (CSS, logo, README).
2. **Atualizar o Cognito:**
   - `cd C:\Projetos\ActionFinance\ops\aws\cognito-hosted-ui`;
   - `.\apply-hosted-ui.ps1` (dry-run: confirma o client e grava `snapshot-atual.json` com a versão azul);
   - `.\apply-hosted-ui.ps1 -Apply`.
3. **Conferir:**
   - `GetUICustomization` devolve o CSS novo (`#4a2a1e`, `#2f5d4b`);
   - abrir a página pública de login (sem entrar): faixa marrom, logo branco e botão verde.
   - Rollback disponível: `.\rollback-hosted-ui.ps1`.

## Entrega
- `documents/reviews/ACTIONFINANCE_REV_LOGIN_COGNITO_063.md` (curto), com o hash do patch aplicado, o resultado do apply e uma captura da tela de login.
- Copiar este prompt para `documents/prompts/`. Commit e push.
