# Baseline quantitativo `panne_demo` — pré-deploy CURSOR-028-RELEASE

**Capturado:** 2026-08-31T16:56:52Z (ECS read-only)  
**Head:** `0022_fiscal_inbound`  
**Regra:** sem reseed/truncate; pós-deploy comparar; redução → stop + rollback app.

Fonte: `panne-demo-counts-pre.json` · prova `panne`: `panne-prod-intact-pre.json`

## Totais

| Métrica | Contagem |
|---------|--------:|
| produtos | 12 |
| ingredientes | 19 |
| receitas | 6 |
| ordens | 10 |
| planos | 10 |
| fornecedores | 4 |
| lotes | 6 |
| saldos | 6 |
| movimentos | 7 |
| entradas_fiscais | 0 |
| usuarios_demo | 9 |

## Por organização

### `panne-demonstracao` (Panne Demonstração)

| Métrica | Contagem |
|---------|--------:|
| produtos | 12 |
| ingredientes | 18 |
| receitas | 6 |
| ordens | 10 |
| planos | 10 |
| fornecedores | 4 |
| lotes | 6 |
| saldos | 6 |
| movimentos | 7 |
| entradas_fiscais | 0 |
| usuarios_demo | 7 |

### `padaria-horizonte-demo` (Padaria Horizonte Demo)

| Métrica | Contagem |
|---------|--------:|
| produtos | 0 |
| ingredientes | 1 |
| receitas | 0 |
| ordens | 0 |
| planos | 0 |
| fornecedores | 0 |
| lotes | 0 |
| saldos | 0 |
| movimentos | 0 |
| entradas_fiscais | 0 |
| usuarios_demo | 2 |

## Banco `panne` (produção)

- Identidade: `panne` / `panne_prod_migrator`
- Sem `alembic_version` / sem `organization` nesta pipeline → **não migrado** (congelado; não é redução da demo)

## Pós-deploy

```text
python run_snapshot_panne_demo_counts_ecs.py post
python snapshot_panne_demo_counts.py --phase post --compare .../panne-demo-counts-pre.json
```

(Comparação automática no runner local; ECS gera o `post.json` para diff.)
