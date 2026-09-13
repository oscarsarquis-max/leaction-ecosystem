# SEGSENSE_ADR_001 — Icatu como executor resolvido pela Spider

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_ADR_001 |
| Título | Icatu como executor resolvido pela Spider |
| Categoria | ADR — decisão arquitetural |
| Versão | 1.1 |
| Status | Aceita |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_ARQ_001 v0.3 §26; SPIDER-ARCH-017; SEGSENSE_ARQ_002 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Registro da decisão e das alternativas rejeitadas. |
| 1.1 | 04/09/2026 | Independência física: SegSense, Spider e mock futuro não compartilham código, banco, runtime nem deployment. |

## Contexto

O `SEGSENSE_ARQ_001` v0.3 descreveu modalidades de integração com a Icatu no recorte do satélite e esclareceu que SegSense, Spider e o Insurance Provider Mock futuro são aplicações fisicamente independentes. O `SPIDER-ARCH-017` estabelece que o satélite não escolhe sistema, route, adapter nem executor, e que capabilities são resolvidas e executadas pela Spider. “Satellite” é padrão de integração, não incorporação. O adendo ARQ §26 declara a precedência do SPIDER-ARCH-017. O projeto SegSense não modifica a Spider.

A Icatu é a primeira seguradora prevista no ecossistema. Sem uma decisão explícita, o código futuro poderia tratar a Icatu como integração operacional do SegSense (client HTTP, sandbox, catálogo ou callback direto).

## Decisão

A Icatu é um **executor potencial** de capabilities **resolvido pela Spider**.

Para operações pertencentes ao plano Spider, é **proibida** a integração operacional direta SegSense–Icatu. O SegSense não escolhe a Icatu, não conhece sua route ou adapter e não implementa client, mock ou contrato paralelo com a seguradora.

Qualquer redirect, sessão, API ou callback da Icatu deverá ser modelado na fronteira definida pela Spider, quando essa fronteira existir e o boundary `MOCK_ONLY` for formalmente alterado.

Funcionalidade puramente local permanece no SegSense somente quando não exigir contexto compartilhado, decisão, composição, capability empresarial, integração ou governança da plataforma.

## Alternativas rejeitadas

1. **SegSense como integrador operacional da Icatu** (ARQ §12 lido isoladamente). Reintroduz o anti-pattern do ARCH-017: o satélite escolheria sistema e adapter.
2. **Client ou mock Icatu no satélite “só para desenvolvimento”**. Inventaria contrato, payload e ambiente; violaria `MOCK_ONLY` e a proibição de integração fictícia.
3. **Dupla integração** (SegSense→Icatu e Spider→Icatu). Criaria duas verdades operacionais e uma máquina de estados paralela.

## Consequências

- `services/icatu-integration` permanece documentação de limite, sem código de integração.
- Um mock de provedor, quando existir, será aplicação independente, com ciclo de vida próprio, e não será módulo da Spider nem do SegSense.
- Produtos, jornadas e confirmações da Icatu não são modelados neste incremento.
- O manifesto preliminar não cita a Icatu.
- A revisão `SEGSENSE_REV_001` v1.2 registra que ARQ §12 × ARCH-017 deixou de ser conflito normativo aberto.
- Integração futura, se houver, exige Satellite Contract executável, resolução pela Spider e alteração formal do boundary.
