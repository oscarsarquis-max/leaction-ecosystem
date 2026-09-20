# SPIDERBANK-PRM-001 — Adequações para o mock de sistemas de crédito

**Status:** DRAFT — inspeção e proposta. Não autoriza integração, scaffold, alteração no Spider, aprovação do ADR nem publicação.  
**Data:** 17 de setembro de 2026  
**Fronteira preservada:** SpiderBank → Spider → resolução de capability → sistema provider. SpiderBank não chama o mock.

**Regra desta conversa:** nenhum pressuposto e nenhuma implementação em `spider/**` sem autorização explícita. Itens na coluna “Spider (proposta)” abaixo são hipóteses de trabalho, não plano aprovado.

## 1. O que foi inspecionado

| Fonte | Achado |
|---|---|
| Caminho do prompt | `C:\Projetos\spider-bank-provider-mock` **não existe** |
| Destino real do mock | `C:\Projetos\mock-sistemas-credito` (README + SPIDERBANK-MOCK-001) |
| Git do mock | sem repositório próprio |
| Spider | branch `feat/spider-sat-003-segsense`, HEAD `5ee7756`; working tree sujo — **não alterado** |
| ADR | `spider-bank/documents/SPIDERBANK-ADR-001.md` continua **DRAFT 0.4** |
| Testes do mock | 6/6 passaram nesta inspeção (`npm test`) |

Arquivos lidos: README, `documents/SPIDERBANK-MOCK-001.md`, `examples/request.json`, `handler.js`, `server.js`, `handler.test.js`; no Spider: catálogo de capabilities, plano `SEEK_WORKING_CAPITAL`, `HttpProviderCapabilityAdapter`, `SatelliteInteractionService`, `SatelliteRegistry`, `DemoSliceRules`, `application-local-demo.yml`, schemas provider 1.1 e satellite 1.0.

## 2. O que já existe (não inventado)

### Mock (`mock-sistemas-credito`) — isolado, `integratedWithSpider: false`

- Loopback `127.0.0.1:8096`, credencial `X-Credit-Mock-Credential` (≥16 chars, compare por hash).
- `POST /v1/provider/capabilities/SIMULATE_WORKING_CAPITAL/executions`.
- Contrato **local** `credit-mock/0.1`. Purpose local `WORKING_CAPITAL_SIMULATION`.
- Inputs: `scenarioKey` + opcionalmente `principalCents` e `termMonths`. Campos extras, PII, objetivo, taxa imposta pelo chamador: rejeitados.
- Cenários: SUCCESS, MISSING_CONTEXT, REJECTED, HUMAN_REVIEW, UNAVAILABLE.
- Resultado SUCCESS: juros simples sintéticos 100 bps/mês; `offerable: false`; `MOCK_ONLY`; watermark de não-oferta.
- `providerId`: `credit-provider-mock`.

### Spider (estado atual, sem mudança)

- Capability `SIMULATE_WORKING_CAPITAL` **está no catálogo** e **está `NOT_AVAILABLE`**, sem rota/adapter.
- Intent `SEEK_WORKING_CAPITAL` compõe um plano de 7 passos; simulação é o 6º, depois perfil/cadastro/elegibilidade — também `NOT_AVAILABLE`.
- Único provider HTTP registrado: `insurance-provider-mock` (`127.0.0.1:8095`, header `X-SEGSENSE-Mock-Credential`).
- Adapter HTTP: `contractVersion` 1.0 ou 1.1; purpose do envelope é o do satélite; aceita `providerId` **somente** `insurance-provider-mock`; COMPLETED com origin de seguros/`NON_BINDING_DEMO` de cotação residencial. PENDING/REJECTED/503 viram `unavailable()`.
- Schema satellite 1.0 de pedido ao provider: `purpose` enum **só** `INSURANCE_PROTECTION_ASSESSMENT`; `inputs` só `scenarioKey`.
- Schema provider 1.1: capability **só** `GENERATE_SYNTHETIC_HOME_QUOTE`.
- Fatia SAT-003 (`DemoSliceRules`) encaminha seguros/agro/cotação residencial. **Não** há ramo de capital de giro nem capability `SIMULATE_WORKING_CAPITAL`.
- Registro EXPERIENCE no YAML local-demo é o satélite SegSense (finalidades de proteção), não SpiderBank.

## 3. Pontos de integração (mapa, sem executar)

```
[SpiderBank EXPERIENCE]  --SAT-003-->  [Spider Control Plane]
                                              |
                                              | (hoje: capability crédito = NOT_AVAILABLE)
                                              v
                                   [Capability Resolution]
                                              |
                    autorização futura?       v
                                   [credit-provider-mock]
                                   POST .../SIMULATE_WORKING_CAPITAL/executions
                                   credit-mock/0.1
```

O mock já fala o *formato* de path do Provider Contract. Não fala a *versão oficial* nem o *adapter atual*.

