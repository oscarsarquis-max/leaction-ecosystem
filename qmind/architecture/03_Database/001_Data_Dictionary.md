# QMind — Dicionário de dados (conceitual)

- Status: Aceito
- Data: 2026-08-03
- Congelamento: `domain-docs-v0`
- Depende de: `../02_Models/001_State_Machines.md`, `../02_Models/002_Roles_and_Permissions.md`, `../02_Models/003_Maturity_Model.md`, `../99_Reference/001_Domain_Glossary.md`
- Base: `../02_Models/000_Domain_Model.md`, ADR-002, ADR-005, ADR-007, ADR-008 Aceitos
- Aceite: `../04_Docs/006_Domain_Acceptance_Checklist.md`
- Escopo: **lógico** — entidades, atributos, chaves e políticas. **Sem DDL** nem migrações físicas neste documento.

## 1. Convenções

| Tema | Regra |
|---|---|
| Identificadores | UUID v4 (ou v7 se adotado depois) como PK externa |
| Tenant | Coluna `organization_id` UUID **NOT NULL** em toda entidade de negócio de cliente |
| Catálogo global | Referenciais (`Standard*`) **sem** `organization_id`; leitura autorizada |
| Tempos | `timestamptz` (UTC); fuso da organização só para apresentação |
| Soft delete | Preferir estado/`deleted_at` quando houver necessidade de trilha; exclusão física só sob retenção |
| Estados | Códigos `snake_case` das máquinas em `001_State_Machines.md` |
| Papéis | Códigos de `002_Roles_and_Permissions.md` |
| Classificação | `public` \| `internal` \| `confidential` \| `restricted` (dados pessoais sobem o piso) |

Atributos comuns (quando aplicável): `id`, `organization_id`, `created_at`, `created_by`, `updated_at`, `updated_by`, `status`.

---

## 2. Entidades e atributos

### 2.1 Identidade e acesso

#### User
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | PK |
| idp_sub | string | sim | Cognito `sub`; único |
| email | string | sim | PII; único operacional |
| display_name | string | não | PII |
| status | enum | sim | `active` / `disabled` |
| last_login_at | timestamptz | não | |

Sem `organization_id` (identidade global). Acesso a dados de cliente só via Membership.

#### Membership
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | PK |
| organization_id | UUID | sim | FK → Organization |
| user_id | UUID | sim | FK → User |
| roles | set\<role_code\> | sim | ≥1 papel |
| status | enum | sim | `invited` / `active` / `revoked` / `expired` |
| valid_from | timestamptz | sim | |
| valid_to | timestamptz | não | |

Único lógico: `(organization_id, user_id)` ativo.

#### PlatformAdminGrant (opcional)
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| user_id | UUID | sim | |
| status | enum | sim | |
| granted_at / revoked_at | timestamptz | | |

### 2.2 Organizações

#### Organization
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | = tenant |
| name | string | sim | |
| status | enum | sim | `active` / `suspended` / `closed` |
| timezone | string | sim | IANA |
| default_retention_policy_id | UUID | não | FK política |
| data_residency_note | string | não | Informativo |

#### Unit
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | |
| name | string | sim | |
| unit_type | string | não | planta, filial… |
| parent_unit_id | UUID | não | mesma org |

#### PersonContact
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | |
| unit_id | UUID | não | |
| name / email / phone | string | var. | PII |
| linked_user_id | UUID | não | se também for User |

### 2.3 Referenciais (catálogo global)

#### Standard / StandardVersion / Requirement
Sem `organization_id`. `Requirement`: `standard_version_id`, `code`, `title_authorized`, `parent_id`, `sort_order`, `status`.

#### AssessmentModel / Criterion / Question
Modelo versionado de avaliação; vínculos N:N com Requirement. Conteúdo só autorizado/licenciado.

### 2.4 Processos

#### OrgProcess
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | |
| unit_id | UUID | não | |
| name | string | sim | |
| owner_membership_id | UUID | não | process_owner |
| status | enum | sim | |

### 2.5 Avaliações

