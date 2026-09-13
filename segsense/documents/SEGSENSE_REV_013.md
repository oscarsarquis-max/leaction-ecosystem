# SEGSENSE_REV_013 — Revisão de aderência do PRM_013 e do corretivo único COR_001

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_REV_013 |
| Versão | 1.2 |
| Data | 13/09/2026 |
| Status | Corretivo único `SEGSENSE_PRM_013_COR_001` executado; **não** autoaprovado |

## Conclusões explícitas (COR_001)

1. **Cadeia multiaplicação demonstrada, não Satellite Contract.** Há três processos reais (SegSense BFF `:8088` → Spider `local-demo` `:8080` → mock `:8095`). A fatia permanece `demoSliceOnly` / `notSatelliteContract=true`. Não existe `SPIDER-SATELLITE-CONTRACT-V1`.
2. **SAT-03 continua o principal gap.** A validação de `originSnapshot` nesta fatia não substitui o contrato pleno, o preview canônico nem a governança de seguro real.
3. **Experience Satellite ≠ Provider Mock.** SegSense apresenta e projeta; o mock é aplicação irmã independente. Não é “Provider Satellite” certificado: essa categoria não existe no contrato Spider.
4. **Icatu futura** só entra como provider substituível por capability **quando houver contrato autorizado**. Esta etapa não implementa Icatu.

## Achados da auditoria independente e tratamento

| Achado | Tratamento neste corretivo |
|---|---|
| `originSnapshot` enviado e ignorado | Spider valida snapshot governado, inclui no fingerprint e na evidência `originProvenance` |
| Identidade tratada como segredo; literais versionados | Identidade pública `local-demo-segsense`; segredo em env local não versionado; comparação SHA-256; mock sem default |
| Formulário abaixo da dobra; “cotação vinculante” na escolha principal | Hero + ação acima; artigo em `<details>`; recusa só em prova técnica |

## Matriz requisito → evidência → lacuna

| Requisito | Evidência | Lacuna |
|---|---|---|
| Inventário antes do código | `SEGSENSE_MVP_001` | — |
| Satellite Contract pleno | Não implementado | REQ_002 / SAT-03 abertos |
| Contexto governado influencia a decisão | Snapshot tipado; 400 sem origem; 409 mesma chave + contexto diferente; objetivo muda a decisão com nova chave | Não é personalização de seguro real |
| Segredo ≠ identidade | Header `X-SEGSENSE-Demo-Application-Secret`; `.mvp-secrets.env` gitignored | Autenticação ainda local/demo, não produção |
| `/go` e SpiderBank não usados | Rotas `/v1/demo/segsense/**` | — |
| Cadeia real SegSense→Spider→mock | `prove-mvp-http.ps1` (COR_001) | Encoding do console Windows pode corromper acentos |
| Mock independente, bind loopback | `server.listen(..., '127.0.0.1')` | Spider/SegSense BFF ainda escutam em todas as interfaces; fatia Spider recusa remoto com 403 |
| Sem proposta Icatu / sem R$ | UI + contratos + testes | — |
| Visual 1440/768/390/320 + zoom 200% | Layout compacto + CSS | **Lacuna:** sem browser interativo nesta sessão; roteiro humano em `SEGSENSE_DEMO_RUN_001` |
| Teclado/foco ponta a ponta | Testes de formulário (checkbox + submit) | Sem evidência visual de foco nesta sessão |
| Admin 401 + home + Icatu separados | Rotas preservadas | Sem IdP |
| Migration V13 | Já aplicada; sem V14 | Volume preservado |

## Evidência HTTP real (COR_001, 13/09/2026)

Não são mocks de teste. Processos reiniciados com `.mvp-secrets.env` (valores **não** registrados). Fixtures `segsense-http-test-only` ficaram só nos testes Maven.

