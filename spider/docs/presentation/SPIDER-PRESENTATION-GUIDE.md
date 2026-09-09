# SPIDER Presentation Guide

## Pré-requisitos

- JDK 21, Maven 3.9+, Node 20+
- Portas livres: `8080` (API), `5180` (UI)
- Sem acesso a legado/rede real

## Validar

```powershell
cd C:\Projetos\spider
.\scripts\validate-presentation.ps1
```

## Iniciar demo

```powershell
cd C:\Projetos\spider
.\scripts\start-presentation.ps1
```

URLs típicas:

- Experience Hub: http://127.0.0.1:5180/
- SpiderBank: http://127.0.0.1:5180/spiderbank
- Console: http://127.0.0.1:5180/console
- CampoAberto: http://127.0.0.1:8080/demo/partner/agro-hoje
- Readiness: http://127.0.0.1:8080/v1/console/presentation/readiness
- Implementation: http://127.0.0.1:8080/v1/console/implementation

Flags: profile `local-demo` + `spider.console.*` + `spider.context.*` + canonical HTTP conforme script.

CTX-002 permanece opt-in para Bedrock. No profile `local-demo` da DEMO-002 o default é
`scripted-evidence` (não é smoke Bedrock). Para Bedrock real:

```powershell
$env:SPIDER_CONTEXT_AI_ENABLED="true"
$env:SPIDER_CONTEXT_AI_PROVIDER="bedrock"
$env:SPIDER_CONTEXT_AI_SCRIPTED_ENABLED="false"
.\scripts\start-presentation.ps1
```

Esse provider é rotulado `scripted-evidence` e não representa smoke Bedrock. Para smoke real, use
provider `bedrock`, região/modelo e a cadeia padrão de credenciais AWS.

Com backend Bedrock ativo:

```powershell
.\scripts\smoke-ctx-002-bedrock.ps1
```

## Roteiro 3 minutos

1. Badge **DEMONSTRAÇÃO MOCK** no topo.
2. **Home operacional**: Spider 0.20.0, Health UP, Presentation READY, Runtime SIMULATED_INFRASTRUCTURE, Integrations MOCK_ONLY.
3. Com IA explicitamente ativa, declarar `Minha proposta 12345 foi aprovada, mas o crédito ainda não foi liberado` e selecionar **Interpretar**.
4. Mostrar o mesmo **SPIDER ENTENDEU**: texto redigido, `NATURAL_LANGUAGE`, confidence, Guard,
   Execution Plan e Business Capabilities. Destacar que nenhuma execução ocorreu.
5. Abrir o detalhe de `CREDIT_RELEASE_DIAGNOSTIC` e mostrar que route/adapter só aparecem depois da
   capability. Confirmar **Executar**.
6. Na Jornada, clicar em **IA interpretou contexto**, **Plano determinado** e na capability; mostrar
   as zonas CONTEXTO, PLANO e DATA PLANE.
7. No Data Plane, selecionar **Solicitação recebida**, **Interaction #1**, **Retry**,
   **Interaction #2** e **Execução concluída**.
8. Aba **Implementação**: CAP-015–020 VERIFIED; 021–026 PLANNED; IA default-off.
9. Aba **Apresentação**: preflight readiness; se READY, capítulo 4 → `RETRY_THEN_SUCCESS`.
10. Detalhe: o que aconteceu → por onde passou → quando → o que tecnicamente ocorreu.

## Cenários manuais CTX-002

1. `Minha proposta 12345 foi aprovada, mas o crédito ainda não foi liberado.` →
   `INVESTIGATE_CREDIT_RELEASE`, Guard aceito, rota de crédito e nenhuma execução antes de confirmar.
2. `Quero saber o que aconteceu com o cliente João.` → `AMBIGUOUS`, opções do catálogo e nenhuma rota.
3. `Minha proposta foi aprovada, mas o crédito ainda não foi liberado.` → `MISSING_CONTEXT`,
   pergunta pelo número da proposta e nenhuma rota.
