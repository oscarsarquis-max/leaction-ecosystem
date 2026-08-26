# ADR — Estoque e compras (CURSOR-023)

## Decisão

A Panne passa a ter um domínio operacional de estoque quantitativo e compras internas, sobre os fatos já existentes de ingredientes, fornecedores, produção, custos e relatórios. Nada deste ciclo calcula custo contábil, envia pedido ao fornecedor ou compra automaticamente.

## Cadeia

`7086faa` → CURSOR-022 local/`0019_reporting_analytics` → CURSOR-023 local/`0020_inventory_procurement`

## Consequências

- Ingrediente permanece a identidade de material; item estocável aponta para ele.
- Movimento é append-only; saldo é projeção.
- Reserva e separação não alteram o físico.
- Consumo de produção continua soberano; o estoque apenas posta referência.
- Relatórios de estoque estendem o motor do 022.
