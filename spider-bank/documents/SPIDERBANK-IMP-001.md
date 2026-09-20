# SPIDERBANK-IMP-001
## Evidência da primeira integração SAT-003 — Experience Satellite de crédito

**Data:** 18 de setembro de 2026  
**Status:** primeira jornada integrada e verificada localmente  
**Conclusão correta:** SpiderBank integrado como Experience Satellite, com contexto governado e diagnóstico fiel dos impedimentos. **Não** é simulação de crédito ponta a ponta.

Referência de execução: `documents/SPIDERBANK-ARQ-003.md`.

## 1. O que mudou

### Spider (`C:\Projetos\spider`)

- Contrato SAT 1.0/1.1/1.2: finalidade `WORKING_CAPITAL_ASSESSMENT` coexistindo com `INSURANCE_PROTECTION_ASSESSMENT`.
- Registro local-demo `spiderbank` (papel EXPERIENCE, fonte `SPIDERBANK_WORKING_CAPITAL_SYNTHETIC_V1`, objetivo permitido `SEEK_WORKING_CAPITAL`).
- Interpretação determinística em `DemoSliceRules`: a declaração reconhecida mapeia para `SEEK_WORKING_CAPITAL` e não cai no READY de seguros.
- Ligação ao plano existente `WORKING_CAPITAL_DIAGNOSTIC_V1` via `WorkingCapitalPlanProjection` + catálogos estáticos.
- Projeção contratual `PLAN_IMPEDED` / `PRESENT_PLAN_IMPEDIMENTS` com os sete passos e impedimentos reais.
- `IDENTIFY_CUSTOMER` permanece AVAILABLE no catálogo, mas **não** é concluída sem principal autenticado do cliente.
- Simulação: card SpiderBank continua `available=false`. A razão “não está no registro” foi substituída pela indisponibilidade real do caminho de provider.

### SpiderBank (`C:\Projetos\spider-bank`)

Aplicação independente:

| Peça | Porta | Papel |
|---|---|---|
| `frontend/` | `:5190` | Experiência de crédito demonstrativa |
| `backend/` | `:8090` | BFF SAT-003; segredo só no servidor |
| `scripts/` | — | setup / start / stop / health |
| `services/` | — | nota contratual; sem conector `:8096` |
| `database/` | — | sem persistência nesta fatia |

O BFF chama apenas `POST /v1/satellites/interactions`. Não chama `mock-sistemas-credito` nem `:8096`. Não usa `GET /v1/demo/spiderbank/entry` nem `POST /v1/demo/spiderbank/understand`.

## 2. Jornada viva comprovada

Após reinício **somente** da engine `:8080` (Monitor, SegSense e mock de seguros permaneceram de pé):

| Prova | Resultado |
|---|---|
| `GET http://127.0.0.1:8090/api/health` | `UP`, identidade `spiderbank` |
| `GET http://127.0.0.1:8090/api/credit/context` | fonte governada sintética |
| `POST /api/credit/journeys` sem confirmação | `400 OBJECTIVE_NOT_CONFIRMED` |
| `POST /api/credit/journeys` confirmado | `200 ANALYSIS_BLOCKED`, `creditDecision=NONE` |
| Replay da mesma `Idempotency-Key` | mesmo `decisionId` |
| Monitor `/v1/console/monitor/events` | eventos `originSatellite=spiderbank`, `currentComponent=SPIDER`, `SATELLITE_RESPONSE_RETURNED`, `reasonCode=PLAN_IMPEDED` |
| Simulação `/v1/console/monitor/simulation` | `spiderbank.available=false` |
| Frontend `http://127.0.0.1:5190/` | `200`, título SpiderBank |

Identidades reais desta prova (após o reinício da engine):

- `correlationId`: `60af6a5b-c0aa-46f7-81c5-0ba7f6ae9d01`
- `decisionId`: `spd-0a8a0130-bed9-4142-ac24-48d0f9b75b89`
- `contextRef`: `ctx-b39dcd8c-4480-4a8b-b99f-20945307cbcd`
- Intent determinado pela Spider: `SEEK_WORKING_CAPITAL`
- Plano determinado pela Spider: `WORKING_CAPITAL_DIAGNOSTIC_V1`
- `providerDispatched`: `false`
- `analysisComplete`: `false`

Arquivos: `documents/evidencias/SPIDERBANK-IMP-001/`.

`SATELLITE_RESPONSE_RETURNED` significa que a Spider produziu/devolveu a resposta. O BFF recebeu HTTP 200 com o mesmo `correlationId` e a projeção de impedimentos; a interface tem testes de apresentação desses dados.

## 3. Testes executados nesta entrega

| Suíte | Resultado |
|---|---|
| Spider `SpiderBankSatelliteContractTest` + `SpiderBankSatelliteInteractionHttpTest` | passou |
| Spider regressão SAT seguros (`SatelliteContractV1Test`, `SatelliteInteractionHttpTest`, `SatelliteContractJsonSchemaTest`) | passou |
| Spider `MonitorEventsTest`, `LocalDemoSimulationScenariosTest` | passou (card continua indisponível) |
| SpiderBank BFF `mvn test` | passou |
| SpiderBank frontend `npm test` | 2 testes, passou |

Não foi reexecutada a suíte Maven completa do Spider nem os 169 testes de frontend do Monitor nesta fatia. Os testes de Simulação/Monitor tocados (`SimulationPanel.test.jsx`, `MonitorShell.test.jsx`) foram atualizados só na cópia do mock de indisponibilidade.

Não houve browser MCP disponível para clicar a UI de ponta a ponta. A verificação de interface foi por teste de componente + HTTP do Vite.

## 4. Limitações

- As capabilities 2–7 continuam `NOT_AVAILABLE`. `IDENTIFY_CUSTOMER` não conclui sem cliente autenticado.
- O mock `C:\Projetos\mock-sistemas-credito` não foi alterado nem chamado.
- O card SpiderBank da Simulação permanece desabilitado de propósito.
- A superfície legada `http://127.0.0.1:5180/spiderbank` **não** é o produto desta entrega.
- Idempotência segue o contrato (replay / conflito). Não é processamento exatamente uma vez.
- Credenciais locais ficam em `scripts/.local-secrets.env` (gitignored). Sem esse arquivo, o BFF classifica a Spider como indisponível técnica — não como recusa de crédito.
- O engine precisa da variável `SPIDER_SPIDERBANK_DEMO_APPLICATION_SECRET` igual à do BFF.

## 5. Como iniciar e validar

1. Engine Spider em `:8080` com profile `local-demo` e `SPIDER_SPIDERBANK_DEMO_APPLICATION_SECRET` definido. Monitor em `:5180`.
2. Em `C:\Projetos\spider-bank`:

```powershell
.\scripts\setup-local-secrets.ps1
.\scripts\start-local.ps1
.\scripts\check-health.ps1
```

3. Abrir **http://127.0.0.1:5190/** — não o card da Simulação e não `/spiderbank` do Monitor.
4. Revisar o contexto sintético, confirmar “buscar capital de giro” e enviar.
5. Esperar impedimentos reais das sete capabilities, sem produto, taxa, limite ou aprovação.
6. No Monitor, buscar a correlação / `spiderbank`. Deve aparecer a interação do satélite mesmo com resultado de impedimento.
7. Encerrar só o que este start registrou:

```powershell
.\scripts\stop-local.ps1
```

O script de start **não** encerra SegSense, Monitor, mock de seguros nem a engine.
