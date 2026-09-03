# SPIDER DETERMINISTIC PLATFORM BASELINE

## Declaração

```text
BASELINE: 0.20.0
STATUS: VERIFIED
CONTEXT INTELLIGENCE: NOT_STARTED
```

Este marco congela a plataforma determinística imediatamente antes do
`SPIDER-CONTEXT-PROMPT-001`. Context Intelligence é construído sobre esta base e não substitui
Engine, contratos canônicos, wait/resume, callback, signal, Operational Events, runtime,
capacidade, segurança, console ou persistência.

## Registro da Fase 0

- HEAD inspecionado antes do fechamento: `16a29e4095a4ce8cf6d9ba37bad616167410f823`;
- commit seletivo de fechamento 020A/020B: `37437c9`;
- branch: `feat/panne-demo-026`, sem upstream configurado;
- origin: `https://github.com/oscarsarquis-max/leaction-ecosystem.git`;
- staging e commit restritos a `spider/`; alterações de projetos irmãos permaneceram fora;
- `git status -- spider` limpo após o commit;
- push não realizado.

## Estado funcional congelado

```text
Spider: 0.20.0
CAP-001–020: VERIFIED
020A: VERIFIED
020B: VERIFIED
Backend: 385 verdes
Frontend: 92 verdes
Build: verde
Lint/diagnósticos: sem erros
CAP-021: NOT_STARTED / PLANNED
Boundary: MOCK_ONLY / SIMULATED_INFRASTRUCTURE
```

As contagens foram validadas contra o workspace e reconciliadas no manifesto no commit de
fechamento. Elas são as contagens do baseline determinístico; testes adicionados pela trilha
Context Intelligence são reportados separadamente.

Verificação pós-CTX-001: 17 testes backend e 6 testes frontend específicos foram adicionados. As
suítes completas passaram com **402 backend / 98 frontend**, além do build de produção.

O refinamento visual CTX-001A preservou esse baseline histórico e acrescentou uma regressão
frontend para cards `preview-only`. A verificação atual passou com **402 backend / 99 frontend**,
build de produção verde e diagnósticos de lint sem erros.

CTX-002 adicionou a fonte probabilística `NATURAL_LANGUAGE` sem mudar a soberania do Guard, Router
ou Core. A regressão completa passou com **417 backend / 103 frontend**, build de produção e ESLint
verdes. O smoke Bedrock permanece separado e condicional a credenciais externas.

CTX-003 desacoplou Intent de Route por `ContextExecutionPlan`, Business Capability Catalog e
Capability Resolver determinísticos. Capital de giro é demonstrável como plano parcial sem
execução fictícia, e Crédito permanece executável. A verificação passou com **423 backend / 104
frontend**, build de produção e ESLint verdes; CAP-021 permanece NOT_STARTED.

CTX-003A tornou visível a cadeia Objetivo → Entendimento → Policy → Plano → Capacidades → Resolução
→ Execução → Resultado na Home, sem nova arquitetura. A verificação passou com **423 backend / 115
frontend**, build de produção e ESLint verdes; CAP-021 permanece NOT_STARTED.

## Evidências preservadas

- `docs/technical/screenshots/020A-home-operacional.png`
- `docs/technical/screenshots/020A-home-execucoes.png`
- `docs/technical/screenshots/020A-home-status.png`
- `docs/technical/screenshots/020B-live-execution-start.png`
- `docs/technical/screenshots/020B-live-execution-retry.png`
- `docs/technical/screenshots/020B-live-execution-complete.png`
- `docs/technical/screenshots/020B-step-details-overview.png`
- `docs/technical/screenshots/020B-step-details-failed-interaction.png`
- `docs/technical/screenshots/020B-step-details-retry.png`
- `docs/technical/screenshots/020B-step-details-success.png`
- `docs/technical/screenshots/020B-step-details-events.png`

As imagens válidas não foram regeneradas na Fase 0.