4. `Quero comprar passagens para Paris.` → `UNSUPPORTED_INTENT`, nenhuma rota ou execução.
5. Reiniciar com `SPIDER_CONTEXT_AI_ENABLED=false` → badge `DESABILITADA`; os seis Business Cards
   continuam produzindo preview e Crédito continua executável após confirmação.

## Cenários manuais CTX-003

1. Informar `Preciso de R$ 50 mil para reforçar meu estoque.` e selecionar **Interpretar**.
2. Confirmar `SEEK_WORKING_CAPITAL`, `ESTOQUE`, `R$ 50.000,00` e
   `WORKING_CAPITAL_DIAGNOSTIC_V1`.
3. Verificar as sete capabilities. `IDENTIFY_CUSTOMER` está disponível pelo contexto autenticado;
   as seis restantes estão explicitamente indisponíveis.
4. Abrir uma capability e inspecionar descrição, razão, input/output, availability e route/adapter
   somente quando houver.
5. Confirmar status `PARCIALMENTE DISPONÍVEL` e ausência do botão **Executar**.
6. Repetir com reforço de caixa, matéria-prima e sazonalidade; todos convergem para o mesmo intent,
   preservando `purpose` e sem inventar `amount`.
7. Executar o card Crédito para demonstrar a Jornada `CONTEXTO → PLANO → DATA PLANE` e comprovar a
   regressão preservada.

## Cenários manuais CTX-003A

1. Informar `Preciso de R$ 50 mil para reforçar meu estoque.` e selecionar **Interpretar**.
2. Percorrer a **Jornada do objetivo**: Objetivo → Entendimento → Policy → Plano → Capacidades →
   Resolução → Execução → Resultado.
3. Confirmar `SEEK_WORKING_CAPITAL`, `INVENTORY`, `50000`, Guard `ACCEPTED` e
   `WORKING_CAPITAL_DIAGNOSTIC_V1`.
4. Distinguir `IDENTIFY_CUSTOMER` disponível (◉) das demais necessárias e indisponíveis (○); nenhuma
   está executada (✓) neste plano parcial.
5. Abrir o detalhe de uma capability e a tabela de resolução Capability → Route → Adapter → Target.
6. Ver o resultado determinístico `PLANO PARCIALMENTE DISPONÍVEL` sem fingir completude.
7. Executar o Crédito somente para evidenciar a DATA PLANE JOURNEY 020B correlacionada.

O usuário declara objetivos. A IA os compreende. O Spider os decompõe em capacidades. O ambiente
determina onde essas capacidades são executadas. A interface torna cada fase, decisão e resultado
visível e explicável.

## Roteiro 8 minutos

1. Visão geral (amostra paginada — não é SLO).
2. Lista/filtros de execuções.
3. Cockpit: flags redigidas, fronteira Mock.
4. Apresentação capítulos 1–8.
5. Jornada `WAIT_SIGNAL_RESUME` se signal HTTP Mock habilitado; senão explicar checklist.
6. Segurança: posture REDACTED, sem JWT.

## Capítulo Failure Lab (PROMPT-018)

Quando as flags `spider.failure-lab.*` estiverem ligadas no local-demo:

1. Abrir a aba **Failure Lab** — banner permanente MOCK_ONLY / falhas simuladas.
2. Mostrar o catálogo (7 cenários): retry, falha terminal, wait/resume, sinal rejeitado, callback incerto, amostra insuficiente, degradação operacional.
3. Executar um cenário (ex.: `RETRY_THEN_SUCCESS`) com confirmação explícita.
4. Acompanhar status do run → predicados → runbook provisório → evidência redigida.
5. Enfatizar: fault injection **só via mocks**; o lab **não** controla a Engine nem toca legado real.

## Capítulo Runtime de Workers (PROMPT-019)

Quando as flags `spider.worker-runtime.*` estiverem ligadas no local-demo:

1. Abrir a aba **Runtime de Workers** — banner de infraestrutura simulada / sem legado real.
2. Mostrar resumo (status, stale, leases), tabela dos 7 tipos, schedules e backlogs.
3. Demonstrar drain com confirmação explícita (quando permitido).
4. Opcional: Failure Lab cenários `WORKER_*` (crash após claim, contenção, drain, backlog, restart).
5. Enfatizar: runtime dá **posse** (lease/fencing); processors continuam com a **semântica**; OFF_BY_DEFAULT.