## 4. Lacunas contratuais

| Lacuna | Lado | Efeito se ninguém autorizar o Spider |
|---|---|---|
| `credit-mock/0.1` ≠ `1.0`/`1.1` | contrato | Adapter atual não monta nem valida esse envelope |
| Purpose `WORKING_CAPITAL_SIMULATION` | contrato 1.0 | Schema rejeitaria; adapter reusa purpose do satélite (hoje, proteção) |
| Inputs `principalCents` / `termMonths` | contrato 1.0 | Só `scenarioKey` é canônico na 1.0 |
| Header `X-Credit-Mock-Credential` | adapter | Spider envia `X-SEGSENSE-Mock-Credential` |
| `providerId` `credit-provider-mock` | adapter | Qualquer id ≠ `insurance-provider-mock` → unavailable |
| PENDING / REJECTED / 503 honestos | adapter | Colapsam em unavailable; a experiência não veria “faltou prazo” vs “recusa sintética” |
| Capability `NOT_AVAILABLE` + sem rota | catálogo | Resolução não despacha o mock |
| Plano de 7 passos | planejamento | Mesmo AVAILABLE, o plano completo ainda exige outras capabilities ausentes |
| DemoSliceRules | SAT-003 | Pedido EXPERIENCE de giro não vira `SIMULATE_WORKING_CAPITAL` |
| Satélite SpiderBank | registry | Não há `satelliteId` EXPERIENCE de crédito no YAML |
| DIRECT_ENTRY vs SATELLITE_GOVERNED | SAT-003 | Continua pendente no ADR; o mock não resolve isso |

## 5. Mudanças propostas (todas condicionadas)

Nada disto será feito até você autorizar, item a item, o que pode tocar no Spider.

### A. Mock (local) — proposta, não feita

Manter `MOCK_ONLY` e `integratedWithSpider: false` até haver contrato aceito. Eventual alinhamento de versão/header só depois de decisão contratual. Não misturar com o mock de seguros.

### B. Spider — **somente com autorização explícita**

Propostas, sem pressupor aceite:

1. Não reutilizar o adapter de seguros para crédito (hoje ele *rejeitaria* o mock).
2. Não marcar `SIMULATE_WORKING_CAPITAL` AVAILABLE sem rota e sem executor registrado.
3. Não fingir que o plano `SEEK_WORKING_CAPITAL` de 7 passos já é executável.
4. Distinguir simulação ilustrativa de aprovação/contratação (o mock já marca `offerable: false`).
5. Tratar PENDING/REJECTED do crédito sem traduzir tudo em “provider down”.
6. Não colocar purpose de seguro em pedido de giro.

Caminhos possíveis **se** você autorizar mais tarde (escolha sua, não do agente):

- **Contrato de crédito versionado** no Spider (schema próprio, não patch no 1.0 de seguros), mais provider registry `credit-provider-mock`, mais adapter/projeção que não hardcodeie seguros; **ou**
- **Fatia SAT-003 de crédito** mínima, satélite EXPERIENCE SpiderBank, purpose e interaction types novos, sem alterar o comportamento SegSense.

### C. SpiderBank satélite — só após ADR APPROVED **e** autorização de implementação

BFF chama `POST /v1/satellites/interactions`. Nunca `8096`. Apresenta só o que o Spider devolver. Sem taxa se o resultado não vier.

## 6. Critérios de validação (quando houver autorização para integrar)

1. Chamada direta SpiderBank → mock: deve falhar ou simplesmente não existir no código do satélite.
2. Sem provider/capability no Spider: resposta honesta de indisponibilidade; sem números inventados na UI.
3. Com autorização e integração: SUCCESS 1.000.000 centavos / 12 meses → total 1.120.000, parcelas somam o total, `offerable: false`, watermark visível.
4. MISSING_CONTEXT / REJECTED / HUMAN_REVIEW / UNAVAILABLE: estados distintos, sem fabricar parcela.
5. Seguros (SegSense + insurance-provider-mock) inalterados.
6. Credencial do mock não no frontend.

## 7. Distinção executado × pendente

| Já existe | Não existe / não autorizado |
|---|---|
| Mock isolado com 6 testes verdes | Registro do provider no Spider |
| Capability nomeada no catálogo | Capability AVAILABLE com rota |
| Path HTTP semelhante ao Provider Contract | Schema oficial de crédito |
| ADR e MOCK-001 em DRAFT | Satélite SpiderBank, BFF, UI |
| SAT-003 para seguros | Ramo SAT-003 para capital de giro |

## 8. Conclusão

O mock é um executor ilustrativo válido **fora** do Spider. Integrá-lo exige decisões suas no Core (contrato, adapter, catálogo, satélite). Enquanto isso não for autorizado, o estado honesto é: simulação de giro **não disponível** na cadeia governada.

**SPIDERBANK-ADR-001 permanece DRAFT.** Este PRM-001 também.
