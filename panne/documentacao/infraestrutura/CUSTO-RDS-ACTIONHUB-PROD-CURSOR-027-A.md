# Estimativa de custo — RDS `actionhub-prod` (CURSOR-027-A)

Região: `us-east-2`. Fonte: AWS Price List API (On-Demand, leitura em 2026-08-28).  
Sem compra de RI/Savings Plans nesta passagem.

## Comparação de classe

| | `db.t4g.micro` | `db.t4g.small` (recomendado) |
|---|---|---|
| vCPU | 2 | 2 |
| Memória | **1 GiB** | **2 GiB** |
| Arquitetura | Graviton2 (ARM) | Graviton2 (ARM) |
| On-Demand PG Single-AZ | **US$ 0,016 / h** | **US$ 0,032 / h** |
| ≈ 730 h/mês | **≈ US$ 11,70** | **≈ US$ 23,40** |
| Créditos burstable | baseline menor; esgota mais fácil sob carga | mais folga de CPU credit / burst |
| max_connections (ordem) | ~80–100 | tipicamente maior (mais RAM) |

### Recomendação

**Adotar `db.t4g.small`.**

Justificativa: a instância hospedará **dois** databases de aplicação (`panne` + `panne_demo`) com pools de conexão de APIs Fargate, migrations e FTS/`unaccent`. O `paneldx-database` em classe micro já opera com freeable memory na faixa de ~130–150 MB — folga insuficiente para colocation de Panne. Duplicar o risco em outro `micro` para plataforma Action Hub/Panne não é prudente; **+~US$ 12/mês** compra margem de memória e créditos relevantes.

Graviton/`t4g` é compatível com RDS PostgreSQL 17 na região (orderable confirmado).

## Componentes de custo (config recomendada)

| Componente | Premissa | Estimativa mensal |
|---|---|---|
| Instância `db.t4g.small` Single-AZ | 0,032 × 730 h | **≈ US$ 23,40** |
| Storage gp3 20 GiB | US$ 0,115 / GB-mês | **≈ US$ 2,30** |
| Autoscaling storage | só se crescer além de 20 GiB | 0 até US$ 0,115 × GiB extras (teto 100 → +≈ US$ 9,20 se cheio) |
| Backup automático | retenção 7d; armazenamento de backup até o tamanho provisionado tipicamente sem custo extra | **≈ US$ 0** na base; excedente ≈ US$ 0,095/GB-mês (ref. lista AWS) |
| Performance Insights 7 dias | retenção padrão gratuita | **≈ US$ 0** |
| Database Insights / PI longo | não habilitar retenção longa no gate | **US$ 0** (evitar) |
| Enhanced Monitoring | **off** | **US$ 0** |
| Secrets Manager (master gerenciado) | 1 secret | **≈ US$ 0,40** |
| Secrets app (4× migrator/runtime) | quando criados | **≈ US$ 1,60** |
| Transferência | VPC same-region AZ↔AZ pode gerar custo baixo; Internet 0 (privado) | tipicamente **&lt; US$ 1–3** em tráfego baixo |
| IOPS gp3 baseline | 3000 IOPS inclusos no gp3 mínimo | incluso |

### Total mensal estimado (fase RDS apenas)

| Cenário | Total |
|---|---|
| Instância + 20 GiB + master secret + PI 7d | **≈ US$ 26–28** |
| + 4 secrets de app Panne | **≈ US$ 28–30** |
| Pico storage 100 GiB (improvável cedo) | adicionar até ≈ US$ 9 |

## micro vs small — resumo de decisão

- Escolher **micro** só se o proprietário aceitar risco alto de pressão de memória com dois DBs e preferir economizar ~US$ 12/mês.
- Gate CURSOR-027-A recomenda **small** como configuração final.

## O que não está incluso

- Fargate / ALB / CloudFront da Panne (custos de app, não deste RDS).
- NAT Gateway (continua NAT instance existente).
- Multi-AZ (dobraria compute + storage gp3).
