# AF-ADR-003 — PostgreSQL próprio + Flyway

## Controle

| Campo | Valor |
|---|---|
| Identificador | AF-ADR-003 |
| Versão | 0.2 |
| Status | PROPOSED |
| Data | 25/09/2026 |
| Dependências | ACTIONFINANCE_ARQ_001 §7 |

## Contexto

SpiderBank documenta, na primeira entrega SAT-003, ausência de banco e idempotência do BFF em memória. O domínio financeiro não pode herdar essa limitação.

SegSense demonstra o padrão desejado: banco lógico próprio, schema próprio, Flyway canônico em `database/migrations`, Hibernate sem DDL automático.

## Decisão

- Banco lógico `actionfinance`, schema `actionfinance`, usuário runtime exclusivo.
- Fundação local: volume persistente dedicado (container próprio se Compose existir). Isolamento permanente não exige, por este ADR, proibir qualquer cluster hospedeiro futuro.
- Mesmo cluster hospedeiro, se um dia for considerado, ainda assim sem tabelas, usuários privilegiados ou credenciais compartilhadas.
- Única origem Flyway em `database/migrations`. Migration aplicada e compartilhada é imutável.
- Testcontainers para invariantes PostgreSQL. Sem H2 ou memória para provar dinheiro, idempotência ou isolamento.
- Inbox/outbox só na primeira integração efetiva, não como tabelas vazias de fachada.

## Alternativas rejeitadas

1. Primeira fatia só em memória “como o SpiderBank”.
2. Tabelas do ActionFinance no schema de outro produto.
3. `ddl-auto=update`.

## Consequências

- Backup/restore e teste de recuperação entram na fundação documental operacional; rotina normal de parada não remove volumes.
- Portas e nomes de container ficam para o inventário do PRM_002.
