# ACTIONFINANCE_DAT_001 — Persistência implementada da fatia de títulos

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_DAT_001 |
| Versão | 0.6 |
| Status | IMPLEMENTADO no recorte local PRM_006_COR_001 (permissões por empresa); sem aprovação de produção |
| Data | 29/09/2026 |
| Dependências | ACTIONFINANCE_PRM_003 §10–11; ACTIONFINANCE_PRM_004 §4–5; V1 fundação preservada |

## Mudança de recorte

O recorte anterior deixava recebíveis e telas para um prompt posterior. **PRM_003 v0.3 inclui recebíveis e UX operacional nesta fatia**, com `financial_title` compartilhado e direção RECEIVABLE/PAYABLE.

## Política

| Regra | Detalhe |
|---|---|
| Banco / schema / usuário | `actionfinance` / `actionfinance` / runtime exclusivo |
| Origem Flyway | `database/migrations` — V1 intacta (checksum 1488219560); V2–V5 inalteradas; V6 identidade/sessões; V7 grants |
| Hibernate | `ddl-auto=none` |
| Seed | Somente `LocalDemoSeed` no perfil `local-demo`. Nenhuma migration semeia dados |
| Proibido | H2; seed corporativo; volume destroy na parada normal; DELETE de runtime nesta fatia |

## Isolamento

**Tenant** é a organização cliente do produto. **Company** é a empresa administrada. O cliente HTTP não envia tenant como autoridade; o servidor resolve `tenant_id` pela empresa autorizada do principal (`authorizedCompanyIds`). Contraparte não é tenant.

FKs compostas `(tenant_id, company_id)` impedem cruzamento no banco.

## Modelo efetivo (implementado)

Confrontado com migrations V2 e classes de persistência JDBC.

```text
tenant
  └── company
        └── counterparty / financial_category / financial_title / financial_account / request_idempotency
        └── company_membership ← app_user ← external_identity (issuer+subject)
app_user ── access_admin_audit
SPRING_SESSION / SPRING_SESSION_ATTRIBUTES  (Spring Session 3.4, schema actionfinance)

Ator em fatos financeiros (created_by, actor_id, recorded_by): UUID opaco.
Sem FK para app_user. Autoria demo/legado permanece; não se fabricam identidades OIDC para esses UUIDs.
```

| Tabela | Papel |
|---|---|
| tenant | Organização cliente do produto |
| company | Empresa administrada; `is_demo` e `business_timezone` |
| counterparty | Cliente, fornecedor ou ambos; código gerado `CTP-` + UUID |
| financial_category | Natureza RECEIVABLE/PAYABLE/BOTH; código `CAT-` + UUID |
| financial_title | Compromisso compartilhado; referência `REC-`/`PAG-` + UUID; origem MANUAL |
| financial_title_history | Append-only; ações CREATED/UPDATED/CONFIRMED/CANCELLED/SETTLEMENT_RECORDED/SETTLEMENT_REVERSED; não é ledger |
| financial_account | Conta gerencial; código `CTA-` + UUID; tipo BANK/CASH/OTHER; `opened_on` e saldo inicial só no movimento OPENING |
| settlement | Baixa imutável; meio PIX/BANK_TRANSFER/CASH/CARD/OTHER; origem MANUAL; UNIQUE(scope,id,account_id) |
| settlement_allocation | Um título por baixa (UNIQUE scope,settlement_id); imutável |
| settlement_reversal | Uma reversão por baixa (UNIQUE scope,settlement_id); motivo 3–500; imutável |
| cash_movement | OPENING (um por conta), SETTLEMENT (um por baixa), REVERSAL (um por reversão); valor assinado; sem running_balance persistido |
| financial_account_history | CREATED/RENAMED/DEACTIVATED/REACTIVATED; INSERT/SELECT |
| request_idempotency | Escopo empresa+ator+operação+chave; desserialização por operação (TitleView / AccountView / SettlementView) |

Dinheiro: `numeric(19,0)` + API string de dígitos (saldo inicial admite sinal). Datas de negócio: `date` na zona da empresa. Instantes: `timestamptz` UTC. Realizado do título = soma de alocações sem reversão. Saldo da conta = soma de movimentos. Vencido é derivado (OPEN, restante > 0 e `due_date` < data de negócio).

Runtime: SELECT/INSERT/UPDATE em cadastros, títulos e contas; SELECT/INSERT em fatos (baixa, alocação, reversão, movimento) e históricos; sem DELETE nem DDL.

## Evolução FUTURE/PROPOSED (não implementada)

Não criar estas tabelas agora.

| Área | Entidades candidatas |
|---|---|
| Estrutura gerencial | business_unit, cost_center, title_allocation |
| Integração | integration_connection, external_object_link, inbox_message, outbox_message, synchronization_issue — vínculo futuro por tenant, conexão, sistema de origem, tipo/ID externo, parcela, versão/evento e correlação. Deduplicação contextual, não só ID global. Nenhuma enumeração fechada HUB/PANNE |
| Parcelas/recorrência | financial_agreement, installment_schedule |
| Tesouraria avançada | transferências entre contas, conciliação, running_balance persistido, distribuição de baixa |
| Execução externa | payment_request, payment_attempt, provider_result |
| Conciliação | statement_import, statement_line, reconciliation_match, reconciliation_exception |
| Custos e planejamento | budget, budget_line, cost_allocation |
| Produto e acesso | identidade corporativa, associação usuário/tenant/empresa |

