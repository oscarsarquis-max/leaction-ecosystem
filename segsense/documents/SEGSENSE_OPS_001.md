# SEGSENSE_OPS_001 — Recorte operacional da demonstração sintética

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_OPS_001 |
| Versão | 1.6 |
| Data | 14/09/2026 |
| Superfície | `/demonstracao/mvp-integrado` — contexto, intenção livre, perguntas e cotação simulada; prova técnica em `details` |

## Recorte desta etapa

O plano `SEGSENSE_PLN_001` inclui o PRM_020: captura server-side de URL pública, revisão humana e possibilidades só de capability registrada. **Jornada governada/residencial permanece 1.0/1.1.** URL extraída usa Satellite **1.2**. Não há cotação Icatu. Quebra de safra não usa o simulador residencial.

Cadeia real, inalterada em direção:

```text
Browser → POST /api/v1/public/demo/context-sources/resolve (opcional, só registro local)
       → POST /api/v1/public/demo/protection-journeys (SegSense)
       → POST /v1/satellites/interactions (Spider, EXPERIENCE)
       → POST /v1/provider/capabilities/{id}/executions (mock)  [só se READY]
       → resposta canônica → projeção persistida → UI
```

SegSense **não** chama o mock. Resolve de URL **não** faz HTTP para a URL informada. O painel **não** lê logs no browser. Provider 1.0 permanece para possibilidades ilustrativas; 1.1 só para a cotação sintética.

## Observabilidade na Spider (operador autorizado)

Não há tela de auditoria pública. Para operador com acesso ao runtime `local-demo`:

| Sinal | Onde |
|---|---|
| Pedido recebido / satélite autenticado / decisão criada | Eventos operacionais `SATELLITE_REQUEST_RECEIVED`, `SATELLITE_AUTHENTICATED`, `SATELLITE_DECISION_CREATED` (`OperationalEventType`) |
| Idempotência da interação | `SatelliteIdempotencyStore` em memória do processo |
| `decisionId`, `status`, `explanation`, `capabilityId`, `providerRequestId`, `providerReference` | Corpo da resposta V1 (ecoado e persistido no BFF SegSense) |
| Capability e base-url do Test Double | Registry YAML `spider.satellite.providers.insurance-provider-mock` — **não** no browser |

Segredos e credenciais não entram nesses eventos nem na UI.

## Campos realmente retornados / persistidos hoje

| Campo | Origem | Persistido no BFF | Exibido |
|---|---|---|---|
| `id` | SegSense ao gravar a jornada | sim | detalhes técnicos |
| `generatedAt` | `Instant.now()` no BFF | sim | rotulado como persistência SegSense |
| `declaredObjective` | corpo do POST público | sim | bloco 2 / cenário da tentativa |
| `status` | mapeamento do status V1 ou validação local | sim | blocos 3/4 e `details` |
| `correlationId` | header/BFF | sim | detalhes |
| `spiderDecisionId` | `decisionId` V1 | sim | detalhes, se presente |
| `explanation` | Spider, ecoada (ou texto local se `MISSING_CONTEXT`/`AMBIGUOUS` **antes** da Spider) | sim | bloco 4 |
| `messageCreatedAt` / `objectiveDeclaredAt` | UTC da interação corrente no BFF | sim | detalhes; distintos do timestamp editorial |
| `editorialSourceTimestamp` | Registry `capturedAt` | sim | rotulado “publicação da fonte” |
| `capabilityId` / `providerRequestId` | V1 só se provedor confirmado | sim / null | detalhes só se pré-proposta ou cotação simulada confirmada |
| `mockResultId` | `providerReference` | sim | detalhes; condição das possibilidades ou `quoteReference` |
| `items` / pertinência / limites | `resultSummary` do Test Double (jornada ilustrativa) | só se provedor confirmado | bloco de possibilidades |
| `simulatedQuote` / `premiumAnnualCents` | cálculo do mock na capability 1.1 | só se `COMPLETED` desta execução | bloco Cotação simulada; nunca fallback |
| `contextElements` / título / versão da fonte | Registro SegSense + parser limitado | sim | bloco 1 e persistência |
| `planId` / `executionId` | **ausentes** | não | nota “Fora desta demonstração” |
| Segredo / credencial | ambiente local | não | nunca |

## Segurança de URL

