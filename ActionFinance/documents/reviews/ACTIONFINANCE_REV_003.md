# ACTIONFINANCE_REV_003 — Primeira entrega funcional (a receber e a pagar)

Versão 0.4 — 29/09/2026 — [aceite do analista](ACTIONFINANCE_REV_003_ENCERRAMENTO.md) para o recorte local demonstrativo. Sem aprovação de produção/piloto. Sem PRM_004.

## Deliberação desta passagem

O parecer inicial classificou a primeira entrega como **parcial**. As correções R1–R6 e o residual de R3 foram executados neste recorte. Em 29/09/2026 o analista **aprovou o PRM_003** para cadastro e acompanhamento local demonstrativo de contas a receber e a pagar e **encerrou o ciclo de revisão**. Não há autorização de produção, piloto, pagamento/recebimento efetivo nem integração. **PRM_004 não é emitido** por este encerramento.

## Como abrir e percorrer

1. Na pasta `C:\Projetos\ActionFinance`, se a aplicação não estiver no ar: `.\scripts\dev\start-local.ps1`.
2. Abrir `http://127.0.0.1:5179/`. A UI inicia em **A receber**.
3. Colar o token de `C:\Projetos\ActionFinance\.local\demo-tokens.env` (`ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A`). O valor não é gravado neste navegador.
4. Percorrer **A receber**: Novo recebível → Registrar → localizar na lista → Corrigir com motivo → Cancelar título → ler o histórico.
5. R2: criar rascunho incompleto → Editar → completar → **Registrar**. O título deve ficar Em aberto, com histórico CONFIRMED.
6. Percorrer **A pagar** do mesmo modo (Nova conta a pagar).
7. Cadastros: `/catalogs/counterparties` e `/catalogs/categories`.
8. Perfil de consulta: token `ACTIONFINANCE_DEMO_TOKEN_VIEWER_A` — lista e detalhe sem botões de alteração.

Não houve recebimento, pagamento, liquidação nem integração com Spider, ActionHub ou Panne.

## Correções R1–R6

| ID | Correção |
|---|---|
| R1 | Hash de atualização inclui o ID do título. Replay devolve o `TitleView` persistido após autorizar. Mesma chave/corpo em outro título → 409. Alteração posterior não muda a resposta original. |
| R2 | `PATCH ?register=true` confirma rascunho de forma atômica (OPEN + CONFIRMED). Formulário de cancelado não oferece botões de rascunho. |
| R3 | `setSession` notifica o React. Geração conferida depois do corpo. Escrita pendente congela chave/rota/corpo até resolução. Confirmar/cancelar não geram chave nova a cada clique. |
| R4 | Tabela só no desktop; cartões só no mobile. Largura medida 360=360 nas listas, formulário, detalhe e cadastros. |
| R5 | Navegação lateral e voltar respeitam formulário sujo. Diálogos com `showModal`, foco contido e Escape. Datas pt-BR, dinheiro/rótulos no histórico, referência compacta com copiar, filtro de categoria, seletores pesquisáveis, erro de histórico com nova tentativa, conflito de versão com recuperação guiada. |
| R6 | `TitleService.list` em `REPEATABLE_READ`. IT de concorrência exige consistência interna da página quando ela contém o conjunto filtrado. |

## Telas e capturas

Capturas refeitas em `documents/reviews/screenshots/prm-003/` após o CSS final:

| Arquivo | Largura medida | Tabela | Cartões |
|---|---|---|---|
| `desktop-1280-receivables.png` / `payables.png` | 1280=1280 | visível | ocultos |
| `mobile-360-receivables.png` / `payables.png` | 360=360 | oculta | visíveis |
| `*-form.png`, `*-detail.png`, `*-catalogs.png` | sem overflow | — | — |
| `mobile-360-menu.png`, `*-cancel.png` | diálogo modal no cancelamento | — | — |

## Contratos e migrations

API `/api/v1`:

| Recurso | Métodos |
|---|---|
| `/receivables`, `/payables` | GET lista+resumo, POST criar (`register=true` para OPEN atômico) |
| `/receivables/{id}`, `/payables/{id}` | GET, PATCH (`register=true` confirma rascunho em edição) |
| `.../{id}/confirm`, `.../{id}/cancel` | POST |
| `.../{id}/history` | GET |
| `/catalogs/counterparties`, `/catalogs/categories` | GET, POST, PATCH |

Empresa via `companyId` autorizado. Cabeçalho `Idempotency-Key` nas escritas. Dinheiro: string de centavos. Situações: DRAFT, OPEN, CANCELLED. Origem: MANUAL.

Flyway: V1 intacta (checksum **1488219560**); V2 tabelas; V3 grants. Sem seed em migration.

Datas da carga demonstrativa permanecem 15/09/2026 (estáveis). ITs usam `Clock` fixo em `2026-09-15T15:00:00Z` para ontem/hoje/amanhã relativos a essa data de negócio — não ao calendário de execução.

## Testes

