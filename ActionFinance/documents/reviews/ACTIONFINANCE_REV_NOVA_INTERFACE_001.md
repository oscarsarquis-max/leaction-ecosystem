# ACTIONFINANCE_REV_NOVA_INTERFACE_001 — Nova interface do ActionFinance

Versão 0.3 — 02/10/2026. Hosted UI clássico aplicado só no client Finance. Aceite visual e funcional: **NÃO**. Imagem frontend/AF **não** republicada. Sem autoaprovação. Não encerra PRM_009, canónica, Pay, APPLY, PRM_007 nem a prova da Spider.

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_NOVA_INTERFACE_001 |
| Prompt | [ACTIONFINANCE_PROMPT_NOVA_INTERFACE_001](../prompts/ACTIONFINANCE_PROMPT_NOVA_INTERFACE_001.md) |
| Base complementar | [ACTIONFINANCE_RETOMADA_FUNCIONAL_001](../prompts/ACTIONFINANCE_RETOMADA_FUNCIONAL_001.md) — proposta; não implementada inteira |
| Produto | ActionFinance apenas |
| Modelo físico | Sem mudança. DAT_001 permanece 0.94; não há versão física nova |
| Publicação | Hosted UI Finance aplicado; imagem FE/ECS **não** aplicada |
| Aceite | Não atribuído ao executor |

## Estado separado

| Estado | Situação |
|---|---|
| Implementado local | Sim — frontend ActionFinance neste working tree |
| Validado (gates FE) | Sim — `npm test` 46/46, `npm run lint` |
| Validado (browser 360/768/1280) | Recorte local com API simulada + Hosted UI público real (login e recuperação, sem senha) |
| Branding Cognito | Aplicado em 02/10/2026 19:24 UTC no client `275ig9d7lfi0j7if9rqe374rqc` apenas. `ClientId=ALL` permanece vazio. Managed login **não** ligado (`ManagedLoginVersion=1`) |
| Publicado (imagem FE) | Não |
| Aceito | Não |

## Levantamento (código atual × prancha)

Rotas e funções existentes preservadas: `/receivables`, `/payables`, `/financial-accounts`, `/catalogs`, `/settlements/:id`, `/pay-receipts`, `/pay-receipts/:id`. Deep links antigos permanecem. Sem “Visão geral”, conciliação, fluxo de caixa, transferências ou centros de custo.

API de recebimentos Pay: `GET /api/v1/pay-receipts` devolve o conjunto da empresa (overview, não página). Campos úteis: `orderReference`, `transactionId`, `processorReference`, `normalizedStatus`, `amountMinor`/`amountAbsent`, `paidAmountMinor`/`paidAmountAbsent`, `classification`, `testLabeled`, `originCreatedAt`, `originUpdatedAt`, `originRevision`, `environment`, `lastCorrelationId`, histórico de revisão. **Não há** contraparte, método, conta de destino, nome do processador, estabelecimento, origem comercial distinta de Pay, nem consulta individual. Sync é `POST /api/v1/pay-receipts/sync` por empresa via Spider.

| Recurso da prancha | Situação |
|---|---|
| Sidebar persistente | Removida |
| Busca global de transações | Não implementada — não há contrato |
| “Buscar ou ir para” | Não — evitaria localizador falso |
| Presets / Personalizar | Não — não haveria ação |
| União títulos + Pay numa lista | Não — entradas separadas (A receber × ActionHub Pay) |
| Cliente / avatar / eventos fictícios | Não transportados |
| Filtro por estabelecimento / processador / método | Lacuna de contrato; filtro inerte evitado |
| Branding HTML livre no Cognito | Fora do Hosted UI clássico; ver § Cognito |
| Pranchas PNG | Copiadas em `documents/ux/interface-aprovada/` |

Filtros da lista Pay: referência, período com rótulo “Atualização na origem”, situação presente no conjunto, pendência. Aplicados no conjunto devolvido pelo servidor (coleção completa da empresa). Sem filtro local de uma página fingindo pesquisa total.

## Identidade e navegação

- Faixa `#1603AD` (amostra do `actionfinance-blue.png`) com lettering branco vazado, largura 200 na faixa de 56 px.
- Navegação horizontal: Recebimentos, Pagamentos, Contas e caixa (se autorizado), Mais. Sem dashboard.
- Mobile: barra inferior Receber / Pagar / Contas / Mais. Sem menu lateral persistente.
- Subnavegação de área: A receber × Recebimentos ActionHub Pay; A pagar.
- Botões primários azuis com texto branco. Âmbar só em pendência, com texto.
- Empresa visível e alterável; troca continua explícita.