| Passo | Resultado |
|---|---|
| Mock health | `providerId=SEGSENSE_PROVIDER_MOCK` em `127.0.0.1:8095` |
| Sem credencial | **401** |
| Identidade sem segredo | **401** |
| Identidade `local-demo-console` | **401** |
| Segredo errado | **401** |
| Origem ausente | **400**; log `VALIDATION_ERROR` **antes** de qualquer POST ao mock |
| Caminho feliz Spider | `decisionId=spd-c05bffe9-a2ee-4852-8a54-ec68b1c7114d`, `status=PRE_PROPOSAL_READY`, `mockCalled=true`, `originProvenance.channel=SEGSENSE_PUBLIC_DEMO`, `spiderPath=VALIDATED_SYNTHETIC_CONTEXT_THEN_ILLUSTRATIVE_PROVIDER`, `mock.resultId=ill-84a31b90-9d94-4dc2-b4d8-ae358c5770b2`; HTTP real `POST http://127.0.0.1:8095/v1/illustrative-protection-items` |
| Jornada pública SegSense | `id=5bb04aa5-662f-4c52-ab5e-806fbfebbb01`, `status=PRE_PROPOSAL_AVAILABLE`, `spiderDecisionId=spd-10d2f96d-4e3f-4cd3-b943-7a5962972564`, `mockResultId=ill-28527b40-7040-48f5-8a33-6b64e6074256`, `origin=SEGSENSE_PUBLIC_DEMO` |
| `REQUEST_BINDING_QUOTE` | `REJECTED`, `mockCalled=false` (sem POST ao mock) |
| Mesma chave + mesmo payload | `sameDecision=True` (`spd-c05bffe9-…`) |
| Mesma chave + canal diferente | **409** `IDEMPOTENCY_CONFLICT` |
| Mock sem credencial | **401** |
| Scan de logs | `log-secret-scan=ok` |
| Flyway volume `:5437` | última versão **V13**; sem migration nova neste corretivo |

Bind: mock `127.0.0.1:8095`; Spider e SegSense BFF em `::` (todas as interfaces). A fatia Spider recusa origem não loopback com 403. Não foi levantada uma segunda JVM Spider **sem** `local-demo`; a rota continua anotada `@Profile("local-demo")` + `ConditionalOnBean`.

Mock fora: não derrubado nesta prova para preservar a reunião; o estado `MOCK_UNAVAILABLE` está coberto pelo teste de unidade `SegSenseDemoDecisionServiceTest`.

## SAT-01 a SAT-10

| SAT | Situação |
|---|---|
| SAT-01 | PARCIAL |
| SAT-02 | PARCIAL |
| SAT-03 | **NÃO IMPLEMENTADO** (principal gap) |
| SAT-04 | PARCIAL (demo local + contexto sintético) |
| SAT-05 | PARCIAL |
| SAT-06 | N/A |
| SAT-07 | N/A |
| SAT-08 | PARCIAL |
| SAT-09 | ATENDIDO (independência das três apps) |
| SAT-10 | ATENDIDO (sem PII nesta jornada) |

## Inventário de mudanças por aplicação (COR_001)

### segsense/

`GovernedDemoOrigin`; adapter envia snapshot + header de segredo; fail-closed se o segredo local estiver vazio; projeção com `originProvenance`/`spiderPath`; UI compacta; scripts `setup/_load/start/prove`; documentos `SEGSENSE_PRM_013_COR_001`, contratos, `DEMO_RUN`, esta revisão.

### spider/

`SegSenseDemoOriginSnapshot`; `Command` + fingerprint; 400/409; `originProvenance`; `SegSenseDemoApplicationAuth` (identidade ≠ segredo, 403 fora de loopback); YAML sem default de segredo. Sem alteração das credenciais de `/v1/canonical/**`, `/go` ou console.

### segsense-provider-mock/

Sem default de credencial; `process.exit(1)` se `SEGSENSE_MOCK_CREDENTIAL` vazia; bind `127.0.0.1`; comparação de segredo por SHA-256; `originSnapshot` **não** entra no contrato HTTP.

### Não tocado

Panne, Hub, School, QMind, Phanton. Sem commit, push, deploy ou `git init` nesta etapa.

## Addendum SPIDER-SAT-003 (13/09/2026)

O gap SAT-03 desta revisão foi encerrado na Spider. SegSense passou a EXPERIENCE SATELLITE. O mock permanece TEST DOUBLE. Conclusões 1–2 acima descrevem o estado **antes** do SAT-003; após o contrato V1:

1. Existe `SPIDER-SATELLITE-CONTRACT-V1` e `POST /v1/satellites/interactions` (sem “segsense” no path).
2. A jornada pública do MVP usa o contrato canônico; a fatia demo permanece deprecated.
3. Prova HTTP: `canonicalStatus=READY`, `sourceType=SATELLITE_GOVERNED`.
4. Icatu, ServiceNow, CAP-021 e CTX-004 não foram iniciados.
5. Lacuna visual de browser interativo permanece.

## Addendum PRM_014 (13/09/2026)

A ressalva impeditiva de apresentação (timer `sending` → `analyzing` sem evento) foi **tratada** em `SEGSENSE_PRM_014` / `SEGSENSE_REV_014`. O histórico COR_001 e o adendo SAT-003 acima permanecem. Este documento não autoaprova o PRM_014.
