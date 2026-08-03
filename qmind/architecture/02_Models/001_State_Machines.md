# QMind — Máquinas de estado

- Status: Aceito
- Data: 2026-08-03
- Congelamento: `domain-docs-v0`
- Precede: `002_Roles_and_Permissions.md`, `../03_Database/001_Data_Dictionary.md`
- Base: `000_Domain_Model.md`, ADRs 001–009 Aceitos
- Aceite: `../04_Docs/006_Domain_Acceptance_Checklist.md`

## 1. Convenções

- Estados são códigos estáveis em `snake_case` (API e persistência).
- Sugestões de IA **nunca** disparam sozinhas transição para estados aprovados/publicados.

### 1.1 Contrato de transição (obrigatório)

Toda linha das tabelas abaixo implica:

| Elemento | Regra padrão |
|---|---|
| Autor | Papel/relação em `002_Roles_and_Permissions.md` (coluna Autor resume; detalhe na matriz) |
| Pré-condições | Coluna Guardas + estado de agregados citados |
| Efeitos | Coluna Efeitos; side-effects em outros agregados só se listados |
| Auditoria | Sempre: `PlatformAuditEvent` com ator, `organization_id`, recurso, evento, de→para, `correlation_id`, resultado |
| Cancelamento | Eventos `cancel` / `discard` / `abandon` / `reject` conforme máquina |
| Reabertura | Só onde houver evento `reopen*` / `rework`; estados `disposed`/`cancelled` terminais não reabrem o mesmo id |

Notação: **※** relação (autor/designado) · **‡** segregação · **sys** ator sistema/worker.

---

## 2. Avaliação (`Assessment`)

### Estados

| Estado | Significado |
|---|---|
| `draft` | Rascunho; escopo e equipe incompletos |
| `planned` | Planejada; agenda e escopo definidos |
| `in_progress` | Em execução (entrevistas, coleta) |
| `analysis` | Análise de evidências e elaboração de constatações |
| `actions` | Plano de ação em elaboração/acompanhamento |
| `report` | Relatório em elaboração ou revisão |
| `closed` | Ciclo encerrado; alterações substanciais bloqueadas |
| `cancelled` | Cancelada sem conclusão (terminal) |

### Transições

| De | Evento | Para | Autor | Guardas | Efeitos |
|---|---|---|---|---|---|
| `draft` | `plan` | `planned` | org_admin, consultant_auditor, quality_manager | Escopo ≥1 processo ou requisito; modelo/versão; equipe mínima | Congela referência ao maturity/assessment model se ainda não congelada |
| `draft` | `cancel` | `cancelled` | org_admin, quality_manager, consultant_auditor※ | Sem Finding `approved` | Bloqueia novas coletas; Jobs em voo → cancel cooperativo |
| `planned` | `start` | `in_progress` | org_admin, consultant_auditor, quality_manager | Data de início autorizada | Abre janela de Interview/Evidence |
| `planned` | `reopen_draft` | `draft` | org_admin, quality_manager, consultant_auditor※ | Nenhuma Evidence `approved` nem Interview concluída | Permite reeditar escopo |
| `planned` | `cancel` | `cancelled` | org_admin, quality_manager, consultant_auditor※ | — | Idem cancel |
| `in_progress` | `begin_analysis` | `analysis` | org_admin, consultant_auditor, quality_manager | Escopo não vazio; coleta mínima **ou** justificativa de insuficiência | Trava expansão livre de escopo (só emenda controlada) |
| `in_progress` | `cancel` | `cancelled` | org_admin, quality_manager, consultant_auditor※ | Sem Finding `approved` | Idem cancel |
| `analysis` | `open_actions` | `actions` | org_admin, consultant_auditor, quality_manager | ≥1 Finding `approved` **ou** `no_findings_declared` | Permite ActionPlan |
| `analysis` | `back_to_field` | `in_progress` | org_admin, consultant_auditor, quality_manager | Nenhuma Finding `approved` (ou todas withdrawn/rework) | Reabre coleta |
| `actions` | `begin_report` | `report` | org_admin, consultant_auditor, quality_manager | ActionPlan criado (ou plano vazio justificado) | Permite Report.draft |
| `actions` | `back_to_analysis` | `analysis` | org_admin, consultant_auditor, quality_manager | Nenhum Report `published` | — |
| `report` | `close` | `closed` | org_admin, quality_manager, consultant_auditor※ | Report `published` **ou** dispensa formal | Imutabilidade substancial; archive elegível |
| `report` | `back_to_actions` | `actions` | org_admin, consultant_auditor, quality_manager | Report não `published` | — |
| `closed` | `reopen` | `report` | org_admin‡, quality_manager‡ | Motivo; auditoria reforçada | Não apaga histórico; republicação = nova versão de Report |

