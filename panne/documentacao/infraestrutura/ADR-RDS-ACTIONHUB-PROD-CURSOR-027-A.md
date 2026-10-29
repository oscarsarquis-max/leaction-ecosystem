# ADR — Novo RDS PostgreSQL `actionhub-prod` (CURSOR-027-A)

| Campo | Valor |
|---|---|
| Status | **Decidido pelo proprietário; provisionamento bloqueado no gate** |
| Data | 2026-08-28 |
| Conta / região | `253137917703` / `us-east-2` |
| Identidade de inspeção | `paneldx-user-admin` (somente leitura nesta passagem) |

## Decisão

1. Criar **nova** instância Amazon RDS PostgreSQL dedicada à plataforma Action Hub / Panne.
2. **Não** usar `paneldx-database` para Panne (Demo nem Produção).
3. **Nenhuma** alteração no RDS do PanelDX nesta iniciativa.
4. Identificador AWS da instância: `actionhub-prod`.
5. Nome lógico inicial do banco na criação (DBName): `actionhub_prod`.
6. Bancos de aplicação posteriores: `panne` e `panne_demo`.
7. Provisionamento **somente** após nova autorização explícita (gate CURSOR-027-A).

## Por que não `paneldx-database`

- Blast radius compartilhado (CPU, conexões, storage, manutenção, PITR).
- Retenção de backup atual do PanelDX é agressiva (1 dia) e a instância é Single-AZ com `PubliclyAccessible=true`.
- Isolamento de produto/segurança exige SG, roles e segredos próprios; colocation enfraquece o modelo.
- Decisão do proprietário: Panne fora do RDS PanelDX.

## Validação de nomes (AWS + PostgreSQL)

| Nome | Uso | Resultado |
|---|---|---|
| `actionhub-prod` | `DBInstanceIdentifier` | **Aceito**: 1–63 chars, letras/dígitos/hífen, começa com letra, sem hífen duplo/final. **Livre** na conta (sem conflito). |
| `actionhub_prod` | `DBName` inicial | **Aceito** como database name Postgres (1–63, `[A-Za-z0-9_]`, não reserved). Serve como DB “casca”/admin; apps **não** usam este DB. |
| `panne` / `panne_demo` | databases lógicos | Criados **após** o provisionamento, via procedimento administrativo seguro. |

## Configuração-base recomendada (gate)

| Parâmetro | Valor recomendado | Evidência |
|---|---|---|
| Engine | PostgreSQL **17.9** | `describe-db-engine-versions` → `available` em `us-east-2` (também existem 17.10/17.11; 17.9 atende o pedido) |
| Classe | **`db.t4g.small`** | Orderable com 17.9; ver comparação micro/small |
| Arquitetura | ARM **Graviton2** | Família `t4g` suportada para RDS PostgreSQL |
| Multi-AZ | **Não** (Single-AZ inicial) | Custo; evoluir depois se SLA exigir |
| Storage | **gp3** 20 GiB, autoscaling até **100** GiB | Orderable; min gp3 = 20 |
| Criptografia | habilitada (KMS default conta ou CMK) | Obrigatório |
| Público | **desabilitado** | Obrigatório |
| VPC | `vpc-017dc4cac16ba2c59` | PanelDX-vpc |
| Subnet group | **novo** privado (ver plano) | Não reutilizar `default-vpc-…` (mistura públicas) |
| SG | **novo** exclusivo (ver plano) | Sem criar nesta passagem |
| Backup | retenção **7** dias | |
| Deletion protection | **habilitada** | |
| Copy tags to snapshots | **habilitada** | |
| Master password | **Secrets Manager** (`ManageMasterUserPassword`) | Sem senha em terminal/docs/Git |
| Performance Insights | **ligado**, retenção **7 dias** (sem custo adicional típico) | Orderable SupportsPI=true |
| Enhanced Monitoring | **desligado** inicialmente | Custo CloudWatch pouco justificado no gate |
| Param group | `default.postgres17` (sem custom no gate) | Timezone **não** forçado no server |
| Logs exportáveis | `postgresql`, `upgrade` (opcional) | |

## Timezone

Aplicações Panne usam `America/Sao_Paulo` em camada de app (`OPERATIONAL_TIMEZONE` / reporting).  
**Não** alterar `timezone` global do parâmetro RDS de forma irresponsável; preferir `timestamptz` + conversão na aplicação.

## Extensão `unaccent`

Migração Alembic `0006_knowledge_grounding` executa `CREATE EXTENSION IF NOT EXISTS unaccent`.  
Em RDS PostgreSQL, `unaccent` está no catálogo de extensões suportadas; criação com usuário master (ou role com privilégio adequado) na **primeira** migration por database.

## Fora de escopo desta passagem

Criar RDS, SG, subnet group, secrets, databases, roles, migrations, deploy, commit/push.
