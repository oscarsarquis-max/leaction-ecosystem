# Migrations

O bootstrap local usa `database/init.sql` via Docker (`docker-entrypoint-initdb.d`).

Evoluções canônicas continuam documentadas aqui.

O schema do Monitor é aplicado pelo `MonitorSchemaMigrator` quando
`spider.monitor.persistence.mode=jpa`. Fontes oficiais:

- `backend/src/main/resources/db/monitor/V*.sql`
- histórico `tb_monitor_schema_history` (versão + checksum + status)
- lock transacional PostgreSQL `pg_advisory_xact_lock(88101316)`

`init.sql` serve só ao first boot do container local. Não é mecanismo de evolução do RDS.

Flyway não entra no runtime da Spider: evitaria o classpath canônico e o interruptor
`spider.canonical.persistence.mode`. CAP-022 deve operar o migrator (ou job equivalente)
com uma única task antes do ECS, credencial de migration separada e o mesmo histórico.
