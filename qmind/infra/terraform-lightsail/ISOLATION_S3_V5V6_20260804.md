# Isolamento + S3 — evidência (gate 011 V5/V6)

| Campo | Valor |
|---|---|
| Resultado | **PASS** |
| Horário (UTC) | ver `ISOLATION_S3_V5V6_evidence.json` → `finished_at` |
| Git | `d61e463` (+ patch `storage/s3.py` regional endpoint implantado) |
| Imagens | `qmind-api:mvp-fullstack-v0` / `qmind-web:mvp-fullstack-v0` |
| SSH ao final | **fechado** |

JSON: `ISOLATION_S3_V5V6_evidence.json` (sem tokens/URLs assinadas/senhas).

## V5 — Isolamento multiempresa

| Check | Resultado |
|---|---|
| Duas orgs + dois usuários Cognito distintos | PASS |
| List assessments isolado | PASS |
| GET assessment cross-org → 404 | PASS |
| `X-Organization-Id` de outra org sem membership → 403 | PASS |
| Troca de contexto / re-list sem vazamento | PASS |

## V6 — S3 evidências reais

| Check | Resultado |
|---|---|
| Authorize upload (presigned, host regional) | PASS |
| PUT objeto | PASS |
| Receive → hash sha256 + size + type | PASS |
| security_pass → approved | PASS |
| Download URL + bytes | PASS |
| Cross-org get/download → 404 sem hash/URL | PASS |
| Receive com size/type mismatch → 422 | PASS |

## Fix implantado

Presigned URLs geradas com endpoint regional `s3.{region}.amazonaws.com` (evita HTTP 307 TemporaryRedirect do host global).
