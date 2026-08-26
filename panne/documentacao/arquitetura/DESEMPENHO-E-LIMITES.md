# Desempenho e limites

- período síncrono máximo: 90 dias
- detalhe: 50 (máx. 200)
- exportação: 2000 linhas
- snapshot: 1 MB
- orçamento: 16 consultas por painel
- timeout: o da sessão HTTP; cancelar no cliente não apaga snapshot já gravado
- índices: `(organization_id, created_at)` em `reporting_execution`
- sem fila, worker, lake, cubo ou materialized view neste ciclo