#### Assessment
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | |
| assessment_model_id | UUID | sim | |
| standard_version_id | UUID | sim | |
| type | enum | sim | `diagnosis` \| `internal_audit` \| `other` (glossário) |
| status | enum | sim | máquina Assessment |
| maturity_model_id | UUID | não | congelado no `plan` se maturidade no escopo |
| planned_start / planned_end | date/timestamptz | não | |
| started_at / closed_at | timestamptz | não | |
| lead_membership_id | UUID | não | |
| no_findings_declared | bool | não | para fechar análise sem achados |

#### AssessmentScope
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | denormalizado = Assessment |
| assessment_id | UUID | sim | |
| org_process_id | UUID | não | XOR parcial com requirement |
| requirement_id | UUID | não | |

#### AssessmentTeamMember
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| assessment_id | UUID | sim | |
| organization_id | UUID | sim | |
| membership_id | UUID | sim | |
| team_role | string | não | lead, auditor… |

#### Interview / Answer / Observation
`organization_id` + `assessment_id`; Answer liga `question_id`/`criterion_id`, conteúdo (pode ser PII se citar pessoas), `author_membership_id`.

### 2.6 Evidências

#### Evidence
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | |
| assessment_id | UUID | não | tipicamente sim no MVP |
| status | enum | sim | máquina Evidence |
| classification | enum | sim | |
| content_type | string | sim | MIME detectado |
| byte_size | int | não | |
| content_hash | string | sim | após receive |
| storage_key | string | sim | S3; nunca URL pública permanente |
| version_no | int | sim | |
| supersedes_evidence_id | UUID | não | |
| retention_until | date | não | |
| legal_hold | bool | sim | default false; **flag ortogonal**, não estado |
| legal_hold_reason | text | cond. | obrig. se legal_hold |
| legal_hold_at / legal_hold_by | | não | |
| uploaded_by | UUID | sim | membership/user |
| disposed_at | timestamptz | não | |

#### EvidenceLink
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | |
| evidence_id | UUID | sim | |
| target_type | enum | sim | requirement, question, finding, action_item, interview |
| target_id | UUID | sim | |

### 2.7 Constatações e maturidade

#### Finding
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | |
| assessment_id | UUID | sim | |
| finding_type | enum | sim | `conformity` \| `nonconformity` \| `opportunity` \| `observation` (glossário) |
| severity | enum | não | |
| status | enum | sim | máquina Finding |
| title / body | text | sim | |
| insufficient_evidence | bool | sim | default false; **só** tipos permitidos (§ integridade) |
| insufficient_evidence_rationale | text | cond. | obrig. se flag |
| author_membership_id | UUID | sim | |
| submitted_at / approved_at | timestamptz | não | |
| approved_by | UUID | não | ≠ author (SoD) |
| withdrawn_reason | text | não | |

#### FindingRequirement / FindingEvidence
Tabelas de vínculo N:N com `organization_id` denormalizado. Ver regra de integridade 3 (base por `finding_type`).

### 2.7b Maturidade (catálogo + scores)

Ver `../02_Models/003_Maturity_Model.md`.

#### MaturityModel (catálogo global)
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| model_code | string | sim | ex. `qmind_maturity_iso9001` |
| model_version | string | sim | semver; UK com code |
| status | enum | sim | `draft` / `active` / `retired` |
| rounding_mode | enum | sim | `half_up` no v0 |
| decimal_places | int | sim | 2 |

#### MaturityDimension / MaturityCriterion
Catálogo: `code`, `title`, `dimension_id`, `sort_order`, âncoras por nível (texto operacional), `min_evidence_rule`. Sem `organization_id`.

#### MaturityAssessment (pacote versionado por avaliação)
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | |
| assessment_id | UUID | sim | |
| version_no | int | sim | UK `(assessment_id, version_no)` |
| supersedes_id | UUID | não | pacote anterior |
| maturity_model_id | UUID | sim | versão de catálogo congelada |
| status | enum | sim | draft / in_review / approved / rejected / superseded / discarded |
| global_score | decimal(5,2) | não | null até cálculo válido |
| author_membership_id | UUID | sim | |
| approved_by | UUID | não | SoD ≠ author |
| discard_reason | text | não | se discarded |

