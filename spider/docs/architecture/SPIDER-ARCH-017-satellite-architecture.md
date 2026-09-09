# SPIDER-ARCH-017 — Satellite Architecture

| Campo | Valor |
|---|---|
| Identificador | SPIDER-ARCH-017 |
| Título | Satellite Architecture |
| Natureza | Ideal arquitetural + registro do canal iniciador ultraleve |
| Boundary ativo | MOCK_ONLY / SIMULATED_INFRASTRUCTURE |
| Estado | Ideal **não implementado**. DEMO-001 registra o Contextual Link. DEMO-002 usa o satélite de referência SpiderBank sobre Context Intelligence existente, sem Satellite Contract. |

## 1. Ideal (não alterar)

Um **Satellite** é um produto/canal que conversa com o Spider por contrato próprio: identidade do
canal, Intent Contract ou equivalente governado, correlação estável, e — quando autorizado —
execução no Data Plane. O Satellite Contract completo inclui, no mínimo:

- autenticação e autorização do canal;
- publicação governada de capacidades que o satélite pode solicitar;
- contratos de entrada/saída versionados;
- correlação `decisionId` → `planId` → `executionId`;
- política de erro e idempotência;
- observabilidade sem vazar payload de negócio.

Esse ideal permanece o norte. **Não está implementado neste incremento.** CAP-021, CTX-004,
crédito rural, Response Composer e integração corporativa continuam fora de escopo.

## 2. O que DEMO-001 não é

O SpiderBank desta demo é um **satélite de referência visual**. A página CampoAberto é uma
**página editorial externa simulada**. Nenhum dos dois realiza Satellite Contract.

O SpiderBank é a aplicação satélite de referência utilizada para demonstrar a experiência de um
Banco Contextual. A experiência do cliente (DEMO-001B/001C) é editorial e bancária: primeira dobra
com wordmark SPIDERBANK / Banco Contextual, hero “um banco que entende primeiro”, e a história
vertical Contexto → Objetivo → Caminho. A prova técnica permanece recolhida. A identidade visual do
SpiderBank (off-white + vinho `#7C2748` + rosé) não se unifica com a do Console nem com a do
Experience Hub.

SpiderBank e Spider Console são superfícies distintas. O Experience Hub (`/`) é a **Spider
Experience**: a narrativa comercial do produto. O modelo de experiência é PRODUTO → CONCEITO →
MECANISMO → CAPACIDADES → PROVA → GOVERNANÇA → ARQUITETURA. A forma da interface deve expressar
o funcionamento do Spider; relações arquiteturais importantes são exploráveis visualmente.
`/spiderbank` abre o satélite de
domínio; `/console` abre a prova técnica. `GET /go` continua redirecionando para
`/spiderbank?ctx=`.

Confundir um `href="/go"` com um satélite completo seria um erro de arquitetura.

## 3. Canal iniciador ultraleve

O Contextual Link é um **canal iniciador ultraleve**. Ele permite que um parceiro origine uma
jornada contextual fornecendo somente um link genérico. Não exige que o parceiro construa Intent
Contracts, Execution Plans ou integrações com o Spider.

Ver `docs/architecture/SPIDER-CONTEXTUAL-LINK.md`.

## 4. Fronteira

```text
SATELLITE CONTRACT (ideal, não implementado)
        ≠
CONTEXTUAL LINK (DEMO-001, implementado)
        +
SPIDERBANK + CONTEXT INTELLIGENCE (DEMO-002, implementado; sem Satellite Contract)
        ≠
SPIDER CORE / DATA PLANE
```

Produção bancária permanece fora de escopo.
