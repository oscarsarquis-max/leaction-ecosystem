# SPIDER-PROMPT-021 — Operações Governadas e Reconciliation Workbench

## 1. Estado oficial e autorização de escopo

- Produto de partida: **Spider 0.20.0**.
- Commit de referência: `5b9a6bc81fc5720b48b600de385088293f6dabac` (`feat(spider): add governed capacity backpressure and resilience`).
- Estado Git observado na emissão: branch `main`, **ahead 10** de `origin/main`, sem push; alterações alheias ao Spider no monorepo devem ser preservadas.
- Baseline confirmado: **374 testes backend + 67 testes frontend**; `npm run build` verde.
- Predecessor obrigatório: **CAP-020 / SPIDER-PROMPT-020 VERIFIED**.
- Grupo: `GROUP_B_RUNTIME_OPERATIONS` — CAP-021 é o terceiro e último incremento (**3/3 somente após VERIFIED**).
- Título oficial: **Operações Governadas e Reconciliation Workbench**.
- Objetivo oficial: **Commands seguros e workbench operacional**.
- Status: `PLANNED / READY FOR IMPLEMENTATION`.
- Implementation: `NOT_STARTED`.
- Integrações: `MOCK_ONLY`.
- Boundary ativo preservado: runtime e capacidade existentes em `SIMULATED_INFRASTRUCTURE`; integrações **`MOCK_ONLY`**; produção fora de escopo.

Este prompt autoriza implementar **somente CAP-021**. Não implementar topologia/HA/DR do CAP-022, SDK/certificação do CAP-023, readiness do CAP-024, fundações corporativas do CAP-025 ou piloto real do CAP-026.

## 2. Missão

Transformar os fatos operacionais já persistidos pelo Spider em uma superfície controlada para **diagnosticar, decidir e executar intervenções seguras**, sem edição livre de estado.

O incremento deve permitir que um operador autorizado:

1. encontre casos que exigem reconciliação;
2. entenda fatos, incerteza, ownership, idade e evidências;
3. veja apenas comandos permitidos para o estado e a policy vigentes;
4. simule/previsualize impacto antes da confirmação quando aplicável;
5. execute um command idempotente, autorizado e auditável;
6. acompanhe o resultado sem confundir aceite do command com conclusão do efeito;
7. encerre ou escale o caso somente com evidência conclusiva.

O workbench não é editor de banco, console genérico de administração, motor paralelo, mecanismo de compensação inventada nem autorização para repetir efeitos desconhecidos.

## 3. Princípios e decisões obrigatórias

1. **Fatos antes de comandos**: toda ação parte de estado canônico persistido e evidência consultável.
2. **Nenhuma mutação livre**: proibir edição direta de execution, step, attempt, wait, outbox, schedule, lease, fencing, circuit ou policy.
3. **Commands tipados**: catálogo fechado, schema/version, precondições, reason code e resultado explícito; nada de script, SpEL ou payload arbitrário.
4. **Idempotência obrigatória**: retry do mesmo command não duplica efeito; conflito de mesma chave com conteúdo diferente falha fechado.
5. **Concorrência segura**: precondição/CAS e versão esperada impedem decisão sobre snapshot obsoleto.
6. **Autorização por ação e recurso**: DenyAll por default, no-enumeration e allowlist de dados.
7. **Maker-checker proporcional**: ações de maior risco exigem solicitação e aprovação separadas; o mesmo ator não acumula papéis quando a policy exigir segregação.
8. **Incerteza preservada**: `UNKNOWN` nunca vira sucesso ou falha por conveniência; repetir efeito requer prova de safety/idempotência.
9. **Engine continua soberana**: commands invocam use cases/processors canônicos; não saltam a máquina de estados nem reescrevem histórico.
10. **Ownership preservado**: CAP-019 continua dono de schedule/lease/fencing/drain; CAP-020 continua dono de admissão/capacidade.
11. **Auditabilidade integral**: solicitação, decisão authz, precondições, aprovação, execução e outcome deixam trilha correlacionada e redigida.
12. **OFF_BY_DEFAULT e MOCK_ONLY**: desligado, o baseline 0.20.0 não muda; nenhuma integração real é criada.

## 4. Modelo mínimo de domínio

Implementar contratos equivalentes, preservando a linguagem existente:

