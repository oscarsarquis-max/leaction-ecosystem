# Reconciliação CURSOR-022

| Domínio | Fonte canônica | Uso analítico | Impossível |
|---|---|---|---|
| Organização/estabelecimento | `organization`, `establishment` | filtro | — |
| Produto técnico | `technical_product` | dimensão | SKU comercial |
| Ingrediente e preço | `ingredient`, `supplier_item_price` | cobertura de preço | estoque |
| Formulação | `formulation_version`, `scale_calculation` | dimensão | — |
| Plano e ordem | `production_plan`, `production_order` | estados, quantidade | venda |
| Consumo | `production_order_material`, `production_material_consumption` | líquido e variação | compra |
| Rendimento | `production_yield_measurement` | pré/pós, leftover, scrap | causa automática |
| Custo | `costing_calculation` | previsto/realizado | lucro |
| Preço | `practiced_price`, `pricing_simulation` | markup/margens 021 | faturamento |
| Conformidade | `labeling_dossier`, `labeling_assessment` | cobertura | certificado |
| Rastreio | `production_event`, `production_sheet_issue` | timeline | token |
| Nutrição | `ingredient_nutrient` | cobertura | laudo fiscal |

Indicadores impossíveis: faturamento, vendas, lucro líquido, giro de estoque, ruptura, folha e apuração tributária.