**Cancelamento:** só até não haver Finding `approved`. **Reabertura:** apenas `closed`→`report` (controlada). `cancelled` é terminal.

---

## 3. Evidência (`Evidence`)

### Estados

| Estado | Significado |
|---|---|
| `upload_pending` | Intenção autorizada; aguarda bytes |
| `quarantined` | Arquivo recebido; em verificação |
| `rejected` | Falhou validação/segurança (terminal da versão) |
| `approved` | Disponível para vínculos de negócio |
| `superseded` | Substituída por nova versão |
| `pending_disposal` | Marcada para descarte |
| `disposed` | Descarte concluído (metadados mínimos) |

**Flag ortogonal (não é estado):** `legal_hold` (bool) + `legal_hold_reason` / timestamps. Pode coexistir com `approved`, `rejected` ou `superseded` sem alterar o estado principal — preserva o ciclo de vida da versão.

### Transições

| De | Evento | Para | Autor | Guardas | Efeitos |
|---|---|---|---|---|---|
| — | `authorize_upload` | `upload_pending` | org_admin, consultant_auditor, quality_manager, process_owner※, action_owner※ | Org/tipo/tamanho OK; Assessment não closed/cancelled | Cria metadados + destino S3 pré-assinado |
| `upload_pending` | `receive` | `quarantined` | sys | Hash/tipo válidos | Enfileira Job de varredura |
| `upload_pending` | `expire` / `abandon` | `disposed` | sys / uploader※ | Timeout ou abandono; `legal_hold=false` | Remove destino órfão |
| `quarantined` | `security_pass` | `approved` | sys (ou operador org_admin/consultant/GQ) | Política OK | Liberada para links/IA |
| `quarantined` | `security_fail` | `rejected` | sys | — | Binário isolado/expurgo conforme política |
| `approved` | `supersede` | `superseded` | org_admin, consultant_auditor, quality_manager | Nova versão `approved` criada | Vínculos históricos preservados no id antigo; `legal_hold` da versão antiga permanece se setado |
| `approved`/`rejected`/`superseded` | `place_hold` | *(mesmo estado)* | org_admin, quality_manager | Motivo; `legal_hold` estava false | `legal_hold=true`; bloqueia `mark_disposal` / `dispose` |
| `approved`/`rejected`/`superseded` | `release_hold` | *(mesmo estado)* | org_admin, quality_manager | Autorização excepcional; `legal_hold` true | `legal_hold=false` |
| `approved`/`rejected`/`superseded` | `mark_disposal` | `pending_disposal` | org_admin, quality_manager | `legal_hold=false`; retenção permite; não única base de Finding approved sem supersede | Marca descarte |
| `pending_disposal` | `dispose` | `disposed` | sys / org_admin | `legal_hold=false` | Expurga objeto, derivados, índices |

**Cancelamento:** `abandon`/`expire`/`rejected`/`dispose`. **Reabertura:** não há; correção = nova versão. `disposed` terminal. Hold não é transição de estado.

---

## 4. Constatação (`Finding`)

### Estados

`draft` · `in_review` · `approved` · `rejected` · `withdrawn`

### Transições

| De | Evento | Para | Autor | Guardas | Efeitos |
|---|---|---|---|---|---|
| — | `create` | `draft` | consultant_auditor, quality_manager; org_admin U | Assessment `in_progress`\|`analysis` (ou `actions` restrito) | — |
| `draft` | `submit` | `in_review` | autor※, quality_manager, org_admin | ≥1 requisito; tipo; **base conforme §4.1** | Congela snapshot de links para revisão |
| `draft` | `discard` | *(soft-delete)* | autor※, quality_manager, org_admin | Nunca foi `approved` | Remove de listagens ativas |
| `in_review` | `approve` | `approved` | quality_manager‡, org_admin‡ | Revisor ≠ autor; Assessment ≠ cancelled; **base §4.1** | Elegível a ActionPlan/Report |
| `in_review` | `reject` | `rejected` | quality_manager, org_admin | Motivo | — |
| `rejected` | `rework` | `draft` | autor※, consultant_auditor, quality_manager | — | Reabre edição |
| `approved` | `withdraw` | `withdrawn` | quality_manager, org_admin; consultant※+GQ | Motivo; Assessment não closed **ou** reopen formal | Itens de ação ligados ficam sinalizados |
| `withdrawn` | `rework` | `draft` | consultant_auditor, quality_manager | — | Novo ciclo; não reativa versão retirada |

### 4.1 Base de evidência por tipo (obrigatório em `submit` e `approve`)

