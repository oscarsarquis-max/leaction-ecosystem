# Seleção determinística de preço

Fonte exclusiva: `supplier_item` + `supplier_item_price`. Sem cópia.

1. Itens ativos do ingrediente na organização.
2. Critério da política: último observado ou item explícito.
3. Somente `observed_at <= valuation_at`.
4. Desempate estável: vigência, criação, identificador.
5. Moeda diferente da política falha (`moeda_incompativel`). Sem câmbio.
6. Custo = `(quantidade convertida / quantidade da embalagem) × preço`.
7. Conversão só na mesma dimensão; massa→volume proibida.
8. Ausência gera lacuna, nunca zero.
9. Não escolhe o menor preço automaticamente.

O snapshot guarda fornecedor, item, preço, embalagem, unidade, fator, vigência, fonte e data.
