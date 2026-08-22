# CURSOR-009 — Retorno da execução

Data: 2026-08-22. Sem commit, push, deploy ou CURSOR-010. Aguarda revisão do arquiteto.

## Incompatibilidade registrada

ADR-011, ADR-012, ADR-014, REG-001 e REG-002 **não existem em `panne/`**. Os ADR de mesmo número em `qmind/` são de outro produto e não foram usados. A implementação segue este prompt e os modelos já existentes da Panne. Nenhuma decisão arquitetural anterior foi alterada em silêncio: FTS não foi ampliado; `grounding_insufficient` permanece falha fechada; proposta de IA continua só `draft`; Guardrail continua pendente de identificador.

## 1. MySQL e FTP

Não foram abertos, consultados nem modificados. Nenhuma credencial da origem foi usada.

## 2. PostgreSQL alvo

Antes da `0008`: PostgreSQL 18.4 (`leaction_db`), banco `panne`, ambiente local/test, head `0007_ai_orchestration`.  
Depois: head `0008_compliance_governance`.

## 3. Arquivos (somente `panne/`)

Criados: migração `0008`; módulo `compliance` (`models`, `constants`, `schemas`, `engine`, `applicability`, `grounding`, `services`); `tests/test_compliance.py`; docs de modelo, catálogo, política, matriz, estados e limitações; prompt e este retorno.

Alterados: `alembic/env.py`; `tests/test_migrations.py`; `tests/helpers.py` (`establishment`); `FRONTEIRAS-FUTURAS-FORMULA.md`.

HTTP permanece `/health` e `/ready`. Sem CRUD, frontend, chat ou Bedrock neste ciclo.

## 4. Tabelas e constraints

`compliance_framework`, `compliance_framework_version`, `compliance_requirement`, `compliance_requirement_source`, `compliance_profile`, `compliance_assessment`, `compliance_finding`, `compliance_evidence`, `compliance_review`.

Checks de domínio, escopo, força, severidade, tipo declarativo, classe normativa, atividade, resultado e completude. Unique de código/sequência/versão ativa. Snapshot de perfil exige `frozen_at`. Filhos e revisões append-only. Exclusão física bloqueada. Conteúdo de versão/requisito/achado imutável; transições humanas controladas.

## 5. Tipos declarativos

`evidence_presence`, `numeric_comparison`, `boolean_condition`, `catalog_membership`, `mandatory_manual_review`, `compound` (`and`/`or` só com cláusulas-folha). Schema `extra="forbid"`. Sem `eval`. `Decimal` nas comparações. Ausência ≠ zero ≠ aprovação.

## 6. Aplicabilidade

Filtro por jurisdição, vigência, atividade, categoria, forma de venda, embalagem, processo, equipamento e chaves de contexto declaradas. Atividade não é inferida do nome da empresa. Critério presente e perfil vazio → `insufficient_context` / `insufficient_data`, nunca `not_applicable` por conveniência.

## 7. Grounding regulatório

`RegulatoryGroundingPolicy`: fonte visível, revisada, vigente, com hash e classe compatível. Papel `foundation` só para `in_force_act` oficial ou `private_standard` licenciada.

## 8. Distinção normativa

Ato vigente, ato futuro, revogado/substituído, proposta (consulta/minuta/AIR), orientação oficial, norma privada e conteúdo técnico não normativo são classes distintas. Proposta não fundamenta obrigação vigente.

## 9. Isolamento e imutabilidade

`organization_id` nas linhas; framework organizacional invisível para outra org; estabelecimento e alvo validados na mesma org. Snapshot de perfil congelado. Requisitos, fontes, achados, evidências e revisões append-only.

## 10. Revisão humana

Submissão e ativação de versão; revisão de avaliação `accepted` / `rejected` / `needs_changes` / `revoked` (novo evento). A IA não transita estados.

## 11. Migração

`0007` → `0008` → `0007` → `0008` e `0001` → `head`. Reversível. Head final `0008_compliance_governance`.

## 12. Testes e Python

129 passed, 1 skipped no venv local (3.11.15) e no container `python:3.12-slim-bookworm` (**3.12.14**). Fixtures fictícias. Sem chamada Bedrock nos testes comuns.

## 13. Regressão CURSOR-008

Os 121 testes anteriores + skip do vivo Bedrock permaneceram verdes.

## 14. `/health` e `/ready`

`200` com `status=ok`, `service=panne`. Rotas HTTP só `/health` e `/ready`.

## 15. `.env`, exemplo e Guardrail

`.env` continua no `.gitignore`. `.env.example` sem access key, secret ou session token. Guardrail ainda sem identificador — defesa adicional, não fonte de verdade. Nenhum valor de ambiente neste retorno.

## 16. Git

`git diff --stat` (rastreados pré-existentes, não tocados neste ciclo):

```
 infra/ecosystem-databases.sql     | 1 +
 leaction-ecosystem.code-workspace | 4 ++++
 2 files changed, 5 insertions(+)
```

`git status --short`: `M` nesses dois; `?? panne/`; lixo pré-existente intacto.

## 17. Riscos e pendências

- Sem RLS; obrigatório antes de APIs de negócio.
- Sem vocabulário controlado/sinônimos no FTS.
- Guardrail Bedrock sem ID.
- Sem ingestão ativada de normas reais.
- Sem rótulo, certificado ou parecer.
- Não avançar ao CURSOR-010 sem revisão.

## 18. Commit, push e deploy

Não houve commit, push nem deploy.
