/**
 * SPIDER-PROMPT-001 — Fundação dos Contratos Canônicos
 *
 * ## Packages adicionados
 * - `canonical.contract|error|validation|versioning`
 * - `execution.application|domain|port`
 * - `integration.port|mock|mapping`
 * - `evidence.reference`, `legacybaseline` (marcador de transição)
 *
 * ## Contratos
 * - `CanonicalExecutionRequest` / `CanonicalExecutionResult` / `CanonicalError`
 * - Schemas Draft 2020-12 em `classpath:contracts/canonical/1.0/`
 * - Porta `UniversalAdapterPort` + `MockUniversalAdapter`
 *
 * ## Compatibilidade
 * `POST /v1/products/orchestrate` permanece. O controller delega a
 * `OrchestrationCompatibilityService`, que valida o envelope canônico e
 * encaminha ao `OrchestrationService` (legacy baseline) sem duplicar efeito.
 *
 * ## Mock Adapter
 * Habilitado por `spider.adapter.mock.enabled=true` (default).
 * Cenário via `payload.canonicalData.mockScenario`: SUCCESS, TECHNICAL_FAILURE,
 * BUSINESS_NEGATIVE, TIMEOUT, INVALID_RESPONSE, UNKNOWN.
 *
 * ## Testes
 * ```powershell
 * cd C:\Projetos\spider\backend
 * ..\.tools\apache-maven-3.9.16\bin\mvn.cmd test
 * ```
 *
 * ## Limitações deste incremento
 * - Sem Execution Plan persistido / máquina de estados
 * - Sem novo endpoint público canônico
 * - Sem Control Plane / schema registry / mensageria
 * - Sem conexão a legado real
 * - Validação canônica ainda não rejeita HTTP do baseline (somente observa)
 *
 * ## Adiado
 * Migração completa do fluxo de orquestração para Engine canônica;
 * publicação de rotas; persistência de evidências; autenticação corporativa.
 */