| Gate | Resultado |
|---|---|
| `mvnw.cmd verify` | Verde, 28/09/2026 ~19:26. Surefire 7/7 (0 skip). Failsafe **25/25** (0 skip; era 21). TitleOperationsIT **11** (R1/R2/R6). FoundationSecurityIT 9. |
| Vitest | **11/11** (era 5): token, PATCH `register=true`, 401 limpa sessão, geração após corpo, escrita congelada, datas/histórico) |
| lint / build | 0 erros; Vite build ok |
| `npm audit --omit=dev` | 0 vulnerabilidades |
| `npm audit` (completo, incl. dev) | 0 vulnerabilidades |
| Capturas Playwright | overflowX=false em 360 e 1280; tabela/cartões mutuamente exclusivos nas listas |

## R1 operacional (start/stop)

`stop-local` / `start-local` desta passagem encerraram o lançamento gravado e relançaram com metadados completos (`launch=2b178041c8b14a4dad6682a4a5e95ce0`). A recusa segura por porta/metadado incompleto permanece. Não houve adoção por porta.

## Estado final dos serviços

- UI `http://127.0.0.1:5179/`
- API `http://127.0.0.1:8091/api/v1/system/info`
- PostgreSQL `actionfinance-postgres-17` no volume `actionfinance_pgdata_17`
- Spider sandbox não foi alterada

## Limitações

- Sem pago/recebido, baixa, cobrança, transferência, conciliação ou liquidação
- Sem conectores, inbox/outbox, parcelas automáticas ou origem externa declarada pelo usuário
- Sem IAM de produto; token demo só local-demo/loopback
- Soma de títulos não é saldo bancário, receita, lucro ou caixa
- Autenticação de produto, comercialização e PRM_004 ficam para entregas próprias
- Aceite do analista: **concedido** em 29/09/2026 para o recorte local demonstrativo ([encerramento](ACTIONFINANCE_REV_003_ENCERRAMENTO.md)); sem autorização de produção/piloto

## Documentação

- Parecer inicial (histórico): `documents/reviews/ACTIONFINANCE_REV_003_PARECER_ANALISTA.md`
- Revalidação (histórico): `documents/reviews/ACTIONFINANCE_REV_003_REVALIDACAO_ANALISTA.md`
- Encerramento e aceite: `documents/reviews/ACTIONFINANCE_REV_003_ENCERRAMENTO.md`
- Prompt integral: `documents/prompts/ACTIONFINANCE_PRM_003.md`
- Sem PRM_004 neste encerramento

## Adendo 29/09/2026 — R3 residual e referência compacta

Revalidação do analista: R1, R2, R4, R5 e R6 confirmados; R3 parcial. Este adendo fecha só o residual e o rótulo compacto. Migrations, modelo e demais correções não foram reabertos.

### R3 residual

`request` passou a tratar perda de transporte (`TypeError`/`Failed to fetch`), AbortError, JSON inválido, corpo ilegível e HTTP sem garantia de rollback (5xx, 408, 429) como **resultado desconhecido**. Validação 400/403/404/409/422 continua definitiva: a chave é descartada e o usuário corrige os campos.

A escrita congelada guarda também `companyId` e `actorId`. Troca de empresa/usuário não reenvia o pedido anterior (`STALE`). Formulário, confirmar e cancelar preservam a mesma chave/corpo na repetição segura.

Prova Vitest: primeira POST efetiva no mock, resposta perdida como `Failed to fetch`; a repetição reutiliza a mesma `Idempotency-Key` e o mesmo corpo e termina num único título. Confirmar: duas tentativas, uma chave. Validação 400: segunda tentativa usa chave nova.

### Referência compacta

O rótulo passou a ser prefixo + 8 últimos caracteres hexadecimais da referência (`PAG-11111304` ≠ `PAG-11111305`). IDs persistidos não mudam. Copiar/title continua com o valor completo. Captura `mobile-360-payables.png` refeita.

### Gates desta passagem

| Gate | Resultado |
|---|---|
| Vitest | **16/16** (era 11) |
| lint / build | 0 erros; Vite ok |
| `npm audit --omit=dev` | 0 |
| `npm audit` completo | 0 |
| Capturas 360 | scrollWidth=360; cartões nas listas; referências distintas |
| Backend Java | sem alteração; `mvnw verify` da v0.2 permanece a evidência do domínio |

Parada para aceite. PRM_004 não iniciado.

## Encerramento 29/09/2026

O analista aprovou o PRM_003 para o recorte funcional local demonstrativo e encerrou o ciclo de revisão. A verificação final delimitou-se ao residual de R3 e ao rótulo compacto; o aceite combina a prova de cliente (mock de transporte) com as provas anteriores de idempotência no backend, sem tratar o mock como ensaio ponta a ponta de rede/banco.

Não haverá outra rodada ampla de revisão do PRM_003. Aperfeiçoamentos menores seguem evolução normal. O próximo ciclo de produto depende de prompt próprio. PRM_004 não é emitido aqui. Autorização do proprietário para operação real permanece separada deste aceite.