## Capítulo Capacidade & Resiliência (PROMPT-020)

Quando as flags `spider.capacity.*` estiverem ligadas no local-demo:

1. Abrir a superfície **Capacidade & Resiliência** — banner de infraestrutura simulada / sem capacidade produtiva aferida.
2. Mostrar modo (`MONITOR_ONLY` vs `ENFORCED`), pressão por escopo, bulkheads e circuits.
3. Drill-down de uma decisão recente → policy/version → reason code.
4. Opcional: Failure Lab cenários `CAPACITY_*` (bulkhead, backlog, circuit, quota, load shedding com fencing intacto).
5. Enfatizar: admissão **antes** do claim; sem HA multi-instância; estado de pressão em memória; OFF_BY_DEFAULT.

## Roteiro 15 minutos

1. ARCH-013 + manifesto como fonte do roadmap.
2. Diferença execution state vs implementation state.
3. Comparar endpoint legado preservado vs jornada canônica (não usar legado na demo).
4. Callback/reconciliation cenário.
5. Capítulo Failure Lab (acima).
6. Capítulo Runtime de Workers (acima).
7. Capítulo Capacidade & Resiliência (acima).
8. Troubleshooting (abaixo) e encerramento.

## Perguntas esperadas

| Pergunta | Resposta honesta |
|----------|------------------|
| É produção? | Não — MOCK_ONLY, flags off by default. |
| Tem SLO? | SLOs do Cockpit Operacional são **provisórios** (017), não contratuais. |
| Failure Lab quebra produção? | Não — só mocks; OFF_BY_DEFAULT; sem legado real. |
| Workers são cluster produtivo? | Não — SIMULATED_INFRASTRUCTURE no store; OFF_BY_DEFAULT; sem Kafka/K8s. |
| Capacidade é autoscaling real? | Não — governo simulado (bulkhead/circuit/quota); sem HA; estado em memória. |
| JWT na UI? | Não no caminho canônico. |
| Dados inventados? | Não — timeline/plan persistidos; evidência do lab é redigida. |

## Mock versus real

Integração real começa quando capabilities saírem de `MOCK_ONLY` sob governança — ainda não. Adapter real ativo falha readiness.

## Troubleshooting

- Console indisponível: `spider.console.enabled` + `http.enabled`.
- Auth negada no **console**: profile `local-demo` + `local-demo.enabled=true`.
- Auth 401 no **ingress canônico**: header `X-Spider-Credential-Ref: local-demo-console` (allowlist; não é permitAll). Sem header o DenyAll permanece.
- Readiness not-ready: habilitar canonical submit/status conforme checklist.
- Porta ocupada: liberar 8080/5180.

## Encerramento seguro

```powershell
# encerrar processos iniciados pelo start-presentation (PIDs impressos)
Stop-Process -Id <backendPid>,<frontendPid> -Force -ErrorAction SilentlyContinue
```

Não apagar bancos amplos; seed local-demo é idempotente por executionId fixo.

## SPIDER-UX-001 — Spider Experience

Superfície comercial permanente: http://127.0.0.1:5180/

Rota legada: http://127.0.0.1:5180/demo/contextual-link

A Home é a narrativa do produto, não um catálogo nem o Console. Modelo:
PRODUTO → CONCEITO → MECANISMO → CAPACIDADES → PROVA → GOVERNANÇA → ARQUITETURA.

Capítulos: proposição, problema, modelo contextual, como funciona, capacidades, integração,
experiência real (CampoAberto → `/go` → SpiderBank), governança, arquitetura, próximo passo.

**Experimentar** abre CampoAberto. `/spiderbank` permanece o satélite. `/console` permanece o
Console. `GET /go` continua em `/spiderbank?ctx=`.

