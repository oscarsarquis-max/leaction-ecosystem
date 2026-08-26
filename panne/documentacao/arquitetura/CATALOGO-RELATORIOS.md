# Catálogo de relatórios

Versionado em `reporting_analytics/catalog.py`, versão `1`. Extensível só por código.

| Código | Nome | Permissão | Métricas |
|---|---|---|---|
| `executive` | Visão executiva | `reporting.dashboard.read` | estados, volume, rendimento, custo e preço autorizados, conformidade, cobertura |
| `production` | Planejamento e produção | `reporting.production.read` | estados, aderência, conclusão, short_closed, ocorrências |
| `consumption` | Consumo de componentes | `reporting.production.read` | líquido, variação, cobertura de preço |
| `yield_losses` | Rendimento e perdas | `reporting.production.read` | rendimento, perda, cobertura |
| `costing` | Custos de produção | `reporting.costing.read` | variação, custo por unidade vendável |
| `pricing` | Formação de preços | `reporting.pricing.read` | markup, margens 021, cobertura |
| `compliance` | Conformidade e rotulagem | `reporting.compliance.read` | cobertura da avaliação; não é certificado |
| `traceability` | Rastreabilidade e auditoria | `reporting.traceability.read` | timeline de ordem, evento, emissão |
| `data_quality` | Qualidade dos dados | `reporting.data_quality.read` | coberturas e lacunas acionáveis |

Na UI, consumo e rendimento compartilham **Componentes e perdas**; custeio e preços compartilham **Custos e preços**.
