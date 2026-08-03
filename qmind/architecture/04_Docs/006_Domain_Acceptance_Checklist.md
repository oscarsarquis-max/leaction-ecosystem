# QMind — Checklist de aceite dos documentos de domínio

- Status: Aceito
- Data: 2026-08-03
- Congelamento: **`domain-docs-v0`**
- Escopo de aceite (pacote):
  - `02_Models/000_Domain_Model.md`
  - `02_Models/001_State_Machines.md`
  - `02_Models/002_Roles_and_Permissions.md`
  - `02_Models/003_Maturity_Model.md`
  - `03_Database/001_Data_Dictionary.md`
  - `03_Database/002_ER_Logical.md`
  - `99_Reference/001_Domain_Glossary.md`
- Regra: aceite exige contrato de transição (não basta “completo”).

## 1. Contrato obrigatório por transição

| Elemento | Pergunta de aceite |
|---|---|
| Autor autorizado | Quem (papel + relação/SoD / sys|service) pode disparar? |
| Pré-condições | Guardas de dados/estado de outros agregados? |
| Efeitos | O que muda no recurso e em agregados relacionados? |
| Auditoria | Evento append-only com de→para, `actor_type`, org, correlação? |
| Cancelamento | Existe caminho de cancel/descarte auditável quando aplicável? |
| Reabertura | Reopen controlado, nova versão, ou imutabilidade justificada? |

## 2. Bloqueadores da revisão — resolução (2026-08-03)

| # | Bloqueador | Resolução |
|---|---|---|
| 1 | Maturidade `approved` sem caminho de correção coerente | `supersede` → novo pacote `draft` `version_no+1`; sem reject/rework de approved |
| 2 | Relatório sem cancelamento auditável | `draft`/`in_review` → `discarded` com autor, guarda, efeitos |
| 3 | `legal_hold` como estado e bool | Flag ortogonal; estados sem `legal_hold`; place/release_hold não mudam status |
| 4 | Insuficiência sustentando conformidade | §4.1: conformity exige Evidence approved; insufficient só NC/observation |
| 5 | `actor_user_id` obrigatório vs autor sys | `actor_type` user\|service\|system + CHECK de identidade |
| 6 | Maturidade/glossário/ER fora do aceite | Incluídos no escopo; promovidos a Aceito no pacote |

## 3. Critérios de promoção — marcados

- [x] Responsável confirma §1 para Assessment, Evidence, Finding, ActionPlan/Item, Report, MaturityAssessment, Job/AiSuggestion (contrato nas máquinas + matriz de papéis)
- [x] Nenhuma transição de aprovação/publicação sem SoD onde exigido
- [x] Cancelamento e reabertura cobertos ou declarados impossíveis com justificativa (incl. Report/Maturity `discarded`; Evidence/`approved` maturidade via nova versão)
- [x] Maturidade e glossário consistentes com entidades/enums do dicionário
- [x] Dicionário e ER lógico atualizados; pacote pronto para congelamento

## 4. Estado dos documentos no congelamento

| Documento | Estado |
|---|---|
| `000_Domain_Model.md` | Aceito |
| `001_State_Machines.md` | Aceito |
| `002_Roles_and_Permissions.md` | Aceito |
| `003_Maturity_Model.md` | Aceito |
| `001_Data_Dictionary.md` | Aceito |
| `002_ER_Logical.md` | Aceito |
| `001_Domain_Glossary.md` | Aceito |

## 5. Congelamento `domain-docs-v0`

- Tag/marco documental: **`domain-docs-v0`** (2026-08-03).
- Mudanças posteriores: emenda versionada ou novo marco (`domain-docs-v0.1` / `v1`); não editar silenciosamente o Aceito.
- **DDL v0 e migração inicial:** liberados para elaboração a partir deste marco; implementação ainda não iniciada neste passo.
