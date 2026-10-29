# CURSOR-027-C3-H3 — evidência sanitizada do incidente H2 (sem senha / sem URL)

| Campo | Valor |
|---|---|
| Task ARN | `arn:aws:ecs:us-east-2:253137917703:task/paneldx-cluster/0501b07f068a41a6ba256277b65dabce` |
| Task definition | `panne-db-migration:3` |
| Log group | `/ecs/panne/db-migrations` |
| Log stream | `c3h2-demo/panne-db-migration/0501b07f068a41a6ba256277b65dabce` |
| Intervalo (epoch ms first→last) | `1787933290894` → `1787933295428` |
| Erro | `ConfigParser` / `ValueError: invalid interpolation syntax` ao setar `sqlalchemy.url` |
| URL no log | **confirmado** (userinfo presente no traceback Alembic) |
| Conteúdo bruto | **não** recopiado (contenção) |
| Escopo credencial | somente `panne/demo/db/migrator` → role `panne_demo_migrator` / DB `panne_demo` |
| Produção no incidente | **não** |
| Migration aplicada | **não** (falha em `alembic current` antes de upgrade) |

## IAM com capacidade potencial de leitura do log group

- Usuário operador da conta (ex.: `paneldx-user-admin`) com permissões CloudWatch Logs na conta
- Role `panne-db-migration-task-role` (somente CreateLogStream/PutLogEvents/DescribeLogStreams — **sem** GetLogEvents)
- Qualquer principal com `logs:GetLogEvents` / `logs:FilterLogEvents` no group `/ecs/panne/db-migrations` (políticas amplas de leitura da conta)

## CloudTrail

Consulta de acesso a `GetLogEvents`/`FilterLogEvents` no stream acima: registrar contagem/eventos de API **sem** payload de log. (executado no preflight H3; ausência de hit adicional além do operador da contenção = OK a documentar no handoff.)