#### MaturityScore (linha por critério)
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | |
| maturity_assessment_id | UUID | sim | |
| criterion_id | UUID | sim | FK catálogo |
| applicability | enum | sim | `applicable` \| `not_applicable` \| `insufficient_info` |
| na_rationale | text | cond. | obrig. se N/A |
| level | int 1–5 | cond. | null se não applicable |
| rationale | text | não | |
| UK | | | `(maturity_assessment_id, criterion_id)` |

#### MaturityDimensionScore
Agregado armazenado ou derivado: `dimension_id`, `score` decimal(5,2), `applicable_count`.

#### MaturityScoreEvidenceLink
`maturity_score_id` → `evidence_id` | `answer_id` | `finding_id` (same org).

### 2.8 Ações

#### ActionPlan
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | |
| assessment_id | UUID | sim | |
| status | enum | sim | máquina ActionPlan |
| empty_plan_rationale | text | não | |

#### ActionItem
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | |
| action_plan_id | UUID | sim | |
| finding_id | UUID | não | origem típica |
| action_kind | enum | sim | `correction` \| `corrective_action` \| `improvement` (glossário) |
| description | text | sim | |
| owner_membership_id | UUID | sim | |
| due_at | timestamptz | sim | |
| status | enum | sim | máquina ActionItem |
| is_overdue | bool | sim | derivado/atualizado |
| efficacy_required | bool | sim | típico true se corrective_action |
| validated_by / efficacy_confirmed_by | UUID | não | SoD vs owner |

### 2.9 Relatórios

#### Report
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | |
| assessment_id | UUID | sim | |
| version_no | int | sim | |
| status | enum | sim | draft / in_review / published / archived / superseded / discarded |
| structured_content | json/doc | sim | |
| maturity_assessment_id | UUID | não | versão de maturidade citada no snapshot |
| export_storage_key | string | não | PDF etc. |
| supersedes_report_id | UUID | não | |
| discard_reason | text | não | se discarded |
| published_at / published_by | | não | SoD |

### 2.10 IA e trabalhos

#### Job
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | |
| job_type | enum | sim | ia_*, report_export, malware_scan… |
| status | enum | sim | máquina Job |
| requested_by | UUID | sim | |
| idempotency_key | string | sim | único por org |
| input_ref | json | sim | IDs de fontes; sem payload sensível em log |
| error_code / error_safe_message | | não | sem vazamento |
| started_at / finished_at | timestamptz | não | |

#### AiSuggestion
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | |
| job_id | UUID | sim | |
| use_case | string | sim | |
| status | enum | sim | suggested/accepted/edited/rejected |
| target_type / target_id | | sim | draft editável |
| suggestion_payload | json | sim | classificação ≥ confidential |
| provenance | json | sim | modelo, prompt hash, fontes (ADR-008) |
| reviewed_by / reviewed_at | | não | |
| human_diff | json/text | não | se `edited` |

### 2.11 Auditoria e suporte excepcional

#### PlatformAuditEvent
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | cond. | nulo só em eventos de plataforma |
| actor_type | enum | sim | `user` \| `service` \| `system` |
| actor_user_id | UUID | cond. | **obrig. se** `actor_type=user`; null caso contrário |
| actor_membership_id | UUID | não | quando user no contexto de org |
| actor_service_id | string | cond. | **obrig. se** `actor_type=service` (ex. `quarantine_worker`, `ai_worker`) |
| action | string | sim | |
| resource_type / resource_id | | sim | |
| from_status / to_status | string | não | |
| correlation_id | UUID | sim | |
| result | enum | sim | success/denied/error |
| metadata | json | não | sem segredos; PII mínima |
| created_at | timestamptz | sim | append-only |

CHECK: (`actor_type=user` ∧ `actor_user_id` NOT NULL ∧ `actor_service_id` IS NULL) ∨ (`actor_type=service` ∧ `actor_service_id` NOT NULL ∧ `actor_user_id` IS NULL) ∨ (`actor_type=system` ∧ ambos null).

