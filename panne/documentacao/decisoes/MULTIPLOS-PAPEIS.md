# Múltiplos papéis por associação

A autorização deixa de depender de um papel único.

- Tabela `organization_membership_role`: organização, associação, papel, concedido por/em, revogado por/em, motivo
- Papel ativo único por par associação+papel (`revoked_at IS NULL`)
- Revogação preserva a linha
- Atribuições 013 foram copiadas sem perda
- `organization_membership.legacy_role_label` é rótulo legado. Alterá-lo não concede permissão
- Autorização usa somente papéis ativos de `organization_membership_role`
- `/api/v1/me` devolve `roles` (lista), sem o singular `role`
- Permissões = união dos papéis ativos da associação selecionada
- Grupos do Cognito não autorizam