- `ReconciliationCase`: `caseId`, categoria, severidade, estado, owner, subject refs, `openedAt`, idade, fatos/evidências, policy/runbook refs e ações permitidas.
- Categorias mínimas: `UNKNOWN_EXTERNAL_EFFECT`, `CALLBACK_MISSING_OR_DIVERGENT`, `ORPHAN_SIGNAL`, `FAILED_COMPENSATION`, `INCONSISTENT_STATE`, `INCONCLUSIVE_OUTBOX`, `MISSING_EVIDENCE`, `DIVERGENT_SNAPSHOT`.
- Estados mínimos: `OPEN | TRIAGED | ACTION_PENDING | IN_PROGRESS | WAITING_EVIDENCE | RESOLVED | ESCALATED | CANCELLED`.
- `GovernedOperationRequest`: command code/version, target refs, expected version, idempotency key, reason code, operator context e parâmetros allowlisted.
- `GovernedOperationDecision`: `ALLOWED | APPROVAL_REQUIRED | REJECTED_AUTHZ | REJECTED_PRECONDITION | REJECTED_POLICY | REJECTED_CONFLICT | REJECTED_UNSAFE`.
- `GovernedOperation`: identidade estável, request digest, policy/authz decision, approval refs, estado, timestamps e correlation refs.
- Estados de operação: `REQUESTED | APPROVAL_PENDING | ACCEPTED | RUNNING | SUCCEEDED | FAILED | INCONCLUSIVE | REJECTED | CANCELLED`.
- `OperationEvidence`: facts before/after, command/result refs, eventos correlacionados e redaction metadata.

IDs, clocks e geradores devem ser injetáveis nos testes. Tokens, secrets, envelopes protegidos e payload bancário não entram no read-model nem na auditoria.

## 5. Catálogo inicial de commands seguros

O catálogo deve ser fechado, versionado e condicionado às capacidades já existentes. Cobrir, no mínimo:

- `REQUEUE_CALLBACK_DELIVERY`: somente outbox elegível e entrega idempotente prevista;
- `REQUEST_RECONCILIATION`: abre/atualiza caso para resultado inconclusivo sem repetir o efeito;
- `RUN_STATUS_RECONCILIATION`: consulta o adapter **Mock** de status e registra evidência;
- `REAPPLY_ORPHAN_SIGNAL`: somente sinal autenticado, íntegro, deduplicado e agora correlacionável;
- `RETRY_WAIT_EXPIRY` ou recuperação equivalente: somente pelo processor canônico e com fencing válido;
- `RECOVER_STALE_SCHEDULE`: usa o protocolo do CAP-019; nunca ignora lease/fencing;
- `RESET_CIRCUIT`: somente circuit do CAP-020, com reason, precondição, audit trail e policy explícita; não altera resultado de execução;
- `ASSIGN_CASE`, `ESCALATE_CASE` e `RESOLVE_CASE`: lifecycle operacional, sem mutar fatos históricos.

Cada command deve declarar elegibilidade, precondições, risk level, autorização, necessidade de aprovação, idempotency scope, processor/use case de destino, efeitos esperados, condições de parada e evidências exigidas.

Não oferecer `FORCE_SUCCESS`, `FORCE_FAILED`, edição de fencing token, alteração retroativa de attempt/outcome, bypass de capacity/authz, replay irrestrito ou compensação não publicada.

## 6. Fluxo governado

```text
case/fato persistido
  → catálogo + ações elegíveis
  → request tipado + idempotency key + expected version
  → authn/authz + policy + precondições
  → preview de impacto
  → aprovação, quando exigida
  → dispatch para use case/processor canônico
  → ACCEPTED/RUNNING
  → SUCCEEDED/FAILED/INCONCLUSIVE
  → evidência + atualização do case
```

- Revalidar autorização e precondições no momento da execução, não apenas na abertura.
- Approval expirada, revogada ou feita pelo mesmo ator quando segregação for exigida deve falhar fechado.
- `ACCEPTED` prova apenas aceite do command; não prova efeito externo nem resolução do case.
- Falha/inconclusão não deve apagar o case nem disparar loop automático ilimitado.
- Execução assíncrona deve usar o runtime 019 e passar pelo gate 020 quando aplicável.

## 7. Persistência, concorrência e auditoria