#### BreakGlassSession
| Atributo | Tipo lógico | Obrig. | Notas |
|---|---|---|---|
| id | UUID | sim | |
| organization_id | UUID | sim | uma org |
| platform_admin_user_id | UUID | sim | |
| reason / ticket_id | string | sim | |
| started_at / expires_at | timestamptz | sim | |
| ended_at | timestamptz | não | |
| scope_notes | text | não | |

---

## 3. Chaves e relacionamentos

```text
User 1──* Membership *──1 Organization
Organization 1──* Unit
Organization 1──* OrgProcess
Organization 1──* Assessment
Assessment 1──* AssessmentScope → OrgProcess | Requirement
Assessment 1──* AssessmentTeamMember → Membership
Assessment 1──* Interview 1──* Answer
Assessment 1──* Evidence 1──* EvidenceLink → …
Assessment 1──* Finding *──* Requirement
Finding *──* Evidence (via FindingEvidence / EvidenceLink)
Assessment 1──* MaturityAssessment (versionado) 1──* MaturityScore → MaturityCriterion
MaturityModel 1──* MaturityDimension 1──* MaturityCriterion
Assessment 1──* ActionPlan 1──* ActionItem
Assessment 1──* Report (versionado; pode FK maturity_assessment)
Job 1──* AiSuggestion → alvo draft
Organization 1──* PlatformAuditEvent
```

### Regras de integridade

1. **FK same-tenant:** toda FK entre entidades de cliente exige `organization_id` igual nos dois lados (enforce na aplicação + CHECK/trigger ou coluna composta nas FKs físicas futuras).
2. **Catálogo → cliente:** Assessment referencia `standard_version_id` / `assessment_model_id` / `maturity_model_id` globais; nunca o inverso com dados de cliente no catálogo.
3. **Finding submit/approve — base por tipo** (ver também `001_State_Machines` §4.1):
   - sempre ≥1 FindingRequirement;
   - `conformity`: `insufficient_evidence=false` e ≥1 Evidence `approved`;
   - `nonconformity` / `observation`: Evidence `approved` **ou** (`insufficient_evidence` + racional);
   - `opportunity`: `insufficient_evidence=false` e (≥1 Evidence `approved` **ou** Answer/observação de entrevista vinculada).
4. **Report.published:** snapshot das Findings aprovadas; não edita Finding in-place. Se incluir maturidade, FK para `MaturityAssessment` `approved` (ou `superseded` se publicado contra versão histórica).
5. **ActionItem.owner_membership_id** deve pertencer à mesma `organization_id`.
6. **MaturityScore:** `level` NOT NULL iff `applicability = applicable`; `na_rationale` NOT NULL iff `not_applicable`; `insufficient_info` proibido em pacote `approved`. Pacote `approved` imutável; correção = nova `version_no`.
7. **Cálculo:** `global_score` / dimension scores com half-up, 2 casas; pesos = 1 no v0.
8. **Evidence.legal_hold:** flag; `mark_disposal`/`dispose` exigem `legal_hold=false`. Estado principal permanece `approved`/`rejected`/`superseded`.
9. **PlatformAuditEvent:** coerência `actor_type` ↔ `actor_user_id` / `actor_service_id` (CHECK acima).

---

## 4. `organization_id`

| Regra | Detalhe |
|---|---|
| Obrigatoriedade | Toda linha de negócio de cliente |
| Origem | Membership/contexto autenticado — **nunca** confiar só no body |
| Propagação | Filhos herdam do agregado raiz (Assessment, Evidence, …) |
| Consultas | Predicado obrigatório em listagens, busca, export, jobs e prompts |
| Índices | Prefixo `(organization_id, …)` em quase todas as tabelas tenant |
| Exceções | `User`, catálogo normativo, grants de plataforma |

---

## 5. Dados pessoais e classificação

