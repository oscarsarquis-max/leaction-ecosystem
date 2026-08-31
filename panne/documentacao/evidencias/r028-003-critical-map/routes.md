# Mapa de rotas — R028-003

| Rota | Papel |
|------|--------|
| `/fluxo` | Mapa (visão geral por padrão) |
| `/fluxo?etapa=N` | Foco na etapa N |
| `/fluxo?modo=produto&produto=CODE` | Jornada do produto (código público) |
| `/fluxo?modo=produto&produto=CODE&origem=comprado\|produzido` | Misto com origem |
| `/demonstracao` | Guia; CTA **Começar roteiro** → `/fluxo` |
| `/entrar` | Login + link ao guia |
| Etapas 1–8 | Destinos existentes (`steps.ts`); retorno via `withFlowReturn` |

Trilha nas telas internas (`FlowTrail`) permanece; no `/fluxo` o mapa substitui a lista dominante.
