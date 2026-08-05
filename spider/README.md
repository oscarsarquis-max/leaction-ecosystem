# Spider — Orquestrador de Contexto

Motor de orquestração entre canais/produtos e sistemas legados internos.

## Stack

- **Backend:** Java 21 · Spring Boot 3.4 · **WebFlux** · JPA (`tb_product_routes`, `tb_audit_trace`) · WebClient · Resilience4j · jjwt · OpenAPI
- **Frontend:** React · Vite (`:5180`) — não usar `:5175` (Phanton)
- **DB técnico:** PostgreSQL 16 (Docker) — rotas, idempotência, audit/trace
- **Mocks:** cadastro `:8091` · crédito `:8092`

## Subir banco

```powershell
cd C:\Projetos\spider
docker compose up -d
```

- Host: `localhost:5432`
- DB / user / pass: `spider_orchestrator` / `spider_user` / `spider_password`
- Schema: `spider.*` (via `database/init.sql`)

## Compilar a base (backend)

Pré-requisitos: JDK 21 + Maven 3.9+.

```powershell
cd C:\Projetos\spider
.\scripts\compile-base.ps1
# ou:
cd backend
mvn -DskipTests package
```

## Rodar a stack local

```powershell
# terminais separados
cd services\mock-sistema-cadastro; npm install; npm start
cd services\mock-sistema-credito;  npm install; npm start
cd backend;  mvn spring-boot:run
cd frontend; npm install; npm run dev
```

| Serviço | URL |
|---------|-----|
| Painel | http://127.0.0.1:5180 |
| API / Swagger | http://127.0.0.1:8080/swagger-ui.html |
| Health | http://127.0.0.1:8080/actuator/health |

## Estrutura

```
spider/
├── .cursorrules
├── docker-compose.yml
├── database/init.sql
├── database/migrations/
├── scripts/
├── services/mock-sistema-*
├── backend/   # br.com.banco.spider
└── frontend/
```

Diretrizes para a IA: ver `.cursorrules`.
