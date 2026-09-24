# Pacote para o Cortex — candidato sobre a linha produtiva (ainda não publicar)

**Não publicado.** Produção permanece em `d0a3451` / `panne-prod-api:15`. SHA `7177805` sem efeito.

## SHA

Ver o commit deste ramo `feat/panne-insumo-manual-on-prod`. Relato completo em `INTEGRACAO-CANDIDATO.md`.

## Migração

- `panne/backend/alembic/versions/0030_ingredient_link_and_lot_declaration.py`
- `revision = 0030_ingredient_link_lot`
- `down_revision = 0029_fiscal_review_without_stock`
- Prova aditiva: `tests/test_0030_additive_from_0029.py` (base descartável a partir de 0029; sem consolidar nem reescrever lote/saldo)

## Provas deste gate

1. Diff só `panne/**` contra `d0a3451`. Login, primeiro acesso, fiscal e Dockerfile intactos.
2. Backend dirigido 57 passed + compileall. Frontend build ok. Vitest do delta 59 passed.
3. Capturas React autenticadas em `:5183` (API `:5083`), org descartável. Ver `COMPARAR-PREVIA.md` e `capturas/`.
4. 0030 não funde tipo 1 / tipo 0 / tipo 00 nem marcas; sem inferência por nome/GTIN.

## Testes dirigidos

```
pytest tests/test_ingredient_link_consolidate.py \
  tests/test_fiscal_review_without_stock.py \
  tests/test_fiscal_receipt_http.py \
  tests/test_inventory_procurement.py \
  tests/test_costing_pricing.py::test_mixed_unknown_lot_blocks_supplier_fallback \
  tests/test_0030_additive_from_0029.py
```

## Capturas reais

`capturas/` — URL visível em `urls.json`. Inclui estoque, lotes, Gigio recolhido/aberto, consolidação, abertura e revisão fiscal em 1440 e 390.