Aceite de exemplo governado: `http` + host `127.0.0.1` ou `localhost` + porta na allowlist (`5178` e, na stack isolada, `15178`) + path `/demonstracao/fontes/{slug}` sem query/fragmento/userinfo. Captura de URL pública: `POST /api/v1/public/demo/url-captures` (SSRF fail-closed; ver `SEGSENSE_URL_001` e `SEGSENSE_SEC_005`). Falha de captura **não** seleciona exemplo governado. Slug revogado: `REVOKED_CONTEXT_SOURCE`.

PII óbvia no relato (e-mail, padrões grosseiros) → `PERSONAL_DATA_NOT_ALLOWED` **antes** do fingerprint. Não promete detecção perfeita. O fingerprint SHA-256 da solicitação canônica (V15) não armazena o relato bruto. Replay idêntico devolve o mesmo `id`; mudança material → 409 sem payload da tentativa anterior. Linhas com fingerprint nulo (pré-V15) → 409 fail-closed.

## Escopo atual versus lacunas futuras

| Existe nesta fatia (DEMO ONLY) | Fora desta demonstração |
|---|---|
| Envelope V1 síncrono `REQUEST_DECISION` | Intent Contract pleno / CTX-004 |
| Três fontes sintéticas (família, renda, incêndios) + uma revogada | Fetch de várias páginas / crawling / JS remoto |
| Captura de **uma** URL pública (HTML/texto), snapshot V17, revisão humana | Browser headless; execução de JavaScript da página |
| Intenção livre classificada + perguntas `MISSING_CONTEXT` | Eligibility Gate |
| `decisionId` + explicação de allowlist | Data Plane (`planId` / `executionId`) |
| Possibilidades ilustrativas (Provider 1.0), caminhos agrícolas demonstrativos sem R$ e cotação simulada `NON_BINDING_DEMO` (Provider 1.1) | Provider certificado / Icatu / cotação agrícola vinculante |
| Idempotência e correlação | Callback / event bus / IdP |
| V14: status `MISSING_CONTEXT` / `AMBIGUOUS` | Reescrita de V1–V13 |
| V15: `request_fingerprint` nullable | Reescrita de V1–V14; persistência do relato bruto |
| V16: status `SIMULATED_QUOTE_AVAILABLE` | Reescrita de V1–V15 |
| V17: `demo_url_capture` / confirmação; status `NO_COMPATIBLE_CAPABILITY` | Reescrita de V1–V16 |
| Stack isolada COR_001 (`:19095/:19080/:19088/:15178/:15437`) | Parada da reunião sem ledger; `pids.txt` |
| Painel da **interação corrente** | Console operacional autenticado |

## Reprodução sem expor segredos

1. Uma vez por máquina: `C:\Projetos\segsense\scripts\setup-mvp-demo-secrets.ps1` (grava `scripts/.mvp-secrets.env`, gitignored, ACL restrita). **Não** cole o arquivo em chat.
2. Prova da versão nova: `.\start-isolated-cor016.ps1` e `.\prove-isolated-prm017.ps1` (deixa a stack no ar; após provider-down, religa o mock e atualiza o alvo `mock` do ledger). `.\prove-isolated-cor016.ps1` encerra a isolada no `finally` e **não** deve ser o roteiro desta auditoria. Não derruba `:8095/:8080/:8088/:5178` nem o volume `segsense_pgdata`.
3. `.\start-mvp-demo.ps1` e `.\preflight-mvp-demo.ps1` só para a reunião nas portas históricas.
4. Abrir `http://127.0.0.1:15178/demonstracao/mvp-integrado` para a versão nova; `:5178` só se a reunião tiver sido reiniciada com este código.
5. Prova HTTP histórica da reunião: `.\prove-mvp-http.ps1` (não é a prova COR_001). A indisponibilidade de provedor da reunião usa Spider **isolada** em `:18080`; a prova COR_001 usa mock `:19095`.
6. PID obsoleto e script de parada: `.\test-mvp-ops.ps1` (invoca `stop-mvp-demo.ps1` com ledger temporário; processo alheio permanece).
7. Parada da reunião: só `.\stop-mvp-demo.ps1` contra `.mvp-logs/owned-run.json`. Parada da stack COR_001: o mesmo script com `-LedgerPath .mvp-logs/owned-run-cor016.json`. Sem `pids.txt`. Sem glob. Sem ledger verificável: inspecione as portas; não mate.

Identidade pública dizível: `local-demo-segsense`. O valor do segredo não é.
