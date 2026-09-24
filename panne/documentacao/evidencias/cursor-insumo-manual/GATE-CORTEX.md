# Pacote para o Cortex — gate corretivo (ainda não publicar)

**Não publicado.** Organização de ensaio descartável. Demo, Hub, CMS e Loja de Pães reais não foram alterados.

## SHA

O commit isolado deste pacote (não o monorepo sujo) é o SHA desta entrega.

## Migração

- `panne/backend/alembic/versions/0030_ingredient_link_and_lot_declaration.py`
- `revision = 0030_ingredient_link_lot` (≤32 chars)
- `down_revision = 0029_fiscal_review_without_stock`
- Validada: `alembic current` → `0030_ingredient_link_lot (head)`
- Aditiva. Sem seed. Sem consolidação das farinhas reais.

## Correções deste gate

1. **Prova visual da aplicação autenticada.** `capture-insumo-manual.mjs` abre `http://127.0.0.1:5182` (Vite da Panne; `:5180` está com o Monitor da Spider) com sessão fake e org descartável. Rotas reais: `/componentes/ingredientes/consolidar`, `/componentes/estoque/abertura`, `/gestao/compras/entradas/:id`. Sem mock `**/api/**`, sem print de `/entrar`. Comparação com a prévia de 960 px em `COMPARAR-PREVIA.md`.
2. **Conteúdo de embalagem após uso.** A condição impossível foi removida. `apply_package_content` vale nas duas rotas: correção auditada e concorrente antes de uso; depois só repetição idêntica (`conteudo_embalagem_ja_usado`).
3. **Reconciliação após reassociação.** Movimentos permanecem append-only. `GET /inventory/lots/{id}/reconciliation` e a projeção em `movement_out` mostram item registrado × item atual do lote, sem somar saldo nem duplicar custo.
4. **Custo desconhecido.** Se o recorte do ingrediente tem lote `unknown`, `select_price` não devolve preço completo (nem fallback de lote conhecido nem recibo). A UI declara recorte por lote.

## Testes dirigidos

```
pytest tests/test_ingredient_link_consolidate.py tests/test_costing_pricing.py::test_mixed_unknown_lot_blocks_supplier_fallback
```

9 + costing: consumo parcial, reserva, replay idêntico, consolidação recusada após uso, duas linhas da mesma nota reconciliadas por lote, lote misto não vira custo completo.

## Contagens no banco descartável (`ensaio-insumo-eb353b`)

| Tabela | Depois |
|---|---|
| ingredient | 4 |
| inventory_lot | 6 |
| inventory_movement | 6 |
| inventory_balance | 6 |
| ingredient_link_reassignment | 3 |

Loja de Pães, Demo e produção não entram nestas contas.

## Capturas reais

`capturas/` — URL visível em `urls.json`:

- consolidar antes/seleção/depois 1440, 390, prévia 960
- abertura antes/erro/desconhecido/depois 1440 e 390
- revisão da nota 1440 e 390
