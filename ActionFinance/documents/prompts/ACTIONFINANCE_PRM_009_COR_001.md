# ACTIONFINANCE_PRM_009_COR_001 — Cursor, limites e restore com FKs

Data: 01/10/2026.

Corretivo autorizado pelo [ADENDO_001](ACTIONFINANCE_PRM_009_ADENDO_001_ACEITE_PUBLICO.md). Preserva o aceite parcial do percurso local. Não aplica mudanças públicas.

## Pedido

1. Tornar cursor e `ORDER BY` coerentes no milissegundo (`date_trunc` + `id::text`).
2. Provar contra PostgreSQL a ausência de perdas nos limites (mesmo milissegundo com microssegundos distintos, mesmo timestamp com IDs distintos, item já percorrido que volta a atualizar).
3. Restore local das estruturas V12 com dependências (`tenant`/`company`), FKs válidas e permissões completas. Sem RDS.

## Fora

Produção, commit/push, payout, baixa automática, Panne, PRM_010, invalidação de sessão do PRM_007.