O fato operacional permanece na origem. Decisões gerenciais permanecem no ActionFinance. Sincronização futura exige contrato específico; sem sobrescrita silenciosa.

## Contratos HTTP deste recorte (`/api/v1`)

Escritas exigem `Idempotency-Key`. Contexto de empresa no servidor (`companyId` autorizado). Dinheiro em string de centavos.

| Método | Rota | Permissão | Corpo / query relevantes | Resposta |
|---|---|---|---|---|
| GET/POST | `/financial-accounts` | financial-accounts:read/write | POST: name, type, openedOn, openingBalanceMinor | lista/detalhe com currentBalanceMinor |
| GET/PATCH | `/financial-accounts/{id}` | read / write | PATCH: name, active, version | conta |
| GET | `/financial-accounts/{id}/movements` | read | from, to, page, size | itens + previous/periodEnd/current |
| POST/GET | `/receivables/{id}/settlements`, `/payables/{id}/settlements` | settlements:write/read | accountId, amountMinor, effectiveDate, method, note, version | baixa + restante do título |
| GET | `/settlements/{id}` | settlements:read | — | detalhe; se estornada, motivo/autor/movimento inverso |
| POST | `/settlements/{id}/reversal` | settlements:reverse | effectiveDate, reason, version | baixa estornada |

Título (lista/detalhe) passa a incluir `amountMinor`, `settledAmountMinor`, `outstandingAmountMinor`, `settlementStatus`, `overdue` recalculado. Filtro `settlement=PENDING|PARTIAL|SETTLED|ALL` (padrão PENDING nos OPEN). GET `/api/v1/settlements` sem id permanece denyAll.

## Índices e nulabilidade (V4)

Além de PK/UNIQUE de escopo: `financial_account(scope,active,name,id)`; `settlement_allocation(scope,title_id,settlement_id)`; `settlement(scope,account_id,effective_date,id)`; `cash_movement(scope,account_id,effective_date,recorded_at,id)`; `financial_account_history(scope,account_id,occurred_at,id)`.

Índices parciais exclusivos: um OPENING por conta; um movimento SETTLEMENT por baixa; um movimento REVERSAL por reversão.

`settlement.note` é a única coluna de texto opcional da baixa. `cash_movement.settlement_id` / `reversal_id` nulos só em OPENING; SETTLEMENT preenche settlement; REVERSAL preenche ambos. Saldo inicial não é coluna em `financial_account`.

## Identidade e sessões (V6–V7)

Mapeamento lógico → físico:

| Requisito | Tabela | PK / unicidade | Exclusão |
|---|---|---|---|
| Usuário da aplicação | `app_user` | PK `id`; `status` ACTIVE/BLOCKED; `version` | Sem DELETE de runtime |
| Identidade externa | `external_identity` | UNIQUE(issuer, subject); FK `user_id` | Sem DELETE de runtime |
| Vínculo de empresa | `company_membership` | UNIQUE(user_id, tenant_id, company_id); FK composta `(tenant_id, company_id)` → `company` | Sem DELETE; status REVOKED |
| Auditoria administrativa | `access_admin_audit` | PK `id`; índices por instante e alvo | INSERT/SELECT; sem UPDATE/DELETE |
| Sessões Spring Session 3.4 | `SPRING_SESSION`, `SPRING_SESSION_ATTRIBUTES` | PK oficial; IX sessão/expiração/principal; atributos em CASCADE | Runtime pode DELETE linhas expiradas |

Papéis e permissões **por empresa** (não por união global):

| Papel na empresa | Ações nesta empresa |
|---|---|
| VIEWER | `system:read`, `company-context:read`, `titles:read`, `catalogs:read`, `financial-accounts:read`, `settlements:read` |
| OPERATOR | as de VIEWER + `titles:write`, `catalogs:write`, `financial-accounts:write`, `settlements:write`, `settlements:reverse` |

O principal carrega `permissionsByCompany`. Escrita e replay idempotente autorizam a empresa do recurso. Navegação HTTP pode ver a união só para chegar na rota. Não existe administrador global de negócio. Criação inicial de tenant/empresa: `bootstrap-org` (dry-run + responsável). Depois, `access-admin provision` com issuer+subject obtidos no provedor, não por e-mail.

## Nota PRM_005 (29/09/2026)

Nenhuma mudança de modelo neste ciclo: sem tabela, coluna, migration, seed ou campo monetário novos. O frontend continua a exibir totais e saldos calculados pelo backend.

## Nota PRM_006 (29/09/2026)

Dinheiro, movimentos, idempotência e saldos inalterados. V1–V5 sem edição. Banco de produção futuro começa vazio (migrations, sem restore demo).

## Nota PRM_006_COR_001 (29/09/2026)

Sem migration nova. Grants de tenant/empresa já existiam em V3. Autorização passou a ser por empresa. Após restore operacional, invalidar `SPRING_SESSION` e preservar fatos financeiros e `access_admin_audit`. Restart normal da aplicação deve preservar a sessão JDBC. ACL completo de recuperação: `scripts/dev/restore-runtime-privileges.sql` (V1–V7).
