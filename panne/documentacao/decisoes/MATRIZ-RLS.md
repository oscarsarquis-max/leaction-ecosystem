# Matriz RLS

Ciclo 010. Runtime: `panne_runtime`. Sem contexto → negação. Políticas explícitas, sem permissiva ampla.

| Tabela | Propriedade | Leitura runtime | Escrita runtime | Política |
|---|---|---|---|---|
| organization | híbrida (o próprio tenant) | org atual ou associação ativa do usuário | negada | `rls_organization_select` |
| establishment | organizacional | `organization_id` = contexto | mesmo | `rls_establishment_org` |
| app_user | identidade | próprio id ou membro da org atual | negada | `rls_app_user_select` |
| auth_identity | identidade | próprio usuário ou par issuer/subject local | negada | `rls_auth_identity_select` |
| organization_membership | organizacional | próprio usuário ou org atual | só org atual | select + org |
| audit_event | híbrida | org atual ou evento próprio sem org | insert controlado; sem update/delete | select + insert |
| permission / role_permission | global | autenticado | negada | select se ator |
| measurement_unit, unit_conversion, nutrient_definition, allergen, data_source, knowledge_tag | global | autenticado | negada | select se ator |
| ingredient* / supplier / supplier_item | organizacional | org atual | org atual | org |
| supplier_item_price | herdada de supplier_item | via pai | via pai | EXISTS pai |
| technical_product … approval | organizacional | org atual | org atual | org |
| nutrition_calculation* / calculation_evidence | organizacional | org atual | org atual | org |
| knowledge_source / version / fragment | híbrida | org atual ou global `released` | só org própria (não global) | select híbrido + write org |
| knowledge_source_tag | herdada | via fonte visível | via fonte organizacional | EXISTS fonte |
| grounding_query | híbrida | org atual ou query própria sem org | só org atual | select + write |
| grounding_result / grounding_citation | herdada | via query organizacional | via query | EXISTS query |
| nutrition_expectation_profile | híbrida | org atual ou global autenticado | só org própria | select + write |
| nutrition_expectation_profile_item | herdada | via perfil | via perfil organizacional | EXISTS perfil |
| ai_* | organizacional | org atual | org atual | org |
| compliance_framework / version / requirement / requirement_source | híbrida | org atual ou global autenticado | só org própria | select + write |
| compliance_profile … review | organizacional | org atual | org atual | org |
| alembic_version | infraestrutura | sem GRANT ao runtime | sem GRANT | sem RLS |
| production_* (0010) | organizacional | org atual | org atual | `rls_*_org`; evento sem update/delete (gatilho) |
| production_* (0011 execução) | organizacional | org atual | org atual | `rls_*_org`; ledgers append-only; política imutável após freeze |

Isolamento A/B: a organização A não lê nem altera linhas de B. `INSERT`/`UPDATE` não podem trocar `organization_id`. Conhecimento global `restricted` permanece invisível.
