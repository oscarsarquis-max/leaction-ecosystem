# Contexto organizacional e RLS

Ciclo de origem: CURSOR-010.

## Fluxo

1. Verificar access token.
2. Localizar `issuer + subject`.
3. Confirmar usuário ativo.
4. Receber organização solicitada (`X-Panne-Organization-Id` quando houver).
5. Confirmar associação ativa.
6. Carregar papéis e permissões.
7. Abrir transação.
8. Definir contexto PostgreSQL local (`set_config(..., true)`).
9. Acessar os dados.
10. Encerrar a transação, eliminando o contexto.

GUCs: `app.current_organization_id`, `app.current_user_id`, e, para a busca do vínculo, `app.current_issuer` / `app.current_subject`. Ausência, UUID inválido ou contexto incompleto → negação por padrão.

O contexto **não** é persistente na sessão do pool. Testes comprovam reutilização de conexão sem vazamento.

## Papéis PostgreSQL

| Papel | Uso |
|---|---|
| migrador / admin (`PANNE_DATABASE_URL`) | Alembic e bootstrap |
| `panne_runtime` (`PANNE_RUNTIME_DATABASE_URL`) | API autenticada |

O runtime não é superusuário, não é dono das tabelas e não possui `BYPASSRLS`. A criação do papel não vai no Alembic (portabilidade); usa `scripts/dev/bootstrap-runtime-role.ps1`.

## HTTP

- `GET /api/v1/me` — contrato mínimo autenticado.
- 401 token ausente, inválido ou expirado.
- 403 sem associação ou sem permissão.
- 503 sanitizado se JWKS indisponível e sem cache.
- `/health` público e independente do banco.
- `/ready` mantém o contrato anterior.

Cabeçalho `Authorization` limitado. JWT e o header não são registrados em log.
