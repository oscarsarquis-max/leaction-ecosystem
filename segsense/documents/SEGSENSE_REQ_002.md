# SEGSENSE_REQ_002 — O que a Spider precisa publicar para desbloquear o PRM_011

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_REQ_002 |
| Título | Condições objetivas para o contrato externo Satellite → Spider |
| Categoria | REQ — requisitos de fronteira |
| Versão | 1.0 |
| Status | Parcialmente satisfeito por SPIDER-SAT-003 (DEMO ONLY); preview/IdP/Data Plane ausentes |
| Data | 12/09/2026 |
| Dependências | SEGSENSE_INT_001; SEGSENSE_ADR_003 |

Este documento **não** redige o contrato em nome da Spider. Lista lacunas que impedem a **integração HTTP real com a Spider**.

**Nota de sequência (12/09/2026):** o identificador `SEGSENSE_PRM_011` foi reprogramado para a âncora visual comercial e o backoffice editorial. As condições abaixo **não** foram satisfeitas. A integração Spider permanece **adiada**, não realizada. As menções a “desbloquear o PRM_011” neste documento referem-se àquele trabalho original de integração.

## Lista

1. **Identidade e registro** — como um satélite (`applicationId`) se registra; identificador estável; ciclo de vida.
2. **Autenticação do canal** — mecanismo (OIDC/mTLS/outro), issuer, JWKS, audiência, rotação de segredo. Sem isso o SegSense não pode autenticar-se.
3. **Autenticação do ator** — se o contrato exige usuário autenticado, o vínculo com IdP; se permite ator anônimo, declaração explícita (a instância SegSense é anônima).
4. **Catálogo de solicitações permitidas** — o que um satélite de seguros pode pedir, sem o satélite escolher capability, route, adapter ou executor.
5. **Schema de entrada versionado** — JSON Schema (ou equivalente) **público**, `$id` estável, semântica do objetivo, `additionalProperties` definido.
6. **Contexto e origem** — como transportar contexto de publicador versus informação fornecida pelo usuário; constraints; referências; canal.
7. **Correlação** — mapeamento declarado entre correlação local do satélite e `requestId` / `decisionId` / `planId` / `executionId` / `interactionId` **sem** o satélite fabricar IDs da plataforma.
8. **Preview sem execução** — endpoint, autenticação, exemplo válido, erros.
9. **Confirmação** — como a confirmação se liga ao preview (hash, identificador, prazo).
10. **Submissão e idempotência** — header/campo, TTL, comportamento de replay, o que acontece se a resposta inicial se perder.
11. **Assincronia** — consulta de estado e/ou callback; autenticação do callback; timeouts.
12. **Erros** — códigos públicos, indisponibilidade, retryability; não apenas o schema interno `CanonicalError`.
13. **Transporte e trust** — TLS, pinning/CA, origem permitida, segredos, retenção.
14. **Minimização** — quais campos consentidos podem cruzar a fronteira; proibição de PII não autorizada; retenção.
15. **Compatibilidade** — política de versão e depreciação.
16. **Testes e exemplos oficiais** — fixtures e testes de contrato publicados, contra os quais o SegSense possa validar um mapper **sem inventar payloads**.

Enquanto qualquer um dos itens 1–12 e 16 estiver `ABSENT`, o PRM_011 permanece bloqueado. Itens 13–15 devem estar definidos antes de tráfego real.

## Fora desta lista

O SegSense não pede que a Spider aceite a cópia `PROPOSED` em `documents/references/SPIDER-ARCH-017.md`. Não trata Contextual Link nem SpiderBank como esse contrato.

## Addendum SPIDER-SAT-003 (13/09/2026)

A Spider publicou schema, endpoint, identidade de satélite, autenticação local (identidade ≠ segredo), purpose, provenance, erros canônicos, idempotência e testes de contrato para EXPERIENCE em `local-demo`. Isso **não** satisfaz preview sem execução, confirmação, IdP, callback, TLS de produção nem Data Plane. O status deste REQ passa a **parcialmente satisfeito**. CAP-021 e CTX-004 não foram iniciados.
