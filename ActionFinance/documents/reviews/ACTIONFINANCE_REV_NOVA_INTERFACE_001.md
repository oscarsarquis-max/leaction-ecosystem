# ACTIONFINANCE_REV_NOVA_INTERFACE_001 — Nova interface do ActionFinance

Versão 0.4 — 02/10/2026. Imagem FE publicada no serviço existente. Hosted UI clássico preservado no client Finance. Aceite: **NÃO**. Sem autoaprovação. Não encerra PRM_009, canónica, Pay, APPLY, PRM_007 nem a prova da Spider.

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_NOVA_INTERFACE_001 |
| Prompt | [ACTIONFINANCE_PROMPT_NOVA_INTERFACE_001](../prompts/ACTIONFINANCE_PROMPT_NOVA_INTERFACE_001.md) (adendos de continuidade e publicação no mesmo arquivo) |
| Parecer | [ACTIONFINANCE_REV_NOVA_INTERFACE_001_PARECER_ANALISTA](ACTIONFINANCE_REV_NOVA_INTERFACE_001_PARECER_ANALISTA.md) |
| Produto | ActionFinance apenas |
| Modelo físico | Sem mudança. DAT_001 permanece 0.94; não há versão física nova |
| Aceite | Não atribuído ao executor |

## Matriz implementado / publicado / verificado / pendente

| Superfície | Implementado | Publicado | Verificado | Pendente |
|---|---|---|---|---|
| Shell sem sidebar, faixa `#1603AD`, marca branca | Sim | Sim — SPA `index-kUHqqCK-.js` no origin | HTML/CSS/JS públicos; capturas locais 360/768/1280 | Telas autenticadas no origin (sessão humana) |
| Recebimentos / Pay como origem / filtros reais | Sim | Sim (mesmo bundle) | Bundle contém rótulos; capturas locais com API simulada | Lista/detalhe públicos com dados reais, sem escrita de teste |
| Detalhe cobrado/pago/situação | Sim | Sim | Capturas locais | Idem |
| Viewer sem escrita | Sim — Mais esconde Registrar | Sim | `App.test.tsx` | Troca de empresa / revogação no origin |
| Hosted UI clássico Finance | Sim — `SetUICustomization` 19:24 UTC | Já estava aplicado; **não** reaplicado | CSSVersion `20261002192427`; deep link público → login branded | Senha/MFA/recuperação com e-mail |
| Retorno ao destino interno | `sessionStorage` + allowlist no bundle | Código publicado (`af.returnPath`) | Testes locais; bundle público contém a chave | Loop autenticado no origin (sessionStorage local ≠ prova pública) |
| Logout / reentrada sem loop | Hold em `login=failed` / `logout=1` | Sim | Teste local + 302 OIDC | Logout público autenticado |

## Estado separado

| Estado | Situação |
|---|---|
| Implementado local | Sim — commit `6914e84aa17bd13214355b419601b749093bfb73` |
| Validado (gates FE) | `npm test` 47/47, `npm run lint`, `npm run build`, `npm audit --omit=dev` 0. Ambiente: Vitest/jsdom no `frontend/`, 02/10/2026 |
| Validado (browser local) | Capturas com **API simulada no Playwright**, não jornada financeira real |
| Branding Cognito | Preservado. Client `275ig9d7lfi0j7if9rqe374rqc`. `ALL` vazio. `ManagedLoginVersion=1` |
| Publicado (imagem FE) | Sim — 02/10/2026 20:33–20:37 UTC |
| Aceito | Não |

## Publicação (canal existente)

A SPA vai no JAR do backend. Não houve deploy separado de frontend.

| Peça | Valor |
|---|---|
| Commit | `6914e84aa17bd13214355b419601b749093bfb73` na branch `feat/prm-009-public-receipt-sync` |
| Conjunto | Só recorte de interface (FE, docs, pranchas, pacote Cognito). Sem Java/V13/PRM_009/terraform/outros produtos |
| Worktree de build | `C:\Projetos\.wt-af-ui` em detached `6914e84a` — backend do commit, sem working tree sujo |
| JAR | sha256 `2232cca5cb3dbd53119a8702d1840a3c57c74acf6fa83479ebf55ef8c4f14c44` |
| Tag local | `actionfinance:nova-interface-6914e84a` |
| Digest ECR | `sha256:b69787a237f9b41947d7bf9283961304d769cb8b51c48e769e2f491b7803826b` |
| Tarefa | `actionfinance-web:7` · desired=1 · running=1 · rollout COMPLETED |
| Origin | `https://actionfinance.actionhub.com.br` readiness **200** (reconfirmado 20:41 UTC) |
| SPA observada | `/assets/index-kUHqqCK-.js` · `/assets/index-BCp1Yj9J.css` (`--brand-mark:#1603ad`) |
| `system/info` sem sessão | **401** `UNAUTHORIZED` — não é prova de flags; flags ficam no bundle e no login autenticado |
| Imagem anterior (rollback) | `actionfinance-web:6` · `sha256:ba58fab9c0b1911f9bda12d3014c3c1b0fa29fbd02c01eb57e168127d94a1a90` |

