# ACTIONFINANCE_REV_004 — Recebimentos, pagamentos registrados e contas financeiras

Versão 0.1 — 29/09/2026. Entrega do PRM_004 no recorte local demonstrativo. Sem aprovação de produção/piloto. Sem PRM_005.

## Delimitação

ActionFinance registra **fatos já ocorridos** no controle local. Não executa cobrança, Pix, transferência, pagamento nem comunicação externa. ActionHub permanece o módulo de execução de pagamentos existente. Panne permanece origem de compras/estoque no cenário de grupo. Botões desta fatia não sugerem envio de dinheiro.

A fundação (PRM_002) e o cadastro de títulos (PRM_003, aprovado em 29/09/2026) não foram reabertos. Migrations V1–V3 permanecem intactas.

## Jornada para o proprietário

1. Na pasta `C:\Projetos\ActionFinance`, se a aplicação não estiver no ar: `.\scripts\dev\start-local.ps1`.
2. Abrir `http://127.0.0.1:5179/`. A UI inicia em **A receber**. Empresa e “Demonstração local” permanecem visíveis.
3. Colar o token de `C:\Projetos\ActionFinance\.local\demo-tokens.env` (`ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A`). O valor não é gravado neste navegador.
4. Abrir o recebível demonstrativo “Recebível demonstrativo de R$ 150 com baixa parcial” (restante R$ 100,00) ou criar um título OPEN de R$ 150,00.
5. **Registrar recebimento**: conta financeira, valor (inicialmente o restante), data efetiva (hoje), meio. Texto na tela: “Este registro atualiza seu controle financeiro. Não envia nem movimenta dinheiro.”
6. Conferir restante e situação **Parcialmente recebido**. Registrar o restante. Situação **Recebido**. Título quitado não entra em vencidos.
7. Abrir a baixa e **Estornar registro** com motivo. O restante recompõe; o extrato da conta ganha movimento inverso. O original permanece visível como Estornado.
8. Percorrer **A pagar** do mesmo modo (saída na conta).
9. **Contas financeiras**: lista com saldo gerencial; criar conta com saldo inicial explícito (zero ou negativo permitidos); extrato com período, saldo anterior/final e saldo atual separados.
10. Perfil de consulta (`ACTIONFINANCE_DEMO_TOKEN_VIEWER_A`): lê títulos, baixas, contas e extrato; sem botões de escrita.

Não houve Pix enviado, pagamento executado, conciliação bancária nem integração com Spider, ActionHub ou Panne.

## Telas

| Rota | Função |
|---|---|
| `/receivables`, `/payables` | Lista com original, restante, filtro “Com pendência” e resumo por restante |
| `/receivables/:id`, `/payables/:id` | Original / recebido ou pago / restante; baixas; histórico |
| `.../settlements/new` | Registrar recebimento ou pagamento realizado |
| `/settlements/:id` | Detalhe da baixa e estorno do registro |
| `/financial-accounts` | Contas da empresa ativa e saldo gerencial |
| `/financial-accounts/:id` | Detalhe, rename/inativar e extrato |

Navegação: A receber, A pagar, Contas financeiras, Cadastros. Sem dashboard no lugar da lista.

Capturas Playwright 1280/360 em `documents/reviews/screenshots/prm-004/` (29/09/2026): lista a receber (original + restante + “Com pendência”), detalhe com baixas visíveis no desktop, formulário “Registrar recebimento realizado” com aviso de não envio de dinheiro, contas e extrato gerencial, diálogo de estorno. Sem overflow horizontal (`scrollWidth = clientWidth`). Mobile 360 usa cartões; desktop 1280 usa tabela.

A lista de baixas no detalhe do título passou a ter tabela no desktop — a primeira passagem só usava `.cards`, ocultas acima de 768 px.

Jornada de escrita ponta a ponta no browser (criar conta nova + duas baixas + estorno) não foi clicada nesta passagem: o seed já contém o recebível 150 com baixa 50, a obrigação 100 quitada e o estorno; as ITs e o Vitest cobrem a escrita. O analista deve percorrer a jornada no runtime local.

## Migrations e contratos

Flyway incremental: **V4** tabelas de conta, baixa, alocação, reversão, movimento e histórico de conta; CHECK de `SETTLEMENT_RECORDED` / `SETTLEMENT_REVERSED`. **V5** grants (conta SELECT/INSERT/UPDATE; fatos INSERT/SELECT; sem DELETE). V1 checksum **1488219560** preservado.

API `/api/v1` (empresa autorizada no servidor):

| Recurso | Métodos |
|---|---|
| `/financial-accounts` | GET, POST |
| `/financial-accounts/{id}` | GET, PATCH |
| `/financial-accounts/{id}/movements` | GET (período inclusivo, paginação, saldos) |
| `/receivables/{id}/settlements`, `/payables/{id}/settlements` | GET, POST |
| `/settlements/{id}` | GET |
| `/settlements/{id}/reversal` | POST |
| títulos | campos novos: `settledAmountMinor`, `outstandingAmountMinor`, `settlementStatus`; `overdue` recalculado |

Permissões: `financial-accounts:read/write`, `settlements:read/write/reverse`. GET `/api/v1/settlements` sem id permanece denyAll.

Seed `local-demo` **aditivo**: conta banco/caixa da padaria, conta do ateliê, recebível 150 com baixa 50, obrigação 100 quitada, baixa estornada. Títulos já existentes da carga PRM_003 não foram reescritos.

## Provas

| Gate | Resultado |
|---|---|
| `mvnw.cmd verify` | Verde, 29/09/2026 ~08:53. Surefire **7/7** (0 skip). Failsafe **32/32** (0 skip; era 25). SettlementOperationsIT **7**. TitleOperationsIT **11**. FoundationSecurityIT 9. |
| Vitest | **17/17** (era 11): jornada de baixa sem “Pix enviado”; token; PATCH register; 401; escrita congelada |
| lint / build | 0 erros ESLint; `tsc --noEmit` + Vite build ok |
| `npm audit --omit=dev` e `npm audit` | 0 vulnerabilidades |
| Isolamento | FK composta rejeita alocação de título de outra empresa; GET de título alheio continua 403 |
| Jornada 150 → 50 → 100 → 0 → estorno 50 | SettlementOperationsIT nas duas direções |
| Concorrência / replay | duas baixas no mesmo restante; replay da mesma chave não cria segundo movimento |
| Regras | DRAFT, valor acima do restante, data futura, conta inativa para nova baixa; estorno em conta inativa permitido |

`verify-backup.ps1` (29/09/2026): `BACKUP_VERIFY_OK` V1–V5 (V1 checksum 1488219560), restore em container descartável, titles=14 history=18 accounts=3 settlements=3 movements=7, runtime sem DDL, falha deliberada com exit nonzero. Volume local `actionfinance_pgdata_17` preservado.

## Limites (não entregues; exigem desenho próprio)

Conciliação bancária, pagamentos externos, baixas em lote, transferências entre contas, juros/descontos/multas/tarifas/impostos/câmbio, recebimento acima do título, distribuição de uma baixa entre vários títulos, IAM corporativo, produção/piloto.

## Estado final

Registro financeiro **manual** no controle local. Nenhuma execução de dinheiro. PRM_005 não iniciado. Aceite do analista pendente, focado em critérios funcionais, dados e UX desta fatia.

Corretivo posterior: [ACTIONFINANCE_REV_004_COR_001](ACTIONFINANCE_REV_004_COR_001.md) (29/09/2026). Este relatório não foi apagado.