- Persistir cases, requests, approvals, attempts/outcomes e evidências usando o padrão técnico existente.
- Usar transição atômica/CAS com versão esperada; dois operadores não podem executar ações incompatíveis sobre o mesmo snapshot.
- A mesma idempotency key + mesmo digest retorna a operação existente; digest diferente produz conflito auditável.
- Retenção e paginação devem ser limitadas; auditoria é append-only do ponto de vista operacional.
- Operational Events não são fonte de verdade, mas devem refletir transições reais da operação.
- Restart deve retomar `ACCEPTED/RUNNING` com segurança ou marcar inconclusão explícita; nunca assumir sucesso.

## 8. Flags e configuração

Adotar prefixo coerente, com defaults `false`:

| Flag | Papel |
|---|---|
| `spider.governed-operations.enabled` | master do módulo |
| `spider.governed-operations.http.enabled` | APIs do Console; exige master + console HTTP |
| `spider.governed-operations.local-demo.enabled` | casos/actions determinísticos para demo |
| `spider.governed-operations.execution.enabled` | permite executar commands; sem ela, workbench é read/preview-only |
| `spider.governed-operations.approval.enabled` | habilita fluxo maker-checker quando exigido pela policy |

Policies detalhadas pertencem a catálogo versionado, não a proliferação de flags. Com master off, nenhum endpoint/coordenador/loop do 021 deve existir.

## 9. API do Console

Sob `/v1/console/operations` e somente com flags aplicáveis:

- `GET /reconciliation-cases` — lista paginada/filtrável;
- `GET /reconciliation-cases/{id}` — detalhe, fatos, evidências, runbook e ações elegíveis;
- `GET /commands` — catálogo seguro e requisitos;
- `POST /reconciliation-cases/{id}/commands/preview` — decisão e impacto sem mutação;
- `POST /reconciliation-cases/{id}/commands` — solicita/executa conforme policy;
- `GET /operations/{operationId}` — acompanha lifecycle e evidências;
- `POST /operations/{operationId}/approve` e `/reject` — somente quando maker-checker aplicável;
- `POST /reconciliation-cases/{id}/assign`, `/escalate` e `/resolve` — commands tipados de lifecycle.

Ações authz mínimas: `VIEW_RECONCILIATION_WORKBENCH`, `PREVIEW_GOVERNED_OPERATION`, `EXECUTE_GOVERNED_OPERATION`, `APPROVE_GOVERNED_OPERATION`, `ASSIGN_RECONCILIATION_CASE`, `RESOLVE_RECONCILIATION_CASE`.

Flag off, DenyAll, recurso ausente ou não autorizado devem preservar resposta externa equivalente (404/no-enumeration). Mutations exigem idempotency key e versão esperada. Nunca expor entity JPA diretamente.

## 10. Observabilidade e saúde

Emitir Operational Events tipados e métricas de baixa cardinalidade para:

- case aberto, triado, atribuído, escalado e resolvido;
- command solicitado, aprovado/rejeitado, iniciado e concluído;
- rejeições por authz, policy, precondição, conflito e safety;
- idade e quantidade de casos por categoria/estado;
- operações inconclusivas e approval aging;
- redrive/reconciliation outcomes sem identificadores de alta cardinalidade.

Adicionar dimensões de saúde apenas quando o módulo estiver ligado, por exemplo `RECONCILIATION`, `GOVERNED_OPERATIONS` e `OPERATION_APPROVALS`. Amostra ausente/stale deve resultar em `UNKNOWN`, não falso verde.

## 11. Failure Lab e jornadas reproduzíveis

Estender o laboratório apenas com cenários `GOVERNED_OPERATIONS`, todos determinísticos e `MOCK_ONLY`:

1. unknown externo → status reconciliation → evidência conclusiva;
2. callback dead-letter elegível → preview → requeue idempotente;
3. stale schedule → recovery respeitando fencing;
4. command concorrente com expected version obsoleta → conflito fail-closed;
5. operação de maior risco → maker-checker → execução/rejeição auditável;
6. ação insegura/replay sem prova → rejeição tipada e escalonamento.

Predicados devem ser tipados; ausência de fatos reais do cenário torna a verificação inconclusiva. Nenhum fault injection toca infraestrutura ou parceiro real.

## 12. Console/UI — representação visual progressiva

Criar a superfície **Operações & Reconciliação** integrada ao Console:

