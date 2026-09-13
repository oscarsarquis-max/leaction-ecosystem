# SEGSENSE_SEC_003 — Ameaças da instância contextual e da manifestação

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_SEC_003 |
| Título | Threat model da instância e do aviso de finalidade |
| Categoria | SEC |
| Versão | 1.1 |
| Status | Vigente nesta etapa |
| Data | 12/09/2026 |
| Dependências | SEGSENSE_SEC_002 |

## 1. Segredos

| Segredo | Tratamento |
|---|---|
| Token do link | Já: digest SHA-256; URL pública; redigido em logs de path |
| Credencial da instância | CSPRNG; uma vez na criação 201; **nunca** cache JVM/Redis; digest no DB; header dedicado; comparação `MessageDigest.isEqual` |

UUID/JWT **não** são o segredo da instância.

## 2. Autorização das mutações públicas

Toda mutação exige: token do link válido + credencial da instância + escopo + estado + expiração + `expectedVersion`.

CSRF global **não** foi desabilitado além do já existente `ignoringRequestMatchers("/api/**")`. Mutações públicas adicionam checagem de `Origin` (se presente, deve igualar a origem configurada) e rejeição de `Sec-Fetch-Site: cross-site`. Cabeçalhos ausentes são permitidos para testes servidor-a-servidor. CORS **não** é autorização.

## 3. CORS

Origem única `SEGSENSE_FRONTEND_ORIGIN`. Métodos: GET, POST, PUT, PATCH, OPTIONS. Headers extras só para essa origem: `X-SegSense-Instance-Credential`, `Idempotency-Key`. Sem `*`. Sem credentials.

## 4. Superfície permitAll

Somente os verbos e caminhos listados em API_006. O restante permanece `denyAll`.

## 5. O que esta etapa não afirma

Não há identidade da pessoa, autenticação de satélite, Guard, Policy, consentimento jurídico, compartilhamento externo nem trilha com IP/UA/fingerprint.
