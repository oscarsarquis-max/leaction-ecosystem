# ACTIONFINANCE_INT_001 — Fronteira Spider e identidades

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_INT_001 |
| Versão | 0.2 |
| Status | EXTERNAL_CONTRACT_PENDING |
| Data | 25/09/2026 |
| Dependências | ACTIONFINANCE_ARQ_001 §8; AF-ADR-004; AF-ADR-009 |

O contrato Satellite vigente **não** é automaticamente compatível com o domínio financeiro. Esta matriz não publica versão futura, não inventa callback e não autoriza `workingCapitalParameters` como pagamento.

## 1. Contrato publicado (não financeiro)

| Afirmação | Fonte | Linha |
|---|---|---|
| `POST /v1/satellites/interactions` | `SatelliteInteractionHttpController.java` | 48 |
| Versões 1.0, 1.1 e 1.2 suportadas | `SatelliteContractV1.java` `supports()` | 26–29 |
| `purpose` só seguros/crédito em 1.0, 1.1 e 1.2 | schemas `satellite-interaction-request.schema.json` | 37–39 |
| `responseChannel` só `SYNC` | schema 1.2 | 69 |
| `satelliteId` minúsculo | schema 1.2 pattern `^[a-z][a-z0-9-]{1,62}$` | 22 |
| `extensions` fechado; `workingCapitalParameters` é crédito | schema 1.2 | 75–88 |
| EXPERIENCE recusa execução/resultado de capability | `SatelliteInteractionService.java` | 92–96 |
| Registry só EXPERIENCE ACTIVE | `SatelliteRegistry.requireExperience` | 19–27 |
| Registry local: `segsense`, `spiderbank` | `application-local-demo.yml` | 113+ e 186+ |
| Idempotência em memória | `SatelliteIdempotencyStore.java` | 9–17 |
| Parser não interpreta envelope financeiro | `SatelliteInteractionParser.java` | 12–31 |

## 2. Matriz de compatibilidade (obrigatória)

| Item | Capacidade observada | Fonte | Requisito ActionFinance | Gap | Proposta | Projeto a alterar | Gate |
|---|---|---|---|---|---|---|---|
| Identidade EXPERIENCE | Papel EXPERIENCE no schema e no registry; satélite precisa estar ACTIVE | Schema 1.2 L23; Registry L24 | Satélite EXPERIENCE independente; frontend só fala com o backend AF | Não há entrada `actionfinance` no registry | Declarar manifesto preliminar não certificado; cadastro na Spider só com contrato | ActionFinance (docs agora); Spider no PRM_005 | PRM_005 |
| Nome técnico minúsculo | `satelliteId` pattern minúsculo | Schema 1.2 L22 | Identidade técnica `actionfinance`; rótulo ActionFinance | Nenhum registro atual | Não enviar rótulo maiúsculo como id | ActionFinance; Spider registry futuro | Fundação (id local); PRM_005 (registry) |
| Autenticação | Header de satélite + secret do registry; `secretMatches` SHA-256 | Registry L46–51; controller headers | Principal e empresa no AF; credencial de satélite só na borda Spider | Sem satélite AF; identidade demo AF ainda não especificada | Demo local deny-by-default no AF; credencial Spider só depois do contrato | ActionFinance PRM_002; Spider PRM_005 | PRM_002 (demo); PRM_005 (satélite) |
| Finalidade financeira | Enum `INSURANCE_PROTECTION_ASSESSMENT`, `WORKING_CAPITAL_ASSESSMENT` | Schema 1.0/1.1/1.2 L37–39; `SatelliteContractV1` L16–17 | Finalidade financeira própria | Ausente | Não reusar seguros/crédito | Spider | PRM_005 |
| Contexto de empresa | Envelope sem `companyId` de gestão financeira | Parser L12–31 | Isolamento por empresa no AF; contexto empresarial no contrato futuro | Contrato atual não carrega empresa AF | Autorização local agora; campo/contexto no contrato posterior | ActionFinance; Spider | PRM_002/003; PRM_005 |
| Contrato financeiro | SAT-003 IMPLEMENTADO / DEMO ONLY para seguros/crédito | SAT-003; ARCH-017 | Envelope financeiro, classificação, referências | Inexistente | Evolução versionada com regressão SegSense/SpiderBank | Spider | PRM_005 |
| Idempotência durável | Mapa em memória; get antes, put depois | Store L9–17; Service L98–100 | Persistida, atômica com o efeito, escopo empresa/operação | RAM some no restart; não é financeira | `request_idempotency` no AF; Spider persistida só se o contrato exigir | ActionFinance PRM_003; Spider se contratado | PRM_003 / PRM_005 |
| Resposta síncrona | Só `SYNC` | Schema 1.2 L69 | Aceitar SYNC para declaração; não inferir liquidação | Adequado só para interação imediata | Usar SYNC sem tratar 200 como pagamento | Spider (manter); AF adapter futuro | PRM_005 |
| Entrega assíncrona | Canal async ausente no schema | Schema 1.2 L69 | Resultado posterior de provider | Bloqueado | Desenhar canal no contrato; sem webhook fictício | Spider | PRM_005 |
| Deduplicação | Fingerprint em memória no satélite; Hub tem outbox própria (legado) | Store; levantamento Hub | Deduplicar evento recebido (`callbackEventId`) sem repetir efeito | Sem inbox AF; store Spider não sobrevive restart | Inbox na primeira integração efetiva | ActionFinance PRM_006; Spider se necessário | PRM_006 |
| Correlação | `correlationId` obrigatório; `decisionId`/`planId`/`executionId` só se produzidos | Service L80–82; SAT-003 | Acompanhar ponta a ponta sem autorizar por correlation | IDs de plano/execução não existem no cadastro local | Não inventar IDs Spider no CRUD | ActionFinance; Spider | PRM_003 local; PRM_005 integração |
| Observabilidade | Eventos SATELLITE_* no serviço; Monitor é da Spider | Service; ARCH-017 | Logs sem payload financeiro; Monitor só o que a Spider processar | Cadastro local não gera evidência Spider | Auditoria no AF; não fabricar card no Monitor | ActionFinance; Spider só com interação real | PRM_002 logs; PRM_006 Monitor |
| Persistência | Spider: adapters JPA existem, default memória (levantamento, **NOT_VERIFIED** em runtime) | `database/README.md` SpiderBank; levantamento §8 | PostgreSQL AF próprio | SpiderBank sem banco na 1ª entrega | Não copiar limitação SAT-003 | ActionFinance | PRM_002/003 |
| Dados proibidos | Schema metadata string curta; Hub loga corpo MP (levantamento) | Schema 1.2 L70–74; levantamento §7 | Sem tokens, documentos, dados bancários, payload integral em log/Monitor | Contrato atual não define envelope financeiro seguro | Minimizar; proibir cartão/QR/segredo no contrato genérico | ActionFinance; Spider; Hub legado fora de escopo | PRM_005 / SEC futuro |

