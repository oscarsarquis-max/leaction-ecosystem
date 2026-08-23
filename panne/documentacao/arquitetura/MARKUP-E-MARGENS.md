# Markup e margens

Autoridade: backend (`costing_pricing.formulas`). Decimal, `ROUND_HALF_UP`.

## Markup

- fator: `preço = custo_base × fator`
- percentual: `(preço / custo_base - 1) × 100`

## Margem bruta alvo

`preço = custo_base / (1 - margem)`. Margem ≥ 0 e < 100%.

## Margem de contribuição alvo

`preço = base_recuperável / (1 - taxa_despesas_variáveis - margem_alvo)`. Denominador ≤ 0 é recusado.

## Reversa

Dado um preço, calcula markup, margem bruta, margem de contribuição e ponto de equilíbrio unitário quando houver fixo e contribuição positiva.

Simulação parcial exibe advertência e exige confirmação reforçada para publicar.
