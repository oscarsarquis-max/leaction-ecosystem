# ADR — Relatórios e painéis

Relatórios são projeções e snapshots sobre fatos canônicos. Não há cadastro operacional paralelo, SQL livre, fila, warehouse ou IA numérica.

## Decisão

- Catálogo e fórmulas ficam em código versionado (`catalog.py`, `metrics.py`).
- Persistência `0019_reporting_analytics` guarda visão salva, preferência, execução, snapshot, item de cobertura, exportação e comando.
- Snapshots são append-only e não recalculam. Atualizar o painel executa nova consulta.
- Moeda v1: BRL. Intervalo canônico: `[início, fim)` no fuso da organização.
- Ausência ≠ zero. Percentual sem denominador fica indisponível, nunca `0%`.
- Padeiro não recebe visão executiva, custos nem preços.

## Consequências

Consultas leem tabelas canônicas já existentes. Índices novos só em `reporting_execution (organization_id, created_at)`. Sem materialized view neste ciclo.
