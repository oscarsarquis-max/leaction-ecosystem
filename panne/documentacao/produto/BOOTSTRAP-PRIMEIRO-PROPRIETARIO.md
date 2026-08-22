# Bootstrap do primeiro proprietário

Não há autocadastro. O primeiro vínculo é explícito e administrativo.

1. Aplicar migrações com `PANNE_DATABASE_URL` (papel migrador).
2. Criar o papel `panne_runtime` com `scripts/dev/bootstrap-runtime-role.ps1`.
3. Em sessão administrativa Python, chamar `bootstrap_first_owner` com emissor, `sub` opaco, e-mail, organização e papel `owner`.
4. Configurar Cognito (emissor e app client) no `.env` local. Não versionar segredos.
5. A API de runtime usa `PANNE_RUNTIME_DATABASE_URL`.

Nenhum endpoint público cria usuário ou organização.
