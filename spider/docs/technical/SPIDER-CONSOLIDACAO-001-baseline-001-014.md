# SPIDER-CONSOLIDAÇÃO-001 — Baseline 001–014

## Status

Consolida auditoria e fechamento do baseline acumulado. Integrações reais permanecem fora de escopo.

## Baseline de testes

| Momento | Totais | Failures | Errors | Skipped |
|---------|--------|----------|--------|---------|
| Início consolidação | 157 | 0 | 0 | 0 |
| Após correções DP/Control Plane | **169** | **0** | **0** | **0** |

## Gaps encontrados (obrigatórios)

| Gap | Evidência inicial | Correção |
|-----|-------------------|----------|
| `DATA_PROTECTION_PROFILE` ausente do Control Plane | Enum sem tipo; profile hardcoded no ingress/processor | Artifact type + codec + catalog + snapshot V2 |
| Snapshot só V1 | `GOVERNANCE_SNAPSHOT_V1` apenas | V2 quando há DP profiles; V1 preservado |
| `ExternalSignalDefinition` sem `dataProtectionProfileRef` | Campo ausente | Campo + validação cross-ref no bundle |
| Wait não fixava DP ref | Sempre `null` na criação | Resolução via fixation/snapshot histórico |
| Encrypt/decrypt com fallback lateral | `publishedAes256("signal-envelope")` hardcoded | Resolve profile do snapshot histórico |
| E2E HTTP+JPA único incompleto | Só unitários token/AES | Routing + transactional + catalog + flag matrix |

## Matriz de rastreabilidade (resumo)

| ID | Origem | Requisito | Código | Wiring | Persistência | Teste | Estado |
|----|--------|-----------|--------|--------|--------------|-------|--------|
| C01 | 001–003 | Records/contratos canônicos | `canonical/**` | Engine | n/a | suite regressão | PASS |
| C02 | 004–005 | Route/plan/state machine | `execution/**` | Engine | JPA/memory | multi-step suite | PASS |
| C03 | 006–008 | Persistência/idempotência | stores + migrations V20260821* | profile mode | JPA+memory | adapters | PASS |
| C04 | 009 | Wait/inbox/resume | wait/inbox | Engine | JPA | suite | PASS |
| C05 | HTTP | Canonical HTTP opt-in | controllers + flags | ConditionalOnProperty | n/a | CanonicalHttp* | PASS |
| C06 | Callback | Outbox/reconciliation | callback/** | processors | JPA | suite | PASS |
| C07 | Integrity | HMAC/replay/fingerprint | security/integrity | IntegritySecurityConfig | replay JPA | MessageIntegrity* | PASS |
| C08 | Control Plane | Lifecycle/snapshot/fixation | governance/** | CONTROL_PLANE flag | V20260821h/i | Historical* | PASS |
| C09 | 013 | Signal Definition + ingress | ExternalSignal* | durable flag | inbox | SignalIngress* | PASS |
| C10 | 014 | Token opaco | continuation/* | token flags | wait fingerprint | ContinuationToken* / DurableTokenLookupE2E | PASS |
| C11 | 014 | Envelope AES-GCM | dataprotection + protected | protection flag | tb_protected_signal_envelope | ProtectedPayload* / RoundTrip | PASS |
| C12 | 014→Consol | DP Profile no snapshot | DATA_PROTECTION_PROFILE + V2 | catalogs | snapshot payload | DataProtectionSnapshotV2CodecTest | FIXED_IN_CONSOLIDATION |
| C13 | 014→Consol | HTTP durable sem resume | ExternalSignalHttpHandlerConfig | signal-http+durable | — | DurableHttpRoutingStrategyTest | FIXED_IN_CONSOLIDATION |
| C14 | Consol | Flags fail-closed | DataProtectionConfig | startup | — | DurableFlagMatrixTest | FIXED_IN_CONSOLIDATION |
| C16 | Consol | E2E JPA H2 fingerprint+ciphertext | ConsolidationJpaProtectedEnvelopeE2ETest | DataJpaTest | JPA entities | ConsolidationJpaProtectedEnvelopeE2ETest | FIXED_IN_CONSOLIDATION |
| C17 | Consol | E2E pipeline Snapshot V2→token→AES | ConsolidationDurablePipelineE2ETest | catalogs | encode/decode | ConsolidationDurablePipelineE2ETest | FIXED_IN_CONSOLIDATION |
| X01 | Fora | KMS/Vault/HSM real | — | — | — | — | BLOCKED_EXTERNAL |
| X02 | Fora | IdP/OAuth/mTLS real | — | — | — | — | BLOCKED_EXTERNAL |
| X03 | Fora | Broker/legado real | — | — | — | — | BLOCKED_EXTERNAL |
| X04 | Fora | Scheduler distribuído | — | — | — | — | BLOCKED_EXTERNAL |
| X05 | Fora | Token reissue externo | — | — | — | — | BLOCKED_EXTERNAL |
| X06 | Fora | Migração endpoint legado | ProductOrchestratorController | intacto | — | CanonicalHttp* legacy | NOT_APPLICABLE_WITH_EVIDENCE |

## Snapshot V1/V2

- V1: sem `dataProtectionProfiles` (ou vazio); schema `GOVERNANCE_SNAPSHOT_V1`; digest sem `;dp=`.
- V2: com DP profiles; schema `GOVERNANCE_SNAPSHOT_V2`; digest inclui `;dp=N`.
- Decode aceita ambos; schema desconhecido falha fechado.

## HTTP durable

```text
signal-http=false → endpoint ausente
signal-http=true + durable=false → inline ExternalSignalApplicationPort
signal-http=true + durable=true → ExternalSignalIngressUseCase (sem resume/processor)
```

Startup rejeita durable sem token + protection + key provider.

## Stores / migrations

Migrations `V20260821` … `V20260821k` alinhadas a `database/init.sql` (inclui fingerprint + `tb_protected_signal_envelope`).

## Fora de escopo legítimo

KMS/Vault/HSM, OAuth/OIDC/mTLS/IdP, bindings físicos, scheduler/worker distribuído, UI/admin API, token reissue, re-encryption/physical delete amplo, migração do endpoint legado.