Diferenças necessárias em relação às pranchas: sem “Buscar ou ir para” e sem Visão geral; sem união de origens; Pay rotulado como sistema integrado, não origem comercial; sem Personalizar.

## Recebimentos

Pay é origem, não o domínio inteiro. Lista Pay: origem, referência compacta + copiar, contraparte “Não informado” (campo inexistente), data de atualização na origem, cobrado, pago, situação, pendência. Ausência = “Não informado”.

Sincronização concluída, resultado daquela execução e pendências atuais são blocos distintos. `EMPTY` não minimiza pendências existentes.

Detalhe em dois níveis + rastreio expansível. “Atualizar da origem” declara alcance por empresa. Sem “aprovar como real”. Voltar à lista restaura filtros.

## Cognito (somente cliente Finance)

| Item | Verificado |
|---|---|
| Tipo | Hosted UI clássico. Domínio `actionfinance-253137917703.auth.us-east-2.amazoncognito.com`. `ManagedLoginVersion=1` |
| Pool | `us-east-2_GYIa11WvX` (`actionfinance-operators`) |
| App client | `actionfinance-confidential` / `275ig9d7lfi0j7if9rqe374rqc`. Único client do pool. Authorization Code, scopes `openid` `profile` |
| Outros pools | `spider-sandbox-monitor`, `panne-prod`, `qmind-homolog-users` **não** tocados. `GetUICustomization` com `ClientId=ALL` no pool Finance permanece vazio |
| Login | Username (não é necessariamente e-mail de contacto) |
| Recuperação | Página nativa `forgotPassword`; e-mail verificado; MFA de software opcional — desafio MFA **não** exercitado |
| Branding | `SetUICustomization` em 02/10/2026 19:24 UTC. CSSVersion `20261002192427`. Logo ≤100 KB (34427 bytes, 350×178) recortada do `actionfinance-blue.png` oficial. Snapshot prévio em `ops/aws/cognito-hosted-ui/snapshot-atual.json` (`HadCustomization=false`) |

Entrada sem sessão chama `/oauth2/authorization/actionfinance` sem clique em Entrar. Prova pública: `GET https://actionfinance.actionhub.com.br/oauth2/authorization/actionfinance` → **302** para o Hosted UI Finance com `client_id=275ig9d7lfi0j7if9rqe374rqc` e `redirect_uri=https://actionfinance.actionhub.com.br/login/oauth2/code/actionfinance`. Falha, logout e expiração mostram “Entrar novamente”.

Retorno à página pedida: o backend continua a devolver `/receivables` ou `/access-pending` após o code (sem open redirect). O frontend grava o caminho interno em `sessionStorage` (`af.returnPath`) antes do OIDC e só restaura prefixos `/receivables`, `/payables`, `/financial-accounts`, `/catalogs`, `/pay-receipts`, `/settlements`. Recusa `//`, `://`, `login=failed` e `logout=1`. Testes em `api.test.ts` e `App.test.tsx`.

### Diferenças impostas pelo Cognito clássico (não são falha do recorte local)

Comparação com [prancha 03](../ux/interface-aprovada/03-acesso-cognito-desktop-mobile.png) e capturas em `documents/reviews/screenshots/nova-interface/cognito-login-*.png` / `cognito-forgot-*.png`:

| Prancha | Hosted UI clássico real |
|---|---|
| Faixa azul de largura total + lettering vazado no campo | A marca entra como **imagem centrada no banner azul** do cartão Cognito. O lettering branco está no PNG oficial; o serviço não recorta letras no HTML |
| Fundo da página `#f3f5fb` contínuo | O CSS `background-customizable` foi enviado; o chrome clássico ainda desenha o cartão sobre um cinza próprio. Não há HTML livre para apagar esse quadro |
| Título “Entre no ActionFinance”, “Usuário”, “Entrar” | Rótulos e botão permanecem os do Cognito (`Username`, `Password`, `Sign in`, `Forgot your password?`). CSS não troca texto |
| “Esqueceu sua senha?” no cartão de login | Link nativo existe; a recuperação é outra página (`forgotPassword`), com o mesmo banner/marca |
| Rodapé com slogan | Inexistente no clássico; não inventado |
| Cartão customizado | Layout, tipografia e idioma do formulário são do Cognito |

