# Concessão e revogação de papéis

- Permissão: `membership.role.manage` (proprietário e administrador)
- Concessão e revogação geram `audit_event`
- Não revogar o último proprietário ativo da organização
- Não revogar o último papel ativo da associação
- Escalada: só proprietário concede/revoga `owner`/`organization_owner`; administrador não promove a proprietário
- Gerente de produção não recebe `membership.role.manage`
- Segunda conferência de pesagem continua exigindo **usuários** diferentes, não papéis diferentes
