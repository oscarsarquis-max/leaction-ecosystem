# CURSOR-009 — Implementar governança regulatória e núcleo de conformidade

## Estado

- Estado: aprovado para execução
- Executor: Cursor
- Dependência: CURSOR-008 aceito
- Próximo prompt: bloqueado até retorno e revisão

## Objetivo

Implementar no backend e no PostgreSQL da Panne a fundação versionada para governança regulatória e avaliações determinísticas de conformidade do setor de produção de alimentos.

Este ciclo não produzirá rótulo final, parecer jurídico, certificado, selo ou declaração automática de conformidade.

## Regras absolutas de escopo

1. Trabalhe somente dentro da aplicação `panne`.
2. Não acesse o FTP nem o MySQL legado.
3. Operações mutáveis só no PostgreSQL local da Panne e em `panne/`.
4. Não faça commit, push ou deploy.
5. Não implemente frontend, chat ou CRUD HTTP. `/health` e `/ready` estáveis.
6. Claude não publica regra, não aprova avaliação e não declara conformidade.
7. Sem `eval`, código Python no banco ou expressão executável.

## Proteção do ciclo anterior

Head inicial `0007_ai_orchestration`. `.env` ignorado. `.env.example` sem credenciais AWS estáticas. `grounding_insufficient` permanece falha fechada. Proposta de IA materializa só `draft`. Guardrail Bedrock é defesa adicional pendente de identificador. Sem ampliar FTS; vocabulário controlado é backlog.

## Migração e modelo

`0008_compliance_governance`: framework e versão, requisitos e fontes, perfil e snapshot, avaliação, achados, evidências e revisão humana. Motor declarativo fechado. Política `RegulatoryGroundingPolicy`. Sem seed jurídico real. Sem RLS parcial. Sem CURSOR-010.