Não foi criada tela intermediária de senha no Finance. Não há iframe nem senha no backend do AF.

## Preservação

Sem reparo histórico, seed de produção, baixa automática, alteração de saldo, nova cobrança ou execução de pagamento. Consulta integrada permanece AF → Spider → Pay → Spider → AF. Sem restart da engine Spider. Viewer/operator, empresa, idempotência e retry de resultado desconhecido não foram alterados neste recorte, salvo a persistência do destino interno no OIDC.

## Matriz requisito → alteração → evidência → limitação

| Requisito | Alteração | Evidência | Limitação |
|---|---|---|---|
| Marca branca sobre azul | `BrandLogo` blue no header `#1603AD` | `AppShell.tsx`, `app.css`, `1280-cabecalho-marca-azul.png` | — |
| Sem sidebar | Nav horizontal + barra inferior + Mais | `AppShell.test.tsx` | — |
| Recebimentos legíveis | Lista/detalhe Pay reescritos | `PayReceiptsPage.test.tsx` | Sem união com títulos |
| Acesso direto OIDC | Auto `startOidcLogin` | `App.test.tsx`; 302 público para o Hosted UI | Senha humana não submetida |
| Retorno à página pedida | `sanitizeReturnPath` + `sessionStorage` | `api.test.ts`, `App.test.tsx` | Loop completo com senha não exercitado |
| Branding Cognito | `SetUICustomization` no client Finance | `applied.json`, capturas `cognito-login-*` / `cognito-forgot-*` | Limites da tabela acima |
| Recuperação | Página nativa com o mesmo estilo | `cognito-forgot-1280.png` | E-mail de reset não enviado |
| Não alterar outros clients | Client único do pool; `ALL` vazio | `list-user-pool-clients`; Get `ALL` | — |
| Não publicar cegamente a imagem FE | Sem ECR/ECS neste passo | Este REV | Shell novo só no working tree até republicar a imagem |

## Gates e provas

Frontend em 02/10/2026: `npm test` (46), `npm run lint`. Backend Java não foi alterado neste passo.

Regressão financeira local (já na suíte, não reescrita): rascunho/registro, retry de transporte, correção após 400, baixa, conflito de versão, estorno, extrato, viewer/permissão por empresa (`withCompanyPermissions`), formulário sujo no Mais. **Não** houve escrita financeira em produção.

Hosted UI público: `npm run capture:cognito-hosted-ui` — login e `forgotPassword` em 360 / 768 / 1280, sem overflow horizontal visível, sem submissão de credencial. Sonda OIDC do origin Finance: 302 com `state`/`nonce` e `redirect_uri` interno.

## Publicação e reversão

1. **Cognito (aplicado).** Snapshot vazio anterior em `ops/aws/cognito-hosted-ui/snapshot-atual.json`. Apply: `.\apply-hosted-ui.ps1 -Apply`. Rollback: `.\rollback-hosted-ui.ps1 -Apply` (restaura CSS vazio neste client; não usa `ALL`). Sem mudança de plano, sem recurso faturável extra identificado.
2. **Imagem frontend/AF (não aplicada).** O canal vigente (ECR + serviço PRM_007/009) continua a ser o caminho. A correção do cabeçalho local, sozinha, não deixa o origin público coerente com o Hosted UI novo até essa imagem ser republicada. Reversão FE: digest anterior `sha256:7c4cc0de22350fe0f3e62873d06fca6423cc25946205b4b70756822729da5b65` ainda em `terraform.tfvars`.
3. Sem tocar Monitor, Hub, Panne ou pool compartilhado. Sem reiniciar a engine Spider.

A publicação do produto, quando autorizada para a imagem FE, deve mostrar o Finance e o acesso com a mesma faixa `#1603AD` e a marca branca, **e** as diferenças da tabela Cognito acima — não uma prancha HTML no Hosted UI.

## O que não foi exercitado

- Submissão de senha, MFA e conclusão do e-mail de recuperação (dependência humana; credencial não pedida neste chat).
- Loop autenticado deep link → Cognito → retorno visual na origem pública.
- Publicação da imagem FE/ECS.
- Qualquer escrita financeira em produção.
