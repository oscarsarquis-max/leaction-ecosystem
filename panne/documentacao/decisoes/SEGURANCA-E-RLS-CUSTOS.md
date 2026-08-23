# Segurança e RLS — custos e preços

Todas as tabelas 0018 têm `ENABLE` + `FORCE` ROW LEVEL SECURITY, política `organization_id = panne_current_org_id()`, default deny. Isolamento A/B sem fallback administrativo no runtime. `panne_runtime` recebe GRANT explícito.

Cálculos, componentes, evidências, lacunas, invalidações, simulações, decisões e comandos são append-only. Versão de política publicada não é reescrita. Exclusão física bloqueada por `panne_forbid_physical_delete()`.

Cognito groups e `legacy_role_label` não autorizam.