1. **Fila executiva**: volume, severidade, aging, ownership, approvals e boundary.
2. **Lista de casos**: filtros por categoria/estado/severidade/owner, freshness e paginação.
3. **Detalhe progressivo**: contexto redigido → timeline de fatos → evidências → runbook → ações elegíveis.
4. **Command drawer/wizard**: preview, precondições, risco, reason, expected version e confirmação explícita.
5. **Maker-checker**: solicitação e decisão visivelmente separadas, com identidade e expiração.
6. **Acompanhamento**: diferenciar `ACCEPTED`, `RUNNING`, terminal e `INCONCLUSIVE`.
7. **Rastreabilidade**: case → operation → processor/schedule → Operational Events/evidence.

Banner permanente: **DEMONSTRAÇÃO · OPERAÇÕES GOVERNADAS MOCK · INFRAESTRUTURA SIMULADA QUANDO APLICÁVEL · SEM INTEGRAÇÃO/OPERAÇÃO PRODUTIVA**.

A UI deve ser responsiva e acessível, ter loading/empty/error/stale/unauthorized/conflict/approval-pending/inconclusive, não depender apenas de cor e não hardcodar dados que pertencem às APIs.

## 13. Evidências visuais obrigatórias

Criar script reprodutível `frontend/scripts/capture-governed-operations-screenshots.mjs` e gravar em `docs/technical/screenshots`:

| Arquivo | Evidência |
|---|---|
| `021-operations-workbench-overview-desktop.png` | fila, aging, ownership e boundary |
| `021-reconciliation-case-detail-desktop.png` | fatos, evidências, runbook e ações elegíveis |
| `021-command-preview-desktop.png` | precondições, impacto, risco e confirmação |
| `021-maker-checker-desktop.png` | solicitação e aprovação segregadas |
| `021-operation-inconclusive-desktop.png` | incerteza preservada e escalonamento |
| `021-operations-workbench-mobile.png` | viewport mobile |

Capturas devem usar local-demo determinístico e conteúdo real das APIs; nenhuma fixture hardcoded no componente.

## 14. Testes e critérios de aceite

### 14.1 Backend

- lifecycle, categorias, ownership, aging e transições válidas de `ReconciliationCase`;
- catálogo/schema/version e elegibilidade de cada command;
- idempotência: replay equivalente, conflito de digest e concorrência real;
- CAS/expected version e revalidação de precondições;
- authn/authz, segregação maker-checker, expiração/revogação e 404 sem enumeração;
- dispatch somente via use case/processor canônico;
- safety para unknown, callback/outbox, signal, wait, stale schedule, circuit e capacity;
- restart/recovery de operação sem falso sucesso;
- redaction, auditoria append-only, eventos, métricas, health e retenção;
- flags/master/http/local-demo/execution/approval;
- Failure Lab e evidence bundles;
- manifesto, roadmap e contrato anti-drift.

### 14.2 Frontend

- fila, filtros, detalhe progressivo e paginação;
- preview/confirm e estados de erro/conflito/stale;
- maker-checker e acompanhamento assíncrono;
- distinção visual entre aceite, sucesso, falha e inconclusão;
- boundary persistente, acessibilidade e responsividade;
- ausência de dados hardcoded e mutations sem confirmação.

### 14.3 Regressão e prova

- `mvn test` no backend completamente verde;
- `npm test` no frontend completamente verde;
- `npm run build` no frontend verde;
- registrar contagens finais, zero failures/errors/skipped e screenshots;
- nenhum teste removido, ignorado ou enfraquecido para obter verde.

## 15. Sincronização arquitetural obrigatória

A implementação só pode ser declarada `VERIFIED` se atualizar, no mesmo incremento:

1. `SPIDER-ARCH-005`: semântica de reconciliação/reprocessamento, precondições e proibição de editar estados terminais.
2. `SPIDER-ARCH-008`: persistência, idempotência, concorrência, auditoria, retenção e recovery dos commands/cases.
3. `SPIDER-ARCH-009`: authz por ação/recurso, maker-checker, segregação de funções, redaction e no-enumeration.
4. `SPIDER-ARCH-010`: cases, runbooks, commands seguros, eventos, métricas, health e evidências.
5. `SPIDER-ARCH-011`: interação com workers/lease/fencing/capacity, sem antecipar HA/DR.
6. `SPIDER-ARCH-012`: suites de idempotência, concorrência, safety, authz, recovery e UI/E2E.
7. `SPIDER-ARCH-013`: superfície, APIs, ações authz, progressive disclosure, boundary e screenshots.
8. `SPIDER-ARCH-014` — **Espelho Funcional do Produto**: baseline pós-021, linguagem de negócio, atores, jornadas, flags, limitações e fechamento do Grupo B.
9. Este `SPIDER-PROMPT-021`: converter autorização em registro fiel do entregue, preservando decisões e limites.
10. Manifesto, contrato anti-drift e roadmap: CAP-021 `VERIFIED`, runtime efetivo coerente com o entregue, integração `MOCK_ONLY`, `currentPrompt=SPIDER-PROMPT-021`, Grupo B 3/3, produto/contagens reais; CAP-022–026 permanecem `PLANNED`.
11. README, guia de apresentação e índice de screenshots quando necessários à reprodução da demo.

