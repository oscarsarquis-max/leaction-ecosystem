# Piloto no domínio principal — 2026-08-04

Ativação controlada de `qmind.com.br` no **mesmo** Lightsail da homolog (sem ALB, ECS ou novos serviços pagos). Observação 7d continua em paralelo.

## Mapa DNS / HTTPS

| Host | Papel | Destino |
|---|---|---|
| `https://qmind.com.br` | App piloto | A → `3.20.155.196` + Caddy LE |
| `https://www.qmind.com.br` | Redirect 301 → apex | A → mesmo IP |
| `https://api.qmind.com.br` | API piloto | A → mesmo IP |
| `*.homolog.qmind.com.br` | Testes exclusivos | inalterado |

## O que mudou

- Route53: registros A apex / www / api piloto
- Cognito: callbacks/logout `https://qmind.com.br/...` (+ homolog mantido); `allow_admin_create_user_only = true` (convidados)
- Caddy: multi-host (homolog + piloto + www redirect)
- Compose: `web` (piloto) + `web_homolog` (testes); API/worker/DB compartilhados
- API: `CORS_ORIGINS` = `https://qmind.com.br`, `https://www.qmind.com.br`, `https://app.homolog.qmind.com.br` (Bearer; sem cookies de sessão API)
- Frontend piloto build: `VITE_API_BASE_URL=https://api.qmind.com.br`

## Evidências E2E (domínio principal)

| Teste | Artefato | Resultado |
|---|---|---|
| Cognito login/logout/API | `PILOT_COGNITO_E2E_evidence.json` | **PASS** |
| Isolamento + evidência S3 | `PILOT_ISOLATION_S3_evidence.json` | **PASS** |
| Worker PDF → S3 | `PILOT_WORKER_PDF_evidence.json` | **PASS** |
| CORS preflight | `Access-Control-Allow-Origin: https://qmind.com.br` | **PASS** |
| www → apex | HTTP 301 | **PASS** |

## Restrições do piloto

- Apenas usuários convidados (Cognito admin create)
- Orgs fictícias / dados não sensíveis
- Homolog permanece para testes; não misturar com piloto de usuário final
- Produção ampla **não** autorizada; observação 7d não bloqueia este incremento

## Publish

```powershell
.\infra\scripts\publish-pilot-lightsail.ps1
```
