# Fronteiras futuras — fórmula, preparação e custo

O núcleo `0004_formulation_lab` já cobre composição, versão, escala, trial e aprovação. O que **não** entra em `ingredient_version` nem neste ciclo:

| Conceito | Destino |
|---|---|
| Ficha técnica renderizada / PDF | `technical_document` (futuro) |
| Tabela nutricional do produto acabado | Prévia técnica em `0005`; perfis/LOQ em `0006`; governança em `0008`; rótulo futuro |
| Embeddings, Bedrock, Claude | Consumidores futuros da biblioteca `0006`; nunca fonte primária |
| Rótulo | `label_snapshot` |
| Ordem legal de declaração | Projeção do snapshot; distinta de `ingredient_composition.sequence` |
| Preparação publicada como insumo | Ver abaixo |
| Custo da formulação | Cálculo satélite; ver abaixo |

`ingredient_composition.sequence` continua sendo a árvore do **insumo composto**. A ordem da formulação é `formulation_item.sequence`.

## Preparação usada como ingrediente

Não há publicação automática de formulação como ingrediente.

Quando for implementada:

1. a formulação precisa estar aprovada e publicada;
2. um ato técnico explícito cria o insumo;
3. nasce `ingredient.ingredient_type = preparation` e uma `ingredient_version`;
4. a origem aponta a `formulation_version` (rastreio);
5. outras formulações usam essa `ingredient_version` — nunca um `formulation_id` polimórfico em `formulation_item`.

## Custos

- Preços observados: `supplier_item_price`.
- Custo da ficha: cálculo satélite com snapshot próprio (não coluna da versão).
- Preço comercial / canal: fora da formulação (`technical_product` não é SKU).
- Alterar preço **não** muda versão publicada, itens, nem `scale_calculation`.
