# AF-ADR-002 — Monólito modular Java 21 + frontend React/TypeScript

## Controle

| Campo | Valor |
|---|---|
| Identificador | AF-ADR-002 |
| Versão | 0.1 |
| Status | PROPOSED |
| Data | 25/09/2026 |
| Dependências | ACTIONFINANCE_ARQ_001 §1.8 e §4 |

Decisão de negócio correlata (CONFIRMED_BY_OWNER): backend/BFF/regras em Java na versão da Spider (21).

## Contexto

SegSense e SpiderBank usam Java 21, mas Spring Boot 4.1.1. A Spider usa Java 21 e Spring Boot 3.4.2 com WebFlux. O domínio financeiro precisa de transação local e um processo implantável simples.

## Decisão

- Backend: **monólito modular Java 21**, pacote `br.com.actionfinance`. BFF e API de domínio no mesmo processo inicial.
- UI: React/TypeScript separada, no padrão dos satélites.
- Spring Boot proposto na linha da Spider (3.4.2 observada), revalidado na fundação.
- Não criar backend Node.js ou Python. Não copiar POM do SegSense nem do SpiderBank. Não atualizar a Spider.

Separação em microserviços só com evidência e ADR futuro.

## Alternativas rejeitadas

1. Dois serviços só para separar BFF e domínio.
2. Stack Python/Node no backend.
3. Copiar POM Boot 4 “porque o satélite vizinho usa”.

## Consequências

- Starters devem corresponder à major escolhida (`spring-boot-starter-web` em 3.4.x, não o nome `webmvc` do Boot 4).
- Domain sem Spring, HTTP, JPA ou classes Spider.
