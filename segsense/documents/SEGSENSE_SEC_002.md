# SEGSENSE_SEC_002 — Threat model do link contextual

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_SEC_002 |
| Título | Ameaças, exposição, logs, headers e riscos residuais do link |
| Categoria | SEC — segurança |
| Versão | 1.1 |
| Status | Vigente nesta etapa |
| Data | 11/09/2026 |
| Dependências | SEGSENSE_SEC_001 v1.3; SEGSENSE_LNK_001; SEGSENSE_API_005 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 11/09/2026 | Token opaco, digest, URL configurada, logs, CORS e rate limit residual. |
| 1.1 | 11/09/2026 | HTTPS fail-closed: só `local`/`test` explícitos relaxam HTTP em loopback. |

## 1. Ameaças

| Ameaça | Mitigação |
|---|---|
| Contexto na query string | URL contém só token; bindings no servidor |
| Token previsível | CSPRNG 256 bits, Base64URL, sem UUID/JWT |
| Recuperação do segredo | Bruto só no 201; banco guarda SHA-256 |
| Enumeração por ID | Path público não usa UUID interno |
| Open redirect / callback | Sem `returnUrl` |
| Host header injection na URL | Base somente de `SEGSENSE_PUBLIC_BASE_URL` |
| Log leakage | MDC `sanitizedPath` redige o segmento; eventos sem token |
| Cache de intermediários | `no-store`, `no-cache`, `no-referrer`, `nosniff` |
| CORS amplo | Origem única; sem `*` |
| PII no binding | Mesma proibição NON_PERSONAL vigente |
| Mutação por GET | Resolução read-only |

## 2. Configuração

`SEGSENSE_PUBLIC_BASE_URL`: https obrigatório salvo profiles ativos **exclusivamente** `local` e/ou `test`. Ausência de profile, `default`, `prod`, desconhecido ou combinação com profile incompatível (`local,prod`) exigem HTTPS. HTTP relaxado só em loopback. Rejeita userinfo, fragment, query, path inesperado e host vazio; remove barra final.

O ambiente local declara `SPRING_PROFILES_ACTIVE=local` (`.env.example`) e `spring-boot.run.profiles=local` no Maven. O profile `local` não é gravado no artefato de produção.

TTL: padrão 30 dias, absoluto 90 dias, nunca além de `validUntil` da revisão.

## 3. Riscos residuais

- Rate limit de resolução pública depende de gateway; não há limiter distribuído no BFF.
- `tokenHint` (8 caracteres) é apoio administrativo, não o segredo.
- Sem IdP, rotas administrativas continuam 401 no runtime real.
- A página `/c/{token}` ainda não existe (PRM_008); o contrato JSON já é estável.