SPIDER-UX-001A: a forma da interface deve expressar o funcionamento do Spider. Relações
arquiteturais importantes devem ser exploráveis visualmente sempre que isso aumentar a
compreensão. Pipeline, capacidades, integração e governança são interativos; exemplos comerciais
são marcados como exemplo, nunca como status operacional.

## DEMO-001D — página editorial realista

Rota principal da reportagem: `http://127.0.0.1:8080/demo/partner/agro-hoje`

Cópia Vite: `http://127.0.0.1:5180/partner/agro-hoje`

Roteiro: http://127.0.0.1:5180/ — **Experimentar** / **Experimentar essa jornada** abrem a reportagem CampoAberto

A demonstração contextual inicia em uma página editorial externa completa. O modelo de negócio aparece como publicidade dentro desse contexto. O parceiro fornece exclusivamente um link genérico para o Contextual Link Gateway. O Spider cria e adquire o contexto somente após o clique.

1. Abrir reportagem CampoAberto.
2. Mostrar o problema econômico da quebra de safra.
3. Mostrar a publicidade SpiderBank ao lado da matéria.
4. Provar que o link é somente `/go` (painel recolhido **Provar link genérico**).
5. Clicar **Conheça suas opções** (abre o SpiderBank em nova aba).
6. Mostrar o contexto nascendo no clique.
7. Mostrar o SpiderBank contextualizado (origem CampoAberto, título da reportagem, fingerprint no drawer).

CTA instalado: `href="http://127.0.0.1:8080/go"` — sem `intent`, `context`, `campaign`, `article`, `purpose`, `product` ou `cropFailure`.

## DEMO-001B — Banco Contextual (experiência de apresentação)

Roteiro do apresentador: http://127.0.0.1:5180/demo/contextual-link

1. CampoAberto (`http://127.0.0.1:8080/demo/partner/agro-hoje`) — reportagem externa independente; publicidade premium SpiderBank; link genérico `/go`.
2. Clique em **Conheça suas opções**.
3. Primeira dobra do SpiderBank — SPIDERBANK / Banco Contextual / “Um banco que entende primeiro”. Sem IDs na superfície.
4. História vertical: **Seu momento** → **Seu objetivo** → **Seu caminho**.
5. **Como identificamos este contexto?** abre o drawer de prova (DEMO-001). A tela principal não vira console.
6. Console (`http://127.0.0.1:5180/console`) permanece a prova técnica da plataforma.

## DEMO-002 — sexta: a demonstração começa fora do Spider

A apresentação começa em http://127.0.0.1:5180/demo/contextual-link

1. Abrir CampoAberto.
2. Ler rapidamente a reportagem sobre quebra de safra.
3. Mostrar a publicidade SpiderBank.
4. Provar que o link é genérico (`http://127.0.0.1:8080/go`, sem intent/campaign/contexto).
5. Clicar **Conheça suas opções**.
6. SpiderBank abre contextualizado.
7. Mostrar **Como identificamos este contexto?**
8. Cliente declara o objetivo (safra + compromissos + próximo plantio).
9. **Entender meu objetivo**.
10. Mostrar o que o Spider entendeu.
11. Coletar o valor (R$ 80.000) — ele não existia na reportagem nem no link.
12. Mostrar o caminho / execution plan / capabilities.
13. Abrir o Spider Console e mostrar a prova técnica.

Controle: `/spiderbank` direto + “Preciso de recursos para manter minha produção.” **não** inventa `CROP_FAILURE`.

O Contextual Link fornece contexto de origem, mas não define a intenção. O objetivo pertence ao usuário. O Context Intelligence combina contexto permitido e objetivo declarado para produzir um Intent Contract governado. A partir dessa fronteira, Policy, Execution Plan e Capability Resolution permanecem determinísticos.

SpiderBank e Spider Console são superfícies distintas. SpiderBank é a experiência contextual de
negócio; Spider Console é a superfície técnica e operacional da plataforma.

A entrada `http://127.0.0.1:5180/` abre a Spider Experience. `/spiderbank` é o banco; `/console` é o
Console operacional. `/demo/contextual-link` permanece como rota legada do Hub.

