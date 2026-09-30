# ACTIONFINANCE_REV_001 — Parecer do analista

Objeto: PRM_001 e ARQ_001 v0.2. Data: 25/09/2026.

**Resultado: APROVADO COM RESSALVAS, no âmbito da revisão técnica/documental do analista.** Aprovação do proprietário não é presumida. Não há aprovação de runtime, piloto ou integração.

## Evidências verificadas

- Projeto contém 22 arquivos, todos Markdown. Não foram encontrados runtime, migration, Compose ou manifesto no inventário realizado.
- ARQ, DOM, DAT, INT, UX, dez ADRs, índice, evidências, lacunas e revisão estão presentes.
- Java 21 obrigatório, independência do produto, PostgreSQL próprio, Panne/estoque, Hub/assinaturas e Spider/governança estão preservados.
- Documentos corretamente mantêm limitações de contratos e ADRs PROPOSED.
- ARQ foi reorganizado e distribuiu detalhes em documentos associados. Isso é aceitável, desde que a alteração editorial seja rastreada; não é cópia literal da baseline entregue.
- O HEAD observado permanece `7177805b`. Não houve diferenças rastreadas mostradas pelo diff consultado de Spider/Panne/Hub. Existem arquivos não rastreados nesses projetos; sem inventário anterior completo, não é possível atribuir sua autoria nem provar ausência absoluta de alterações por um executor.

## Ressalvas e fechamento

| Item | Achado | Correção pelo Cursor antes de implementar a fundação |
|---|---|---|
| R1 | `documents/prompts/ACTIONFINANCE_PRM_001.md` contém síntese da execução, não a cópia integral exigida | Preservar síntese como histórico, restaurar o prompt recebido em arquivo identificado e vincular ambos no índice |
| R2 | O mesmo documento declara edição de `.cursor/rules/ecosystem-focus.mdc`, fora do escopo exclusivo ActionFinance do prompt recebido | Registrar exceção e evidência disponível; não afirmar que só ActionFinance mudou. Não reverter automaticamente regra global que pode ter outra autoria |
| R3 | ADR-001/003 ampliam isolamento para proibição genérica de cluster compartilhado | Fixar container/volume dedicado no local; requisitos permanentes são banco, schema, usuário e acesso isolados. Topologia física futura exige decisão própria; mesmo cluster não equivale a mesmas tabelas |
| R4 | Matriz INT ainda não apresenta todos os requisitos, gaps, projeto responsável e gate em uma única tabela | Consolidar autenticação, empresa, contrato, idempotência, retorno, deduplicação, correlação, observabilidade, persistência e dados proibidos; sem inventar implementação |
| R5 | Aprovação documental e autorização de desenvolvimento precisam permanecer distinguíveis | Registrar este parecer como parecer do analista; manter aprovação do proprietário separada. Entrega explícita do PRM_002 ao Cursor para execução autoriza somente seu escopo |

R1–R4 são acertos documentais e podem ser concluídos na abertura do PRM_002, sem um ciclo adicional de implementação. O Cursor deve mostrar seu fechamento no relatório.

## Decisões técnicas para o PRM_002

Fundação local independente: Java 21, Spring Boot 3.4.2 como baseline observada, Spring MVC, PostgreSQL/Flyway, frontend React/TypeScript mínimo e segurança deny-by-default. Não copiar POM Boot 4. Compatibilidade de banco/driver/Flyway e dependências será demonstrada, não inferida de um README.

O PRM_002 não cria contas a pagar, idempotência financeira, saldo, integração Spider ou telas de gestão. Identidade demo técnica permite testar autenticação e contexto empresarial; não será apresentada como login corporativo. A UX operacional permanece para prompt próprio.

Não foram executados testes de runtime nesta revisão, pois a entrega é documental. Este parecer foi produzido fora do monorepo; o Cursor deverá incorporá-lo de forma rastreável quando receber o próximo prompt.