Ordem: Cognito já estava aplicado → build no commit isolado → push ECR → `register-task-definition` só com troca de imagem → `update-service` → wait stable. Sem `terraform apply`. Sem restart da Spider. Sem alteração de Pay/Hub/Panne. Sem atomicidade entre Cognito e imagem.

Reversão FE: `python scripts/ops/register-af-web-image.py sha256:ba58fab9c0b1911f9bda12d3014c3c1b0fa29fbd02c01eb57e168127d94a1a90` e apontar o serviço a `actionfinance-web:6`. Reversão Cognito: `ops/aws/cognito-hosted-ui/rollback-hosted-ui.ps1 -Apply` (snapshot vazio deste client).

## Levantamento e diferenças às pranchas

Rotas preservadas. Sem Visão geral, busca global, Personalizar, união títulos+Pay, cliente/processador inventados. Pay = sistema integrado. Ausência ≠ zero.

Cognito clássico **não** replica a prancha 03: logo centrada no banner do cartão; rótulos `Username` / `Password` / `Sign in` em inglês; recuperação nativa; chrome cinza do serviço. Sem HTML livre, sem tela intermediária de senha no AF.

## Cognito (conferido, não reaplicado)

| Item | Estado em 02/10/2026 20:35 UTC |
|---|---|
| CSSVersion | `20261002192427` (inalterado) |
| ImageUrl | CloudFront do client Finance |
| `ClientId=ALL` | Vazio |
| Deep link `/pay-receipts` anónimo | 200 HTML da SPA, depois Hosted UI branded (`public-deeplink-pay-1280.png`) |
| OIDC start | 302 para o mesmo client e `redirect_uri` interno |

## Gates e regressão controlada

Ambiente explícito: **Vitest 4 + jsdom**, fixtures identificadas em `App.test.tsx` / `PayReceiptsPage.test.tsx` / `api.test.ts`. **Não** é local-demo com Postgres nem escrita em produção.

Coberto na suíte: rascunho/registro, retry de transporte, correção após 400, baixa, conflito, estorno, extrato, permissão por empresa, viewer sem `titles:write` (some **Novo recebível** e **Registrar recebível**), retorno interno allowlist, OIDC sem clique em Entrar, `login=failed` sem loop.

Não exercitado como jornada real: local-demo ponta a ponta; senha/MFA; e-mail de recuperação; logout autenticado no origin; troca de empresa no origin.

## Verificação pública (sem sessão)

| Prova | Resultado |
|---|---|
| Readiness | 200 |
| SPA no `/` e `/pay-receipts` | `index-kUHqqCK-.js` (20:41 UTC) |
| Bundle | `af.returnPath`, Recebimentos, Pagamentos, Contas e caixa, Novo recebível, Não informado, Action Finance Capital |
| Entrada `/pay-receipts` e `/oauth2/authorization/actionfinance` | Hosted UI Finance, client `275ig9d7lfi0j7if9rqe374rqc`, `redirect_uri` interno; capturas `public-deeplink-pay-1280.png` / `360` e `public-oauth-start-1280.png` |
| Escrita financeira de teste | **Não** feita |

`returnPath` nulo nas capturas Playwright após o 302: o storage fica na origem AF e o browser já está no Cognito. Isso **não** comprova o retorno autenticado.

## O que falta (dependência humana)

Abrir `https://actionfinance.actionhub.com.br/pay-receipts`, autenticar no Hosted UI (e MFA se aparecer). O executor continua a prova: retorno ao deep link, navegação, logout/reentrada, troca de empresa se houver mais de uma. Não enviar senha, MFA ou cookies neste chat. Não disparar e-mail de recuperação.

## Preservação

Sem seed, baixa, cobrança, alteração de saldo ou contrato Spider/Pay. Sem restart da engine. PRM_009 / Spider / canónica / APPLY / PRM_007 permanecem separados.
