# Reconciliação — CURSOR-021

## Dados disponíveis (reutilizados)

| Fato | Origem | Uso no custeio |
|---|---|---|
| Fornecedor, item e preço observado | `supplier`, `supplier_item`, `supplier_item_price` | valoração vigente; desempate `observed_at`, `created_at`, `id` |
| Formulação e itens | `formulation_version`, `formulation_item` | previsto/padrão; `role=packaging` → categoria embalagem |
| Escala | `scale_calculation` / itens | quantidade bruta/líquida escalada |
| Ordem e materiais congelados | `production_order`, `production_order_material`, `production_batch_material` | realizado; não reescritos |
| Consumo, retorno, desperdício | `project_consumption()` | líquido de retorno; desperdício separado |
| Rendimento, sobra, descarte | `project_yield()` | denominadores; sobra/descarte sem valoração automática |
| Produto técnico | `technical_product` | âncora do preço praticado, não SKU |
| Identidade e RLS | `authorization`, `panne_current_org_id()` | permissões novas; FORCE RLS |

## Dados derivados

Cálculo, componente, evidência, lacuna, invalidação, simulação, decisão e preço praticado. Hash canônico do snapshot. Composição percentual. Variações previsto/realizado e sensibilidade ±10%.

## Lacunas reconhecidas

| Lacuna | Tratamento na v1 |
|---|---|
| Sem `valid_to` no preço de compra | vigente = `observed_at <= valuation_at` |
| Sem entidade de retrabalho | premissa `rework` ou ordem substituta |
| Mão de obra, energia, terceiros, rateio | premissa/tarifa versionada, qualidade `manual_assumption` |
| Tempo de etapa incompleto | não entra no realizado |
| Câmbio | falha `moeda_incompativel` |
| Massa↔volume | rejeitado sem conversão documentada |
| Custo médio / FIFO / LIFO | fora |
| Tributo | só premissa comercial com aviso; sem apuração |