| Dado | Classificação mínima | Notas |
|---|---|---|
| email, nome, telefone (User/Contact) | restricted (PII) | Minimizar em logs/auditoria |
| Respostas de entrevista citando pessoas | confidential+ | |
| Evidências (conteúdo) | conforme marcação; default confidential | Binário no S3 |
| Finding/Report body | confidential | |
| AiSuggestion + provenance | confidential / restricted | Prompt completo não em log de app |
| IDs técnicos, status, contagens | internal | |
| Catálogo normativo autorizado | internal/public conforme licença | |

Marcações: `classification` em Evidence e, quando útil, em anexos de Report/export. Jobs de IA só leem fontes com classificação permitida pelo caso de uso.

---

## 6. Retenção

| Classe | Política típica (ajustável por Organization) |
|---|---|
| Assessment + Finding + Report publicados | Retenção longa (ciclo de certificação / contrato) |
| Evidence aprovada vinculada | ≥ retenção do Assessment/Report; `legal_hold` bloqueia descarte |
| Evidence rejeitada / upload abandonado | Curta (dias) → `disposed` |
| AiSuggestion rejeitada | Curta ou anonimização de payload |
| Job logs técnicos | Curta; sem conteúdo de evidência |
| PlatformAuditEvent | Longa; append-only; purga só por política legal |
| BreakGlassSession | Longa (compliance) |

Descarte segue máquina Evidence (`pending_disposal` → `disposed`): objeto S3, derivados e índices; metadados mínimos + auditoria permanecem.

---

## 7. Auditoria

Eventos mínimos a registrar:

- Transições de estado das máquinas (de→para, ator, correlação).
- Aprovações com SoD (Finding, Report, MaturityAssessment, validação de ação).
- Upload/download/descarte de Evidence.
- Enfileiramento e conclusão de Job; accept/edit/reject de AiSuggestion.
- Declaração de N/A em maturidade (justificativa + ator).
- Mudanças de Membership/papéis; revoke.
- Ativação/uso de BreakGlassSession.
- Tentativas negadas relevantes (autorização).

`PlatformAuditEvent` é **append-only**. Correlação liga API request ↔ Job ↔ sugestão.

---

## 8. Índices e restrições (orientação física futura)

Ainda sem DDL; intenções:

| Alvo | Intenção |
|---|---|
| PK | UUID em todas as entidades |
| UK Membership | `(organization_id, user_id)` onde status ativo |
| UK User | `idp_sub`; `email` |
| UK Job | `(organization_id, idempotency_key)` |
| UK Report | `(assessment_id, version_no)` |
| UK MaturityModel | `(model_code, model_version)` |
| UK MaturityAssessment | `(assessment_id, version_no)` |
| CHECK audit actor | ver PlatformAuditEvent |
| CHECK finding base | conformidade sem insufficient; etc. (app + CHECK parcial) |
| UK MaturityScore | `(maturity_assessment_id, criterion_id)` |
| UK Evidence versão | `(organization_id, lineage_id, version_no)` se lineage for introduzido |
| IDX listagens | `(organization_id, status, updated_at DESC)` em Assessment, Finding, ActionItem, Report |
| CHECK level | `level BETWEEN 1 AND 5` ou NULL |
| CHECK applicability | coerência level/na_rationale (regra 6) |
| IDX Evidence | `(organization_id, assessment_id, status)`; hash para dedup opcional |
| IDX Audit | `(organization_id, created_at DESC)`; `(correlation_id)` |
| CHECK status | valores ∈ conjuntos das máquinas |
| CHECK SoD (app) | `approved_by ≠ author` em Finding; regras análogas em Report/ActionItem |
| NOT NULL | `organization_id` em tabelas tenant |
| FK same-org | composta ou trigger na implementação |

---

## 9. Fora deste documento

- Scripts SQL / Alembic / migrations.
- Particionamento físico, tablespaces, RLS PostgreSQL (candidato futuro alinhado ao ADR-002).
- Schemas OpenAPI.
- Modelo dimensional de analytics.

## 10. Próximos passos sugeridos

1. ER lógico: `002_ER_Logical.md` (este ciclo).
2. DDL v0 / migração **somente** após Aceito + congelamento (`006_Domain_Acceptance_Checklist.md`).
3. Política de retenção versionada por organização.