Roadmap, manifesto e contrato devem permanecer idênticos em grupo, título, objetivo, status, runtime, integração e dependência.

## 16. Definition of Done

CAP-021 estará concluído somente quando:

- cases de reconciliação forem consultáveis, atribuíveis, escaláveis e resolvíveis por commands tipados;
- preview, precondições, idempotência, CAS, authz e audit trail forem provados;
- operações de maior risco respeitarem maker-checker conforme policy;
- nenhum command editar histórico, burlar Engine, fencing ou capacidade;
- `UNKNOWN` e outcomes inconclusivos forem preservados até evidência;
- flags off preservarem o baseline 0.20.0;
- boundary `MOCK_ONLY` e infraestrutura simulada quando aplicável estiverem evidentes em API, UI, docs e screenshots;
- Console/UI representar progressivamente fila, caso, decisão, execução e evidência;
- screenshots forem reprodutíveis e estiverem gravados;
- suítes backend/frontend e build estiverem verdes;
- arquitetura e Espelho Funcional estiverem sincronizados;
- Grupo B fechar 3/3 sem implementar ou iniciar CAP-022–026.

## 17. Não objetivos e boundaries invioláveis

- não conectar legado, callback HTTP, broker, IdP, KMS, mTLS, Kubernetes ou cloud real;
- não implementar HA, multi-instância, restore ou DR (CAP-022);
- não criar SDK/harness de certificação (CAP-023) nem readiness gate (CAP-024);
- não promover `CORPORATE_SANDBOX`, `REAL_PILOT` ou `PRODUCTION`;
- não oferecer SQL/JSON/state editor, `force success/fail` ou replay genérico;
- não repetir efeito `UNKNOWN` sem prova idempotente/safe;
- não inventar compensação nem alterar rota/policy publicada;
- não ignorar lease, fencing, drain, admission, circuit ou quota;
- não tornar telemetria fonte de verdade nem comando implícito;
- não implementar qualquer parte de CAP-022–026.

## 18. Referências autoritativas

- `docs/roadmap/SPIDER-ROADMAP-IMPLEMENTACAO-016-026.md`.
- `backend/src/main/resources/implementation/spider-capability-manifest.json`.
- `backend/src/main/resources/implementation/spider-roadmap-015-026-contract.json`.
- `docs/technical/SPIDER-PROMPT-019-durable-workers-scheduling.md`.
- `docs/technical/SPIDER-PROMPT-020-capacity-backpressure-resilience.md`.
- `docs/architecture/SPIDER-ARCH-003-contrato-canonico-e-modelo-de-execucao.md`.
- `docs/architecture/SPIDER-ARCH-005-definicao-de-rotas-execution-plan-e-maquina-de-estados.md`.
- `docs/architecture/SPIDER-ARCH-006-protocolo-universal-engine-adapter-e-perfis-de-integracao.md`.
- `docs/architecture/SPIDER-ARCH-008-persistencia-tecnica-idempotencia-evidencias-e-retencao.md`.
- `docs/architecture/SPIDER-ARCH-009-seguranca-identidade-autorizacao-e-protecao-de-dados.md`.
- `docs/architecture/SPIDER-ARCH-010-observabilidade-slos-operacao-e-resposta-a-falhas.md`.
- `docs/architecture/SPIDER-ARCH-011-topologia-implantacao-escalabilidade-e-alta-disponibilidade.md`.
- `docs/architecture/SPIDER-ARCH-012-estrategia-de-testes-certificacao-e-qualidade-arquitetural.md`.
- `docs/architecture/SPIDER-ARCH-013-console-operacional-e-visualizacao.md`.
- `docs/architecture/SPIDER-ARCH-014-arquitetura-funcional-do-produto.md`.
