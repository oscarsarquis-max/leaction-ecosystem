# SPIDER CONTEXTUAL LINK

Um Spider Contextual Link permite que um canal externo origine uma jornada contextual
fornecendo somente um link genérico. O contexto é criado após o clique a partir dos sinais
efetivamente disponíveis, sem exigir que o parceiro construa Intent Contracts, Execution Plans
ou integrações com o Spider.

## Posição

```text
PÁGINA EXTERNA
      ↓
LINK GENÉRICO   (/go — sem intent, campanha, produto ou contextId)
      ↓
CLIQUE
      ↓
CONTEXTUAL LINK GATEWAY
      ↓
CLICK CONTEXT
      ↓
ORIGEM (Referer, best effort)
      ↓
PAGE CONTEXT (allowlist + fingerprint local)
      ↓
SPIDERBANK   (/spiderbank?ctx=<opaco>)
```

DEMO-001 para o canal iniciador. A compreensão (CTX-004 como incremento dedicado), Intent, plano e
Data Plane da sexta-feira continuam no roteiro DEMO-002 já existente; este incremento (DEMO-001D)
completa somente a página editorial e a prova do link genérico.

A demonstração contextual inicia em uma página editorial externa completa. O modelo de negócio
aparece como publicidade dentro desse contexto. O parceiro fornece exclusivamente um link genérico
para o Contextual Link Gateway. O Spider cria e adquire o contexto somente após o clique.

## Experiência do satélite de referência (DEMO-001B)

O SpiderBank é a aplicação satélite de referência utilizada para demonstrar a experiência de um
Banco Contextual. A primeira impressão é editorial: SPIDERBANK, Banco Contextual, “um banco que
entende primeiro”. A jornada visível é Contexto → Objetivo → Caminho. A arquitetura e as decisões
técnicas permanecem observáveis no Spider Console e no drawer de prova.

Princípio visual da demonstração:

- SpiderBank: off-white + vinho institucional (`#7C2748`) + espectro rosé; composição editorial, não
  dashboard;
- Spider Console: identidade técnica própria.

O Contextual Link fornece contexto de origem, mas não define a intenção. O objetivo pertence ao
usuário. O Context Intelligence combina contexto permitido e objetivo declarado para produzir um
Intent Contract governado. A partir dessa fronteira, Policy, Execution Plan e Capability Resolution
permanecem determinísticos.

DEMO-002 liga o CTA **Entender meu objetivo** a essa cadeia. A demonstração **começa fora do Spider**,
na página editorial CampoAberto. O parceiro instala somente `http://127.0.0.1:8080/go`. `CROP_FAILURE`
não viaja no link: nasce do PageContext da reportagem e/ou da declaração do cliente, com provenance
visível (`PAGE_CONTEXT` / `USER_OBJECTIVE`). A entrada direta `/spiderbank` permanece o controle:
PageContext ausente, `DIRECT_ENTRY`, e um objetivo só de continuidade da produção **não** inventa
quebra de safra.

```text
PÁGINA EDITORIAL EXTERNA (CampoAberto)
      ↓
REPORTAGEM SOBRE QUEBRA DE SAFRA
      ↓
PUBLICIDADE SPIDERBANK (CTA genérico /go)
      ↓
CLIQUE → clickId → Referer → PageContext → fingerprint → contextId → 302
      ↓
SPIDERBANK
      ↓
OBJETIVO DO CLIENTE
      ↓
CONTEXT INTELLIGENCE → INTENT → POLICY → EXECUTION PLAN → CAPABILITIES
```

## Contratos

- `ClickContext`: clickId, createdAt, sourceType, referrer, referrerOrigin,
  contextAcquisitionStatus, contextId. Sem Intent.
- `PageContext`: contextId, clickId, sourceUrl, sourceTitle, sourceOrigin, contentFingerprint,
  acquisitionTimestamp, acquisitionStatus, safeExtractedText.
- Referer: `FULL_REFERRER_AVAILABLE` | `ORIGIN_ONLY` | `REFERRER_UNAVAILABLE`.
- Correlação: clickId → contextId → decisionId → planId. `executionId` permanece nulo no capital de
  giro desta demo (plano parcialmente disponível, sem Data Plane).

## Segurança da aquisição

Fetch contextual não é SSRF genérico. Allowlist de origens e prefixos de path; bloqueio de
`file://`, metadata, redes privadas não autorizadas e redirect para origem fora da lista. O
HTML é dado não confiável: scripts não executam.

## Superfícies DEMO

| URL | Papel |
|---|---|
| `http://127.0.0.1:5180/` | **Spider Experience Hub** — superfície comercial da plataforma |
| `http://127.0.0.1:5180/demo/contextual-link` | Rota legada do Experience Hub |
| `http://127.0.0.1:8080/demo/partner/agro-hoje` | Portal editorial CampoAberto (a página que o gateway adquire) |
| `http://127.0.0.1:5180/partner/agro-hoje` | Cópia estática no origin do Vite |
| `http://127.0.0.1:8080/go` | Gateway — único href do CTA; redireciona para `/spiderbank?ctx=` |
| `http://127.0.0.1:5180/spiderbank` | Satélite SpiderBank (`?ctx=` opaco quando houver clique) |
| `http://127.0.0.1:5180/console` | Spider Console / Home operacional |

O Experience Hub (`/`) é a Spider Experience: narrativa comercial do produto.
Modelo: PRODUTO → CONCEITO → MECANISMO → CAPACIDADES → PROVA → GOVERNANÇA → ARQUITETURA.
Não cria contexto, Intent nem execução. `GET /go` nunca redireciona para `/`.

SpiderBank e Spider Console são superfícies distintas. SpiderBank é a experiência contextual de
negócio; Spider Console é a superfície técnica e operacional da plataforma.

Boundary: `SIMULATED_INFRASTRUCTURE` / `MOCK_ONLY`. Produção fora de escopo.
