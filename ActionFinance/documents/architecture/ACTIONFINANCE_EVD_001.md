# ACTIONFINANCE_EVD_001 — Evidências revalidadas e matriz de estado

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_EVD_001 |
| Versão | 0.1 |
| Data | 25/09/2026 |
| Método | Leitura estática; nenhum serviço iniciado; nenhuma chamada financeira |
| Destino ActionFinance antes de escrever | vazio (0 arquivos) |

## 1. Versões observadas

| Artefato | Achado | Uso permitido |
|---|---|---|
| Spider `java.version` | `21` (`pom.xml` propriedade L21) | Baseline obrigatória do ActionFinance |
| Spider parent | Spring Boot `3.4.2` (`pom.xml` L10) | Proposta inicial de alinhamento; revalidar na fundação |
| Spider HTTP | `spring-boot-starter-webflux` | Não implica WebFlux no ActionFinance |
| SegSense parent | Spring Boot `4.1.1` | Referência de pastas/Flyway; **não copiar POM** |
| SegSense HTTP | `spring-boot-starter-webmvc` (Boot 4) | Nome de starter da major 4; na 3.4.x o equivalente é `spring-boot-starter-web` |
| SpiderBank parent | Spring Boot `4.1.1` | Evidência adicional; mesma proibição de copiar POM |
| SegSense PostgreSQL Compose | `postgres:18.6`, DB `segsense`, porta default `5437` | Convenção de isolamento; porta ActionFinance **não reservada** |
| SegSense Flyway | `database/migrations` → Maven `db/migration`; `ddl-auto=none` | Única fonte de migrations |
| SegSense frontend | React `19.2.8`, TypeScript `5.9.3`, Vite | Referência de stack UI, não de identidade visual |
| SegSense manifesto | `DRAFT / NOT_CERTIFIED`, `acceptedBySpider: false` | Mesmo recato no manifesto futuro do ActionFinance |

## 2. Contrato Satellite (código vigente)

| Afirmação do ARQ_001 | Evidência | Estado |
|---|---|---|
| `POST /v1/satellites/interactions` | `SatelliteInteractionHttpController` path `/v1/satellites/interactions`; OpenApiConfig cita o mesmo | Implementado na Spider (DEMO ONLY) |
| Schemas 1.0, 1.1 e 1.2 | Três `satellite-interaction-request.schema.json` sob `contracts/satellite/` | Presentes |
| Finalidade 1.2 só seguros/crédito | `purpose` enum: `INSURANCE_PROTECTION_ASSESSMENT`, `WORKING_CAPITAL_ASSESSMENT` | Bloqueia finalidade financeira genérica |
| Canal de resposta só SYNC | `responseChannel` enum: `["SYNC"]` | Bloqueia retorno assíncrono no contrato atual |
| EXPERIENCE não executa capability | `SatelliteInteractionService`: 403 se `EXECUTE_CAPABILITY` ou `CAPABILITY_RESULT` — “Experience Satellite não executa capability.” | Implementado |
| Idempotência em memória | `SatelliteIdempotencyStore` usa `ConcurrentHashMap` | Sem persistência; não garante restart |
| Papéis V1 | SAT-003: EXPERIENCE e PROVIDER; papéis futuros não implementados | Confirmado no documento vigente |
| ARCH-017 | Ideal vigente; boundary `MOCK_ONLY / SIMULATED_INFRASTRUCTURE`; SAT-003 IMPLEMENTADO / DEMO ONLY | Não copiar prontidão histórica |

## 3. Matriz implementado / proposto / bloqueado

| Tema | Na referência (hoje) | Proposto no ActionFinance | Bloqueado |
|---|---|---|---|
| Java 21 | Spider, SegSense, SpiderBank | Obrigatório | Trocar de linguagem |
| Spring Boot | Spider 3.4.2; satélites 4.1.1 | Alinhar à Spider 3.4.2 e revalidar | Copiar POM SegSense/SpiderBank; atualizar a Spider |
| PostgreSQL + Flyway | SegSense | Banco/schema/usuário `actionfinance` | H2; DDL automático; banco compartilhado |
| Persistência na 1ª entrega | SpiderBank: **ausente** | Obrigatória (não repetir SAT-003 financeiro em memória) | Idempotência só em RAM no domínio financeiro |
| EXPERIENCE local | SegSense: local sem Spider | CRUD de obrigações independente da Spider | Transformar CRUD em capability |
| Contrato financeiro | Inexistente | Evolução futura (PRM_005) | Metadata/campos de seguro/crédito como atalho |
| ActionHub | Recebimento de assinaturas | Fonte de resultado de subscrição, via Spider | Executor financeiro geral; cobrança avulsa nova no Hub |
| Panne | Estoque físico | Referência operacional futura | Replicar lote/validade/movimento |
| CAP-021 | Fora de escopo ARCH-017 | — | Iniciar workbench ou chamar conciliação AF de reconciliação Spider |
| UI | SegSense/SpiderBank editoriais | Ferramenta operacional | Copiar homepage ou Monitor |
| Runtime ActionFinance | Inexistente | Fundação no PRM_002 após revisão | Criar neste PRM_001 |

## 4. Divergência Hub (somente registro)

O ARQ_001 registra código de cobrança avulsa no working tree do Hub como divergência legada. Este snapshot **não** remove, move nem reaproveita esse código. Tratamento exige prompt próprio no Hub, fora deste ciclo.

## 5. O que este snapshot não prova

- Disponibilidade de pacotes Maven/npm na rede.
- Compatibilidade Boot 3.4.2 × dependências futuras.
- Aceite da Spider a um satélite `actionfinance`.
- Portas locais livres.
- Existência de APIs Panne de compra/custo utilizáveis.
