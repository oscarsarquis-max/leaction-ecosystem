# SEGSENSE_MVP_001 — Inventário e riscos do MVP integrado de demonstração

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_MVP_001 |
| Versão | 1.0 |
| Data | 13/09/2026 |
| Status | Inventário **antes** da implementação do PRM_013 |

## 1. O que existe e o que não existe

| Artefato | Estado |
|---|---|
| Satellite Contract externo (schema, endpoint, autenticação de satélite, testes oficiais) | **IMPLEMENTADO / DEMO ONLY** em `SPIDER-SAT-003` (13/09/2026). Preview/IdP/Data Plane em `SEGSENSE_REQ_002` permanecem abertos. |
| `SEGSENSE_ADR_003` | Vigente: não implementar DTO/mapper/client do contrato pleno. |
| `SEGSENSE_ADR_004` | Autoriza **fatia mínima local** SegSense → Spider → mock, sem declarar o contrato completo. |
| Contextual Link `/go` e SpiderBank | Implementados na Spider; **não** são o contrato SegSense; não serão usados como integração de seguros. |
| Intent Contract / Canonical Execution | Internos ao Data Plane Spider (`INTERNAL_ONLY`). Não serão copiados nem expostos. |
| Credencial Spider `X-Spider-Credential-Ref` | Existe no profile `local-demo` para o console (`local-demo-console`). **Não** será reutilizada pelo SegSense (evita acesso ao Data Plane). |
| Jornada SegSense `/c/{token}` | Operante localmente; emissão de token exige admin/IdP. **Inadequada** como entrada da reunião sem identidade. |
| Insurance Provider Mock | Só conceitual (`SEGSENSE_MCK_001`). Camada B Icatu **BLOQUEADA**. |

## 2. Portas (não colidir)

| Processo | Porta |
|---|---|
| SegSense frontend | 5178 |
| SegSense BFF | 8088 |
| SegSense Postgres | 5437 |
| Spider API | 8080 |
| Spider frontend | 5180 |
| Spider Postgres (compose; local-demo usa H2) | 5432 |
| Mocks bancários Spider | 8091 / 8092 |
| **Insurance Provider Mock (novo)** | **8095** |

## 3. Fatia mínima autorizada (não é Satellite Contract)

```
Visitante (dados sintéticos)
  → SegSense UI /demonstracao/mvp-integrado
  → SegSense BFF  POST /api/v1/public/demo/protection-journeys   (local/test)
  → Spider        POST /v1/demo/segsense/protection-decisions    (profile local-demo)
  → Mock          POST /v1/illustrative-protection-items
  → Spider devolve decisão + itens ilustrativos
  → SegSense apresenta pré-proposta demonstrativa
```

Papéis (ARCH-017): SegSense = experiência e apresentação; Spider = compreensão/decisão e acionamento do provedor; mock = resultado ilustrativo. O SegSense **não** chama o mock. A Spider **não** altera governança de proposta securitária real.

## 4. Riscos e mitigações

| Risco | Tratamento |
|---|---|
| Declarar Satellite Contract pronto | Documentar `demoSliceOnly=true` no SegSense e `notSatelliteContract=true` só na fatia Spider; fatia só `local-demo`. |
| Confundir com Icatu | Sem logo, produto, preço ou API Icatu; watermark obrigatório. |
| Invadir SpiderBank / `/go` / crédito rural | Pacote e rotas novos; objetivo agrícola rejeitado. |
| Reusar `local-demo-console` | Identidade distinta `local-demo-segsense`, só nas rotas `/v1/demo/segsense/**`. Identidade ≠ segredo. |
| Tratar identidade como segredo / literais versionados | Segredos só em `.mvp-secrets.env` (não versionado); fail-closed se ausentes. |
| Enviar contexto e ignorá-lo na Spider | `originSnapshot` tipado, validado, no fingerprint e na evidência. |
| CORS `/v1` da Spider | SegSense BFF (servidor) chama a Spider; o browser não chama `:8080`. |
| GlobalExceptionHandler Spider (“legacy unavailable”) | Adapter do mock captura falhas e devolve estado `MOCK_UNAVAILABLE`. |
| ArchUnit SegSense `SpiderClient` | Adapter nomeado sem `SpiderClient` / `SatelliteContract`. |
| Token permanente / login fictício | Jornada isolada do domínio de convite; fixture resetável. |
| PII | Campos pessoais rejeitados; só objetivo allowlisted. |
| Proposta com valor | Sem valores monetários. |

## 5. Bloqueio vs. seguir

A trilha segura **não** está bloqueada: há extensão pequena no padrão já usado (`/v1/demo/*` + profile `local-demo` + header de credencial), sem Data Plane e sem Intent público. Segue-se a fatia. Se a reunião exigir cotação Icatu ou contrato pleno, **parar**.