## 3. Identidades

| Identidade | Origem | Não é |
|---|---|---|
| companyId / actorId | Contexto autorizado no ActionFinance | Confiança no payload |
| payableId / receivableId | Domínio ActionFinance | ID de pagamento |
| businessReference + sourceSystem + sourceRecordId | Vínculo com fato externo | Chave de autorização |
| messageId | Interação de satélite | Chave de obrigação |
| correlationId | Acompanhamento ponta a ponta | Autorização |
| idempotencyKey | Intenção mutável estável (escopo + fingerprint) | Token de liquidação |
| decisionId / planId / executionId | Só se a Spider os produzir | Inventados no satélite |
| providerRequestId / providerTransactionId | Execução externa futura | Identidade da obrigação |
| callbackEventId | Evento recebido e deduplicado | Chave do pagamento |

Timeout não renova a chave. 200/202 não é liquidação.

## 4. Sequências

Registro local — **fluxo proposto da primeira fatia; não implementado**:

```mermaid
sequenceDiagram
  actor U as Usuário
  participant A as API ActionFinance
  participant DB as PostgreSQL ActionFinance
  U->>A: Registrar obrigação + chave idempotente
  A->>A: Autenticar, autorizar empresa e validar
  A->>DB: Transação: idempotência + obrigação + histórico
  DB-->>A: Resultado persistido
  A-->>U: Obrigação em aberto, sem pagamento
```

Execução governada — **arquitetura alvo; contratos ausentes**:

```mermaid
sequenceDiagram
  participant A as ActionFinance futuro
  participant SP as Spider
  participant PR as Provider aprovado
  A->>A: Persistir intenção e outbox local
  A->>SP: Intenção governada, contrato aprovado
  SP->>PR: Execução autorizada e idempotente
  PR-->>SP: Aceite ou resultado
  SP-->>A: Resultado governado
  PR-->>SP: Evento posterior autenticado
  SP->>SP: Persistir, deduplicar e correlacionar
  SP-->>A: Entrega de resultado, contrato a definir
  A->>A: Inbox + aplicação atômica + auditoria
```

Inbox/outbox: evolução da primeira integração efetiva, não capacidade existente.

## 5. Proibições deste incremento

- Colocar pagamento em `workingCapitalParameters` ou `metadata`.
- Escolher provider no BFF.
- Inventar endpoint de callback.
- Redirecionar webhook do Hub para `POST /v1/canonical/signals` (ingresso distinto; levantamento §8).
- Tratar cobrança avulsa do Hub como base da fatia (achado fora de escopo).

## Atualização de precedência — 28/09/2026

As novas diretrizes do proprietário substituem os limites anteriores conflitantes de ActionHub/assinaturas e endereço de publicação. Consultar ACTIONFINANCE_ARQ_002_DIRETRIZES_INTEGRACAO e a fonte ACTIONFINANCE_DIR_INT_001_2026-09-28, vinculadas no índice. Preservar domínio financeiro local, estoque Panne e histórico. Não iniciar integração nem publicar domínios. PRM_002_COR_001 permanece pendente de retorno.
