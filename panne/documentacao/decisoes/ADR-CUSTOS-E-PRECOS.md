# ADR — Custos de produção e formação de preços (CURSOR-021)

Data: 2026-08-23. Moeda inicial: BRL.

## Decisão

O custeio da Panne é um domínio versionado, append-only e reconstruível. Reutiliza preços de `ingredient_catalog`, formulações, escalas, snapshots de ordem e projeções de consumo/rendimento. Não cria segundo cadastro de ingrediente, receita, ordem, consumo ou preço de compra.

Cálculo previsto, padrão e realizado são memórias distintas. Preço sugerido é simulação. Preço praticado é decisão humana com vigência e canal. IA não calcula, não aprova e não publica.

## Reconciliação

| Módulo existente | Reúso | Não duplicar |
|---|---|---|
| `supplier` / `supplier_item` / `supplier_item_price` | preço vigente e embalagem | segundo histórico de compra |
| `formulation_version` / `formulation_item` | receita e fator de correção | cópia de ficha |
| `scale_calculation` | quantidades escaladas | segundo motor de escala |
| `production_order` / materiais | snapshot planejado | reescrita da ordem |
| `project_consumption` / `project_yield` | fatos de execução | ledger paralelo |
| `technical_product` | âncora do preço praticado | SKU comercial |

## Consequências

- Ausência de preço ou rendimento nunca vira zero.
- Política publicada é imutável; alteração cria versão nova.
- Invalidação cria evento; recálculo cria nova memória.
- Markup, margem bruta e margem de contribuição permanecem fórmulas distintas no backend.
