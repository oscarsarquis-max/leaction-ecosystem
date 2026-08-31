# Handoff — CURSOR-028-RELEASE (demo consolidada)

## Escopo

- CURSOR-028-C Produto · 028-D Entrada fiscal · Fluxo · Gigio · mobile/tablet · CMS `/entrar`
- Action Hub: keys aditivas `panne-demo` / `panne` apenas
- Panne: ambiente **demo** · banco `panne_demo` · CMS ativo `panne-demo`
- **Produção congelada** · DB `panne` intacto · key `panne` preparatória (não usada pela demo) · sem force push · fiscal live=0

## Git

| Item | Valor |
|------|-------|
| Branch | `release/cursor-028-consolidate` → `main` |
| SHA release | `b852c35` (Hub CMS + Panne consolidado) |
| SHA fix runtime | `9274ba9` (`httpx` em deps de runtime) |
| Commits | `4dcc5cb` Hub keys · `b852c35` Panne · `9274ba9` httpx |

## Imagem / ECS

| Item | Valor |
|------|-------|
| Tag | `backend-028-release-9274ba9-202608311441` |
| Digest | `sha256:c2257a42b8284900f053ba3dded3dbee413614f40969e20f8901644eeb29e7c8` |
| Scan | COMPLETE · CRITICAL=0 · HIGH=0 |
| Task def | `panne-demo-api:6` |
| Env | `PANNE_ENV=demo` · DB `panne_demo` · `ACTION_HUB_API_URL=https://api.actionhub.com.br` · `PANNE_FISCAL_LIVE=0` · `PANNE_OCR_LIVE=0` |

## URLs

| Superfície | URL |
|------------|-----|
| Demo FE | https://demo.panne.ia.br |
| Demo API | https://api.demo.panne.ia.br |
| Login editorial | https://api.demo.panne.ia.br/api/v1/public/login-editorial → `source=hub` |
| Hub CMS `panne-demo` | https://api.actionhub.com.br/api/public/cms?config_key=panne-demo |

## Action Hub

- Gateway reiniciado com allowlist `panne-demo`/`panne` (PM2 `gateway-api`).
- FE admin Hub **não** rebuildado nesta passagem: disco EC2 6.7G esgotou no `next build` (ENOSPC). Limpeza liberou ~930M; gateway-only foi suficiente para CMS público.
- Regressão CMS: `default` / `inove4us` / `inove4us-school` / `panne-demo` → 200.
- Key `panne`: defaults preparatórios (não ativar produção Panne).

## Baseline DB

`documentacao/evidencias/cursor-028-release/`

- Head: `0022_fiscal_inbound` (pré = pós)
- Contagens: deltas **zero** (`panne-demo-counts-compare.json`)
- DB `panne`: intacto (sem schema migrado nesta pipeline)

## Rollback

| Camada | Como |
|--------|------|
| Hub gateway | revisão anterior do gateway + `pm2 restart gateway-api` |
| API | task/digest `sha256:52c0f7ca4e22…` (`deploy_demo_api_028d.py`) |
| FE | invalidação CF + bundle S3 anterior |
| CMS | fallback estático Panne; key `panne-demo` |
| Alembic | `0022` não reverter se íntegra |

## Evidências

`panne/documentacao/evidencias/cursor-028-release/` — builds, scan, deploys, snapshots, `EXTERNAL-VALIDATION.txt`.
