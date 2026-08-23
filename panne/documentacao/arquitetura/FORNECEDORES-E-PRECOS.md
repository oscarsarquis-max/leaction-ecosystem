# Fornecedores, itens e valores de compra

Fornecedor e item são da organização. O item liga-se ao ingrediente (SKU, descrição, embalagem, unidade, situação).

Novo valor de compra: data, moeda (`BRL`, `USD`, `EUR`), fonte opcional. Histórico append-only em `supplier_item_price`. O mais recente é projeção, não overwrite.

O valor pertence ao item, não à identidade do ingrediente. Não há custo de receita, custo de produção, markup, margem nem valor de venda.
