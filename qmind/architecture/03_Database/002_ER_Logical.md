# QMind — ER conceitual / lógico (v0)

- Status: Aceito
- Data: 2026-08-03
- Congelamento: `domain-docs-v0`
- Depende de: `001_Data_Dictionary.md`, `../02_Models/003_Maturity_Model.md`, `../99_Reference/001_Domain_Glossary.md`
- Aceite: `../04_Docs/006_Domain_Acceptance_Checklist.md`
- Escopo: modelo **lógico** (entidades, cardinalidades, chaves). **Não é DDL.**
- DDL físico: liberado somente após este congelamento (ainda não iniciado).

## 1. Convenções do diagrama

- Retângulo = entidade; `PK` / `FK` / `UK` anotados.
- `«tenant»` = possui `organization_id` NOT NULL.
- `«catalog»` = global, sem tenant.
- Cardinalidade: `1` / `*` / `0..1`.

## 2. Visão geral

```text
«catalog»                         «tenant»
Standard ─* StandardVersion       Organization ─* Unit
                │                      │
                *                      ├─* Membership *─ User
           Requirement                 ├─* OrgProcess
                ▲                      └─* Assessment
AssessmentModel *──* Criterion/Question         │
MaturityModel ─* MaturityDimension ─* MaturityCriterion
        ▲                                       │
        └─────────────── MaturityAssessment ────┤
                              │                 ├─* AssessmentScope
                              *                 ├─* AssessmentTeamMember
                        MaturityScore           ├─* Interview ─* Answer
                                                ├─* Evidence ─* EvidenceLink
                                                ├─* Finding ─* FindingRequirement
                                                │         └─* FindingEvidence
                                                ├─* ActionPlan ─* ActionItem
                                                └─* Report
Job «tenant» ─* AiSuggestion
PlatformAuditEvent «tenant?»
BreakGlassSession «tenant»
```

## 3. Núcleo de identidade e organização

```text
User (PK id, UK idp_sub, UK email)
  └──1──* Membership «tenant» (UK org+user ativo)
              *──1 Organization (PK id = tenant)
                      └──1──* Unit «tenant» (FK parent_unit opcional, same org)
                      └──1──* OrgProcess «tenant» (FK owner_membership, unit?)
                      └──1──* PersonContact «tenant» (opcional)
```

## 4. Catálogos

```text
Standard 1──* StandardVersion 1──* Requirement (FK parent_requirement?)
AssessmentModel (*──* Requirement | Criterion)
Question N──1 Criterion (ou AssessmentModel)
MaturityModel 1──* MaturityDimension 1──* MaturityCriterion
```

## 5. Avaliação e coleta

```text
Organization 1──* Assessment «tenant»
  FK assessment_model_id → AssessmentModel
  FK standard_version_id → StandardVersion
  FK maturity_model_id → MaturityModel (0..1)
  type ∈ {diagnosis, internal_audit, other}
  status ∈ máquina Assessment

Assessment 1──* AssessmentScope «tenant»
  FK org_process_id?  FK requirement_id?  (≥1 preenchido)

Assessment 1──* AssessmentTeamMember «tenant»
  FK membership_id (same org)

Assessment 1──* Interview «tenant» 1──* Answer «tenant»
  Answer FK question_id / criterion_id
```

## 6. Evidência, constatação, maturidade

```text
Assessment 1──* Evidence «tenant»
  status ∈ {upload_pending, quarantined, rejected, approved, superseded, pending_disposal, disposed}
  legal_hold bool (ortogonal; não é estado)
  UK futuro (org, lineage_id, version_no)

Evidence 1──* EvidenceLink «tenant»
  target_type + target_id

Assessment 1──* Finding «tenant»
  finding_type ∈ {conformity, nonconformity, opportunity, observation}
  insufficient_evidence bool (restrito por tipo — dicionário regra 3)
  status ∈ máquina Finding
  Finding *──* Requirement (FindingRequirement)
  Finding *──* Evidence (FindingEvidence)

Assessment 1──* MaturityAssessment «tenant»
  UK (assessment_id, version_no)
  status ∈ {draft, in_review, approved, rejected, superseded, discarded}
  FK maturity_model_id; FK supersedes_id?
  global_score decimal?

MaturityAssessment 1──* MaturityScore «tenant»
  UK (maturity_assessment_id, criterion_id)
  applicability ∈ {applicable, not_applicable, insufficient_info}
  level 1..5?
  MaturityScore *──* Evidence|Answer|Finding (links)
```

## 7. Ações e relatório

```text
Assessment 1──* ActionPlan «tenant» 1──* ActionItem «tenant»
  ActionItem.action_kind ∈ {correction, corrective_action, improvement}
  ActionItem FK finding_id?
  ActionItem FK owner_membership_id
  status ∈ máquinas ActionPlan / ActionItem

Assessment 1──* Report «tenant»
  UK (assessment_id, version_no)
  status ∈ {draft, in_review, published, archived, superseded, discarded}
  FK supersedes_report_id?
  FK maturity_assessment_id?
```

## 8. IA, auditoria, suporte

```text
Organization 1──* Job «tenant»
  UK (organization_id, idempotency_key)
  Job 1──* AiSuggestion «tenant» (target polimórfico draft)

PlatformAuditEvent
  actor_type ∈ {user, service, system}
  actor_user_id? / actor_service_id? (CHECK mútuo)
Organization 1──* BreakGlassSession «tenant»
```

## 9. Integridade same-tenant (lógica)

Para todo par `A.fk → B.id` entre entidades `«tenant»`:

```text
A.organization_id = B.organization_id
```

Implementação física futura: FK composta `(id, organization_id)` ou trigger/RLS — decisão de DDL, não deste ER.

## 10. Fora deste documento

- Tipos PostgreSQL, indexes físicos, particionamento.
- Seed do catálogo de maturidade v0.
- OpenAPI.

Próximo após **Aceito**: `003_DDL_v0.md` + migração inicial no repositório de código (ainda não criado).
