# Auditoria CURSOR-018 — receitas e fichas técnicas

## Base

- Git HEAD ao iniciar o ciclo: `3d14c01145547a45ba403f55aac2450762235a38` (`main` = `origin/main`)
- CURSOR-017 versionado e preservado
- Alembic de partida: `0014_ingredient_http`

## Tabelas auditadas (0004–0005)

| Tabela | Estados / regras |
|---|---|
| `technical_product` | `development\|approved\|retired`; código único por org |
| `recipe_reference` | fonte `book\|url\|internal\|oral\|other` |
| `formulation` | identidade da receita; `development\|active\|retired` |
| `formulation_recipe_reference` | papel `inspiration\|source\|comparison`; ligação na identidade, não na versão |
| `formulation_version` | `draft\|published\|retired`; uma publicada por formulação; sem `current_version_id` |
| `formulation_item` | papel `ingredient\|preparation\|additive`; líquido + fator; bruto derivado; `is_flour_basis` explícito |
| `process_step` | sequência, instrução, duração, temperatura |
| `scale_calculation` + itens | append-only; `deterministic_scale` v1 |
| `trial` | `planned\|in_progress\|completed\|cancelled` |
| `trial_measurement` | medições do ensaio |
| `approval` | eventos `submitted\|approved\|rejected\|revoked`; publicação exige `approved` mais recente |
| nutrição técnica | prévia; não é rótulo |

## Triggers e imutabilidade

- Publicada/aposentada: filhos congelados; delete físico bloqueado
- Transição permitida: `published → retired`
- Percentual do padeiro: líquido ÷ soma dos líquidos `is_flour_basis` × 100; ausência de farinha-base é válida
- Escala e nutrição: motores existentes; Decimal; sem float

## Lacunas fechadas em 0015

- `row_version` em produto, formulação, versão e referência
- `formulation_command` (idempotência)
- permissões `recipe.*`, grants `panne_runtime`, RLS da tabela de comando

Não houve redesenho nem tabela paralela de ficha.
