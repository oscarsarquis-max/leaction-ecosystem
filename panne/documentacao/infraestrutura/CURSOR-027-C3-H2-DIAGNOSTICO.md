# CURSOR-027-C3-H2 — diagnóstico pré-retomada

| Item | Valor |
|---|---|
| Demo falha (C3) | `…/3b39fd9a719a4e8bb6d3d83f43d90560` |
| TD | `panne-db-migration:2` (deregistrada; **proibida**) |
| Exit | **2** |
| Args efetivos | ENTRYPOINT uvicorn + command `python -u /app/migrate_runner.py` → uvicorn recebeu `-u` |
| Log | `Error: No such option '-u'.` |
| Conexão/migration | **não** (uvicorn saiu antes de qualquer SQL) |
| `alembic_version` demo | inferido **ausente** (sem mutação; logs suficientes) |
| Tasks ativas | 0 RUNNING/PENDING |
| Serviço ECS Panne | nenhum |
| Snapshot | `actionhub-prod-pre-panne-migrations-20260828-151146` **available** |
| RDS | `available` |
| Digest | `sha256:b4625c5ca416cd014d89f3e65d849fa740edc5f1ea8a16352981c3bd84e4dc2a` |
| Scan | COMPLETE CRITICAL=0 HIGH=0 |

## Teste local no digest

- Default ENTRYPOINT = uvicorn
- Padrão quebrado reproduz exit 2 / `No such option '-u'`
- `--entrypoint python … -u /app/migrate_runner.py` inicia o runner (não uvicorn)
- Migrate PG17 + idempotência: exit 0, head `0020_inventory_procurement`, fingerprint `d16e9254…`
