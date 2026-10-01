# ACTIONFINANCE_REV_009_COR_001 — Cursor, limites e restore

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_REV_009_COR_001 |
| Prompt | [ACTIONFINANCE_PRM_009_COR_001](../prompts/ACTIONFINANCE_PRM_009_COR_001.md) |
| Data | 01/10/2026 |
| Executor | Cursor |
| Ambiente | Homologação local. Sem produção. Sem commit/push. |
| Estado | **Correções concluídas.** Aceite parcial do percurso local preservado. |

## O que foi corrigido

1. Hub `spider-pay-lookup.js`: `WHERE` e `ORDER BY` usam o mesmo `date_trunc('milliseconds', updated_at)` + `id::text`. O cursor grava o ISO truncado. Sem isso, dois pedidos no mesmo milissegundo com microssegundos distintos podiam sair da janela ou repetir a página.
2. `ACTIONHUB_PAY_LOOKUP_PUBLIC_TEST` passa a ligar a listagem sem exigir `LOOKUP_ISOLATED`. Isolado continua a existir para o Hub descartável. Produção **não** recebeu nenhuma flag.
3. Prova PostgreSQL 17.6 em `:55434`: cinco linhas (mesmo ms / micros distintos, mesmo timestamp / IDs distintos, limite 2). Primeira caminhada = 5/5. Depois de atualizar o primeiro item, ele reaparece no fim. Sem perda. Evidência: `evidence/prm-009-cor-001/cursor-pg-proof.json`.
4. Restore local em `:55433`: Flyway V1–V12, dump de `tenant` + `company` + tabelas V12, FKs válidas (`fk_ok=16`, `orphans=0`), grants de runtime (SELECT/INSERT/UPDATE conforme V12; sem DELETE). `DELETE` de runtime recusado (`delete_denied=1`). Contagens: 2 tenants, 3 empresas, 16 runs, 156 transações, 157 revisões, 1 checkpoint. Sem RDS.

Unidade Hub: 11/11.

## Fora deste corretivo

Produção, commit/push, payout, baixa, Panne, PRM_010, invalidação de sessão do PRM_007.