| `finding_type` | `insufficient_evidence` | Exigência de base |
|---|---|---|
| `conformity` | **Proibido** (`false`) | ≥1 `Evidence` `approved` vinculada (evidência **positiva**) |
| `nonconformity` | Permitido | ≥1 Evidence `approved` **ou** `insufficient_evidence=true` com racional (quando a própria ausência/falha de evidência exigida é o achado) |
| `observation` | Permitido | ≥1 Evidence `approved` **ou** `insufficient_evidence=true` com racional |
| `opportunity` | **Proibido** | ≥1 Evidence `approved` **ou** ≥1 `Answer`/observação de entrevista concluída vinculada |

**Cancelamento:** `discard` (pré-aprovação) / `withdraw` (pós). **Reabertura:** `rework` a partir de `rejected`/`withdrawn`.

---

## 5. Plano de ação (`ActionPlan` / `ActionItem`)

### 5.1 ActionPlan

| De | Evento | Para | Autor | Guardas | Efeitos |
|---|---|---|---|---|---|
| — | `create` | `draft` | org_admin, consultant_auditor, quality_manager | Assessment `analysis`\|`actions` | — |
| `draft` | `activate` | `active` | idem | ≥1 item ∨ justificativa vazia | Itens executáveis |
| `active` | `complete` | `completed` | org_admin, quality_manager | Itens em `done`\|`cancelled`\|`ineffective_closed` | — |
| `draft`/`active` | `cancel` | `cancelled` | org_admin, quality_manager, consultant_auditor | Sem Report `published` dependente ∨ emenda | Cancela itens `open` elegíveis |

### 5.2 ActionItem

`overdue` é **flag** (`is_overdue`), não estado exclusivo.

| De | Evento | Para | Autor | Guardas | Efeitos |
|---|---|---|---|---|---|
| — | `create` | `open` | org_admin, consultant_auditor, quality_manager | Plano draft/active; owner designado | — |
| `open` | `start` | `in_progress` | action_owner※, process_owner※ | — | — |
| `open`/`in_progress` | `cancel` | `cancelled` | org_admin, GQ, consultant; owner※ se `open` | Motivo | — |
| `in_progress` | `mark_implemented` | `implemented` | action_owner※, process_owner※ | Evidência conforme tipo | — |
| `implemented` | `validate` | `validated` ou `done` | quality_manager, org_admin, process_owner※‡ | Validador ≠ owner (salvo política); se sem eficácia → `done` | — |
| `implemented` | `reject_implementation` | `in_progress` | quality_manager, org_admin, process_owner※ | Motivo | — |
| `validated` | `confirm_efficacy` | `done` | quality_manager, org_admin | — | — |
| `validated` | `fail_efficacy` | `ineffective` | quality_manager, org_admin | Motivo | Pode exigir novo item |
| `ineffective` | `reopen` | `in_progress` | quality_manager, org_admin, owner※ | — | — |
| `ineffective` | `close_ineffective` | `ineffective_closed` | quality_manager, org_admin | Aceite formal | Terminal do item |

**Cancelamento:** plano/item `cancel`. **Reabertura:** `ineffective`→`in_progress`; plano `completed` não reabre sem emenda de Assessment.

---

## 6. Relatório (`Report`)

Estados: `draft` · `in_review` · `published` · `archived` · `superseded` · `discarded`

| De | Evento | Para | Autor | Guardas | Efeitos |
|---|---|---|---|---|---|
| — | `create` | `draft` | consultant_auditor, quality_manager; org_admin U | Assessment em `report` (ou antecipação controlada) | — |
| `draft` | `submit` | `in_review` | autor※, quality_manager, org_admin | Seções obrigatórias; Findings aprovadas congeladas; maturidade aprovada (versão vigente) se incluída | Snapshot imutável para revisão |
| `draft` | `discard` | `discarded` | autor※, quality_manager, org_admin | Nunca foi `published`; motivo opcional mas auditado | Terminal desta versão; Assessment pode criar novo Report `draft` |
| `in_review` | `request_changes` | `draft` | quality_manager, org_admin | Comentários | — |
| `in_review` | `discard` | `discarded` | quality_manager, org_admin | Motivo obrigatório; nunca foi `published` | Idem discard; libera elaboração de nova versão |
| `in_review` | `publish` | `published` | quality_manager‡, org_admin‡ | Publicador ≠ único elaborador | Gera export versionado; habilita Assessment.close |
| `published` | `supersede` | `superseded` | quality_manager, org_admin; consultant※+GQ | Nova versão `published` | Versão antiga permanece legível |
| `published` | `archive` | `archived` | quality_manager, org_admin | Assessment `closed` | — |

**Cancelamento:** `discard` (`draft`/`in_review` → `discarded`), auditável. Publicado: sem cancel; correção = `supersede`. **Reabertura:** não reativa `discarded`; nova versão/`create`.

