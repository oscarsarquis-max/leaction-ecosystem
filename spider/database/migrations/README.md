# Migrations

O bootstrap local usa `database/init.sql` via Docker (`docker-entrypoint-initdb.d`).

Evoluções de schema devem entrar aqui (Flyway ou Liquibase) — ainda não amarrado ao Spring Boot neste scaffold.
