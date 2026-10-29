# Checklist — segurança e validação RDS `actionhub-prod` (CURSOR-027-A)

## A. Antes do provisionamento (gate atual)

- [x] Proprietário decidiu **não** usar `paneldx-database`
- [x] Identificador `actionhub-prod` livre e válido
- [x] DBName `actionhub_prod` válido
- [x] PostgreSQL 17.9 disponível em `us-east-2`
- [x] `db.t4g.small` + gp3 orderable
- [x] Subnets privadas 2 AZs identificadas
- [x] Plano de SG sem `0.0.0.0/0`
- [x] Custo estimado documentado
- [x] **Autorização explícita** do proprietário/Cortex para provisionar (CURSOR-027-B)

## B. Imediatamente após `create-db-instance` (CURSOR-027-B)

- [x] Status `available`
- [x] Engine/version = postgres 17.9
- [x] Classe = `db.t4g.small`
- [x] `PubliclyAccessible` = false
- [x] Storage encrypted = true
- [x] Subnet group = apenas privadas 2a/2b
- [x] SG = `actionhub-prod-rds-sg` / `sg-04269196534d71e08` (sem CIDR aberto; **0 inbound**)
- [x] Backup retention = 7
- [x] Deletion protection = true
- [x] Copy tags to snapshot = true
- [x] Performance Insights on / retention 7
- [x] Enhanced Monitoring off
- [x] Master gerenciado no Secrets Manager (ARN `rds!db-…`; valor **não** lido)
- [x] `paneldx-database` describe **inalterado**

## C. Pós-bootstrap lógico

- [ ] Databases `panne` e `panne_demo` existem
- [ ] Roles migrator/runtime criadas
- [ ] Sem CONNECT cruzado (teste negativo)
- [ ] Apps **não** usam master
- [ ] Secrets app criados; rotação definida
- [ ] Conexão TLS validada (`sslmode=require` mínimo)
- [ ] `CREATE EXTENSION unaccent` ok em cada DB app (ou na 1ª migration)
- [ ] Alembic upgrade head em `panne` e `panne_demo` separados
- [ ] Timezone app `America/Sao_Paulo` sem GUC global arriscado

## D. Segurança contínua

- [ ] Nenhum secret em Git/docs/logs
- [ ] Ingress RDS limitado a SGs Panne (+ bastion se aprovado)
- [ ] PanelDX SG **não** tem 5432 neste RDS
- [ ] Alarme CloudWatch: storage, CPU, conexões, freeable memory
- [ ] Runbook de restore/PITR (instância inteira)

## E. Rollback pronto

- [ ] Procedimento de delete com remoção de deletion protection documentado
- [ ] Confirmação de que nenhum dado de negócio impede delete