---

## 7. Maturidade (`MaturityAssessment` — pacote versionado)

Ver `003_Maturity_Model.md`. Correção de pacote **aprovado** = **nova versão** (não há `reject`/`rework` a partir de `approved`).

Estados do pacote: `draft` · `in_review` · `approved` · `rejected` · `superseded` · `discarded`

| De | Evento | Para | Autor | Guardas | Efeitos |
|---|---|---|---|---|---|
| — | `create`/`upsert_draft` | `draft` | consultant_auditor, quality_manager | Assessment `analysis` (tip.); modelo congelado; se já existe `approved`, só via `supersede` | Scores/N/A em rascunho; `version_no` |
| `draft` | `submit` | `in_review` | autor※, quality_manager | Sem `insufficient_info`; N/A justificados; evidência mínima por nível | Congela números para revisão |
| `draft` | `discard` | `discarded` | autor※, quality_manager, org_admin | Nunca `approved`; motivo auditado | Terminal desta versão |
| `in_review` | `approve` | `approved` | quality_manager‡, org_admin‡ | SoD; cálculo confere; torna-se versão **vigente** da Assessment | Elegível a Report; versões `approved` anteriores desta Assessment → `superseded` se houver cadeia |
| `in_review` | `reject` | `rejected` | quality_manager, org_admin | Motivo | — |
| `in_review` | `discard` | `discarded` | quality_manager, org_admin | Motivo | Terminal desta versão |
| `rejected` | `rework` | `draft` | consultant_auditor, quality_manager | Mesmo `version_no` | Reabre edição |
| `approved` | `supersede` | `superseded` | quality_manager‡, org_admin‡ | Motivo; Assessment ≠ cancelled | Cria novo pacote `draft` com `version_no+1` e `supersedes_id`; Report já `published` que citou a versão antiga permanece válido; novo Report deve referenciar a versão vigente |

**Cancelamento:** `discard` pré-aprovação. **Reabertura de aprovado:** inexistente no mesmo id — só `supersede` → novo draft. `rejected`→`rework` ok.

---

## 8. Processamento de IA (`Job` / `AiSuggestion`)

### 8.1 Job

| De | Evento | Para | Autor | Guardas | Efeitos |
|---|---|---|---|---|---|
| — | `enqueue` | `queued` | org_admin, consultant_auditor, quality_manager | Caso de uso permitido; fontes mesma org; Evidence `approved` se conteúdo | Persiste idempotency_key |
| `queued` | `start` | `running` | sys | Worker disponível | — |
| `queued` | `cancel` | `cancelled` | solicitante※, org_admin, GQ | — | Não materializa sugestão |
| `running` | `succeed` | `succeeded` | sys | Validação estrutural; proveniência | Pode `materialize` AiSuggestion |
| `running` | `fail` | `failed` | sys | — | Erro sanitizado |
| `running` | `cancel` | `cancelled` | solicitante※, org_admin, GQ, sys | Cooperativo | — |
| `failed` | `retry` | `queued` | solicitante※, org_admin, GQ | Política retry; mesma idempotency | — |

### 8.2 AiSuggestion

| De | Evento | Para | Autor | Guardas | Efeitos |
|---|---|---|---|---|---|
| — | `materialize` | `suggested` | sys | Job `succeeded` | Cria sugestão; alvo inalterado até accept |
| `suggested` | `accept` | `accepted` | org_admin, consultant_auditor, quality_manager | Alvo editável (`draft`…) | Aplica payload ao alvo |
| `suggested` | `accept_edit` | `edited` | idem | Diff registrado | Aplica versão editada |
| `suggested` | `reject` | `rejected` | idem | Motivo opcional auditado | Alvo intacto |

**Invariante:** nenhum caminho para Finding.approved / Report.published / MaturityScore.approved sem transição humana própria.

---

## 9. Dependências entre máquinas

```text
Assessment.in_progress  → Evidence.approve, Finding.draft, Interview
Assessment.analysis     → Finding.submit/approve, MaturityAssessment.draft/submit
Finding.approved / no_findings → ActionPlan.activate
MaturityAssessment.approved (vigente, se no relatório) + Findings → Report.submit/publish
Report.published        → Assessment.close
Evidence.approved       → base obrigatória de Finding.conformity; NC/observation podem usar insuficiência (§4.1)
AiSuggestion            → só alvos draft/editáveis
legal_hold (flag)       → bloqueia disposal sem mudar status da Evidence
```

## 10. Próximos documentos

Autoridade detalhada: `002_Roles_and_Permissions.md`. Aceite formal: `../04_Docs/006_Domain_Acceptance_Checklist.md`.
